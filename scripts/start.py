#!/usr/bin/env python3
"""Start the local development application; never install tools or upload media."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"
PORTS = (8000, 5173)


def prerequisites() -> tuple[Path, str]:
    python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        raise RuntimeError("Ambiente Python assente. Esegui prima lo script setup del tuo sistema.")
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js non trovato nel PATH. Installa Node.js 22.12 o una versione LTS successiva.")
    version = subprocess.check_output([node, "--version"], text=True, timeout=10).strip()
    parts = tuple(int(part) for part in version.lstrip("v").split(".")[:2])
    if parts < (22, 12):
        raise RuntimeError(f"Node.js {version} non supportato: serve almeno 22.12.")
    missing = [tool for tool in ("ffmpeg", "ffprobe") if not shutil.which(tool)]
    if missing:
        raise RuntimeError(f"Strumenti mancanti nel PATH: {', '.join(missing)}. Consulta README.md.")
    if not (ROOT / "frontend/node_modules/vite/bin/vite.js").is_file():
        raise RuntimeError("Dipendenze frontend assenti. Esegui npm ci nella cartella frontend.")
    probe = subprocess.run(
        [str(python), "-c", "import sys, fastapi, uvicorn; assert (3,11) <= sys.version_info[:2] < (3,14)"],
        cwd=ROOT, capture_output=True, text=True, timeout=10,
    )
    if probe.returncode:
        raise RuntimeError("Dipendenze Python mancanti o versione non supportata. Esegui uv sync --frozen.")
    return python, node


def ensure_ports_available() -> None:
    for port in PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if os.name != "nt":
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            elif hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                sock.bind((HOST, port))
            except OSError as exc:
                raise RuntimeError(f"La porta locale {port} è già occupata. Chiudi l'altra istanza prima di avviare.") from exc


def start_process(args: list[str], cwd: Path) -> subprocess.Popen:
    kwargs = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    return subprocess.Popen(args, cwd=cwd, **kwargs)


def stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=10)
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


def wait_for_services(processes: list[subprocess.Popen], timeout: float = 30) -> None:
    # Loopback must not pass through a configured corporate/network proxy.
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for process in processes:
            if process.poll() is not None:
                raise RuntimeError(f"Un servizio si è arrestato durante l'avvio (codice {process.returncode}). Leggi il log sopra.")
        try:
            with opener.open(f"http://{HOST}:8000/api/health", timeout=1) as response:
                health = json.load(response)
            with opener.open(f"http://{HOST}:5173/", timeout=1) as response:
                frontend_ready = response.status == 200 and b"<html" in response.read(8192).lower()
            if health.get("status") == "ok" and frontend_ready:
                return
        except (OSError, URLError, ValueError):
            pass
        time.sleep(0.2)
    raise RuntimeError("Avvio non completato entro 30 secondi. Controlla gli errori dei servizi nel terminale.")


def _shutdown_signal(signum, frame) -> None:
    raise KeyboardInterrupt


def main() -> int:
    parser = argparse.ArgumentParser(description="Avvia VideoScript AI Studio soltanto sul computer locale.")
    parser.add_argument("--no-browser", action="store_true", help="Non aprire automaticamente il browser.")
    parser.add_argument("--check", action="store_true", help="Verifica prerequisiti e porte, senza avviare servizi.")
    args = parser.parse_args()
    for name in ("SIGTERM", "SIGHUP", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), _shutdown_signal)
    processes: list[subprocess.Popen] = []
    try:
        python, node = prerequisites()
        ensure_ports_available()
        if args.check:
            print("Prerequisiti locali e porte: OK. Nessun servizio avviato.")
            return 0
        processes.append(start_process([
            str(python), "-m", "uvicorn", "app.main:app", "--app-dir", "backend",
            "--host", HOST, "--port", "8000",
        ], ROOT))
        # Running Vite through Node avoids shell/batch quoting on Windows.
        processes.append(start_process([
            node, str(ROOT / "frontend/node_modules/vite/bin/vite.js"),
            "--host", HOST, "--port", "5173", "--strictPort",
        ], ROOT / "frontend"))
        wait_for_services(processes)
        print(f"\nVideoScript AI Studio pronto sul computer locale: http://{HOST}:5173", flush=True)
        print("Mantieni aperto questo terminale. Premi Ctrl+C per arrestare entrambi i servizi.\n", flush=True)
        if not args.no_browser:
            webbrowser.open(f"http://{HOST}:5173")
        while True:
            for process in processes:
                if process.poll() is not None:
                    raise RuntimeError(f"Un servizio si è arrestato (codice {process.returncode}).")
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\nArresto dei servizi locali…", flush=True)
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
        print(f"\nImpossibile avviare VideoScript: {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        for process in reversed(processes):
            stop_process(process)


if __name__ == "__main__":
    raise SystemExit(main())
