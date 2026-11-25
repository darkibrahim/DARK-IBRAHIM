# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Builds an Android Studio / Gradle project that wraps a static web app."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, Optional

import config
from apk_generator.manifest_generator import generate_manifest
from security.validator import slugify, validate_app_name, validate_package_name

TEMPLATES = Path(__file__).resolve().parent / "templates"


def default_package(name: str) -> str:
    """A valid package name such as com.darkibrahim.mynotes."""
    tail = re.sub(r"[^a-z0-9]", "", name.lower())
    if not tail or not tail[0].isalpha():
        tail = "app" + tail
    return validate_package_name(f"com.darkibrahim.{tail[:30]}")


def _template(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def _render(text: str, values: Dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def _android_string(value: str) -> str:
    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    value = value.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
    return "\\" + value if value[:1] in "@?" else value


def web_root(files: Dict[str, str]) -> Optional[str]:
    """Folder prefix ('' or 'www/') that holds a static index.html (no template syntax)."""
    for prefix in ("www/", "public/", "static-site/", ""):
        page = files.get(prefix + "index.html")
        if page is not None and "{{" not in page and "{%" not in page:
            return prefix
    return None


def build_project_files(app_name: str, package: str, project_files: Dict[str, str],
                        permissions: Iterable[str] | None = None, version_name: str = "1.0.0",
                        version_code: int = 1) -> Dict[str, str]:
    """Return {path: text} for a complete Android project, prefixed with 'android/'."""
    app_name = validate_app_name(app_name)
    package = validate_package_name(package)
    prefix = web_root(project_files)
    if prefix is None:
        raise ValueError("No static web app found: the project needs a plain index.html "
                         "(in www/ or the project root).")
    values = {
        "PACKAGE": package, "APP_LABEL": _android_string(app_name), "PROJECT_SLUG": slugify(app_name, "app"),
        "VERSION_NAME": re.sub(r"[^0-9A-Za-z.\-]", "", version_name) or "1.0.0",
        "VERSION_CODE": str(max(1, int(version_code))), "BRAND": config.brand_block(),
    }
    java_dir = "android/app/src/main/java/" + package.replace(".", "/")
    out = {
        "android/settings.gradle": _render(_template("settings.gradle.tpl"), values),
        "android/build.gradle": _template("build.gradle.tpl"),
        "android/gradle.properties": _template("gradle.properties.tpl"),
        "android/app/build.gradle": _render(_template("app_build.gradle.tpl"), values),
        "android/app/src/main/AndroidManifest.xml": generate_manifest(package, permissions),
        f"{java_dir}/MainActivity.java": _render(_template("MainActivity.java.tpl"), values),
        "android/app/src/main/res/values/strings.xml": _render(_template("strings.xml.tpl"), values),
        "android/app/src/main/res/values/styles.xml": _template("styles.xml.tpl"),
        "android/app/src/main/res/drawable/ic_launcher.xml": _template("ic_launcher.xml.tpl"),
        "android/README.md": _render(_template("README_ANDROID.md.tpl"), values),
        ".github/workflows/build-apk.yml": _template("build-apk.yml.tpl"),
    }
    for path, content in project_files.items():
        if prefix and not path.startswith(prefix):
            continue
        rel = path[len(prefix):]
        if rel.endswith((".html", ".css", ".js", ".json", ".svg", ".txt", ".md")):
            out[f"android/app/src/main/assets/www/{rel}"] = content
    return out


def write_project(dest: Path, files: Dict[str, str]) -> Path:
    """Write a project produced by build_project_files() below `dest`."""
    dest = Path(dest).resolve()
    for rel, content in files.items():
        target = (dest / rel).resolve()
        if dest not in target.parents:
            raise ValueError(f"Unsafe path: {rel}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    return dest / "android"
