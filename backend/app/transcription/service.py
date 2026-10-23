"""Opt-in speech recognition. Media and transcripts never leave this machine."""
from __future__ import annotations

import importlib.util
import math
import os
import tempfile
from pathlib import Path
from uuid import uuid4

from app.core.config import CACHE_DIR, DATA_DIR

MODEL_FILES = ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt")


def _model_path(value: str | None = None) -> Path:
    setting = value or os.environ.get("VIDEOSCRIPT_WHISPER_MODEL")
    return Path(setting).expanduser().resolve() if setting else DATA_DIR / "models" / "whisper-tiny"


def _model_ready(path: Path) -> bool:
    return path.is_dir() and all((path / name).is_file() and (path / name).stat().st_size > 0 for name in MODEL_FILES)


def status() -> dict:
    path = _model_path()
    return {
        "installed": importlib.util.find_spec("faster_whisper") is not None,
        "model_configured": _model_ready(path),
        "model_path": str(path),
    }


def transcribe(media: dict, options: dict, ctx) -> list[dict]:
    """Extract a selected interval, run a local CTranslate2 model, publish segments.

    Cancellation is cooperative between decoder segments; native model inference
    currently cannot be interrupted in the middle of one segment. No online model
    identifiers are accepted and every required tokenizer file must be local.
    """
    metadata = media.get("metadata", {})
    if not metadata.get("audio_codec") and not metadata.get("audio_tracks"):
        raise ValueError("Il media non contiene una traccia audio trascrivibile.")
    source = Path(media["path"])
    if not source.is_file():
        raise ValueError("File sorgente non disponibile. Ricollega il media prima di trascrivere.")
    model_path = _model_path(options.get("model_path"))
    if not _model_ready(model_path):
        raise ValueError(
            "Modello AI non configurato. Scarica esplicitamente un modello con "
            "python scripts/download_model.py e configura VIDEOSCRIPT_WHISPER_MODEL. "
            "La trascrizione non scarica modelli automaticamente."
        )
    if importlib.util.find_spec("faster_whisper") is None:
        raise ValueError("Motore faster-whisper non installato. Esegui uv sync --extra ai --frozen.")
    duration = float(media.get("media_duration", 0))
    start = float(options.get("start", 0) or 0)
    end = float(options["end"]) if options.get("end") is not None else duration
    if not all(math.isfinite(value) for value in (start, end, duration)) or not 0 <= start < end <= duration + 0.001:
        raise ValueError("Intervallo audio non valido: usa 0 ≤ inizio < fine ≤ durata del media.")
    language = options.get("language") or None
    if language is not None and (not isinstance(language, str) or len(language) > 16):
        raise ValueError("Codice lingua non valido.")

    from app.media.timecode import timestamp_to_frame
    try:
        from faster_whisper import WhisperModel
    except (ImportError, OSError) as exc:
        raise ValueError("Motore faster-whisper non caricabile. Verifica l’installazione delle dipendenze AI e delle librerie native.") from exc

    ctx.check_cancelled()
    ctx.progress(2, "Estrazione audio locale (mono PCM 16 kHz)")
    with tempfile.TemporaryDirectory(prefix="transcription-", dir=CACHE_DIR) as directory:
        audio = Path(directory) / "speech.wav"
        ctx.run([
            "ffmpeg", "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
            "-protocol_whitelist", "file,pipe", "-ss", str(start), "-i", str(source),
            "-t", str(end - start), "-vn", "-map", "0:a:0", "-ac", "1",
            "-ar", "16000", "-c:a", "pcm_s16le", str(audio),
        ])
        ctx.check_cancelled()
        ctx.progress(10, "Caricamento modello locale CPU / int8")
        model = WhisperModel(
            str(model_path), device="cpu", compute_type="int8", cpu_threads=2,
            num_workers=1, local_files_only=True,
        )
        segments, _info = model.transcribe(
            str(audio), language=language, beam_size=5, temperature=0,
            vad_filter=True, condition_on_previous_text=False, word_timestamps=False,
        )
        result: list[dict] = []
        for segment in segments:
            ctx.check_cancelled()
            text = segment.text.strip()
            if not text:
                continue
            uncertainty: list[str] = []
            no_speech = float(getattr(segment, "no_speech_prob", 0))
            avg_logprob = float(getattr(segment, "avg_logprob", 0))
            # Reject likely non-speech rather than inventing a silent dialogue.
            if no_speech >= 0.8 and avg_logprob < -0.5:
                continue
            if avg_logprob < -1 or no_speech > 0.5 or float(getattr(segment, "compression_ratio", 0)) > 2.4:
                uncertainty.append("Segmento incerto")
            segment_start = min(end, max(start, start + float(segment.start)))
            segment_end = min(end, max(segment_start, start + float(segment.end)))
            if segment_end <= segment_start:
                continue
            value = {
                "id": str(uuid4()), "start": segment_start, "end": segment_end,
                "text": text, "uncertainty": uncertainty, "verification": "Da verificare",
                "start_frame": timestamp_to_frame(segment_start, media["fps_numerator"], media["fps_denominator"]),
                "end_frame": timestamp_to_frame(segment_end, media["fps_numerator"], media["fps_denominator"]),
                "timing_note": "Timestamp AI approssimativi: verificare testo e sincronizzazione.",
            }
            result.append(value)
            ctx.partial("transcript", value)
            ctx.progress(min(99, 10 + 89 * (segment_end - start) / (end - start)), "Trascrizione locale: segmenti da verificare")
        ctx.check_cancelled()
        ctx.progress(99, "Trascrizione completata" if result else "Nessun parlato riconosciuto: nessun dialogo generato")
        return result
