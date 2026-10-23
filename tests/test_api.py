"""Exercise the real local API against isolated databases and generated media.

The media are synthetic black/test-pattern pictures and silence/sine tones. No
user file or pretrained model is needed, and no inference result is fabricated.
"""
import csv
import hashlib
import io
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.database import store
from app.main import app
from app.media import service as media_service
from app.transcription import service as transcription_service


@pytest.fixture
def client(tmp_path, monkeypatch):
    data = tmp_path / "data"
    cache = data / "cache"
    cache.mkdir(parents=True)
    monkeypatch.setattr(store, "DB_PATH", data / "studio.sqlite3")
    monkeypatch.setattr(routes, "DATA_DIR", data)
    monkeypatch.setattr(media_service, "CACHE_DIR", cache)
    monkeypatch.setattr(transcription_service, "CACHE_DIR", cache)
    monkeypatch.setenv("VIDEOSCRIPT_WHISPER_MODEL", str(tmp_path / "no-model"))
    monkeypatch.delenv("VIDEOSCRIPT_OLLAMA_MODEL", raising=False)
    with TestClient(app, base_url="http://127.0.0.1") as session:
        yield session


def make_video(path, rate=25):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("Real FFmpeg/FFprobe required for audiovisual integration tests")
    subprocess.run([
        "ffmpeg", "-v", "error", "-nostdin", "-f", "lavfi", "-i",
        f"color=black:size=160x90:rate={rate}:duration=1", "-f", "lavfi", "-i",
        f"testsrc2=size=160x90:rate={rate}:duration=2", "-f", "lavfi", "-i",
        "anullsrc=channel_layout=mono:sample_rate=48000:duration=1",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=2",
        "-filter_complex_threads", "2", "-filter_complex",
        "[0:v][1:v]concat=n=2:v=1:a=0[v];[2:a][3:a]concat=n=2:v=0:a=1[a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-threads", "2",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-timecode", "00:10:00:00", str(path),
    ], capture_output=True, check=True, timeout=30)
    return path


@pytest.fixture
def media_path(tmp_path):
    return make_video(tmp_path / "source.mp4")


def create_project(client, name="Progetto di prova"):
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def import_media(client, project, path):
    response = client.post("/api/media/import", json={"project_id": project["id"], "path": str(path)})
    assert response.status_code == 201, response.text
    return response.json()


def wait_job(client, job_id, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200, response.text
        job = response.json()
        if job["status"] not in {"queued", "running"}:
            return job
        time.sleep(0.03)
    pytest.fail(f"Job {job_id} did not finish within {timeout}s: {job}")


def test_project_annotation_persistence_timecode_and_exports(client, media_path):
    original_hash = hashlib.sha256(media_path.read_bytes()).hexdigest()
    project = create_project(client, "Sessione città")
    media = import_media(client, project, media_path)
    assert media["import_mode"] == "local_reference"
    assert media["path"] == str(media_path)
    assert media["original_timecode"] == "00:10:00:00"
    metadata = client.get(f"/api/media/{media['id']}/metadata").json()
    assert metadata["metadata"]["width"] == 160
    assert metadata["metadata"]["height"] == 90
    assert metadata["metadata"]["video_codec"] == "h264"
    assert metadata["metadata"]["audio_codec"] == "aac"
    assert (metadata["fps_numerator"], metadata["fps_denominator"]) == (25, 1)
    assert metadata["available"] is True

    result = client.patch(f"/api/media/{media['id']}/timecode", json={"start_timecode": "01:00:00:00"})
    assert result.status_code == 200, result.text
    annotation = client.post(f"/api/projects/{project['id']}/annotations", json={
        "media_id": media["id"], "start_frame": 25, "end_frame": 50,
        "category": "Dubbing Note", "description": "Battuta d’apertura, verificare accento è.",
    })
    assert annotation.status_code == 201, annotation.text
    note = annotation.json()
    assert note["tc_in"] == "01:00:01:00" and note["tc_out"] == "01:00:02:00"
    assert note["origin"] == "manual" and note["verification"] == "Da verificare"
    assert note["created_at"] and note["updated_at"]
    seek = client.post(f"/api/media/{media['id']}/seek", json={"timecode": note["tc_in"]})
    assert seek.status_code == 200 and seek.json() == {"frame": 25, "seconds": 1.0}
    assert client.get(f"/api/media/{media['id']}/timecode?frame=25").json()["timecode"] == note["tc_in"]

    updated = client.patch(f"/api/annotations/{note['id']}", json={
        "description": "=formula non eseguibile; accento è, virgola e \"citazione\"", "verification": "Verificato", "end_frame": None,
    })
    assert updated.status_code == 200, updated.text
    assert updated.json()["tc_out"] is None
    duplicate = client.post(f"/api/projects/{project['id']}/annotations", json={
        k: updated.json()[k] for k in ("media_id", "start_frame", "end_frame", "category", "description", "origin", "verification")
    })
    assert duplicate.status_code == 201, duplicate.text
    assert duplicate.json()["id"] != note["id"]
    assert client.post(f"/api/projects/{project['id']}/save").status_code == 200
    reopened = client.get(f"/api/projects/{project['id']}").json()
    assert len(reopened["annotations"]) == 2
    assert reopened["annotations"][0]["description"] == updated.json()["description"]
    # A new connection reads committed data, rather than frontend-local state.
    assert store.get("annotation", note["id"])["verification"] == "Verificato"
    assert any(p["id"] == project["id"] for p in client.get("/api/projects").json())

    txt = client.get(f"/api/projects/{project['id']}/export?format=txt")
    assert txt.status_code == 200 and "01:00:01:00" in txt.text and "accento è" in txt.text
    exported = client.get(f"/api/projects/{project['id']}/export?format=json")
    assert exported.status_code == 200 and exported.json()["annotations"] == reopened["annotations"]
    csv_export = client.get(f"/api/projects/{project['id']}/export?format=csv")
    assert csv_export.status_code == 200 and csv_export.content.startswith(b"\xef\xbb\xbf")
    rows = list(csv.DictReader(io.StringIO(csv_export.content.decode("utf-8-sig"))))
    assert rows[0]["tc_in"] == "'01:00:01:00"
    assert rows[0]["description"] == "'" + updated.json()["description"]
    assert client.get(f"/api/projects/{project['id']}/export?format=srt").status_code == 422
    assert client.delete(f"/api/annotations/{duplicate.json()['id']}").json() == {"deleted": True}
    assert len(client.get(f"/api/projects/{project['id']}/annotations").json()) == 1
    assert hashlib.sha256(media_path.read_bytes()).hexdigest() == original_hash


def test_real_qc_review_link_proxy_and_range_stream(client, media_path):
    source = media_path.read_bytes()
    project = create_project(client)
    media = import_media(client, project, media_path)
    queued = client.post(f"/api/media/{media['id']}/qc", json={"preset": "hd25", "expected_duration": 3, "duration_tolerance": 0.2})
    assert queued.status_code == 202, queued.text
    job = wait_job(client, queued.json()["id"])
    assert job["status"] == "completed", job
    assert job["progress"] == 100 and job["result"]["count"] >= 5
    results = client.get(f"/api/projects/{project['id']}").json()["qc_results"]
    black = next(q for q in results if q["test"] == "Black detect" and q["start_frame"] is not None)
    silence = next(q for q in results if q["test"] == "Silence detect" and q["start_frame"] is not None)
    assert black["status"] == "WARNING" and silence["status"] == "WARNING"
    assert black["start_frame"] == 0 and 24 <= black["end_frame"] <= 26
    assert black["verification"] == "Da verificare" and black["measured"] and black["threshold"]
    assert next(q for q in results if q["test"] == "Media properties")["status"] == "FAIL"
    assert next(q for q in results if q["test"] == "Expected duration")["status"] == "PASS"
    review = client.patch(f"/api/qc/{black['id']}", json={"verification": "Respinto"})
    assert review.status_code == 200 and review.json()["verification"] == "Respinto"
    linked = client.post(f"/api/projects/{project['id']}/annotations", json={
        "media_id": media["id"], "start_frame": black["start_frame"], "end_frame": black["end_frame"],
        "category": "Video QC", "description": "Nero iniziale intenzionale", "origin": "qc", "qc_result_id": black["id"],
    })
    assert linked.status_code == 201 and linked.json()["qc_result_id"] == black["id"]
    assert client.post(f"/api/media/{media['id']}/seek", json={"timecode": black["tc_in"]}).json()["frame"] == 0

    proxy = client.post(f"/api/media/{media['id']}/proxy")
    assert proxy.status_code == 202, proxy.text
    completed = wait_job(client, proxy.json()["id"])
    assert completed["status"] == "completed", completed
    metadata = client.get(f"/api/media/{media['id']}/metadata").json()
    assert metadata["proxy_available"] is True
    assert metadata["proxy_mapping"]["source_media_id"] == media["id"]
    assert metadata["proxy_mapping"]["frame_rate_preserved"] is True
    assert metadata["proxy_mapping"]["frame_accurate"] is False
    stream = client.get(f"/api/media/{media['id']}/stream", headers={"Range": "bytes=0-63"})
    assert stream.status_code == 206, stream.text
    assert stream.headers["content-type"] == "video/mp4"
    assert stream.headers["content-range"].startswith("bytes 0-63/")
    assert stream.content == Path(metadata["proxy_path"]).read_bytes()[:64]
    assert media_path.read_bytes() == source


def test_assistant_consults_saved_notes_and_persists_chat(client, media_path):
    project = create_project(client)
    media = import_media(client, project, media_path)
    note = client.post(f"/api/projects/{project['id']}/annotations", json={
        "media_id": media["id"], "start_frame": 25, "description": "Nome proprio da pronunciare: Città", "category": "Dubbing Note",
    }).json()
    response = client.post("/api/assistant/query", json={
        "project_id": project["id"], "media_id": media["id"], "query": "Elenca le annotazioni degli ultimi 30 secondi", "position": 2,
    })
    assert response.status_code == 200, response.text
    assert note["description"] in response.json()["content"]
    assert note["tc_in"] in response.json()["content"]
    chat = client.get(f"/api/projects/{project['id']}").json()["chat"]
    assert [c["role"] for c in chat] == ["user", "assistant"]
    assert client.get("/api/health").json()["assistant"]["llm_available"] is False
    llm = client.post("/api/assistant/query", json={"project_id": project["id"], "query": "Riscrivi la nota", "mode": "llm"})
    assert llm.status_code == 422 and "Modello AI non configurato" in llm.text
    assert store.get("annotation", note["id"])["description"] == note["description"]


def test_curating_stored_transcript_srt_and_timecode_relabel(client, media_path):
    """Explicit fixture input tests curation/export, not speech recognition."""
    project = create_project(client)
    media = import_media(client, project, media_path)
    segment = {
        "id": "stored-transcript-fixture", "project_id": project["id"], "media_id": media["id"],
        "start": 1.04, "end": 2.08, "start_frame": 26, "end_frame": 52,
        "tc_in": "00:10:01:01", "tc_out": "00:10:02:02", "text": "Testo inserito come dato di test",
        "verification": "Da verificare", "origin": "ai", "uncertainty": [],
    }
    store.put("transcript", segment)
    response = client.patch(f"/api/transcripts/{segment['id']}", json={
        "text": "Trascrizione corretta dall’operatore.", "verification": "Verificato", "uncertainty": ["Voci sovrapposte"],
    })
    assert response.status_code == 200, response.text
    assert response.json()["verification"] == "Verificato"
    assert response.json()["uncertainty"] == ["Voci sovrapposte"]
    annotation = client.post(f"/api/transcripts/{segment['id']}/annotation")
    assert annotation.status_code == 201, annotation.text
    assert annotation.json()["description"] == response.json()["text"]
    assert annotation.json()["origin"] == "transcript" and annotation.json()["start_frame"] == 26

    relabel = client.patch(f"/api/media/{media['id']}/timecode", json={"start_timecode": "01:00:00:00"})
    assert relabel.status_code == 200, relabel.text
    reopened = client.get(f"/api/projects/{project['id']}").json()
    assert reopened["media"][0]["original_timecode"] == "00:10:00:00"
    for item in (reopened["transcripts"][0], reopened["annotations"][0]):
        assert item["tc_in"] == "01:00:01:01" and item["tc_out"] == "01:00:02:02"
        assert item["start_frame"] == 26 and item["end_frame"] == 52
    srt = client.get(f"/api/projects/{project['id']}/export?format=srt&media_id={media['id']}")
    assert srt.status_code == 200, srt.text
    assert "1\n00:00:01,040 --> 00:00:02,080\nTrascrizione corretta dall’operatore." in srt.text
    consult = client.post("/api/assistant/query", json={
        "project_id": project["id"], "media_id": media["id"], "query": "Mostrami cosa viene detto in questa scena", "position": 0,
    })
    assert consult.status_code == 200
    assert response.json()["text"] in consult.json()["content"] and "01:00:01:01" in consult.json()["content"]


def test_qc_assistant_with_temporal_context_handles_project_level_results(client, media_path):
    project = create_project(client)
    media = import_media(client, project, media_path)
    queued = client.post(f"/api/media/{media['id']}/qc")
    assert queued.status_code == 202
    assert wait_job(client, queued.json()["id"])["status"] == "completed"
    response = client.post("/api/assistant/query", json={
        "project_id": project["id"], "media_id": media["id"], "query": "Quali problemi QC in questa scena?", "position": 0,
    })
    assert response.status_code == 200, response.text
    assert "Black detect" in response.json()["content"]


def test_missing_media_and_relink_preserve_annotations(client, media_path, tmp_path):
    project = create_project(client)
    media = import_media(client, project, media_path)
    note = client.post(f"/api/projects/{project['id']}/annotations", json={"media_id": media["id"], "start_frame": 25, "description": "Nota da conservare"}).json()
    relocated = tmp_path / "renamed.mp4"
    media_path.rename(relocated)
    reopened = client.get(f"/api/projects/{project['id']}")
    assert reopened.status_code == 200 and reopened.json()["media"][0]["available"] is False
    assert reopened.json()["annotations"][0]["id"] == note["id"]
    for endpoint in ("stream", "proxy", "qc", "transcribe"):
        response = client.get(f"/api/media/{media['id']}/{endpoint}") if endpoint == "stream" else client.post(f"/api/media/{media['id']}/{endpoint}")
        assert response.status_code == 409 and "mancante" in response.text.lower()
    relink = client.post(f"/api/media/{media['id']}/relink", json={"path": str(relocated)})
    assert relink.status_code == 200, relink.text
    assert relink.json()["available"] is True and relink.json()["path"] == str(relocated)
    assert client.get(f"/api/projects/{project['id']}/annotations").json()[0]["tc_in"] == note["tc_in"]
    wrong_rate = make_video(tmp_path / "different-rate.mp4", rate=30)
    rejected = client.post(f"/api/media/{media['id']}/relink", json={"path": str(wrong_rate)})
    assert rejected.status_code == 409 and "Frame rate o durata diversi" in rejected.text
    assert client.get(f"/api/media/{media['id']}/metadata").json()["path"] == str(relocated)


def test_missing_ffprobe_and_missing_whisper_are_actionable(client, media_path, monkeypatch):
    project = create_project(client)
    original_which = shutil.which
    with monkeypatch.context() as patch:
        patch.setattr(media_service.shutil, "which", lambda name: None if name == "ffprobe" else original_which(name))
        failed = client.post("/api/media/import", json={"project_id": project["id"], "path": str(media_path)})
        assert failed.status_code == 503 and "FFprobe non installato" in failed.text
    assert client.get(f"/api/projects/{project['id']}").json()["media"] == []
    media = import_media(client, project, media_path)
    job_response = client.post(f"/api/media/{media['id']}/transcribe")
    assert job_response.status_code == 202, job_response.text
    job = wait_job(client, job_response.json()["id"])
    assert job["status"] == "failed" and "Modello AI non configurato" in job["error"]
    assert client.get(f"/api/projects/{project['id']}").json()["transcripts"] == []
    assert client.post(f"/api/projects/{project['id']}/save").status_code == 200


@pytest.mark.parametrize("path", ["https://example.com/source.mp4", "file:///etc/passwd", "relative.mp4", "/etc/passwd", "/missing.mp4", "concat:/tmp/a.mp4|/tmp/b.mp4"])
def test_import_rejects_remote_protocols_and_invalid_paths(client, path):
    project = create_project(client)
    response = client.post("/api/media/import", json={"project_id": project["id"], "path": path})
    assert response.status_code == 422, response.text
    assert client.get(f"/api/projects/{project['id']}").json()["media"] == []


def test_host_origin_and_input_validation(client):
    assert client.get("/api/health", headers={"Host": "attacker.example"}).status_code == 400
    denied = client.post("/api/projects", headers={"Origin": "https://attacker.example"}, json={"name": "Forbidden"})
    assert denied.status_code == 403
    assert client.get("/api/projects").json() == []
    assert client.get("/api/health", headers={"Origin": "null"}).status_code == 403
    accepted = client.post("/api/projects", headers={"Origin": "http://127.0.0.1:5173"}, json={"name": "Allowed"})
    assert accepted.status_code == 201
    assert accepted.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert client.post("/api/projects", json={"name": "   "}).status_code == 422
    assert client.post("/api/projects", json={"name": "Test", "unexpected": "field"}).status_code == 422
    assert client.get("/api/nonexistent").status_code == 404


def test_cross_project_and_invalid_frame_edits_are_rejected(client, media_path):
    project = create_project(client)
    other = create_project(client, "Altro progetto")
    media = import_media(client, project, media_path)
    assert client.post(f"/api/projects/{other['id']}/annotations", json={"media_id": media["id"], "start_frame": 0}).status_code == 422
    for frames in ({"start_frame": -1}, {"start_frame": 50, "end_frame": 25}, {"start_frame": 1000}):
        assert client.post(f"/api/projects/{project['id']}/annotations", json={"media_id": media["id"], **frames}).status_code == 422
    assert client.post(f"/api/media/{media['id']}/seek", json={"timecode": "00:10:05:00"}).status_code == 422
    assert client.patch(f"/api/media/{media['id']}/timecode", json={"start_timecode": "00:00:00:25"}).status_code == 422
    assert client.post("/api/assistant/query", json={"project_id": other["id"], "media_id": media["id"], "query": "note"}).status_code == 422


def test_browser_file_selection_copies_only_into_managed_local_storage(client, media_path):
    original = media_path.read_bytes()
    project = create_project(client)
    response = client.post("/api/media/upload", data={"project_id": project["id"]}, files={"file": ("input.mp4", original, "video/mp4")})
    assert response.status_code == 201, response.text
    media = response.json()
    assert media["import_mode"] == "browser_copy" and media["name"] == "input.mp4"
    assert Path(media["path"]).parent == routes.DATA_DIR / "imports"
    assert Path(media["path"]).read_bytes() == original and media_path.read_bytes() == original
    invalid = client.post("/api/media/upload", data={"project_id": project["id"]}, files={"file": ("invalid.mp4", b"not media", "video/mp4")})
    assert invalid.status_code == 422
    assert list((routes.DATA_DIR / "imports").iterdir()) == [Path(media["path"])]
