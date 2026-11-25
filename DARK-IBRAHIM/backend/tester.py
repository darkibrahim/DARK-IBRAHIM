# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Static project checks. Generated code is parsed, never executed."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List
import ast
import re

from security.validator import scan_for_secrets

# import name -> PyPI distribution (only for names that differ or are well known)
KNOWN_PACKAGES = {
    "flask": "Flask", "requests": "requests", "numpy": "numpy", "pandas": "pandas",
    "PIL": "pillow", "yaml": "pyyaml", "bs4": "beautifulsoup4", "dotenv": "python-dotenv",
    "flask_cors": "flask-cors", "jwt": "pyjwt", "dateutil": "python-dateutil",
    "matplotlib": "matplotlib", "colorama": "colorama", "rich": "rich", "click": "click",
    "flask_sqlalchemy": "flask-sqlalchemy", "sqlalchemy": "sqlalchemy", "aiohttp": "aiohttp",
    "fastapi": "fastapi", "uvicorn": "uvicorn", "pydantic": "pydantic", "cryptography": "cryptography",
}
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().lower())


class _TagChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack: List[str] = []
        self.errors: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in _VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in _VOID:
            return
        if tag in self.stack:
            while self.stack and self.stack[-1] != tag:
                self.errors.append(f"<{self.stack.pop()}> is never closed")
            self.stack.pop()
        else:
            self.errors.append(f"unexpected </{tag}>")


class ProjectTester:
    def run(self, files: Dict[str, str]) -> Dict:
        checks: List[Dict] = []
        issues: List[Dict] = []

        def check(name: str, problems: List[Dict], skipped: str = ""):
            if skipped:
                checks.append({"name": name, "status": "skip", "detail": skipped})
                return
            hard = [p for p in problems if p["level"] == "fail"]
            status = "fail" if hard else ("warn" if problems else "pass")
            detail = "; ".join(p["message"] for p in problems[:3]) or "OK"
            checks.append({"name": name, "status": status, "detail": detail})
            issues.extend(problems)

        py = {p: c for p, c in files.items() if p.endswith(".py")}
        check("Python syntax", self._python_syntax(py)) if py else check("Python syntax", [], "no Python files")
        check("Python imports", self._imports(files, py)) if py else check("Python imports", [], "no Python files")
        check("JSON / XML syntax", self._data_files(files))
        html_files = {p: c for p, c in files.items() if p.endswith(".html")}
        check("HTML structure", self._html(html_files)) if html_files else check("HTML structure", [], "no HTML files")
        check("JavaScript syntax", self._javascript(files))
        check("Shell syntax", self._shell(files))
        check("Secret scan", self._secrets(files))
        check("Project structure", self._structure(files))
        return {
            "passed": not any(c["status"] == "fail" for c in checks),
            "checks": checks, "issues": issues,
            "note": "Static checks only; generated code is never executed by DARK-IBRAHIM.",
        }

    # -- individual checks -------------------------------------------------
    def _python_syntax(self, py: Dict[str, str]) -> List[Dict]:
        problems = []
        for path, code in py.items():
            try:
                compile(code, path, "exec", dont_inherit=True)
            except SyntaxError as exc:
                problems.append({"level": "fail", "kind": "syntax", "path": path,
                                 "message": f"{path}:{exc.lineno}: {exc.msg}"})
        return problems

    def _imports(self, files: Dict[str, str], py: Dict[str, str]) -> List[Dict]:
        local = {Path(p).parts[0].removesuffix(".py") for p in files}
        required = set()
        for line in files.get("requirements.txt", "").splitlines():
            m = re.match(r"^\s*([A-Za-z0-9_.\-]+)", line)
            if m and not line.strip().startswith("#"):
                required.add(_norm(m.group(1)))
        problems, reported = [], set()
        for path, code in py.items():
            try:
                tree = ast.parse(code)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module.split(".")[0]]
                for name in names:
                    if name in sys.stdlib_module_names or name in local or name in reported:
                        continue
                    dist = KNOWN_PACKAGES.get(name)
                    if dist and _norm(dist) in required or _norm(name) in required:
                        continue
                    reported.add(name)
                    if dist:
                        problems.append({"level": "warn", "kind": "missing_requirement", "path": path,
                                         "package": dist, "message": f"'{name}' is not listed in requirements.txt"})
                    else:
                        problems.append({"level": "warn", "kind": "unknown_import", "path": path,
                                         "message": f"{path}: cannot verify import '{name}' (not stdlib, local or listed)"})
        return problems

    def _data_files(self, files: Dict[str, str]) -> List[Dict]:
        problems = []
        for path, content in files.items():
            try:
                if path.endswith(".json"):
                    json.loads(content)
                elif path.endswith(".xml"):
                    ET.fromstring(content)
            except (ValueError, ET.ParseError) as exc:
                problems.append({"level": "fail", "kind": "syntax", "path": path, "message": f"{path}: {exc}"})
        return problems

    def _html(self, html_files: Dict[str, str]) -> List[Dict]:
        problems = []
        for path, content in html_files.items():
            if "{{" in content or "{%" in content:
                continue  # Jinja template, not plain HTML
            checker = _TagChecker()
            checker.feed(content)
            checker.errors.extend(f"<{t}> is never closed" for t in checker.stack if t not in ("html", "body", "head"))
            for err in checker.errors[:3]:
                problems.append({"level": "warn", "kind": "html", "path": path, "message": f"{path}: {err}"})
        return problems

    def _run_tool(self, command: List[str]) -> str:
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return str(exc)
        return "" if result.returncode == 0 else (result.stderr or result.stdout).strip()[:300]

    def _javascript(self, files: Dict[str, str]) -> List[Dict]:
        scripts = {p: c for p, c in files.items() if p.endswith(".js")}
        node = shutil.which("node")
        problems: List[Dict] = []
        if not scripts or not node:
            return problems  # node is optional; the check is skipped without it
        for path, content in scripts.items():
            with tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / "check.js"
                target.write_text(content, encoding="utf-8")
                error = self._run_tool([node, "--check", str(target)])
            if error:
                problems.append({"level": "fail", "kind": "syntax", "path": path, "message": f"{path}: {error[:200]}"})
        return problems

    def _shell(self, files: Dict[str, str]) -> List[Dict]:
        bash, problems = shutil.which("bash"), []
        for path, content in files.items():
            if path.endswith(".sh") and bash:
                with tempfile.TemporaryDirectory() as tmp:
                    target = Path(tmp) / "check.sh"
                    target.write_text(content, encoding="utf-8")
                    error = self._run_tool([bash, "-n", str(target)])
                if error:
                    problems.append({"level": "fail", "kind": "syntax", "path": path, "message": f"{path}: {error[:200]}"})
        return problems

    def _secrets(self, files: Dict[str, str]) -> List[Dict]:
        return [{"level": "warn", "kind": "secret", "path": p, "message": msg}
                for p, c in files.items() for msg in scan_for_secrets(p, c)]

    def _structure(self, files: Dict[str, str]) -> List[Dict]:
        problems = []
        if "README.md" not in files:
            problems.append({"level": "warn", "kind": "structure", "path": "", "message": "README.md missing"})
        return problems
