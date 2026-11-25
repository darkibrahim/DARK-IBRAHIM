# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Choose and manage Ollama models."""
from __future__ import annotations

from typing import Dict, List, Optional

import config
from ai_engine.ollama_client import OllamaClient, OllamaError
from security.validator import validate_model_name


class ModelManager:
    def __init__(self, client: Optional[OllamaClient] = None):
        self.client = client or OllamaClient()

    def installed(self) -> List[str]:
        try:
            return [m.get("name", "") for m in self.client.list_models() if m.get("name")]
        except OllamaError:
            return []

    def overview(self) -> Dict:
        available = self.client.is_available()
        installed = self.installed() if available else []
        return {
            "ollama_available": available,
            "host": self.client.host,
            "installed": installed,
            "default": config.DEFAULT_MODEL,
            "recommended": config.RECOMMENDED_MODELS,
            "resolved": self.resolve(None, installed) if installed else None,
        }

    def resolve(self, preferred: Optional[str], installed: Optional[List[str]] = None) -> Optional[str]:
        """Return a model that is really installed, or None."""
        installed = installed if installed is not None else self.installed()
        if not installed:
            return None
        for wanted in (preferred, config.DEFAULT_MODEL):
            if wanted and wanted in installed:
                return wanted
        for name in installed:
            if any(tag in name.lower() for tag in ("coder", "code")):
                return name
        return installed[0]

    def pull(self, model: str) -> str:
        return self.client.pull(validate_model_name(model))
