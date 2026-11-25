# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Prompt builders for the planner, generator and debugger."""
from __future__ import annotations

from typing import Dict, List

import config

PLANNER_SYSTEM = (
    "You are a senior software architect. Reply with ONE JSON object and nothing else.\n"
    'Schema: {"name": "short-kebab-case-name", "description": "one sentence", '
    '"project_type": "python-cli|flask-web|static-website|android-app", '
    '"files": [{"path": "relative/path.ext", "purpose": "what it contains"}], '
    '"run_command": "how to run it"}.\n'
    f"Rules: at most 12 files; relative paths only; include README.md and, for Python, requirements.txt; "
    "use only real, free, open-source libraries that exist on PyPI; never put secrets in files. "
    "For android-app put a vanilla HTML/CSS/JS web app under www/ with www/index.html as entry point."
)

GENERATOR_SYSTEM = (
    "You are a senior full-stack engineer. Write ONE complete file.\n"
    "Output ONLY the full file content inside a single fenced code block, no explanations.\n"
    "Rules: complete working code, no TODO or placeholder functions, only real libraries, "
    "read secrets from environment variables, handle errors, keep imports consistent with the other files."
)

DEBUGGER_SYSTEM = (
    "You are a debugging engineer. You receive one file and the errors found in it.\n"
    "Return the COMPLETE corrected file inside a single fenced code block, no explanations. "
    "Change only what is needed to fix the errors."
)


def planner_messages(prompt: str, project_type: str | None) -> List[Dict]:
    hint = f"\nRequired project_type: {project_type}" if project_type else ""
    return [
        {"role": "system", "content": PLANNER_SYSTEM},
        {"role": "user", "content": f"Project idea:\n{prompt}{hint}"},
    ]


def file_messages(plan: Dict, spec: Dict, done: Dict[str, str]) -> List[Dict]:
    overview = "\n".join(f"- {f['path']}: {f.get('purpose', '')}" for f in plan["files"])
    context, budget = [], 12000
    for path, content in done.items():
        snippet = content[:2500]
        if budget - len(snippet) < 0:
            break
        budget -= len(snippet)
        context.append(f"### {path}\n{snippet}")
    previous = "\n\n".join(context) or "(none yet)"
    user = (
        f"Project: {plan['name']} ({plan['project_type']})\nGoal: {plan['description']}\n\n"
        f"All files:\n{overview}\n\nFiles already written:\n{previous}\n\n"
        f"Now write the file `{spec['path']}` — {spec.get('purpose', '')}."
    )
    return [{"role": "system", "content": GENERATOR_SYSTEM}, {"role": "user", "content": user}]


def fix_messages(path: str, content: str, errors: List[str]) -> List[Dict]:
    problems = "\n".join(f"- {e}" for e in errors)
    user = f"File `{path}`:\n```\n{content[:12000]}\n```\n\nErrors:\n{problems}\n\nReturn the corrected file."
    return [{"role": "system", "content": DEBUGGER_SYSTEM}, {"role": "user", "content": user}]
