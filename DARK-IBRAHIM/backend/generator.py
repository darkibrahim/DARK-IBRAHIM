# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""File generation: AI mode (Ollama) and built-in offline templates."""
from __future__ import annotations

import html
import json
import re
from typing import Callable, Dict, List

import config
from ai_engine import prompts
from ai_engine.ollama_client import OllamaClient

BRAND_HTML = html.escape(f"{config.BRAND['developer']} — {config.BRAND['title']}")


class GenerationError(RuntimeError):
    pass


def extract_code(text: str) -> str:
    """Return the biggest fenced block, or the whole text if there is none."""
    blocks = re.findall(r"```[\w+.-]*\n(.*?)```", text, flags=re.S)
    if blocks:
        return max(blocks, key=len).strip("\n") + "\n"
    return text.strip("\n") + "\n"


# --------------------------------------------------------------------------
# Built-in templates (work completely offline)
# --------------------------------------------------------------------------
def _fill(template: str, plan: Dict) -> str:
    title = plan.get("title") or plan["name"]
    desc = plan["description"]
    return (
        template.replace("__TITLE_HTML__", html.escape(title))
        .replace("__DESC_HTML__", html.escape(desc))
        .replace("__TITLE_PY__", json.dumps(title, ensure_ascii=False))
        .replace("__DESC_PY__", json.dumps(desc, ensure_ascii=False))
        .replace("__NAME__", plan["name"])
        .replace("__BRAND_HTML__", BRAND_HTML)
        .replace("__GITHUB__", config.BRAND["github"])
    )


_CLI = '''#!/usr/bin/env python3
"""__NAME__ - command line tool."""
import argparse
import sys

TITLE = __TITLE_PY__
DESCRIPTION = __DESC_PY__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="__NAME__", description=DESCRIPTION)
    parser.add_argument("--name", default="world", help="who to greet")
    parser.add_argument("--shout", action="store_true", help="print in upper case")
    return parser


def greet(name: str, shout: bool = False) -> str:
    message = f"Hello, {name}! Welcome to {TITLE}."
    return message.upper() if shout else message


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    print(greet(args.name, args.shout))
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

_CLI_TEST = '''import unittest

from main import greet


class GreetTests(unittest.TestCase):
    def test_greet(self):
        self.assertIn("Hello, Ada", greet("Ada"))

    def test_shout(self):
        self.assertEqual(greet("a", True), greet("a").upper())


if __name__ == "__main__":
    unittest.main()
'''

_FLASK_APP = '''"""__NAME__ - Flask web application."""
import os

from flask import Flask, jsonify, render_template, request

TITLE = __TITLE_PY__
DESCRIPTION = __DESC_PY__

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html", title=TITLE, description=DESCRIPTION)


@app.get("/api/health")
def health():
    return jsonify(status="ok", app=TITLE)


@app.post("/api/echo")
def echo():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    if not text:
        return jsonify(error="Field 'text' is required."), 400
    return jsonify(text=text[:500], length=len(text))


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5000")))
'''

_FLASK_INDEX = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
  <main class="card">
    <h1>{{ title }}</h1>
    <p>{{ description }}</p>
    <input id="text" placeholder="Type something" maxlength="500">
    <button id="send">Send</button>
    <p id="out" aria-live="polite"></p>
  </main>
  <footer>__BRAND_HTML__</footer>
  <script src="{{ url_for('static', filename='app.js') }}"></script>
</body>
</html>
'''

_WEB_CSS = '''* { box-sizing: border-box; }
body { margin: 0; min-height: 100vh; display: grid; place-items: center; gap: 1rem;
  font-family: system-ui, sans-serif; background: #0d1117; color: #e6edf3; }
.card, main { width: min(560px, 92vw); padding: 1.5rem; border: 1px solid #263041;
  border-radius: 10px; background: #151b24; }
h1 { margin-top: 0; }
input { width: 100%; padding: .6rem; margin: .5rem 0; border-radius: 6px; border: 1px solid #2c3a4f;
  background: #0d1117; color: inherit; }
button { padding: .6rem 1.2rem; border: 0; border-radius: 6px; background: #3d8bff; color: #fff; cursor: pointer; }
button:focus-visible, input:focus-visible { outline: 2px solid #8ab4ff; outline-offset: 2px; }
footer { font-size: .8rem; color: #8b98a9; padding-bottom: 1rem; }
'''

_FLASK_JS = '''document.getElementById("send").addEventListener("click", async () => {
  const out = document.getElementById("out");
  const text = document.getElementById("text").value;
  try {
    const res = await fetch("/api/echo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    out.textContent = res.ok ? `Received ${data.length} characters: ${data.text}` : data.error;
  } catch (err) {
    out.textContent = "Request failed: " + err.message;
  }
});
'''

_STATIC_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE_HTML__</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main>
    <h1>__TITLE_HTML__</h1>
    <p>__DESC_HTML__</p>
    <button id="counter">Clicked 0 times</button>
  </main>
  <footer>__BRAND_HTML__</footer>
  <script src="__JS__"></script>
</body>
</html>
'''

_STATIC_JS = '''let clicks = 0;
const button = document.getElementById("counter");
button.addEventListener("click", () => {
  clicks += 1;
  button.textContent = `Clicked ${clicks} time${clicks === 1 ? "" : "s"}`;
});
'''


def _static_files(plan: Dict, prefix: str, js_name: str) -> Dict[str, str]:
    page = _fill(_STATIC_HTML, plan).replace("__JS__", js_name)
    return {f"{prefix}index.html": page, f"{prefix}style.css": _WEB_CSS, f"{prefix}{js_name}": _STATIC_JS}


def builtin_files(plan: Dict) -> Dict[str, str]:
    kind = plan["project_type"]
    if kind == "python-cli":
        return {"main.py": _fill(_CLI, plan), "tests/test_main.py": _CLI_TEST}
    if kind == "flask-web":
        return {
            "app.py": _fill(_FLASK_APP, plan),
            "templates/index.html": _fill(_FLASK_INDEX, plan),
            "static/style.css": _WEB_CSS,
            "static/app.js": _FLASK_JS,
        }
    if kind == "android-app":
        return _static_files(plan, "www/", "app.js")
    return _static_files(plan, "", "script.js")


# --------------------------------------------------------------------------
# AI generator
# --------------------------------------------------------------------------
class Generator:
    def __init__(self, client: OllamaClient | None = None):
        self.client = client

    def generate(self, plan: Dict, model: str | None, log: Callable[[str], None]) -> Dict[str, str]:
        if plan.get("mode") != "ai" or not self.client or not model:
            log("Using built-in template generator.")
            return builtin_files(plan)
        files: Dict[str, str] = {}
        specs: List[Dict] = plan["files"]
        for number, spec in enumerate(specs, 1):
            log(f"[{number}/{len(specs)}] Writing {spec['path']} ...")
            text = self.client.chat(prompts.file_messages(plan, spec, files), model)
            content = extract_code(text)
            if len(content.strip()) < 2:
                raise GenerationError(f"The model returned an empty file for {spec['path']}.")
            files[spec["path"]] = content
        return files
