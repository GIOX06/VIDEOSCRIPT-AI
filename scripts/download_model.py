#!/usr/bin/env python3
"""Explicitly download model weights. This command never reads audiovisual media."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIZES = ("tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large-v3")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scarica pesi faster-whisper da Hugging Face, senza inviare media.")
    parser.add_argument("--size", choices=SIZES, default="tiny")
    parser.add_argument("--output", type=Path, help="Cartella modello locale (default .data/models/whisper-<size>)")
    parser.add_argument("--revision", default="main", help="Commit/revisione modello da scaricare (opzionale)")
    args = parser.parse_args()
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("Installa prima le dipendenze AI: uv sync --extra ai --frozen", file=sys.stderr)
        return 1
    destination = (args.output or ROOT / ".data" / "models" / f"whisper-{args.size}").expanduser().resolve()
    print(f"Download esplicito dei pesi Systran/faster-whisper-{args.size} in {destination}")
    print("Nessun video, audio o trascrizione viene inviato. La verifica TLS rimane attiva.")
    try:
        snapshot_download(
            repo_id=f"Systran/faster-whisper-{args.size}", revision=args.revision,
            local_dir=str(destination),
            allow_patterns=["config.json", "preprocessor_config.json", "model.bin", "tokenizer.json", "vocabulary.txt"],
        )
        required = ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt")
        missing = [name for name in required if not (destination / name).is_file()]
        if missing:
            print("Download incompleto: file mancanti " + ", ".join(missing), file=sys.stderr)
            return 1
    except Exception as exc:
        # Credential values must never be echoed even if a transport exception contains a URL.
        print(f"Download non riuscito ({type(exc).__name__}). Verifica rete e accesso a huggingface.co e CDN hf.co/xethub.hf.co; riprova il comando.", file=sys.stderr)
        return 1
    print(f"Modello pronto. Configura VIDEOSCRIPT_WHISPER_MODEL con il percorso: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
