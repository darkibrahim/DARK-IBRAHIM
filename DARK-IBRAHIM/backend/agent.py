# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""The build agent: plan -> generate -> test -> fix -> package."""
from __future__ import annotations

import logging
import uuid
from typing import Callable, Dict, Optional

import config
from ai_engine.model_manager import ModelManager
from ai_engine.ollama_client import OllamaClient, OllamaError
from apk_generator.android_builder import build_project_files, default_package
from backend.debugger import Debugger
from backend.generator import GenerationError, Generator, builtin_files
from backend.planner import Planner, template_plan
from backend.tester import ProjectTester
from database import database as db
from project_manager import file_builder
from project_manager.workspace import Workspace
from project_manager.zip_export import export_zip
from security.validator import slugify, validate_project_type, validate_prompt

LOG = logging.getLogger("dark.agent")
MODES = ("auto", "ai", "template")


class BuildAgent:
    def __init__(self, client: Optional[OllamaClient] = None):
        self.client = client or OllamaClient()
        self.models = ModelManager(self.client)
        self.planner = Planner(self.client)
        self.generator = Generator(self.client)
        self.tester = ProjectTester()
        self.debugger = Debugger(self.client)
        self.workspace = Workspace()

    def build(self, prompt: str, name: Optional[str] = None, project_type: Optional[str] = None,
              model: Optional[str] = None, mode: str = "auto",
              log: Optional[Callable[[str], None]] = None) -> Dict:
        log = log or (lambda _m: None)
        prompt = validate_prompt(prompt)
        project_type = validate_project_type(project_type)
        if mode not in MODES:
            mode = "auto"
        project_id = uuid.uuid4().hex
        db.save_project({"id": project_id, "name": slugify(name or "", "dark-project"), "prompt": prompt,
                         "project_type": project_type, "mode": mode, "status": "running"})
        try:
            return self._run(project_id, prompt, name, project_type, model, mode, log)
        except Exception as exc:  # recorded, then re-raised for the job runner
            LOG.exception("Build failed")
            db.update_project(project_id, status="error", error=str(exc)[:500])
            raise

    def _run(self, project_id, prompt, name, project_type, model, mode, log) -> Dict:
        warnings = []
        use_model = None
        if mode in ("auto", "ai"):
            use_model = self.models.resolve(model) if self.client.is_available() else None
            if use_model is None and mode == "ai":
                raise OllamaError("AI mode needs Ollama running with at least one model installed.")
            if use_model is None:
                log("Ollama is not available - using offline templates.")
                warnings.append("Ollama was not available; a template project was generated.")
        else:
            log("Template mode selected.")

        plan = self.planner.plan(prompt, project_type, name, use_model, log)
        try:
            files = self.generator.generate(plan, use_model, log)
        except (OllamaError, GenerationError) as exc:
            if mode == "ai":
                raise
            log(f"AI generation failed ({exc}); falling back to templates.")
            warnings.append(f"AI generation failed ({exc}); a template project was generated.")
            plan, use_model = template_plan(prompt, plan["project_type"], plan["name"]), None
            files = builtin_files(plan)

        if plan["project_type"] == "android-app" and "www/index.html" not in files:
            files.update(builtin_files(plan))
        files, extra = file_builder.sanitize_files(files)
        warnings.extend(extra)
        file_builder.ensure_base_files(files, plan)

        report, fixes = self._test_and_fix(files, use_model, log)
        if plan["project_type"] == "android-app":
            files.update(build_project_files(plan["title"], default_package(plan["name"]), files))
        file_builder.apply_branding(files)
        files, extra = file_builder.sanitize_files(files)
        warnings.extend(extra)

        root = self.workspace.create(project_id, plan["name"])
        file_builder.write_files(root, files)
        log(f"Packaging {len(files)} files into a ZIP ...")
        zip_path = export_zip(root, config.PROJECTS_DIR, f"{plan['name']}-{project_id[:8]}.zip")

        summary = {
            "plan": {k: plan[k] for k in ("name", "title", "project_type", "description")},
            "mode": plan["mode"], "model": use_model, "tests": report, "fixes": fixes,
            "warnings": warnings, "files": sorted(files),
            "limitations": ["Static checks only: generated code was not executed.",
                            "AI output quality depends on the local model you use."],
        }
        db.update_project(project_id, name=plan["name"], project_type=plan["project_type"], mode=plan["mode"],
                          model=use_model, status="done", files_count=len(files), zip_path=str(zip_path),
                          root_dir=str(root), report=summary)
        log("Done.")
        return {"id": project_id, "name": plan["name"], "status": "done", "zip_name": zip_path.name,
                "download_url": f"/api/projects/{project_id}/download", "files_count": len(files),
                "report": summary}

    def _test_and_fix(self, files: Dict[str, str], model: Optional[str], log):
        fixes, report = [], self.tester.run(files)
        for attempt in range(config.MAX_FIX_ATTEMPTS + 1):
            log(f"Testing (round {attempt + 1}): " + ("passed" if report["passed"] else "problems found"))
            applied = self.debugger.auto_fix(files, report["issues"])
            if not report["passed"] and attempt < config.MAX_FIX_ATTEMPTS:
                applied += self.debugger.ai_fix(files, report["issues"], model, log)
            if not applied:
                break
            fixes.extend(applied)
            report = self.tester.run(files)
        return report, fixes
