# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Thread-safe in-memory store for background jobs (project builds, APK builds)."""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, Optional

import config


class JobStore:
    def __init__(self, ttl: int = config.JOB_TTL_SECONDS):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._ttl = ttl

    def create(self, kind: str) -> str:
        job_id = uuid.uuid4().hex
        with self._lock:
            self._purge()
            self._jobs[job_id] = {
                "id": job_id, "kind": kind, "status": "queued", "logs": [],
                "result": None, "error": None, "created": time.time(), "updated": time.time(),
            }
        return job_id

    def log(self, job_id: str, message: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job["logs"].append(message)
                job["logs"] = job["logs"][-500:]
                job["updated"] = time.time()

    def finish(self, job_id: str, status: str, result: Any = None, error: Optional[str] = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.update(status=status, result=result, error=error, updated=time.time())

    def set_status(self, job_id: str, status: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = status

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            return None if job is None else {**job, "logs": list(job["logs"])}

    def _purge(self) -> None:
        now = time.time()
        for key in [k for k, j in self._jobs.items()
                    if now - j["updated"] > self._ttl and j["status"] in ("done", "error")]:
            del self._jobs[key]
