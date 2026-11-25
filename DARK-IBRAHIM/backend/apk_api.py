# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""APK endpoints: build an Android project (and an APK when the SDK is available)."""
from __future__ import annotations

import logging
import shutil
import threading
import uuid
from pathlib import Path
from typing import Dict

from flask import Blueprint, current_app, jsonify, request, send_file

import config
from apk_generator import apk_signer, apk_validator, gradle_manager
from apk_generator.android_builder import build_project_files, default_package, web_root, write_project
from database import database as db
from project_manager.zip_export import export_zip
from security.permissions import filter_permissions
from security.validator import (
    ALLOWED_EXTENSIONS, ValidationError, slugify, validate_app_name, validate_package_name,
    validate_project_id,
)

LOG = logging.getLogger("dark.apk")
apk_bp = Blueprint("apk", __name__, url_prefix="/api/apk")
APK_SLOT = threading.Semaphore(1)


def _collect_web_files(root: Path) -> Dict[str, str]:
    files: Dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if (not path.is_file() or rel.startswith(("android/", ".")) or path.suffix.lower() not in ALLOWED_EXTENSIONS
                or path.stat().st_size > config.MAX_FILE_BYTES):
            continue
        files[rel] = path.read_text(encoding="utf-8", errors="replace")
    return files


@apk_bp.get("/environment")
def environment():
    return jsonify(gradle_manager.check_environment())


def _run(svc, job_id: str, build_id: str, project: Dict, params: Dict) -> None:
    log = lambda m: svc.jobs.log(job_id, m)  # noqa: E731
    with APK_SLOT:
        svc.jobs.set_status(job_id, "running")
        try:
            result = _build(build_id, project, params, log)
            db.update_apk_build(build_id, status="done", apk_path=result.pop("_apk", None),
                                project_zip=result.pop("_zip"), report=result)
            svc.jobs.finish(job_id, "done", result=result)
        except (ValidationError, ValueError, OSError) as exc:
            db.update_apk_build(build_id, status="error", log=str(exc))
            svc.jobs.finish(job_id, "error", error=str(exc))
        except Exception:  # noqa: BLE001
            LOG.exception("APK build failed")
            db.update_apk_build(build_id, status="error", log="unexpected error")
            svc.jobs.finish(job_id, "error", error="Unexpected error. Check output/logs for details.")


def _build(build_id: str, project: Dict, params: Dict, log) -> Dict:
    root = Path(project["root_dir"])
    if not root.is_dir():
        raise ValueError("Project files are no longer available.")
    web_files = _collect_web_files(root)
    if web_root(web_files) is None:
        raise ValueError("This project has no plain index.html, so it cannot be wrapped as an Android app.")
    app_name = validate_app_name(params.get("app_name") or project["name"].replace("-", " ").title())
    package = validate_package_name(params.get("package") or default_package(project["name"]))
    permissions, rejected = filter_permissions(params.get("permissions"))
    work = config.APK_DIR / build_id
    log("Generating Android project ...")
    files = build_project_files(app_name, package, web_files, permissions)
    android_dir = write_project(work, files)
    structure = apk_validator.validate_project(android_dir)
    if not structure["valid"]:
        raise ValueError("Generated Android project is invalid: " + "; ".join(structure["problems"]))
    log("Android project is valid. Packaging project ZIP ...")
    project_zip = export_zip(android_dir, config.APK_DIR, f"{slugify(app_name)}-android-project-{build_id[:8]}.zip")

    env = gradle_manager.check_environment()
    result = {"build_id": build_id, "package": package, "permissions": permissions,
              "rejected_permissions": rejected, "environment": env, "apk_built": False,
              "project_zip_url": f"/api/apk/download/{build_id}/project", "apk_url": None,
              "validation": None, "_zip": str(project_zip)}
    if not env["ready"]:
        result["message"] = ("APK was not built here: " + " ".join(env["problems"]) +
                             " Use the project ZIP with Android Studio or the included GitHub Actions workflow.")
        log(result["message"])
        return result

    release = bool(params.get("release"))
    log(f"Running Gradle ({'release' if release else 'debug'}) - this can take several minutes ...")
    ok, output, apk = gradle_manager.build(android_dir, "assembleRelease" if release else "assembleDebug")
    if not ok or apk is None:
        result["message"] = "Gradle build failed. Last output:\n" + output[-1500:]
        log("Gradle build failed.")
        return result
    final = config.APK_DIR / f"{slugify(app_name)}-{build_id[:8]}{'-release' if release else '-debug'}.apk"
    if release:
        signed, message = apk_signer.sign(apk, final)
        log(message)
        if not signed:
            result["message"] = message
            return result
    else:
        shutil.copyfile(apk, final)
    result["validation"] = apk_validator.validate_apk(final)
    result.update(apk_built=result["validation"]["valid"], apk_url=f"/api/apk/download/{build_id}/apk",
                  message="APK built.", _apk=str(final))
    log(result["message"])
    return result


@apk_bp.post("/build")
def start_build():
    body = request.get_json(silent=True) or {}
    project_id = validate_project_id(body.get("project_id"))
    project = db.get_project(project_id)
    if not project or project["status"] != "done":
        raise LookupError("Project not found.")
    svc = current_app.extensions["dark"]
    build_id, job_id = uuid.uuid4().hex, svc.jobs.create("apk")
    db.save_apk_build(build_id, project_id)
    params = {k: body.get(k) for k in ("app_name", "package", "permissions", "release")}
    threading.Thread(target=_run, args=(svc, job_id, build_id, project, params), daemon=True).start()
    return jsonify(job_id=job_id, build_id=build_id), 202


@apk_bp.get("/download/<build_id>/<kind>")
def download(build_id, kind):
    row = db.get_apk_build(validate_project_id(build_id))
    column = {"apk": "apk_path", "project": "project_zip"}.get(kind)
    if not row or not column or not row.get(column):
        raise LookupError("File not found.")
    path = Path(row[column]).resolve()
    try:
        path.relative_to(config.APK_DIR.resolve())
    except ValueError:
        raise LookupError("File not found.")
    if not path.is_file():
        raise LookupError("File not found.")
    mime = "application/vnd.android.package-archive" if kind == "apk" else "application/zip"
    return send_file(path, as_attachment=True, download_name=path.name, mimetype=mime)
