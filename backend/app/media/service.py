"""Local-only media probing and cancellable proxy creation."""
from fractions import Fraction
import json
import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

from app.core.config import CACHE_DIR
from app.media.timecode import nominal_fps, parse_timecode, format_timecode

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mxf", ".webm"}


def validate_media_path(value: str) -> Path:
    if not isinstance(value, str) or not value.strip() or "\x00" in value or "://" in value:
        raise ValueError("Indicare il percorso assoluto di un file video locale.")
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("Il percorso del video deve essere assoluto.")
    path = path.resolve(strict=False)
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError("Formato non supportato: selezionare MP4, MOV, MXF o WebM.")
    if not path.is_file() or not os.access(path, os.R_OK):
        raise ValueError("Il file video non esiste o non è leggibile. Ricollegare il media.")
    return path


def _fraction(value) -> Fraction | None:
    try:
        rate = Fraction(str(value))
        return rate if rate > 0 else None
    except (ValueError, ZeroDivisionError, TypeError):
        return None


def _number(value, default=None):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _integer(value, default=None):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def probe_media(path: Path) -> dict:
    path = validate_media_path(str(path))
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("FFprobe non installato. Installare FFmpeg e aggiungerlo al PATH.")
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-protocol_whitelist", "file,pipe", "-show_format", "-show_streams", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Analisi FFprobe interrotta: timeout di 30 secondi.") from None
    if result.returncode:
        raise ValueError("FFprobe non riesce a leggere il video: " + result.stderr.strip()[-1200:])
    try:
        raw = json.loads(result.stdout)
    except (ValueError, TypeError):
        raise ValueError("FFprobe ha restituito metadati non validi.") from None
    streams = raw.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")), None)
    if video is None:
        raise ValueError("Il file non contiene una traccia video utilizzabile.")
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    primary_audio = audio[0] if audio else {}
    fmt = raw.get("format", {})
    average = _fraction(video.get("avg_frame_rate"))
    base = _fraction(video.get("r_frame_rate"))
    rate = average or base
    if rate is None:
        raise ValueError("Frame rate non disponibile: il file non consente una base timecode affidabile.")
    nominal = nominal_fps(rate.numerator, rate.denominator)
    duration = _number(fmt.get("duration"), _number(video.get("duration"), 0))
    if not duration or duration <= 0:
        raise ValueError("Durata del file video non disponibile o non positiva.")
    original_tc = video.get("tags", {}).get("timecode") or fmt.get("tags", {}).get("timecode")
    if not original_tc:
        original_tc = next((s.get("tags", {}).get("timecode") for s in streams if s.get("tags", {}).get("timecode")), None)
    drop = bool(original_tc and ";" in original_tc)
    warnings = ["Navigazione HTML5 approssimata: la posizione non è garantita al singolo fotogramma."]
    start_tc = original_tc or "00:00:00:00"
    try:
        start_frame = parse_timecode(start_tc, rate.numerator, rate.denominator, drop)
        start_tc = format_timecode(start_frame, rate.numerator, rate.denominator, drop)
    except ValueError:
        warnings.append("Il timecode originale non è compatibile con il frame rate rilevato: impostare manualmente il TC iniziale.")
        drop = False
        start_tc = "00:00:00:00"
    variable = bool(average and base and average != base)
    if variable:
        warnings.append("Possibile frame rate variabile: si usa il frame rate medio; la corrispondenza frame-accurate non è garantita.")
    # Codec support varies between browsers: the player can request a proxy if decoding fails.
    playable = (
        path.suffix.lower() == ".mp4" and video.get("codec_name") == "h264"
        and (not audio or primary_audio.get("codec_name") in {"aac", "mp3"})
    ) or (
        path.suffix.lower() == ".webm" and video.get("codec_name") in {"vp8", "vp9", "av1"}
        and (not audio or primary_audio.get("codec_name") in {"opus", "vorbis"})
    )
    tracks = [{
        "index": s.get("index"), "codec": s.get("codec_name"), "codec_name": s.get("codec_name"),
        "sample_rate": _integer(s.get("sample_rate")), "channels": s.get("channels"),
        "channel_layout": s.get("channel_layout"), "language": s.get("tags", {}).get("language"),
    } for s in audio]
    return {
        "name": path.name, "path": str(path),
        "metadata": {
            "container": fmt.get("format_name"), "video_codec": video.get("codec_name"),
            "audio_codec": primary_audio.get("codec_name"), "width": video.get("width"), "height": video.get("height"),
            "bit_rate": _integer(fmt.get("bit_rate")), "sample_rate": _integer(primary_audio.get("sample_rate")),
            "channels": primary_audio.get("channels"), "audio_tracks": tracks,
            "pixel_format": video.get("pix_fmt"), "field_order": video.get("field_order"),
            "source_start_seconds": _number(fmt.get("start_time"), 0),
            "video_start_seconds": _number(video.get("start_time"), 0),
            "vfr_detection": "indicative_from_stream_metadata",
        },
        "fps_numerator": rate.numerator, "fps_denominator": rate.denominator, "nominal_fps": nominal,
        "drop_frame": drop, "original_timecode": original_tc, "start_timecode": start_tc,
        "media_duration": duration, "source_frame_index": 0, "variable_frame_rate": variable,
        "playback_supported": bool(playable), "proxy_path": None, "available": True, "warnings": warnings,
    }


def build_proxy(media: dict, ctx) -> dict:
    source = validate_media_path(media["path"])
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg non installato: impossibile generare il proxy.")
    destination = CACHE_DIR / "proxies"
    destination.mkdir(parents=True, exist_ok=True)
    unique = f"{media['id']}-{uuid4().hex}"
    partial = destination / f"{unique}.partial.mp4"
    output = destination / f"{unique}.mp4"
    args = [
        ffmpeg, "-hide_banner", "-nostdin", "-y", "-protocol_whitelist", "file,pipe", "-i", str(source),
        "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-threads", "2", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-fps_mode", "passthrough", "-movflags", "+faststart",
        "-progress", "pipe:1", "-nostats", str(partial),
    ]
    ctx.progress(1, "Generazione proxy H.264/AAC")
    try:
        ctx.run(args, duration=media["media_duration"])
        ctx.check_cancelled()
        proxy = probe_media(partial)
        ctx.check_cancelled()
        partial.replace(output)
        preserved = Fraction(media["fps_numerator"], media["fps_denominator"]) == Fraction(proxy["fps_numerator"], proxy["fps_denominator"])
        warnings = list(media.get("warnings", []))
        if not preserved:
            warnings.append("Il proxy ha un frame rate diverso dall'originale: corrispondenza al fotogramma non garantita.")
        if abs(proxy["media_duration"] - media["media_duration"]) > max(0.1, 2 * media["fps_denominator"] / media["fps_numerator"]):
            warnings.append("Il proxy ha una durata diversa dall'originale: verificare manualmente la sincronizzazione.")
        return {
            "proxy_path": str(output), "warnings": warnings,
            "proxy_mapping": {
                "source_media_id": media["id"], "source_start_seconds": 0, "proxy_start_seconds": 0,
                "time_scale": 1, "frame_rate_preserved": preserved, "frame_accurate": False,
                "source_fps_numerator": media["fps_numerator"], "source_fps_denominator": media["fps_denominator"],
                "proxy_fps_numerator": proxy["fps_numerator"], "proxy_fps_denominator": proxy["fps_denominator"],
                "source_duration": media["media_duration"], "proxy_duration": proxy["media_duration"],
                "note": "Mappatura temporale relativa 1:1; seek HTML5 approssimato, VFR non garantito al frame.",
            },
        }
    except BaseException:
        partial.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
        raise
