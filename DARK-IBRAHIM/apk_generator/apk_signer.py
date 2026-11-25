# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Signs release APKs with apksigner. Keystore secrets stay outside the code."""
from __future__ import annotations

import os
import secrets
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

import config
from apk_generator.gradle_manager import find_android_sdk

ALIAS = "dark-ibrahim"


def _build_tool(name: str) -> Optional[str]:
    found = shutil.which(name)
    if found:
        return found
    sdk = find_android_sdk()
    if sdk and (sdk / "build-tools").is_dir():
        for version in sorted((sdk / "build-tools").iterdir(), reverse=True):
            candidate = version / name
            if candidate.exists():
                return str(candidate)
    return None


def _password() -> str:
    """DARK_KEYSTORE_PASSWORD, or a random one kept (chmod 600) next to the keystore."""
    env = os.environ.get("DARK_KEYSTORE_PASSWORD")
    if env:
        return env
    config.KEYSTORE_DIR.mkdir(parents=True, exist_ok=True)
    path = config.KEYSTORE_DIR / ".password"
    if not path.exists():
        path.write_text(secrets.token_urlsafe(24), encoding="utf-8")
        path.chmod(0o600)
    return path.read_text(encoding="utf-8").strip()


def ensure_keystore() -> Path:
    keystore = config.KEYSTORE_DIR / "release.keystore"
    if keystore.exists():
        return keystore
    keytool = shutil.which("keytool")
    if not keytool:
        raise RuntimeError("keytool (JDK) is required to create a signing key.")
    config.KEYSTORE_DIR.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "DARK_KS_PASS": _password()}
    subprocess.run(
        [keytool, "-genkeypair", "-keystore", str(keystore), "-alias", ALIAS, "-keyalg", "RSA",
         "-keysize", "2048", "-validity", "10000", "-storepass:env", "DARK_KS_PASS",
         "-keypass:env", "DARK_KS_PASS", "-dname", "CN=DARK IBRAHIM, O=DARK-IBRAHIM, C=US"],
        check=True, capture_output=True, text=True, env=env, timeout=60,
    )
    keystore.chmod(0o600)
    return keystore


def sign(unsigned_apk: Path, signed_apk: Path) -> Tuple[bool, str]:
    apksigner, zipalign = _build_tool("apksigner"), _build_tool("zipalign")
    if not apksigner or not zipalign:
        return False, "apksigner/zipalign not found (install Android build-tools)."
    aligned = signed_apk.with_suffix(".aligned.apk")
    try:
        subprocess.run([zipalign, "-f", "-p", "4", str(unsigned_apk), str(aligned)],
                       check=True, capture_output=True, text=True, timeout=120)
        env = {**os.environ, "DARK_KS_PASS": _password()}
        subprocess.run([apksigner, "sign", "--ks", str(ensure_keystore()), "--ks-key-alias", ALIAS,
                        "--ks-pass", "env:DARK_KS_PASS", "--out", str(signed_apk), str(aligned)],
                       check=True, capture_output=True, text=True, timeout=120, env=env)
        verify = subprocess.run([apksigner, "verify", str(signed_apk)], capture_output=True, text=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, RuntimeError, OSError) as exc:
        return False, f"Signing failed: {exc}"
    finally:
        aligned.unlink(missing_ok=True)
    return verify.returncode == 0, "Signed and verified." if verify.returncode == 0 else verify.stderr[:300]
