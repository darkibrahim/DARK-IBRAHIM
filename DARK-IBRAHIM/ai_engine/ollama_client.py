# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Minimal Ollama HTTP client (https://github.com/ollama/ollama/blob/main/docs/api.md)."""
from __future__ import annotations

from typing import Dict, List, Optional

import requests

import config


class OllamaError(RuntimeError):
    """Raised when Ollama is unreachable or returns an error."""


class OllamaClient:
    def __init__(self, host: Optional[str] = None, timeout: Optional[int] = None):
        self.host = (host or config.OLLAMA_HOST).rstrip("/")
        self.timeout = timeout or config.REQUEST_TIMEOUT

    def is_available(self) -> bool:
        try:
            return requests.get(f"{self.host}/api/tags", timeout=3).status_code == 200
        except requests.RequestException:
            return False

    def list_models(self) -> List[Dict]:
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            resp.raise_for_status()
            return resp.json().get("models", [])
        except (requests.RequestException, ValueError) as exc:
            raise OllamaError(f"Cannot reach Ollama at {self.host}: {exc}") from exc

    def chat(self, messages: List[Dict], model: str, temperature: float = 0.2,
             json_mode: bool = False) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": 8192},
        }
        if json_mode:
            payload["format"] = "json"
        try:
            resp = requests.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
            if resp.status_code != 200:
                raise OllamaError(f"Ollama error {resp.status_code}: {resp.text[:300]}")
            return resp.json()["message"]["content"]
        except requests.RequestException as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc
        except (KeyError, ValueError) as exc:
            raise OllamaError(f"Unexpected Ollama response: {exc}") from exc

    def pull(self, model: str) -> str:
        try:
            resp = requests.post(
                f"{self.host}/api/pull", json={"model": model, "stream": False}, timeout=3600
            )
            if resp.status_code != 200:
                raise OllamaError(f"Pull failed ({resp.status_code}): {resp.text[:300]}")
            return resp.json().get("status", "success")
        except requests.RequestException as exc:
            raise OllamaError(f"Pull failed: {exc}") from exc
