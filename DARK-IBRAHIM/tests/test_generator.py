# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Tests: planner, templates, tester, debugger, file safety, ZIP export, agent."""
import json
import tempfile
import threading
import unittest
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import config
from ai_engine.ollama_client import OllamaClient
from backend.agent import BuildAgent
from backend.debugger import Debugger
from backend.generator import builtin_files, extract_code
from backend.planner import detect_project_type, extract_json, normalize_plan, template_plan
from backend.tester import ProjectTester
from database import database as db
from project_manager import file_builder
from project_manager.zip_export import export_zip, verify_zip
from security.validator import ValidationError, safe_relative_path, scan_for_secrets, validate_prompt


class PlannerTests(unittest.TestCase):
    def test_detect_type(self):
        self.assertEqual(detect_project_type("make an android app"), "android-app")
        self.assertEqual(detect_project_type("a flask dashboard"), "flask-web")
        self.assertEqual(detect_project_type("my portfolio website"), "static-website")
        self.assertEqual(detect_project_type("rename files"), "python-cli")

    def test_extract_json_and_code(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertIsNone(extract_json("no json here"))
        self.assertEqual(extract_code("text\n```python\nprint(1)\n```\nmore"), "print(1)\n")

    def test_normalize_plan_drops_unsafe_paths(self):
        raw = {"name": "Demo", "files": [{"path": "../evil.py"}, {"path": "main.py"}, {"path": ".env"}]}
        plan = normalize_plan(raw, "demo", "python-cli", None)
        self.assertEqual([f["path"] for f in plan["files"]], ["main.py"])
        self.assertIsNone(normalize_plan({"files": [{"path": "/etc/passwd"}]}, "x", None, None))


class TemplateTests(unittest.TestCase):
    def test_every_template_passes_static_checks(self):
        for kind in ("python-cli", "flask-web", "static-website", "android-app"):
            with self.subTest(kind=kind):
                plan = template_plan('A "quoted" <b>demo</b> idea', kind, "demo-app")
                files = builtin_files(plan)
                file_builder.ensure_base_files(files, plan)
                report = ProjectTester().run(files)
                self.assertTrue(report["passed"], report["checks"])


class TesterTests(unittest.TestCase):
    def test_syntax_error_is_reported(self):
        report = ProjectTester().run({"main.py": "def broken(:\n    pass\n", "README.md": "x"})
        self.assertFalse(report["passed"])

    def test_missing_requirement_is_autofixed(self):
        files = {"app.py": "import flask\nimport requests\n", "requirements.txt": "Flask>=3.0\n", "README.md": "x"}
        report = ProjectTester().run(files)
        fixes = Debugger().auto_fix(files, report["issues"])
        self.assertTrue(fixes)
        self.assertIn("requests", files["requirements.txt"])

    def test_unknown_import_is_only_a_warning(self):
        report = ProjectTester().run({"a.py": "import totally_made_up_lib\n", "README.md": "x"})
        self.assertTrue(report["passed"])
        self.assertTrue(any(i["kind"] == "unknown_import" for i in report["issues"]))

    def test_secret_scan(self):
        self.assertTrue(scan_for_secrets("a.py", 'API_KEY = "abcd1234efgh5678ijkl"'))
        self.assertFalse(scan_for_secrets("a.py", 'API_KEY = os.environ["API_KEY"]'))
        self.assertFalse(scan_for_secrets("a.py", 'password = "your-password-here"'))


class SafetyTests(unittest.TestCase):
    def test_path_rules(self):
        for bad in ("../x.py", "/etc/passwd", "a/../../b.py", ".env", "C:/x.py", "x.exe", "", "~/x.py"):
            with self.subTest(path=bad), self.assertRaises(ValidationError):
                safe_relative_path(bad)
        self.assertEqual(safe_relative_path("src\\app/main.py"), "src/app/main.py")
        self.assertEqual(safe_relative_path(".github/workflows/x.yml"), ".github/workflows/x.yml")

    def test_sanitize_files(self):
        clean, warnings = file_builder.sanitize_files({"ok.py": "x=1\n", "../bad.py": "x", "run.exe": "x"})
        self.assertEqual(list(clean), ["ok.py"])
        self.assertEqual(len(warnings), 2)

    def test_prompt_validation(self):
        with self.assertRaises(ValidationError):
            validate_prompt("hi")
        with self.assertRaises(ValidationError):
            validate_prompt("x" * (config.MAX_PROMPT_CHARS + 1))


class ZipTests(unittest.TestCase):
    def test_export_excludes_junk_and_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "proj"
            (root / "__pycache__").mkdir(parents=True)
            (root / "__pycache__" / "a.pyc").write_bytes(b"x")
            (root / ".env").write_text("SECRET=1")
            (root / "main.py").write_text("print(1)\n")
            (root / "run.sh").write_text("#!/bin/sh\n")
            archive = export_zip(root, Path(tmp) / "out", "proj.zip")
            self.assertTrue(verify_zip(archive)[0])
            with zipfile.ZipFile(archive) as zf:
                self.assertEqual(sorted(zf.namelist()), ["proj/main.py", "proj/run.sh"])
                self.assertEqual(zf.getinfo("proj/run.sh").external_attr >> 16, 0o755)

    def test_corrupt_zip_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.zip"
            bad.write_bytes(b"not a zip")
            self.assertFalse(verify_zip(bad)[0])


class AgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config.ensure_dirs()
        db.init_db()

    def test_template_build_end_to_end(self):
        result = BuildAgent().build("A flask dashboard for my notes", name="Notes Dash", mode="template")
        self.assertEqual(result["status"], "done")
        zip_path = config.PROJECTS_DIR / result["zip_name"]
        self.assertTrue(verify_zip(zip_path)[0])
        self.assertTrue(result["report"]["tests"]["passed"])
        self.assertIn("app.py", result["report"]["files"])
        self.assertEqual(db.get_project(result["id"])["status"], "done")

    def test_auto_mode_falls_back_without_ollama(self):
        result = BuildAgent().build("Small python tool to rename files", mode="auto")
        self.assertEqual(result["report"]["mode"], "template")
        self.assertTrue(result["report"]["warnings"])

    def test_ai_mode_fails_clearly_without_ollama(self):
        with self.assertRaises(Exception) as ctx:
            BuildAgent().build("Small python tool to rename files", mode="ai")
        self.assertIn("Ollama", str(ctx.exception))

    def test_android_project_is_included(self):
        result = BuildAgent().build("An android app that counts clicks", mode="template")
        files = result["report"]["files"]
        self.assertIn("android/app/src/main/AndroidManifest.xml", files)
        self.assertIn("android/app/src/main/assets/www/index.html", files)


class _FakeOllama(BaseHTTPRequestHandler):
    """Tiny stand-in for the Ollama HTTP API (no real model involved)."""

    def log_message(self, *args):
        pass

    def _send(self, payload):
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send({"models": [{"name": "fake-coder:1b"}]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        user = body["messages"][-1]["content"]
        if body.get("format") == "json":
            content = json.dumps({"name": "fake-app", "description": "Fake app", "project_type": "python-cli",
                                  "files": [{"path": "main.py", "purpose": "entry"},
                                            {"path": "README.md", "purpose": "docs"}]})
        elif "Errors:" in user:
            content = "```python\nprint('fixed')\n```"
        elif "`main.py`" in user:
            content = "```python\ndef broken(:\n    pass\n```"
        else:
            content = "```markdown\n# Fake app\n```"
        self._send({"message": {"role": "assistant", "content": content}})


class AiPathTests(unittest.TestCase):
    """Exercises the AI pipeline (plan -> generate -> test -> debug) against a simulated Ollama."""

    def test_ai_pipeline_with_self_repair(self):
        server = HTTPServer(("127.0.0.1", 0), _FakeOllama)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            agent = BuildAgent(OllamaClient(host=f"http://127.0.0.1:{server.server_port}", timeout=10))
            result = agent.build("A tiny python tool", mode="ai")
        finally:
            server.shutdown()
            server.server_close()
        report = result["report"]
        self.assertEqual(report["mode"], "ai")
        self.assertEqual(report["model"], "fake-coder:1b")
        self.assertTrue(any("main.py" in f for f in report["fixes"]))
        self.assertTrue(report["tests"]["passed"])


if __name__ == "__main__":
    unittest.main()
