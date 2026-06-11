from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = BASE_DIR / "data"
ATTACHMENTS_DIR = BASE_DIR / "attachments"
DB_PATH = DATA_DIR / "mail_agent.sqlite3"
SAMPLES_DIR = PROJECT_ROOT / "samples"
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def ensure_runtime_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)


def load_env_file(path: Path | None = None) -> None:
    env_path = path or (PROJECT_ROOT / ".env")
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_setting(name: str, default: str = "") -> str:
    return os.environ.get(name, default)

