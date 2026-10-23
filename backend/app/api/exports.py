import csv
import io
import json
import math
from fastapi import HTTPException
from fastapi.responses import Response


def safe_cell(value, timecode=False):
    text = str(value if value is not None else "")
    # Apostrophe preserves timecodes as text in spreadsheet import and neutralizes formulas.
    return "'" + text if timecode or text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else text


def srt_timestamp(seconds):
    ms = max(0, math.floor(float(seconds) * 1000 + 0.5))
    sec, millis = divmod(ms, 1000)
    minutes, sec = divmod(sec, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{sec:02},{millis:03}"


def export_project(project, format, media_id=None):
    if format == "json":
        content = json.dumps(project, ensure_ascii=False, indent=2)
        mime = "application/json"
    elif format == "txt":
        rows = [f"VideoScript AI Studio · {project['name']}", "Navigazione HTML5 approssimata. QC preliminare: non certifica conformità broadcast.", "", "ANNOTAZIONI"]
        rows += [f"{a['tc_in']} {a.get('tc_out') or ''} [{a['category']}] {a['description']}" for a in project["annotations"]]
        rows += ["", "TRASCRIZIONE (timestamp AI da verificare)"]
        rows += [f"{s['tc_in']} → {s['tc_out']} {s['text']}" for s in project["transcripts"]]
        rows += ["", "QC"] + [f"{q.get('tc_in') or 'Media'} [{q['status']}] {q['test']}: {q['description']} ({q.get('verification', 'Da verificare')})" for q in project["qc_results"]]
        content = "\n".join(rows)
        mime = "text/plain"
    elif format == "csv":
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerow(["type", "media_id", "tc_in", "tc_out", "start_frame", "end_frame", "category", "description", "origin", "verification"])
        for kind, key in (("annotation", "annotations"), ("transcript", "transcripts"), ("qc", "qc_results")):
            for item in project[key]:
                values = [kind, item["media_id"], item.get("tc_in"), item.get("tc_out"), item.get("start_frame"), item.get("end_frame"), item.get("category", item.get("test", "Dialogue")), item.get("description", item.get("text", "")), item.get("origin", kind), item.get("verification", "Da verificare")]
                writer.writerow([safe_cell(v, i in (2, 3) and v is not None) for i, v in enumerate(values)])
        content = "\ufeff" + buffer.getvalue()
        mime = "text/csv"
    elif format == "srt":
        segments = [s for s in project["transcripts"] if not media_id or s["media_id"] == media_id]
        if not segments:
            raise HTTPException(422, "Nessuna trascrizione con inizio e fine da esportare")
        if len({s["media_id"] for s in segments}) > 1:
            raise HTTPException(422, "Per SRT selezionare un solo media con media_id")
        segments.sort(key=lambda s: (s["start"], s["end"]))
        content = "\n\n".join(f"{i}\n{srt_timestamp(s['start'])} --> {srt_timestamp(s['end'])}\n{s['text'].replace(chr(13), '').replace(chr(10)+chr(10), chr(10))}" for i, s in enumerate(segments, 1)) + "\n"
        mime = "application/x-subrip"
    else:
        raise HTTPException(422, "Formato non supportato: txt, csv, json, srt")
    return Response(content=content.encode("utf-8"), media_type=mime, headers={"Content-Disposition": f'attachment; filename="videoscript-{project["id"]}.{format}"'})
