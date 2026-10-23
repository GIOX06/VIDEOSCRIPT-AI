"""Failure handling is tested without treating fabricated model output as inference."""
from pathlib import Path
import subprocess
import sys

import pytest

from app.transcription import service


class UnusedContext:
    def __getattr__(self, name):
        raise AssertionError(f"No decoding or model work should start: {name}")


def media_file(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"path validation fixture; never decoded")
    return {
        "path": str(source), "metadata": {"audio_codec": "aac"},
        "media_duration": 3.0, "fps_numerator": 25, "fps_denominator": 1,
    }


def local_model_files(tmp_path):
    path = tmp_path / "model"
    path.mkdir()
    for name in service.MODEL_FILES:
        (path / name).write_bytes(b"invalid model fixture; never loaded")
    return path


def test_status_requires_all_local_files(tmp_path, monkeypatch):
    path = tmp_path / "not-downloaded"
    monkeypatch.setenv("VIDEOSCRIPT_WHISPER_MODEL", str(path))
    state = service.status()
    assert state["model_configured"] is False
    assert state["model_path"] == str(path)
    path.mkdir()
    (path / "model.bin").write_bytes(b"partial")
    assert service.status()["model_configured"] is False


def test_missing_model_fails_without_decoding_or_download(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEOSCRIPT_WHISPER_MODEL", str(tmp_path / "missing"))
    with pytest.raises(ValueError, match="Modello AI non configurato"):
        service.transcribe(media_file(tmp_path), {}, UnusedContext())


def test_no_audio_is_reported_before_transcription(tmp_path):
    media = media_file(tmp_path)
    media["metadata"] = {"audio_tracks": []}
    with pytest.raises(ValueError, match="non contiene una traccia audio"):
        service.transcribe(media, {}, UnusedContext())


def test_missing_source_explains_relink(tmp_path):
    media = media_file(tmp_path)
    Path(media["path"]).unlink()
    with pytest.raises(ValueError, match="Ricollega il media"):
        service.transcribe(media, {}, UnusedContext())


def test_missing_engine_is_actionable(tmp_path, monkeypatch):
    model = local_model_files(tmp_path)
    monkeypatch.setattr(service.importlib.util, "find_spec", lambda _: None)
    with pytest.raises(ValueError, match="uv sync --extra ai --frozen"):
        service.transcribe(media_file(tmp_path), {"model_path": str(model)}, UnusedContext())


@pytest.mark.parametrize("start,end", [(-1, 2), (2, 1), (0, 4), (float("nan"), 2), (0, float("inf"))])
def test_invalid_interval_never_starts_inference(tmp_path, monkeypatch, start, end):
    model = local_model_files(tmp_path)
    monkeypatch.setattr(service.importlib.util, "find_spec", lambda _: object())
    with pytest.raises(ValueError, match="Intervallo audio non valido"):
        service.transcribe(media_file(tmp_path), {"model_path": str(model), "start": start, "end": end}, UnusedContext())


def test_downloader_help_has_no_network_side_effects():
    result = subprocess.run([sys.executable, "scripts/download_model.py", "--help"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert "--size" in result.stdout and "--revision" in result.stdout
