"""SMPTE frame labels, with rational rates and explicit drop-frame arithmetic.

Timecodes do not wrap at 24 hours: a long recording can display 24:00:00:00.
Frame indexes are integers. HTML5 seek accuracy is a separate player limitation.
"""
from fractions import Fraction
import math
import re


def _rate(num: int, den: int) -> tuple[Fraction, int]:
    if not isinstance(num, int) or not isinstance(den, int) or num <= 0 or den <= 0:
        raise ValueError("Il frame rate deve essere una frazione positiva di interi.")
    rate = Fraction(num, den)
    nominal = (rate.numerator * 2 + rate.denominator) // (2 * rate.denominator)
    if not 1 <= nominal <= 120:
        raise ValueError("Frame rate nominale non supportato (1–120 fps).")
    return rate, nominal


def nominal_fps(num: int, den: int) -> int:
    return _rate(num, den)[1]


def _drop_count(num: int, den: int, drop_frame: bool) -> int:
    rate, nominal = _rate(num, den)
    if not drop_frame:
        return 0
    if rate not in (Fraction(30000, 1001), Fraction(60000, 1001)):
        raise ValueError("Drop Frame disponibile soltanto per 30000/1001 e 60000/1001 fps.")
    return 2 if nominal == 30 else 4


def format_timecode(frame_index: int, num: int = 25, den: int = 1, drop_frame: bool = False) -> str:
    if not isinstance(frame_index, int) or frame_index < 0:
        raise ValueError("L'indice del fotogramma deve essere un intero non negativo.")
    nominal = nominal_fps(num, den)
    drop = _drop_count(num, den, drop_frame)
    label_frame = frame_index
    if drop:
        per_ten_minutes = nominal * 600 - drop * 9
        per_drop_minute = nominal * 60 - drop
        tens, remainder = divmod(frame_index, per_ten_minutes)
        label_frame += drop * 9 * tens
        if remainder >= drop:
            label_frame += drop * ((remainder - drop) // per_drop_minute)
    seconds, frames = divmod(label_frame, nominal)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    delimiter = ";" if drop_frame else ":"
    return f"{hours:02}:{minutes:02}:{seconds:02}{delimiter}{frames:02}"


def parse_timecode(tc: str, num: int = 25, den: int = 1, drop_frame: bool = False) -> int:
    nominal = nominal_fps(num, den)
    drop = _drop_count(num, den, drop_frame)
    match = re.fullmatch(r"(\d{2,}):(\d{2}):(\d{2})([:;])(\d{2,3})", str(tc).strip())
    if not match:
        raise ValueError("Timecode non valido: usare HH:MM:SS:FF (o HH:MM:SS;FF per DF).")
    hours, minutes, seconds = map(int, match.group(1, 2, 3))
    delimiter, frames = match.group(4), int(match.group(5))
    if minutes >= 60 or seconds >= 60 or frames >= nominal:
        raise ValueError("Minuti, secondi o numero del fotogramma fuori intervallo.")
    if delimiter == ";" and not drop_frame:
        raise ValueError("Il separatore ';' richiede la modalità Drop Frame.")
    total_minutes = hours * 60 + minutes
    if drop and minutes % 10 != 0 and seconds == 0 and frames < drop:
        raise ValueError("Questo numero di fotogramma viene saltato nella numerazione Drop Frame.")
    labels = ((hours * 3600 + minutes * 60 + seconds) * nominal) + frames
    return labels - drop * (total_minutes - total_minutes // 10)


def timestamp_to_frame(seconds: float | str | Fraction, num: int = 25, den: int = 1) -> int:
    rate, _ = _rate(num, den)
    try:
        timestamp = Fraction(str(seconds)) if not isinstance(seconds, Fraction) else seconds
    except (ValueError, ZeroDivisionError):
        raise ValueError("Timestamp non valido.") from None
    if timestamp < 0:
        raise ValueError("Il timestamp non può essere negativo.")
    # The containing frame, not milliseconds rounded to a nominal frame rate.
    return math.floor(timestamp * rate)


def frame_to_timestamp(frame_index: int, num: int = 25, den: int = 1) -> float:
    rate, _ = _rate(num, den)
    if not isinstance(frame_index, int) or frame_index < 0:
        raise ValueError("Indice del fotogramma non valido.")
    return float(Fraction(frame_index, 1) / rate)


def relative_frame_to_tc(media: dict, frame: int) -> str:
    num, den = media["fps_numerator"], media["fps_denominator"]
    drop = bool(media.get("drop_frame", False))
    start = parse_timecode(media.get("start_timecode", "00:00:00:00"), num, den, drop)
    return format_timecode(start + frame, num, den, drop)


def tc_to_relative_frame(media: dict, tc: str) -> int:
    num, den = media["fps_numerator"], media["fps_denominator"]
    drop = bool(media.get("drop_frame", False))
    start = parse_timecode(media.get("start_timecode", "00:00:00:00"), num, den, drop)
    result = parse_timecode(tc, num, den, drop) - start
    if result < 0:
        raise ValueError("Il timecode precede l'inizio del media.")
    return result
