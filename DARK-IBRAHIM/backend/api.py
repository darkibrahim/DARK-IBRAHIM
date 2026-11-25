# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""REST API + static frontend for DARK-IBRAHIM."""
from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Dict

from flask import Blueprint, Flask, current_app, jsonify, request, send_file, send_from_directory

import config
from ai_engine.ollama_client import OllamaClient, OllamaError
from backend.agent import MODES, BuildAgent
from backend.apk_api import apk_bp
from backend.jobs import JobStore
from database import database as db
from project_manager.workspace import Workspace
from security.validator import (
    ValidationError, safe_relative_path, validate_model_name, validate_project_id,
    validate_project_type, validate_prompt,
)

LOG = logging.getLogger("dark.api")
api_bp = Blueprint("api", __name__, url_prefix="/api")
BUILD_SLOT = threading.Semaphore(1)  # local LLMs are heavy: one build at a time


class Services:
    def __init__(self):
        self.client = OllamaClient()
        self.agent = BuildAgent(self.client)
        self.jobs = JobStore()
        self.workspace = Workspace()


def services() -> Services:
    return current_app.extensions["dark"]


def _is_inside(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _project_or_404(project_id: str) -> Dict:
    project = db.get_project(validate_project_id(project_id))
    if not project:
        raise LookupError("Project not found.")
    return project


# ---------------------------------------------------------------- status
@api_bp.get("/health")
def health():
    return jsonify(status="ok", app=config.APP_NAME, version=config.VERSION,
                   tagline=config.APP_TAGLINE, brand=config.BRAND,
                   ollama=services().agent.models.overview())


@api_bp.get("/models")
def models():
    return jsonify(services().agent.models.overview())


@api_bp.post("/models/pull")
def pull_model():
    body = request.get_json(silent=True) or {}
    try:
        status = services().agent.models.pull(body.get("model", ""))
    except OllamaError as exc:
        return jsonify(error=str(exc)), 502
    return jsonify(status=status)


# ---------------------------------------------------------------- builds
def _run_build(svc: Services, job_id: str, params: Dict) -> None:
    with BUILD_SLOT:
        svc.jobs.set_status(job_id, "running")
        try:
            result = svc.agent.build(**params, log=lambda m: svc.jobs.log(job_id, m))
            svc.jobs.finish(job_id, "done", result=result)
        except (ValidationError, OllamaError, ValueError, OSError) as exc:
            svc.jobs.finish(job_id, "error", error=str(exc))
        except Exception:  # noqa: BLE001 - never leak internals to the client
            LOG.exception("Unexpected build error")
            svc.jobs.finish(job_id, "error", error="Unexpected error. Check output/logs for details.")


@api_bp.post("/projects/build")
def start_build():
    body = request.get_json(silent=True) or {}
    prompt = validate_prompt(body.get("prompt"))
    project_type = validate_project_type(body.get("project_type"))
    mode = body.get("mode", "auto")
    if mode not in MODES:
        raise ValidationError("mode must be auto, ai or template.")
    model = body.get("model") or None
    if model:
        validate_model_name(model)
    name = str(body.get("name") or "")[:50] or None
    svc = services()
    job_id = svc.jobs.create("build")
    params = {"prompt": prompt, "name": name, "project_type": project_type, "model": model, "mode": mode}
    threading.Thread(target=_run_build, args=(svc, job_id, params), daemon=True).start()
    return jsonify(job_id=job_id), 202


@api_bp.get("/jobs/<job_id>")
def job_status(job_id):
    job = services().jobs.get(validate_project_id(job_id))
    if not job:
        raise LookupError("Job not found.")
    return jsonify(job)


# ---------------------------------------------------------------- history / files
@api_bp.get("/projects")
def projects():
    return jsonify(projects=db.list_projects(request.args.get("limit", 50, type=int)))


@api_bp.get("/projects/<project_id>")
def project_detail(project_id):
    project = _project_or_404(project_id)
    project.pop("root_dir", None)
    project["zip_name"] = Path(project.pop("zip_path") or "").name or None
    return jsonify(project)


@api_bp.get("/projects/<project_id>/download")
def download(project_id):
    project = _project_or_404(project_id)
    zip_path = Path(project.get("zip_path") or "")
    if not zip_path.is_file() or not _is_inside(zip_path, config.PROJECTS_DIR):
        raise LookupError("ZIP file not found.")
    return send_file(zip_path, as_attachment=True, download_name=zip_path.name, mimetype="application/zip")


def _root(project: Dict) -> Path:
    root = Path(project.get("root_dir") or "")
    if not root.is_dir() or not _is_inside(root, config.WORKSPACE_DIR):
        raise LookupError("Project files are no longer available.")
    return root.resolve()


@api_bp.get("/projects/<project_id>/files")
def project_files(project_id):
    root = _root(_project_or_404(project_id))
    items = [{"path": p.relative_to(root).as_posix(), "size": p.stat().st_size}
             for p in sorted(root.rglob("*")) if p.is_file()]
    return jsonify(files=items)


@api_bp.get("/projects/<project_id>/file")
def project_file(project_id):
    root = _root(_project_or_404(project_id))
    rel = safe_relative_path(request.args.get("path", ""))
    target = (root / rel).resolve()
    if not _is_inside(target, root) or not target.is_file():
        raise LookupError("File not found.")
    if target.stat().st_size > 200_000:
        raise ValidationError("File is too large to preview.")
    return jsonify(path=rel, content=target.read_text(encoding="utf-8", errors="replace"))


@api_bp.delete("/projects/<project_id>")
def delete_project(project_id):
    project = _project_or_404(project_id)
    zip_path = Path(project.get("zip_path") or "")
    if zip_path.is_file() and _is_inside(zip_path, config.PROJECTS_DIR):
        zip_path.unlink()
    services().workspace.remove(project["id"])
    db.delete_project(project["id"])
    return jsonify(deleted=True)


# ---------------------------------------------------------------- app factory
def create_app() -> Flask:
    config.ensure_dirs()
    db.init_db()
    app = Flask(__name__, static_folder=str(config.FRONTEND_DIR), static_url_path="")
    app.config["MAX_CONTENT_LENGTH"] = 1_000_000
    app.extensions["dark"] = Services()
    app.register_blueprint(api_bp)
    app.register_blueprint(apk_bp)

    @app.get("/")
    def index():
        return send_from_directory(config.FRONTEND_DIR, "index.html")

    @app.after_request
    def security_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        if request.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.errorhandler(ValidationError)
    def bad_request(exc):
        return jsonify(error=str(exc)), 400

    @app.errorhandler(LookupError)
    def not_found(exc):
        return jsonify(error=str(exc.args[0]) if exc.args else "Not found."), 404

    @app.errorhandler(404)
    def not_found_http(_exc):
        return jsonify(error="Not found."), 404

    @app.errorhandler(413)
    def too_large(_exc):
        return jsonify(error="Request is too large."), 413

    @app.errorhandler(Exception)
    def server_error(exc):
        if hasattr(exc, "code") and isinstance(exc.code, int):
            return jsonify(error=getattr(exc, "description", "Error")), exc.code
        LOG.exception("Unhandled error")
        return jsonify(error="Internal server error."), 500

    return app
