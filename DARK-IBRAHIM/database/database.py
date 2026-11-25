# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""SQLite storage for project and APK build history (standard library only)."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, prompt TEXT NOT NULL,
    project_type TEXT, mode TEXT, model TEXT, status TEXT NOT NULL,
    files_count INTEGER DEFAULT 0, zip_path TEXT, root_dir TEXT,
    report TEXT, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS apk_builds (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL, status TEXT NOT NULL,
    apk_path TEXT, project_zip TEXT, log TEXT, report TEXT,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
"""
_PROJECT_COLUMNS = {
    "name", "prompt", "project_type", "mode", "model", "status", "files_count",
    "zip_path", "root_dir", "report", "error",
}
_APK_COLUMNS = {"status", "apk_path", "project_zip", "log", "report"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _conn():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(config.DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _row(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    data = dict(row)
    if data.get("report"):
        try:
            data["report"] = json.loads(data["report"])
        except ValueError:
            pass
    return data


def init_db() -> None:
    with _conn() as conn:
        conn.executescript(_SCHEMA)


def _dump(fields: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(fields)
    if isinstance(out.get("report"), (dict, list)):
        out["report"] = json.dumps(out["report"], ensure_ascii=False)
    return out


def save_project(record: Dict[str, Any]) -> None:
    now = _now()
    data = _dump(record)
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO projects (id, name, prompt, project_type, mode, model, status, "
            "files_count, zip_path, root_dir, report, error, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                data["id"], data["name"], data["prompt"], data.get("project_type"), data.get("mode"),
                data.get("model"), data.get("status", "running"), data.get("files_count", 0),
                data.get("zip_path"), data.get("root_dir"), data.get("report"), data.get("error"),
                now, now,
            ),
        )


def update_project(project_id: str, **fields: Any) -> None:
    fields = _dump({k: v for k, v in fields.items() if k in _PROJECT_COLUMNS})
    if not fields:
        return
    assignments = ", ".join(f"{col} = ?" for col in fields)
    with _conn() as conn:
        conn.execute(
            f"UPDATE projects SET {assignments}, updated_at = ? WHERE id = ?",
            (*fields.values(), _now(), project_id),
        )


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    with _conn() as conn:
        return _row(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())


def list_projects(limit: int = 50) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit), config.MAX_HISTORY))
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, name, prompt, project_type, mode, model, status, files_count, created_at "
            "FROM projects ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def delete_project(project_id: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM apk_builds WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))


def save_apk_build(build_id: str, project_id: str, status: str = "running") -> None:
    now = _now()
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO apk_builds (id, project_id, status, created_at, updated_at) "
            "VALUES (?,?,?,?,?)", (build_id, project_id, status, now, now),
        )


def update_apk_build(build_id: str, **fields: Any) -> None:
    fields = _dump({k: v for k, v in fields.items() if k in _APK_COLUMNS})
    if not fields:
        return
    assignments = ", ".join(f"{col} = ?" for col in fields)
    with _conn() as conn:
        conn.execute(
            f"UPDATE apk_builds SET {assignments}, updated_at = ? WHERE id = ?",
            (*fields.values(), _now(), build_id),
        )


def get_apk_build(build_id: str) -> Optional[Dict[str, Any]]:
    with _conn() as conn:
        return _row(conn.execute("SELECT * FROM apk_builds WHERE id = ?", (build_id,)).fetchone())
