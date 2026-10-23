"""Durable job state and cancellation of a real operating-system subprocess."""
import os
import sys
import time

import pytest

from app.core.jobs import JobManager
from app.database import store


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "jobs.sqlite3")
    store.init_db()
    return tmp_path


def wait_for(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(0.02)
    pytest.fail(f"Condition not met within {timeout}s")


def test_cancel_kills_actual_subprocess_and_preserves_saved_work(isolated_store):
    pidfile = isolated_store / "worker.pid"
    finished = isolated_store / "unexpected-finish.txt"
    note = {"id": "manual-note", "project_id": "project", "description": "Lavoro manuale da conservare"}
    store.put("annotation", note)
    manager = JobManager()
    try:
        def work(ctx):
            ctx.run([sys.executable, "-c",
                     "import os,pathlib,sys,time;pathlib.Path(sys.argv[1]).write_text(str(os.getpid()));time.sleep(30);pathlib.Path(sys.argv[2]).write_text('finished')",
                     str(pidfile), str(finished)])
            return {"should_not": "complete"}

        job = manager.submit("test-process", {"id": "media", "project_id": "project"}, {}, work)
        wait_for(pidfile.exists)
        process_id = int(pidfile.read_text())
        assert store.get("job", job["id"])["status"] == "running"
        started = time.monotonic()
        assert manager.cancel(job["id"]) is True
        terminal = wait_for(lambda: (value if (value := store.get("job", job["id"]))["status"] in {"cancelled", "failed", "completed"} else None))
        assert terminal["status"] == "cancelled", terminal
        assert terminal["result"] is None and terminal["finished_at"]
        assert time.monotonic() - started < 5
        assert not finished.exists()
        if os.name != "nt":
            with pytest.raises(ProcessLookupError):
                os.kill(process_id, 0)
        assert store.get("annotation", note["id"]) == note
    finally:
        manager.shutdown()


def test_startup_recovery_marks_only_unfinished_jobs_interrupted(isolated_store):
    note = {"id": "saved", "project_id": "p", "description": "Nota preesistente"}
    store.put("annotation", note)
    for status in ("queued", "running", "completed", "failed", "cancelled"):
        store.put("job", {"id": status, "project_id": "p", "status": status, "result": {"retained": True}})
    manager = JobManager()
    try:
        manager.recover()
        for status in ("queued", "running"):
            job = store.get("job", status)
            assert job["status"] == "interrupted" and job["finished_at"]
            assert "può essere rilanciato" in job["message"]
        for status in ("completed", "failed", "cancelled"):
            assert store.get("job", status)["status"] == status
        assert store.get("annotation", "saved") == note
    finally:
        manager.shutdown()
