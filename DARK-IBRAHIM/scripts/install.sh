#!/usr/bin/env bash
# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
# DARK-IBRAHIM installer - Kali / Debian / Ubuntu, Arch, Termux (Android).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[*] DARK-IBRAHIM installer"

install_python() {
  if command -v python3 >/dev/null 2>&1 && python3 -c "import venv" >/dev/null 2>&1; then
    return
  fi
  echo "[*] Installing Python 3 ..."
  if [ -n "${PREFIX:-}" ] && [[ "$PREFIX" == *com.termux* ]]; then
    pkg install -y python
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --needed --noconfirm python python-pip
  else
    echo "[!] Unsupported system. Install Python 3.9+ manually and run this script again." >&2
    exit 1
  fi
}

install_python

echo "[*] Creating virtual environment (.venv) ..."
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

[ -f .env ] || cp .env.example .env
mkdir -p workspace output/projects output/apk output/logs database

echo
echo "[+] Installed."
echo "    Start it with:  ./scripts/run.sh   then open http://127.0.0.1:5000"
echo
echo "[i] Optional but recommended: install Ollama (free, local AI) from https://ollama.com"
echo "    then run:  ollama pull qwen2.5-coder:7b"
echo "    Without Ollama the tool still works with built-in offline templates."
