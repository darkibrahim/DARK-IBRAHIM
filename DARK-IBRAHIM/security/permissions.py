# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Android permission policy.

Only a small allow-list of low-risk permissions can be put in a generated app.
Surveillance-style permissions are refused on purpose.
"""
from __future__ import annotations

from typing import Iterable, List, Tuple

PREFIX = "android.permission."

ALLOWED = {
    "INTERNET", "ACCESS_NETWORK_STATE", "ACCESS_WIFI_STATE", "VIBRATE", "WAKE_LOCK",
    "POST_NOTIFICATIONS",
}
BLOCKED = {
    "READ_SMS", "SEND_SMS", "RECEIVE_SMS", "RECEIVE_MMS", "READ_CALL_LOG", "WRITE_CALL_LOG",
    "PROCESS_OUTGOING_CALLS", "READ_CONTACTS", "WRITE_CONTACTS", "BIND_ACCESSIBILITY_SERVICE",
    "BIND_DEVICE_ADMIN", "SYSTEM_ALERT_WINDOW", "REQUEST_INSTALL_PACKAGES", "READ_PHONE_STATE",
    "RECORD_AUDIO", "CAMERA", "ACCESS_BACKGROUND_LOCATION", "MANAGE_EXTERNAL_STORAGE",
}
DEFAULT_PERMISSIONS = ["INTERNET", "ACCESS_NETWORK_STATE"]


def _short(name: str) -> str:
    name = str(name).strip()
    return name[len(PREFIX):] if name.startswith(PREFIX) else name


def filter_permissions(requested: Iterable[str] | None) -> Tuple[List[str], List[str]]:
    """Return (allowed full names, rejected reasons)."""
    names = [_short(p) for p in (requested or []) if str(p).strip()] or list(DEFAULT_PERMISSIONS)
    allowed: List[str] = []
    rejected: List[str] = []
    for short in names:
        key = short.upper()
        if key in ALLOWED:
            full = PREFIX + key
            if full not in allowed:
                allowed.append(full)
        elif key in BLOCKED:
            rejected.append(f"{short}: blocked (sensitive permission)")
        else:
            rejected.append(f"{short}: not on the allow-list")
    if not allowed:
        allowed = [PREFIX + p for p in DEFAULT_PERMISSIONS]
    return allowed, rejected
