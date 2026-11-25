# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Validation of generated Android projects and built APK files."""
from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Dict, List

ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


def validate_project(project_dir: Path) -> Dict:
    """Structural checks on an Android project folder (no SDK needed)."""
    project_dir, problems = Path(project_dir), []
    manifest = project_dir / "app/src/main/AndroidManifest.xml"
    for rel in ("settings.gradle", "build.gradle", "app/build.gradle", "app/src/main/assets/www/index.html"):
        if not (project_dir / rel).is_file():
            problems.append(f"Missing {rel}")
    package = None
    if manifest.is_file():
        try:
            root = ET.parse(manifest).getroot()
            if root.find("application") is None:
                problems.append("Manifest has no <application>")
            names = [p.get(ANDROID_NS + "name", "") for p in root.findall("uses-permission")]
            package = None
            gradle = (project_dir / "app/build.gradle")
            if gradle.is_file() and "namespace '" in gradle.read_text(encoding="utf-8"):
                package = gradle.read_text(encoding="utf-8").split("namespace '")[1].split("'")[0]
            if package and not (project_dir / "app/src/main/java" / package.replace(".", "/") / "MainActivity.java").is_file():
                problems.append("MainActivity.java is not in the package folder")
        except ET.ParseError as exc:
            problems.append(f"Manifest is not valid XML: {exc}")
            names = []
    else:
        problems.append("Missing AndroidManifest.xml")
        names = []
    return {"valid": not problems, "problems": problems, "package": package, "permissions": names}


def validate_apk(apk_path: Path) -> Dict:
    """Checks that an APK is a healthy ZIP containing a manifest and compiled code."""
    apk_path, checks = Path(apk_path), []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    if not apk_path.is_file() or apk_path.stat().st_size == 0:
        add("file exists", False, "missing or empty")
        return {"valid": False, "checks": checks}
    add("file exists", True, f"{apk_path.stat().st_size} bytes")
    try:
        with zipfile.ZipFile(apk_path) as zf:
            bad = zf.testzip()
            add("zip integrity", bad is None, bad or "OK")
            names: List[str] = zf.namelist()
    except zipfile.BadZipFile as exc:
        add("zip integrity", False, str(exc))
        return {"valid": False, "checks": checks}
    add("AndroidManifest.xml", "AndroidManifest.xml" in names)
    add("classes.dex", any(n.startswith("classes") and n.endswith(".dex") for n in names))
    add("web assets", any(n.startswith("assets/www/") for n in names))
    signed = any(n.startswith("META-INF/") and n.endswith((".RSA", ".EC", ".DSA", ".SF")) for n in names)
    add("signature files", signed, "v1 signature present" if signed else "no v1 signature (may be v2-only or unsigned)")
    required = ("zip integrity", "AndroidManifest.xml", "classes.dex")
    return {"valid": all(c["ok"] for c in checks if c["name"] in required), "checks": checks}
