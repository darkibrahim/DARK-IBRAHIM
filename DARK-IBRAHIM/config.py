# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Central configuration for DARK-IBRAHIM.

Every setting can be changed with an environment variable or a local `.env`
file (see `.env.example`). Secrets are never stored in the source code.
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv(path: Path) -> None:
    """Tiny .env loader (KEY=VALUE). Real environment variables win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------
# Identity / branding
# --------------------------------------------------------------------------
APP_NAME = "DARK-IBRAHIM"
APP_TAGLINE = "Local AI Software & APK Builder"
VERSION = "1.0.0"

BRAND = {
    "developer": "DARK IBRAHIM",
    "title": "Bug Bounty Hunter & Cyber Security Expert",
    "facebook": "https://www.facebook.com/profile.php?id=61580661413217",
    "github": "https://github.com/darkibrahim",
    "telegram": "@Hunter_1B4H14",
}

BANNER = r"""
 ____    _    ____  _  __   ___ ____  ____      _    _   _ ___ __  __
|  _ \  / \  |  _ \| |/ /  |_ _| __ )|  _ \    / \  | | | |_ _|  \/  |
| | | |/ _ \ | |_) | ' /    | ||  _ \| |_) |  / _ \ | |_| || || |\/| |
| |_| / ___ \|  _ <| . \    | || |_) |  _ <  / ___ \|  _  || || |  | |
|____/_/   \_\_| \_\_|\_\  |___|____/|_| \_\/_/   \_\_| |_|___|_|  |_|
""".strip("\n")


def brand_block() -> str:
    """The title block printed in the terminal, README files and the UI."""
    return (
        f"Developer : {BRAND['developer']}\n"
        f"Title     : {BRAND['title']}\n"
        f"Facebook  : {BRAND['facebook']}\n"
        f"GitHub    : {BRAND['github']}\n"
        f"Telegram  : {BRAND['telegram']}"
    )


# --------------------------------------------------------------------------
# Server
# --------------------------------------------------------------------------
HOST = os.environ.get("DARK_HOST", "127.0.0.1")
PORT = _int("DARK_PORT", 5000)

# --------------------------------------------------------------------------
# AI engine (Ollama - free, local, open source)
# --------------------------------------------------------------------------
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
if not OLLAMA_HOST.startswith(("http://", "https://")):
    OLLAMA_HOST = "http://" + OLLAMA_HOST
DEFAULT_MODEL = os.environ.get("DARK_MODEL", "qwen2.5-coder:7b")
RECOMMENDED_MODELS = ["qwen2.5-coder:7b", "qwen2.5-coder:3b", "deepseek-coder-v2:16b", "codellama:7b"]
REQUEST_TIMEOUT = _int("DARK_REQUEST_TIMEOUT", 600)

# --------------------------------------------------------------------------
# Limits
# --------------------------------------------------------------------------
MAX_PROMPT_CHARS = 4000
MAX_FILES = 30
MAX_FILE_BYTES = 300_000
MAX_FIX_ATTEMPTS = 2
MAX_HISTORY = 200
JOB_TTL_SECONDS = 3600

# --------------------------------------------------------------------------
# Storage (DARK_DATA_DIR lets tests and Docker keep data elsewhere)
# --------------------------------------------------------------------------
DATA_DIR = Path(os.environ.get("DARK_DATA_DIR", str(BASE_DIR))).resolve()
WORKSPACE_DIR = DATA_DIR / "workspace"
OUTPUT_DIR = DATA_DIR / "output"
PROJECTS_DIR = OUTPUT_DIR / "projects"
APK_DIR = OUTPUT_DIR / "apk"
LOGS_DIR = OUTPUT_DIR / "logs"
KEYSTORE_DIR = OUTPUT_DIR / "keystore"
DB_PATH = DATA_DIR / "database" / "history.db"
FRONTEND_DIR = BASE_DIR / "frontend"


def ensure_dirs() -> None:
    for path in (WORKSPACE_DIR, PROJECTS_DIR, APK_DIR, LOGS_DIR, DB_PATH.parent):
        path.mkdir(parents=True, exist_ok=True)


def setup_logging() -> logging.Logger:
    ensure_dirs()
    logger = logging.getLogger("dark")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler = RotatingFileHandler(
        LOGS_DIR / "dark-ibrahim.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)
    return logger
