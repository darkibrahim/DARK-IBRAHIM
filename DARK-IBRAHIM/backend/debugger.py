# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Automatic fixes: deterministic ones first, AI-assisted ones for syntax errors."""
from __future__ import annotations

from collections import defaultdict
from typing import Callable, Dict, List, Optional

from ai_engine import prompts
from ai_engine.ollama_client import OllamaClient, OllamaError
from backend.generator import extract_code


class Debugger:
    def __init__(self, client: Optional[OllamaClient] = None):
        self.client = client

    def auto_fix(self, files: Dict[str, str], issues: List[Dict]) -> List[str]:
        """Safe, deterministic repairs (e.g. add a known package to requirements.txt)."""
        fixes: List[str] = []
        for issue in issues:
            if issue.get("kind") == "missing_requirement" and issue.get("package"):
                text = files.get("requirements.txt", "")
                if issue["package"].lower() not in text.lower():
                    files["requirements.txt"] = (text.rstrip("\n") + "\n" if text else "") + issue["package"] + "\n"
                    fixes.append(f"Added {issue['package']} to requirements.txt")
        return fixes

    def ai_fix(self, files: Dict[str, str], issues: List[Dict], model: str,
               log: Callable[[str], None]) -> List[str]:
        if not self.client or not model:
            return []
        by_file: Dict[str, List[str]] = defaultdict(list)
        for issue in issues:
            if issue.get("level") == "fail" and issue.get("kind") == "syntax" and issue.get("path") in files:
                by_file[issue["path"]].append(issue["message"])
        fixes: List[str] = []
        for path, errors in by_file.items():
            log(f"Debugging {path} ...")
            try:
                fixed = extract_code(self.client.chat(prompts.fix_messages(path, files[path], errors), model))
            except OllamaError as exc:
                log(f"Could not fix {path}: {exc}")
                continue
            if path.endswith(".py"):
                try:
                    compile(fixed, path, "exec", dont_inherit=True)
                except SyntaxError:
                    log(f"The suggested fix for {path} still had errors; kept the original.")
                    continue
            files[path] = fixed
            fixes.append(f"Rewrote {path} to fix syntax errors")
        return fixes
