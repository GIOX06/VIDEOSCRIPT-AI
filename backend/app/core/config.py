import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.environ.get("VIDEOSCRIPT_DATA_DIR", ROOT / ".data")).expanduser().resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "studio.sqlite3"
