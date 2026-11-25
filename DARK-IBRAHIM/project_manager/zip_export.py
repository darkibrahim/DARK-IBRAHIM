# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Create and verify the final project ZIP archive."""
from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

EXCLUDE_DIRS = {
    "__pycache__", ".venv", "venv", "env", "node_modules", ".git", ".gradle", "build",
    ".idea", ".vscode", ".pytest_cache", ".mypy_cache",
}
EXCLUDE_NAMES = {".env", ".DS_Store", "local.properties", "history.db"}
EXCLUDE_SUFFIXES = (".pyc", ".pyo", ".log", ".keystore", ".jks", ".tmp", ".swp")


def _excluded(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in EXCLUDE_DIRS for part in rel.parts[:-1]):
        return True
    return path.name in EXCLUDE_NAMES or path.name.endswith(EXCLUDE_SUFFIXES)


def export_zip(root: Path, out_dir: Path, zip_name: Optional[str] = None) -> Path:
    """Zip `root` into out_dir. Everything is placed inside one top-level folder."""
    root, out_dir = Path(root).resolve(), Path(out_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Project folder not found: {root}")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    target = out_dir / (zip_name or f"{root.name}-{stamp}.zip")
    count = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.is_symlink() or _excluded(path, root):
                continue
            arcname = f"{root.name}/{path.relative_to(root).as_posix()}"
            info = zipfile.ZipInfo.from_file(path, arcname)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.suffix == ".sh" else 0o644) << 16
            zf.writestr(info, path.read_bytes())
            count += 1
    if count == 0:
        target.unlink(missing_ok=True)
        raise ValueError("Nothing to export: the project folder is empty.")
    ok, message = verify_zip(target)
    if not ok:
        target.unlink(missing_ok=True)
        raise ValueError(f"ZIP verification failed: {message}")
    return target


def verify_zip(path: Path) -> Tuple[bool, str]:
    try:
        with zipfile.ZipFile(path) as zf:
            bad = zf.testzip()
            if bad:
                return False, f"corrupted entry: {bad}"
            names = zf.namelist()
            if not names:
                return False, "archive is empty"
            if any(n.startswith("/") or ".." in n.split("/") for n in names):
                return False, "unsafe entry names"
            return True, f"{len(names)} files, OK"
    except (zipfile.BadZipFile, OSError) as exc:
        return False, str(exc)
