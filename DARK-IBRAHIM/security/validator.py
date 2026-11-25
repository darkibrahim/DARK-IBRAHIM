# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Validation helpers: names, prompts, file paths and secret scanning."""
from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import List

import config


class ValidationError(ValueError):
    """Raised when user supplied data is not acceptable."""


PROJECT_TYPES = ("python-cli", "flask-web", "static-website", "android-app")

ALLOWED_EXTENSIONS = {
    ".py", ".txt", ".md", ".json", ".html", ".css", ".js", ".sh", ".yml", ".yaml",
    ".toml", ".ini", ".cfg", ".xml", ".gradle", ".properties", ".java", ".kt",
    ".svg", ".csv", ".sql",
}
ALLOWED_NAMES = {
    "Dockerfile", "Makefile", "LICENSE", ".gitignore", ".env.example", ".gitkeep", "Procfile",
}
ALLOWED_HIDDEN_DIRS = {".github"}

_ID_RE = re.compile(r"^[a-f0-9]{32}$")
_PACKAGE_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
_JAVA_KEYWORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char", "class",
    "const", "continue", "default", "do", "double", "else", "enum", "extends", "final",
    "finally", "float", "for", "goto", "if", "implements", "import", "instanceof", "int",
    "interface", "long", "native", "new", "package", "private", "protected", "public",
    "return", "short", "static", "strictfp", "super", "switch", "synchronized", "this",
    "throw", "throws", "transient", "try", "void", "volatile", "while",
}


def slugify(name: str, default: str = "dark-project") -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", (name or "").strip()).strip("-_").lower()
    return slug[:50] or default


def validate_prompt(prompt) -> str:
    if not isinstance(prompt, str):
        raise ValidationError("Prompt must be text.")
    prompt = prompt.strip()
    if len(prompt) < 5:
        raise ValidationError("Describe your project in at least 5 characters.")
    if len(prompt) > config.MAX_PROMPT_CHARS:
        raise ValidationError(f"Prompt is too long (max {config.MAX_PROMPT_CHARS} characters).")
    if "\x00" in prompt:
        raise ValidationError("Prompt contains invalid characters.")
    return prompt


def validate_project_type(value):
    if value in (None, "", "auto"):
        return None
    if value not in PROJECT_TYPES:
        raise ValidationError(f"Unknown project type. Choose one of: {', '.join(PROJECT_TYPES)}.")
    return value


def validate_project_id(value) -> str:
    if not isinstance(value, str) or not _ID_RE.match(value):
        raise ValidationError("Invalid id.")
    return value


def validate_model_name(value) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}", value):
        raise ValidationError("Invalid model name.")
    return value


def safe_relative_path(path) -> str:
    """Return a normalised relative POSIX path or raise ValidationError."""
    if not isinstance(path, str) or not path.strip():
        raise ValidationError("Empty file path.")
    p = path.strip().replace("\\", "/")
    if len(p) > 200 or "\x00" in p or p.startswith(("/", "~")) or re.match(r"^[A-Za-z]:", p):
        raise ValidationError(f"Unsafe file path: {path!r}")
    parts = [x for x in p.split("/") if x not in ("", ".")]
    if not parts or ".." in parts:
        raise ValidationError(f"Unsafe file path: {path!r}")
    for index, part in enumerate(parts):
        if part.startswith("."):
            is_last = index == len(parts) - 1
            if not ((is_last and part in ALLOWED_NAMES) or (not is_last and part in ALLOWED_HIDDEN_DIRS)):
                raise ValidationError(f"Hidden path not allowed: {path!r}")
    name = parts[-1]
    suffix = PurePosixPath(name).suffix.lower()
    if name not in ALLOWED_NAMES and suffix not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"File type not allowed: {path!r}")
    return "/".join(parts)


def validate_package_name(value) -> str:
    if not isinstance(value, str) or len(value) > 80 or not _PACKAGE_RE.match(value):
        raise ValidationError("Invalid Android package name (example: com.example.myapp).")
    if any(seg in _JAVA_KEYWORDS for seg in value.split(".")):
        raise ValidationError("Package name contains a reserved Java keyword.")
    return value


def validate_app_name(value) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("App name is required.")
    value = value.strip()
    if len(value) > 40 or re.search(r"[<>&\"'\\/\x00-\x1f]", value):
        raise ValidationError("App name must be 1-40 characters without < > & quotes or slashes.")
    return value


_SECRET_PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}"), "API secret key"),
    (re.compile(r"\bghp_[A-Za-z0-9]{30,}"), "GitHub token"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private key"),
    (
        re.compile(r"""(?i)\b(?:api[_-]?key|secret|password|passwd|token)\b\s*[=:]\s*["']([^"'\s]{8,})["']"""),
        "hardcoded credential",
    ),
]
_PLACEHOLDER_HINTS = ("your", "change", "example", "xxx", "<", "os.environ", "getenv", "placeholder", "***")


def scan_for_secrets(path: str, content: str) -> List[str]:
    findings: List[str] = []
    for regex, label in _SECRET_PATTERNS:
        for match in regex.finditer(content):
            value = match.group(1) if match.groups() else match.group(0)
            if any(hint in value.lower() for hint in _PLACEHOLDER_HINTS):
                continue
            findings.append(f"{path}: possible {label}")
            break
    return findings
