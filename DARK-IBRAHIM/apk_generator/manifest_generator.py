# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""AndroidManifest.xml generation."""
from __future__ import annotations

from typing import Iterable, List
from xml.sax.saxutils import quoteattr

from security.permissions import filter_permissions
from security.validator import validate_package_name


def generate_manifest(package: str, permissions: Iterable[str] | None = None) -> str:
    package = validate_package_name(package)
    allowed: List[str]
    allowed, _rejected = filter_permissions(permissions)
    perms = "\n".join(f"    <uses-permission android:name={quoteattr(p)} />" for p in allowed)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

{perms}

    <application
        android:allowBackup="false"
        android:icon="@drawable/ic_launcher"
        android:label="@string/app_name"
        android:usesCleartextTraffic="false"
        android:theme="@style/AppTheme">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:configChanges="orientation|screenSize|keyboardHidden">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""
