"""Real FFmpeg filter smoke tests with generated, non-user media."""
import subprocess
import shutil
from pathlib import Path

import pytest

from app.qc.service import run_qc


class Context:
    def __init__(self):
        self.commands = []
        self.progress_events = []

    def check_cancelled(self):
        pass

    def progress(self, value, message):
        self.progress_events.append((value, message))

    def run(self, args, duration=None):
        self.commands.append(args)
        result = subprocess.run(args, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        return result.stderr


@pytest.fixture
def sample_factory(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg non installato: i test QC richiedono il motore reale")

    def generate(*, black=True, audio=True, silent=True):
        destination = tmp_path / f"sample-{black}-{audio}-{silent}.mp4"
        args = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "color=c=black:s=160x90:r=25:d=2" if black else "testsrc2=s=160x90:r=25:d=2"]
        if audio:
            args += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo" if silent else "sine=frequency=440:sample_rate=48000"]
        args += ["-t", "2", "-c:v", "libx264", "-threads", "2", "-pix_fmt", "yuv420p"]
        if audio:
            args += ["-c:a", "aac", "-shortest"]
        args += [str(destination)]
        subprocess.run(args, check=True, capture_output=True, timeout=30)
        return {"path": str(destination), "media_duration": 2.0,
                "fps_numerator": 25, "fps_denominator": 1,
                "metadata": {"width": 160, "height": 90, "video_codec": "h264",
                             "audio_codec": "aac" if audio else None,
                             "audio_tracks": [{"codec_name": "aac"}] if audio else []}}
    return generate


def test_actual_black_and_silence_are_review_warnings(sample_factory):
    media = sample_factory()
    ctx = Context()
    rows = run_qc(media, {}, ctx)
    black = [row for row in rows if row["test"] == "Black detect"]
    silence = [row for row in rows if row["test"] == "Silence detect"]
    assert black and all(row["status"] == "WARNING" for row in black)
    assert silence and all(row["status"] == "WARNING" for row in silence)
    assert black[0]["start_frame"] == 0
    assert black[0]["end_frame"] >= 48
    assert silence[0]["start_frame"] == 0
    assert any(row["test"] == "Sample peak" and row["status"] == "PASS" for row in rows)
    assert len(ctx.commands) == 2
    assert all("-protocol_whitelist" in command for command in ctx.commands)


def test_missing_audio_is_not_tested(sample_factory):
    ctx = Context()
    rows = run_qc(sample_factory(audio=False), {}, ctx)
    assert all(row["status"] == "NOT TESTED" for row in rows if row["test"] in {"Sample peak", "Silence detect"})
    assert len(ctx.commands) == 1


def test_clean_tone_and_picture_pass_filters(sample_factory):
    rows = run_qc(sample_factory(black=False, silent=False), {}, Context())
    assert all(row["status"] == "PASS" for row in rows if row["test"] in {"Black detect", "Silence detect", "Sample peak"})


def test_presets_duration_and_future_analyzers_are_honest(sample_factory):
    rows = run_qc(sample_factory(audio=False), {
        "preset": "hd25", "expected_duration": 10, "duration_tolerance": 1,
        "requested_advanced_tests": ["pse", "true_peak"]}, Context())
    assert next(row for row in rows if row["test"] == "Media properties")["status"] == "FAIL"
    assert next(row for row in rows if row["test"] == "Expected duration")["status"] == "FAIL"
    assert next(row for row in rows if row["test"] == "Flash / PSE")["status"] == "NOT TESTED"
    assert next(row for row in rows if row["test"] == "True Peak")["status"] == "NOT TESTED"


def test_rejects_non_finite_threshold_before_running():
    with pytest.raises(ValueError):
        run_qc({"media_duration": 2, "metadata": {}}, {"black_threshold": float("nan")}, Context())
