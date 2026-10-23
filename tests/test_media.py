import shutil
import subprocess
from pathlib import Path
import pytest
from app.media.service import probe_media, validate_media_path, build_proxy


@pytest.fixture
def sample(tmp_path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg/FFprobe not installed")
    path=tmp_path / "sample.mp4"
    subprocess.run(["ffmpeg","-v","error","-nostdin","-f","lavfi","-i","testsrc2=size=160x90:rate=25:duration=1","-f","lavfi","-i","sine=frequency=440:duration=1","-c:v","libx264","-threads","2","-pix_fmt","yuv420p","-c:a","aac","-timecode","01:00:00:00",str(path)],check=True)
    return path


def test_probe_real_mp4_and_timecode(sample):
    media=probe_media(sample)
    assert media["metadata"]["video_codec"] == "h264"
    assert media["metadata"]["audio_codec"] == "aac"
    assert media["metadata"]["width"] == 160
    assert media["fps_numerator"] == 25 and media["fps_denominator"] == 1
    assert media["start_timecode"] == "01:00:00:00"
    assert media["playback_supported"]
    assert 0.99 <= media["media_duration"] <= 1.1
    assert len(media["metadata"]["audio_tracks"]) == 1


def test_validate_path_rejects_remote_relative_missing_and_fake_video(tmp_path):
    for path in ["https://example.com/video.mp4", "relative.mp4",str(tmp_path/"missing.mp4"),str(tmp_path/"text.txt")]:
        with pytest.raises(ValueError): validate_media_path(path)
    fake=tmp_path/"fake.mp4"; fake.write_text("not a video")
    with pytest.raises(ValueError): probe_media(fake)


def test_missing_ffprobe_has_actionable_message(sample, monkeypatch):
    monkeypatch.setattr("app.media.service.shutil.which",lambda _: None)
    with pytest.raises(RuntimeError,match="FFprobe non installato"):
        probe_media(sample)


def test_proxy_real_media_preserves_source(sample, tmp_path, monkeypatch):
    monkeypatch.setattr("app.media.service.CACHE_DIR",tmp_path/"cache")
    original=sample.read_bytes()
    media={"id":"test-source",**probe_media(sample)}
    class Context:
        def progress(self,*args): pass
        def check_cancelled(self): pass
        def run(self,args,duration=None):
            result=subprocess.run(args,text=True,capture_output=True,check=True)
            return result.stderr
    proxy=build_proxy(media,Context())
    assert sample.read_bytes() == original
    assert Path(proxy["proxy_path"]).is_file()
    assert proxy["proxy_mapping"]["source_media_id"] == "test-source"
    assert proxy["proxy_mapping"]["frame_rate_preserved"]
    assert not proxy["proxy_mapping"]["frame_accurate"]
    assert probe_media(Path(proxy["proxy_path"]))["metadata"]["video_codec"] == "h264"
