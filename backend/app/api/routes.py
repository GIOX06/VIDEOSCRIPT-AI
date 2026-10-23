import math
import shutil
import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.exports import export_project
from app.assistant.service import answer, llm_status
from app.core.config import DATA_DIR
from app.core.jobs import now
from app.database import store
from app.media.service import ALLOWED_EXTENSIONS, build_proxy, probe_media, validate_media_path
from app.media.timecode import parse_timecode, relative_frame_to_tc, tc_to_relative_frame, timestamp_to_frame
from app.qc.service import run_qc
from app.transcription.service import status as transcription_status, transcribe

router = APIRouter(prefix="/api")
CATEGORIES = Literal["Dialogue", "Visual Description", "Sound Effect", "Music", "Audio QC", "Video QC", "Technical QC", "Dubbing Note", "General Note"]
VERIFICATION = Literal["Da verificare", "Verificato", "Confermato", "Respinto"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ProjectInput(Input):
    name: str = Field(min_length=1, max_length=160)


class ImportInput(Input):
    project_id: str
    path: str = Field(max_length=4096)


class RelinkInput(Input):
    path: str = Field(max_length=4096)


class TimecodeInput(Input):
    start_timecode: str = Field(max_length=24)
    drop_frame: bool = False


class SeekInput(Input):
    timecode: str = Field(max_length=24)


class AnnotationInput(Input):
    media_id: str
    start_frame: int = Field(ge=0)
    end_frame: int | None = Field(default=None, ge=0)
    category: CATEGORIES = "General Note"
    description: str = Field(default="", max_length=20000)
    origin: Literal["manual", "transcript", "qc", "assistant"] = "manual"
    verification: VERIFICATION = "Da verificare"
    qc_result_id: str | None = None


class AnnotationPatch(Input):
    media_id: str | None = None
    start_frame: int | None = Field(default=None, ge=0)
    end_frame: int | None = Field(default=None, ge=0)
    category: CATEGORIES | None = None
    description: str | None = Field(default=None, max_length=20000)
    verification: VERIFICATION | None = None
    qc_result_id: str | None = None


class TranscriptPatch(Input):
    text: str | None = Field(default=None, max_length=20000)
    verification: VERIFICATION | None = None
    uncertainty: list[Literal["Parlato incomprensibile", "Voci sovrapposte", "Segmento incerto"]] | None = None


class QCPatch(Input):
    verification: VERIFICATION


class QCInput(Input):
    black_duration: float = Field(default=0.3, ge=0.001, le=3600)
    black_threshold: float = Field(default=0.1, ge=0, le=1)
    silence_duration: float = Field(default=0.5, ge=0.001, le=3600)
    silence_threshold_db: float = Field(default=-40, ge=-120, le=0)
    peak_threshold_db: float = Field(default=-1, ge=-120, le=0)
    preset: Literal["source", "hd25", "hd2997"] = "source"
    expected_duration: float | None = Field(default=None, ge=0, le=604800)
    duration_tolerance: float = Field(default=1, ge=0, le=3600)


class TranscriptionInput(Input):
    language: str | None = Field(default=None, max_length=16)
    start: float = Field(default=0, ge=0)
    end: float | None = Field(default=None, gt=0)
    model_path: str | None = Field(default=None, max_length=4096)

    @model_validator(mode="after")
    def ordered(self):
        if self.end is not None and self.end <= self.start:
            raise ValueError("La fine deve seguire l'inizio")
        return self


class AssistantInput(Input):
    project_id: str
    media_id: str | None = None
    query: str = Field(min_length=1, max_length=8000)
    position: float = Field(default=0, ge=0)
    in_frame: int | None = Field(default=None, ge=0)
    out_frame: int | None = Field(default=None, ge=0)
    mode: Literal["base", "llm"] = "base"


def required(kind, record_id):
    value = store.get(kind, record_id)
    if not value:
        raise HTTPException(404, f"{kind}: elemento non trovato")
    return value


def touch(project_id):
    project = required("project", project_id)
    project["updated_at"] = now()
    store.put("project", project)


def media_view(media):
    return {**media, "available": Path(media["path"]).is_file(),
            "proxy_available": bool(media.get("proxy_path") and Path(media["proxy_path"]).is_file())}


def project_view(project_id):
    project = required("project", project_id)
    project["media"] = [media_view(m) for m in store.all_records("media", project_id)]
    for key, kind in (("annotations", "annotation"), ("transcripts", "transcript"), ("qc_results", "qc"), ("chat", "chat"), ("jobs", "job")):
        project[key] = store.all_records(kind, project_id)
    project["annotations"].sort(key=lambda a: (a["media_id"], a["start_frame"]))
    project["transcripts"].sort(key=lambda a: (a["media_id"], a["start"]))
    return project


def source_media(media_id):
    media = required("media", media_id)
    if not Path(media["path"]).is_file():
        raise HTTPException(409, "Media mancante: ricollegare il file sorgente")
    return media


def frame_bounds(media, start, end):
    last = math.ceil(media["media_duration"] * media["fps_numerator"] / media["fps_denominator"])
    if start > last or (end is not None and (end < start or end > last)):
        raise HTTPException(422, "Intervallo di frame non valido o fuori dalla durata del media")


def timed_record(media, value):
    start = value.get("start_frame")
    end = value.get("end_frame")
    value.update(media_id=media["id"], project_id=media["project_id"],
                 tc_in=relative_frame_to_tc(media, start) if start is not None else None,
                 tc_out=relative_frame_to_tc(media, end) if end is not None else None)
    return value


@router.get("/health")
def health():
    return {"status": "ok", "ffmpeg": bool(shutil.which("ffmpeg")), "ffprobe": bool(shutil.which("ffprobe")),
            "privacy": "local-only", "transcription": transcription_status(), "assistant": llm_status()}


@router.get("/projects")
def projects():
    return sorted(store.all_records("project"), key=lambda p: p["updated_at"], reverse=True)


@router.post("/projects", status_code=201)
def create_project(body: ProjectInput):
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "Inserire il nome del progetto")
    return store.put("project", dict(id=str(uuid.uuid4()), name=name, created_at=now(), updated_at=now(), settings={}))


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    return project_view(project_id)


@router.post("/projects/{project_id}/save")
def save_project(project_id: str):
    touch(project_id)
    with store.connection() as conn:
        conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
    return required("project", project_id)


def import_path(project_id, path, original_name=None):
    required("project", project_id)
    value = probe_media(validate_media_path(path))
    value.update(id=str(uuid.uuid4()), project_id=project_id, created_at=now())
    if original_name:
        value.update(name=original_name, import_mode="browser_copy")
    else:
        value["import_mode"] = "local_reference"
    store.put("media", value)
    touch(project_id)
    return media_view(value)


@router.post("/media/import", status_code=201)
def import_media(body: ImportInput):
    return import_path(body.project_id, body.path)


@router.post("/media/upload", status_code=201)
def upload_media(project_id: str = Form(...), file: UploadFile = File(...)):
    required("project", project_id)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(422, "Selezionare MP4, MOV, MXF o WebM")
    destination = DATA_DIR / "imports"
    destination.mkdir(exist_ok=True)
    path = destination / f"{uuid.uuid4()}{suffix}"
    limit = 20 * 1024 ** 3
    total = 0
    try:
        with path.open("xb") as out:
            while chunk := file.file.read(1024 * 1024):
                total += len(chunk)
                if total > limit or shutil.disk_usage(destination).free < 512 * 1024 ** 2:
                    raise HTTPException(413, "File oltre 20 GB o spazio disco insufficiente; usare il percorso locale senza copia")
                out.write(chunk)
        return import_path(project_id, str(path), Path(file.filename or "Video").name)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()


@router.get("/media/{media_id}/metadata")
def metadata(media_id: str):
    return media_view(required("media", media_id))


@router.get("/media/{media_id}/stream")
def stream(media_id: str):
    media = required("media", media_id)
    proxy = media.get("proxy_path")
    path = Path(proxy) if proxy and Path(proxy).is_file() else Path(media["path"])
    if not path.is_file():
        raise HTTPException(409, "Media mancante: ricollegare il file")
    return FileResponse(path, media_type="video/mp4" if path.suffix.lower() in (".mp4", ".mov") else "video/webm" if path.suffix.lower() == ".webm" else "application/octet-stream")


@router.post("/media/{media_id}/relink")
def relink(media_id: str, body: RelinkInput):
    media = required("media", media_id)
    if any(j["media_id"] == media_id and j["status"] in ("queued", "running") for j in store.all_records("job", media["project_id"])):
        raise HTTPException(409, "Annullare i processi sul media prima di ricollegarlo")
    new = probe_media(validate_media_path(body.path))
    if (new["fps_numerator"], new["fps_denominator"]) != (media["fps_numerator"], media["fps_denominator"]) or abs(new["media_duration"] - media["media_duration"]) > media["fps_denominator"] / media["fps_numerator"]:
        raise HTTPException(409, "Frame rate o durata diversi: per preservare le annotazioni importare questo file come nuovo media")
    media.update(path=new["path"], metadata=new["metadata"], available=True)
    media["warnings"] = list(dict.fromkeys(media["warnings"] + ["Media ricollegato: verificare che il contenuto corrisponda all'originale."]))
    store.put("media", media)
    touch(media["project_id"])
    return media_view(media)


@router.patch("/media/{media_id}/timecode")
def set_timecode(media_id: str, body: TimecodeInput):
    media = required("media", media_id)
    parse_timecode(body.start_timecode, media["fps_numerator"], media["fps_denominator"], body.drop_frame)
    media.update(start_timecode=body.start_timecode, drop_frame=body.drop_frame)
    # One transaction prevents mixed old/new labels if the process stops here.
    with store.connection() as conn:
        import json
        records = [("media", media)]
        for kind in ("annotation", "transcript", "qc"):
            records += [(kind, timed_record(media, item)) for item in store.all_records(kind, media["project_id"]) if item["media_id"] == media_id]
        for kind, value in records:
            conn.execute("UPDATE records SET data=? WHERE kind=? AND id=?", (json.dumps(value, ensure_ascii=False), kind, value["id"]))
    touch(media["project_id"])
    return media_view(media)


@router.get("/media/{media_id}/timecode")
def timecode(media_id: str, frame: int = 0):
    media = required("media", media_id)
    frame_bounds(media, frame, None)
    if frame < 0:
        raise HTTPException(422, "Il frame non può essere negativo")
    return {"frame": frame, "timecode": relative_frame_to_tc(media, frame)}


@router.post("/media/{media_id}/seek")
def seek(media_id: str, body: SeekInput):
    media = required("media", media_id)
    frame = tc_to_relative_frame(media, body.timecode)
    frame_bounds(media, frame, None)
    return {"frame": frame, "seconds": frame * media["fps_denominator"] / media["fps_numerator"]}


@router.get("/projects/{project_id}/annotations")
def annotations(project_id: str):
    required("project", project_id)
    return sorted(store.all_records("annotation", project_id), key=lambda a: a["start_frame"])


@router.post("/projects/{project_id}/annotations", status_code=201)
def add_annotation(project_id: str, body: AnnotationInput):
    required("project", project_id)
    media = required("media", body.media_id)
    if media["project_id"] != project_id:
        raise HTTPException(422, "Il media appartiene a un altro progetto")
    frame_bounds(media, body.start_frame, body.end_frame)
    if body.qc_result_id:
        qc = required("qc", body.qc_result_id)
        if qc["media_id"] != body.media_id:
            raise HTTPException(422, "Il rilievo QC appartiene a un altro media")
    value = timed_record(media, {**body.model_dump(), "id": str(uuid.uuid4()), "created_at": now(), "updated_at": now()})
    store.put("annotation", value)
    touch(project_id)
    return value


@router.patch("/annotations/{annotation_id}")
def edit_annotation(annotation_id: str, body: AnnotationPatch):
    value = required("annotation", annotation_id)
    updates = body.model_dump(exclude_unset=True)
    if any(v is None for k, v in updates.items() if k not in ("end_frame", "qc_result_id")):
        raise HTTPException(422, "Solo OUT può essere nullo")
    if "media_id" in updates and updates["media_id"] != value["media_id"]:
        raise HTTPException(422, "Non è possibile spostare un'annotazione su un altro media")
    if updates.get("qc_result_id"):
        qc_item = required("qc", updates["qc_result_id"])
        if qc_item["media_id"] != value["media_id"]:
            raise HTTPException(422, "Il rilievo QC appartiene a un altro media")
    value.update(updates, updated_at=now())
    media = required("media", value["media_id"])
    frame_bounds(media, value["start_frame"], value.get("end_frame"))
    store.put("annotation", timed_record(media, value))
    touch(value["project_id"])
    return value


@router.delete("/annotations/{annotation_id}")
def delete_annotation(annotation_id: str):
    value = required("annotation", annotation_id)
    store.remove("annotation", annotation_id)
    touch(value["project_id"])
    return {"deleted": True}


@router.patch("/transcripts/{transcript_id}")
def edit_transcript(transcript_id: str, body: TranscriptPatch):
    value = required("transcript", transcript_id)
    updates = body.model_dump(exclude_unset=True)
    if any(v is None for v in updates.values()):
        raise HTTPException(422, "Valore nullo non valido")
    value.update(updates, updated_at=now())
    store.put("transcript", value)
    touch(value["project_id"])
    return value


@router.post("/transcripts/{transcript_id}/annotation", status_code=201)
def transcript_annotation(transcript_id: str):
    item = required("transcript", transcript_id)
    return add_annotation(item["project_id"], AnnotationInput(media_id=item["media_id"], start_frame=item["start_frame"], end_frame=item["end_frame"], category="Dialogue", description=item["text"], origin="transcript"))


@router.patch("/qc/{qc_id}")
def review_qc(qc_id: str, body: QCPatch):
    item = required("qc", qc_id)
    item.update(verification=body.verification, updated_at=now())
    store.put("qc", item)
    touch(item["project_id"])
    return item


def queue(request, kind, media, options, worker, partial=None):
    try:
        return request.app.state.jobs.submit(kind, media, options, worker, partial)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/media/{media_id}/proxy", status_code=202)
def proxy(media_id: str, request: Request):
    media = source_media(media_id)
    def work(ctx):
        updates = build_proxy(media, ctx)
        current = required("media", media_id)
        current.update(updates)
        store.put("media", current)
        touch(media["project_id"])
        return {"media_id": media_id, "proxy_mapping": updates["proxy_mapping"]}
    return queue(request, "proxy", media, {}, work)


@router.post("/media/{media_id}/qc", status_code=202)
def qc(media_id: str, request: Request, body: QCInput = QCInput()):
    media = source_media(media_id)
    options = body.model_dump()
    def work(ctx):
        values = run_qc(media, options, ctx)
        ctx.check_cancelled()
        current_media = required("media", media_id)
        # Persist a whole run atomically; previous reviews remain intact.
        import json
        records = [timed_record(current_media, {**value, "id": str(uuid.uuid4()), "run_id": ctx.job["id"], "verification": "Da verificare", "created_at": now()}) for value in values]
        with store.connection() as conn:
            for value in records:
                conn.execute("INSERT INTO records(kind,id,project_id,data) VALUES(?,?,?,?)", ("qc", value["id"], media["project_id"], json.dumps(value, ensure_ascii=False)))
        touch(media["project_id"])
        return {"count": len(records)}
    return queue(request, "qc", media, options, work)


@router.post("/media/{media_id}/transcribe", status_code=202)
def transcription(media_id: str, request: Request, body: TranscriptionInput = TranscriptionInput()):
    media = source_media(media_id)
    if body.start >= media["media_duration"] or (body.end is not None and body.end > media["media_duration"] + 0.001):
        raise HTTPException(422, "Intervallo fuori dalla durata del media")
    def partial(kind, item):
        current_media = required("media", media_id)
        item = timed_record(current_media, {**item, "origin": "ai", "created_at": now()})
        store.put("transcript", item)
        touch(media["project_id"])
    def work(ctx):
        values = transcribe(media, body.model_dump(), ctx)
        return {"count": len(values), "message": "Timestamp AI da verificare"}
    return queue(request, "transcribe", media, body.model_dump(), work, partial)


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    return required("job", job_id)


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, request: Request):
    job = required("job", job_id)
    if job["status"] in ("queued", "running"):
        request.app.state.jobs.cancel(job_id)
    return required("job", job_id)


@router.post("/assistant/query")
def assistant(body: AssistantInput):
    project = project_view(body.project_id)
    if body.media_id and not any(m["id"] == body.media_id for m in project["media"]):
        raise HTTPException(422, "Media estraneo al progetto")
    if body.in_frame is not None and body.out_frame is not None and body.out_frame < body.in_frame:
        raise HTTPException(422, "OUT deve seguire IN")
    content = answer(project, body.query, body.media_id, body.position, body.in_frame, body.out_frame, body.mode)
    store.put("chat", {"id": str(uuid.uuid4()), "project_id": body.project_id, "role": "user", "content": body.query, "created_at": now()})
    response = dict(id=str(uuid.uuid4()), project_id=body.project_id, role="assistant", content=content, mode=body.mode, created_at=now())
    store.put("chat", response)
    touch(body.project_id)
    return response


@router.get("/projects/{project_id}/export")
def export(project_id: str, format: str = "json", media_id: str | None = None):
    return export_project(project_view(project_id), format, media_id)
