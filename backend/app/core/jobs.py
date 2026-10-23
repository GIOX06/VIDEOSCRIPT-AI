"""Bounded local worker queue with durable status and cooperative cancellation."""
import os
import signal
import subprocess
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from app.database import store


def now():
    return datetime.now(timezone.utc).isoformat()


class Cancelled(Exception):
    pass


class JobContext:
    def __init__(self, job, event, partial=None):
        self.job = job
        self.event = event
        self.on_partial = partial

    def check_cancelled(self):
        if self.event.is_set():
            raise Cancelled("Operazione annullata")

    def progress(self, value, message=""):
        self.check_cancelled()
        self.job.update(progress=max(self.job.get("progress", 0), min(99, float(value))), message=message)
        store.put("job", self.job)

    def partial(self, kind, data):
        self.check_cancelled()
        if self.on_partial:
            self.on_partial(kind, data)

    def run(self, args, duration=None):
        self.check_cancelled()
        command = [str(arg) for arg in args]
        if Path(command[0]).name.lower() in ("ffmpeg", "ffmpeg.exe"):
            if "-nostdin" not in command:
                command[1:1] = ["-nostdin"]
            if "-progress" not in command:
                command[1:1] = ["-progress", "pipe:1", "-stats_period", "0.5", "-nostats"]
        with tempfile.TemporaryDirectory(prefix="videoscript-process-") as directory:
            return self._run_logged(command, duration, Path(directory))

    def _run_logged(self, command, duration, directory):
        # Separate file descriptors keep progress reads from moving the child's
        # write offset, which would corrupt logs with a shared seekable handle.
        with (directory / "stdout").open("wb") as stdout, (directory / "stderr").open("w+b") as stderr, (directory / "stdout").open("rb") as progress_reader:
            proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                    start_new_session=(os.name != "nt"))
            started = time.monotonic()
            try:
                while proc.poll() is None:
                    self.check_cancelled()
                    if time.monotonic() - started > 4 * 3600:
                        raise RuntimeError("Tempo massimo del processo superato (4 ore)")
                    if duration and duration > 0:
                        data = progress_reader.read().decode("utf-8", "replace")
                        for line in data.splitlines():
                            if line.startswith("out_time_us="):
                                try:
                                    self.progress(min(95, int(line.split("=", 1)[1]) / 1_000_000 / duration * 95), "Elaborazione media locale")
                                except ValueError:
                                    pass
                    self.event.wait(0.1)
                self.check_cancelled()
            finally:
                if proc.poll() is None:
                    if os.name == "nt":
                        proc.terminate()
                    else:
                        os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        if os.name == "nt":
                            proc.kill()
                        else:
                            os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait(timeout=3)
            stderr.seek(0)
            output = stderr.read(16 * 1024 * 1024 + 1)
            if len(output) > 16 * 1024 * 1024:
                raise RuntimeError("Log di analisi troppo grande; analizzare un media più breve")
            text = output.decode("utf-8", "replace")
            if proc.returncode:
                raise RuntimeError(f"{Path(command[0]).name}: {text[-3000:]}")
            return text


class JobManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="videoscript")
        self.events = {}
        self.lock = threading.Lock()

    def recover(self):
        for job in store.all_records("job"):
            if job["status"] in ("queued", "running"):
                job.update(status="interrupted", message="Processo interrotto dal precedente arresto; può essere rilanciato", finished_at=now())
                store.put("job", job)

    def submit(self, kind, media, options, worker, partial=None):
        with self.lock:
            if len(self.events) >= 8:
                raise RuntimeError("Coda piena: attendere o annullare un processo")
            if any(j["media_id"] == media["id"] and j["kind"] == kind and j["status"] in ("queued", "running") for j in store.all_records("job")):
                raise RuntimeError("Questo processo è già in esecuzione sul media")
            job = dict(id=str(uuid.uuid4()), kind=kind, media_id=media["id"], project_id=media["project_id"],
                       options=options, status="queued", progress=0, message="In coda", error=None,
                       result=None, created_at=now(), finished_at=None)
            event = threading.Event()
            self.events[job["id"]] = event
            store.put("job", job)
        self.executor.submit(self._execute, job, event, worker, partial)
        return dict(job)

    def _execute(self, job, event, worker, partial):
        ctx = JobContext(job, event, partial)
        try:
            ctx.check_cancelled()
            job.update(status="running", message="Avviato")
            store.put("job", job)
            result = worker(ctx)
            ctx.check_cancelled()
            job.update(status="completed", progress=100, message="Completato", result=result)
        except Cancelled:
            job.update(status="cancelled", message="Annullato; i dati già salvati sono conservati")
        except Exception as exc:
            job.update(status="failed", message="Elaborazione non completata", error=str(exc))
        finally:
            job["finished_at"] = now()
            store.put("job", job)
            with self.lock:
                self.events.pop(job["id"], None)

    def cancel(self, job_id):
        with self.lock:
            event = self.events.get(job_id)
            if event:
                event.set()
        return bool(event)

    def shutdown(self):
        with self.lock:
            for event in self.events.values():
                event.set()
        self.executor.shutdown(wait=True, cancel_futures=False)
