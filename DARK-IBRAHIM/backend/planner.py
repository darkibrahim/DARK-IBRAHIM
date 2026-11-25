# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Turns a free-text idea into a validated project plan."""
from __future__ import annotations

import json
import re
from typing import Callable, Dict, Optional

import config
from ai_engine import prompts
from ai_engine.ollama_client import OllamaClient, OllamaError
from backend.generator import builtin_files
from security.validator import PROJECT_TYPES, ValidationError, safe_relative_path, slugify


def detect_project_type(prompt: str) -> str:
    text = prompt.lower()
    if re.search(r"android|apk|mobile app|অ্যান্ড্রয়েড|এপিকে", text):
        return "android-app"
    if re.search(r"flask|api|server|dashboard|backend|web ?app|ওয়েব অ্যাপ", text):
        return "flask-web"
    if re.search(r"website|landing|portfolio|html|ওয়েবসাইট", text):
        return "static-website"
    return "python-cli"


def extract_json(text: str) -> Optional[dict]:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _title(name: str) -> str:
    return " ".join(w.capitalize() for w in re.split(r"[-_]+", name) if w) or "Project"


def normalize_plan(raw: dict, prompt: str, project_type: Optional[str], name: Optional[str]) -> Optional[Dict]:
    """Validate an AI plan. Returns None if it is unusable."""
    kind = project_type or raw.get("project_type")
    if kind not in PROJECT_TYPES:
        kind = detect_project_type(prompt)
    files, seen = [], set()
    for item in raw.get("files") or []:
        if not isinstance(item, dict):
            continue
        try:
            path = safe_relative_path(item.get("path", ""))
        except ValidationError:
            continue
        if path in seen:
            continue
        seen.add(path)
        files.append({"path": path, "purpose": str(item.get("purpose", ""))[:200]})
        if len(files) >= 12:
            break
    if not files:
        return None
    if kind == "android-app" and not any(f["path"].startswith("www/") for f in files):
        return None
    plan_name = slugify(name or str(raw.get("name", "")))
    return {
        "name": plan_name, "title": _title(plan_name), "project_type": kind, "mode": "ai",
        "description": str(raw.get("description") or prompt)[:300],
        "run_command": str(raw.get("run_command", ""))[:200], "files": files,
    }


def template_plan(prompt: str, project_type: Optional[str], name: Optional[str]) -> Dict:
    kind = project_type or detect_project_type(prompt)
    plan_name = slugify(name or "", default="dark-project")
    plan = {
        "name": plan_name, "title": _title(plan_name), "project_type": kind, "mode": "template",
        "description": prompt[:300], "run_command": "", "files": [],
    }
    plan["files"] = [{"path": p, "purpose": "template"} for p in builtin_files(plan)]
    return plan


class Planner:
    def __init__(self, client: Optional[OllamaClient] = None):
        self.client = client

    def plan(self, prompt: str, project_type: Optional[str], name: Optional[str],
             model: Optional[str], log: Callable[[str], None]) -> Dict:
        if self.client and model:
            log(f"Planning with {model} ...")
            try:
                raw = extract_json(self.client.chat(prompts.planner_messages(prompt, project_type),
                                                    model, json_mode=True))
                plan = normalize_plan(raw, prompt, project_type, name) if raw else None
                if plan:
                    log(f"Plan ready: {len(plan['files'])} files ({plan['project_type']}).")
                    return plan
                log("The model's plan was not usable; switching to template plan.")
            except OllamaError as exc:
                log(f"AI planning failed ({exc}); switching to template plan.")
        return template_plan(prompt, project_type, name)
