from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.database.store import init_db
from app.core.config import ROOT
from app.core.jobs import JobManager
from app.api.routes import router

ORIGINS = ["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:8000", "http://localhost:8000"]

@asynccontextmanager
async def lifespan(app):
    init_db()
    app.state.jobs = JobManager()
    app.state.jobs.recover()
    try:
        yield
    finally:
        app.state.jobs.shutdown()

app = FastAPI(title="VideoScript AI Studio", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Content-Type"])
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

@app.middleware("http")
async def local_origin(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin is not None and origin not in ORIGINS:
        return JSONResponse({"detail": "Origine non autorizzata: usare l'applicazione locale"}, status_code=403)
    return await call_next(request)

@app.exception_handler(ValueError)
async def value_error(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=422)

@app.exception_handler(RuntimeError)
async def runtime_error(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=503)

@app.exception_handler(FileNotFoundError)
async def missing_tool(request, exc):
    return JSONResponse({"detail": "Componente locale mancante: controllare FFmpeg/FFprobe e il percorso del media"}, status_code=503)

app.include_router(router)

# Production build can also be served by the same strictly local backend.
@app.get("/{path:path}")
def frontend(path: str):
    if path == "api" or path.startswith("api/"):
        return JSONResponse({"detail": "Endpoint non trovato"}, status_code=404)
    dist = ROOT / "frontend" / "dist"
    target = (dist / path).resolve()
    if not target.is_relative_to(dist.resolve()):
        return JSONResponse({"detail": "Percorso non valido"}, status_code=400)
    if target.is_file():
        return FileResponse(target)
    index = dist / "index.html"
    if index.is_file():
        return FileResponse(index)
    return JSONResponse({"detail": "Frontend non compilato: eseguire npm ci e npm run build in frontend"}, status_code=404)
