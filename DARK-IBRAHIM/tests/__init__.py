# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Test package. Redirects all data to a temporary folder before anything imports config."""
import atexit
import os
import shutil
import tempfile

_TMP = tempfile.mkdtemp(prefix="dark-ibrahim-tests-")
os.environ["DARK_DATA_DIR"] = _TMP
os.environ["OLLAMA_HOST"] = "http://127.0.0.1:9"  # nothing listens here: forces offline mode
atexit.register(shutil.rmtree, _TMP, ignore_errors=True)
