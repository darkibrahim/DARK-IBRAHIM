# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Detects Java / Gradle / Android SDK and runs Gradle (no shell, fixed arguments)."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _run(cmd: List[str], timeout: int = 20) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (result.stdout + result.stderr).strip()


def find_java() -> Tuple[Optional[str], Optional[int]]:
    java = shutil.which("java")
    if not java:
        return None, None
    match = re.search(r'version "(\d+)', _run([java, "-version"]))
    return java, int(match.group(1)) if match else None


def find_gradle() -> Tuple[Optional[str], Optional[str]]:
    candidates = [shutil.which("gradle")]
    home = os.environ.get("GRADLE_HOME")
    if home:
        candidates.insert(0, str(Path(home) / "bin" / "gradle"))
    for path in candidates:
        if path and Path(path).exists():
            match = re.search(r"Gradle (\d+\.\d+(?:\.\d+)?)", _run([path, "--version"], timeout=60))
            return path, match.group(1) if match else None
    return None, None


def find_android_sdk() -> Optional[Path]:
    options = [os.environ.get("ANDROID_HOME"), os.environ.get("ANDROID_SDK_ROOT"),
               str(Path.home() / "Android" / "Sdk"), str(Path.home() / "Library" / "Android" / "sdk"),
               "/opt/android-sdk", "/usr/lib/android-sdk"]
    for option in options:
        if option and (Path(option) / "platforms").is_dir():
            return Path(option)
    return None


def check_environment() -> Dict:
    java, java_major = find_java()
    gradle, gradle_version = find_gradle()
    sdk = find_android_sdk()
    problems = []
    if not java or (java_major or 0) < 17:
        problems.append("JDK 17 or newer is required.")
    if not gradle:
        problems.append("Gradle 8.2+ is not installed.")
    elif gradle_version and int(gradle_version.split(".")[0]) < 8:
        problems.append(f"Gradle {gradle_version} is too old (need 8.2+).")
    if not sdk:
        problems.append("Android SDK not found (set ANDROID_HOME).")
    return {"java": java_major, "gradle": gradle_version, "android_sdk": bool(sdk),
            "ready": not problems, "problems": problems}


def write_local_properties(project_dir: Path, sdk: Path) -> None:
    escaped = str(sdk).replace("\\", "\\\\")
    (project_dir / "local.properties").write_text(f"sdk.dir={escaped}\n", encoding="utf-8")


def build(project_dir: Path, task: str = "assembleDebug", timeout: int = 1800) -> Tuple[bool, str, Optional[Path]]:
    """Run Gradle. Returns (success, log tail, apk path)."""
    if task not in ("assembleDebug", "assembleRelease"):
        raise ValueError("Unsupported Gradle task")
    gradle, _ = find_gradle()
    sdk = find_android_sdk()
    if not gradle or not sdk:
        return False, "Gradle or the Android SDK is not available.", None
    write_local_properties(project_dir, sdk)
    env = {**os.environ, "ANDROID_HOME": str(sdk)}
    try:
        result = subprocess.run([gradle, "--console=plain", "--no-daemon", task], cwd=project_dir,
                                capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return False, "Gradle build timed out.", None
    log = (result.stdout + "\n" + result.stderr)[-8000:]
    if result.returncode != 0:
        return False, log, None
    variant = "debug" if task == "assembleDebug" else "release"
    apks = sorted((project_dir / "app" / "build" / "outputs" / "apk" / variant).glob("*.apk"))
    return (True, log, apks[0]) if apks else (False, log + "\nNo APK was produced.", None)
