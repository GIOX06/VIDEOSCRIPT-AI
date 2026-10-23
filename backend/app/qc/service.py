"""Preliminary local QC. Findings require human review, never broadcast certification."""
from __future__ import annotations

import math
import re
from fractions import Fraction
from typing import Protocol, Any


class QCContext(Protocol):
    def run(self, args: list[str], duration: float | None = None) -> str: ...
    def progress(self, value: float, message: str) -> None: ...
    def check_cancelled(self) -> None: ...


# Extension points; intentionally not reported as executed by the MVP.
FUTURE_ANALYZERS = {
    "ebu_r128": "Loudness EBU R128",
    "true_peak": "True Peak",
    "freeze": "Freeze detection avanzata",
    "pse": "Flash / PSE",
    "multichannel": "Analisi multicanale",
    "phase": "Correlazione di fase",
    "letterbox": "Letterbox / Pillarbox",
    "gop": "Vincoli codec e GOP",
}


def _row(test: str, status: str, description: str, *, start_frame=None,
         end_frame=None, measured=None, threshold=None) -> dict[str, Any]:
    return {"test": test, "status": status, "start_frame": start_frame,
            "end_frame": end_frame, "description": description,
            "measured": measured, "threshold": threshold}


def _frame(seconds: float, media: dict, *, end: bool = False) -> int:
    rate = Fraction(int(media["fps_numerator"]), int(media["fps_denominator"]))
    value = Fraction(str(max(0, seconds))) * rate
    # An event interval encloses its measured duration, without claiming frame precision.
    return math.ceil(value) if end else math.floor(value)


def _command(path: str) -> list[str]:
    return ["ffmpeg", "-hide_banner", "-nostdin", "-nostats", "-threads", "2",
            "-filter_threads", "2", "-filter_complex_threads", "2",
            "-progress", "pipe:1", "-protocol_whitelist", "file,pipe", "-i", path]


def _finite(value: Any, default: float, lo: float, hi: float) -> float:
    number = float(default if value is None else value)
    if not math.isfinite(number) or not lo <= number <= hi:
        raise ValueError(f"Soglia QC non valida: atteso valore tra {lo} e {hi}.")
    return number


def run_qc(media: dict, options: dict, ctx: QCContext) -> list[dict]:
    """Analyze the first video/audio streams, preserving the source file.

    Uses blackdetect, silencedetect and volumedetect. The latter measures decoded
    sample peak, not true peak. No speech, visual or compliance inference occurs.
    """
    ctx.check_cancelled()
    duration = float(media["media_duration"])
    metadata = media["metadata"]
    black_duration = _finite(options.get("black_duration"), 0.3, 0.001, 3600)
    black_threshold = _finite(options.get("black_threshold"), 0.1, 0, 1)
    silence_duration = _finite(options.get("silence_duration"), 0.5, 0.001, 3600)
    silence_db = _finite(options.get("silence_threshold_db"), -40, -120, 0)
    peak_db = _finite(options.get("peak_threshold_db"), -1, -120, 0)
    results: list[dict] = []
    ctx.progress(1, "Analisi degli intervalli neri")
    video_log = ctx.run(_command(media["path"]) + [
        "-map", "0:v:0", "-an", "-vf",
        f"blackdetect=d={black_duration}:pix_th={black_threshold}",
        "-threads", "2", "-f", "null", "-"], duration=duration)
    ctx.check_cancelled()
    black_events = re.findall(
        r"black_start:([\d.eE+-]+)\s+black_end:([\d.eE+-]+)\s+black_duration:([\d.eE+-]+)",
        video_log)
    black_ref = {"minimum_duration_seconds": black_duration,
                 "pixel_luminance_threshold": black_threshold,
                 "picture_black_ratio_threshold": 0.98}
    for start, end, measured in black_events:
        results.append(_row("Black detect", "WARNING",
            "Intervallo nero da verificare: potrebbe essere intenzionale. Limiti temporali stimati dal filtro FFmpeg.",
            start_frame=_frame(float(start), media), end_frame=_frame(float(end), media, end=True),
            measured={"duration_seconds": float(measured)}, threshold=black_ref))
    if not black_events:
        results.append(_row("Black detect", "PASS", "Nessun intervallo nero rilevato alle soglie selezionate.",
                            measured={"events": 0}, threshold=black_ref))

    ctx.check_cancelled()
    has_audio = bool(metadata.get("audio_tracks") or metadata.get("audio_codec"))
    if has_audio:
        ctx.progress(52, "Analisi silenzi e sample peak della prima traccia audio")
        audio_log = ctx.run(_command(media["path"]) + [
            "-map", "0:a:0", "-vn", "-af",
            f"silencedetect=n={silence_db}dB:d={silence_duration},volumedetect",
            "-threads", "2", "-f", "null", "-"], duration=duration)
        ctx.check_cancelled()
        # FFmpeg emits a final silence_end on EOF on supported versions. Retain
        # open events too, because a trailing interval still needs human review.
        silence_events: list[tuple[float, float]] = []
        pending_start = None
        for match in re.finditer(r"silence_(start|end):\s*([\d.eE+-]+)", audio_log):
            kind, value = match.group(1), float(match.group(2))
            if kind == "start":
                pending_start = max(0.0, value)
            elif pending_start is not None:
                silence_events.append((pending_start, min(duration, value)))
                pending_start = None
        if pending_start is not None:
            silence_events.append((pending_start, duration))
        silence_ref = {"minimum_duration_seconds": silence_duration, "noise_db": silence_db}
        for start, end in silence_events:
            if end < start:
                continue
            results.append(_row("Silence detect", "WARNING",
                "Silenzio sulla prima traccia audio da verificare: potrebbe essere intenzionale.",
                start_frame=_frame(start, media), end_frame=_frame(end, media, end=True),
                measured={"duration_seconds": round(end - start, 6)}, threshold=silence_ref))
        if not silence_events:
            results.append(_row("Silence detect", "PASS", "Nessun silenzio rilevato sulla prima traccia alle soglie selezionate.",
                                measured={"events": 0}, threshold=silence_ref))
        peak = re.search(r"max_volume:\s*(-?inf|[-+\d.]+)\s*dB", audio_log)
        if peak:
            raw_peak = float(peak.group(1))
            # JSON forbids infinities. A wholly silent track is represented explicitly.
            measured_peak = raw_peak if math.isfinite(raw_peak) else None
            results.append(_row("Sample peak", "WARNING" if raw_peak >= peak_db else "PASS",
                "Picco dei campioni decodificati sulla prima traccia; non è una misura True Peak."
                + (" Traccia completamente silenziosa." if not math.isfinite(raw_peak) else ""),
                measured={"sample_peak_dbfs": measured_peak, "silent": not math.isfinite(raw_peak)},
                threshold={"warning_at_dbfs": peak_db}))
        else:
            results.append(_row("Sample peak", "NOT TESTED", "FFmpeg non ha restituito una misura utilizzabile del sample peak."))
    else:
        results.extend([
            _row("Silence detect", "NOT TESTED", "Il file non contiene una traccia audio."),
            _row("Sample peak", "NOT TESTED", "Il file non contiene una traccia audio."),
        ])

    ctx.check_cancelled()
    ctx.progress(95, "Verifica delle proprietà tecniche")
    preset = options.get("preset", "source")
    if preset not in {"source", "hd25", "hd2997"}:
        raise ValueError("Preset QC non riconosciuto.")
    measured_properties = {"width": metadata.get("width"), "height": metadata.get("height"),
                           "fps": f"{media['fps_numerator']}/{media['fps_denominator']}",
                           "video_codec": metadata.get("video_codec"),
                           "audio_codec": metadata.get("audio_codec")}
    if preset == "source":
        results.append(_row("Media properties", "PASS", "Metadati letti. Nessun vincolo di consegna selezionato; non costituisce certificazione broadcast.",
                            measured=measured_properties, threshold={"preset": "source"}))
    else:
        expected_rate = Fraction(25, 1) if preset == "hd25" else Fraction(30000, 1001)
        actual_rate = Fraction(int(media["fps_numerator"]), int(media["fps_denominator"]))
        valid = metadata.get("width") == 1920 and metadata.get("height") == 1080 and actual_rate == expected_rate
        results.append(_row("Media properties", "PASS" if valid else "FAIL",
            "Verifica di risoluzione e frame rate del preset tecnico; non verifica tutti i requisiti broadcast.",
            measured=measured_properties, threshold={"width": 1920, "height": 1080, "fps": str(expected_rate), "preset": preset}))
    expected_duration = options.get("expected_duration")
    if expected_duration is None:
        results.append(_row("Expected duration", "NOT TESTED", "Durata attesa non impostata.", measured={"duration_seconds": duration}))
    else:
        expected = _finite(expected_duration, 0, 0, 60 * 60 * 24 * 7)
        tolerance = _finite(options.get("duration_tolerance"), 1, 0, 3600)
        valid_duration = abs(duration - expected) <= tolerance
        results.append(_row("Expected duration", "PASS" if valid_duration else "FAIL",
            "Confronto della durata misurata con la durata attesa e la tolleranza impostate.",
            measured={"duration_seconds": duration}, threshold={"expected_seconds": expected, "tolerance_seconds": tolerance}))
    for analyzer in options.get("requested_advanced_tests", []):
        if analyzer in FUTURE_ANALYZERS:
            results.append(_row(FUTURE_ANALYZERS[analyzer], "NOT TESTED", "Analizzatore previsto per una versione futura; controllo non eseguito."))
    ctx.check_cancelled()
    return results
