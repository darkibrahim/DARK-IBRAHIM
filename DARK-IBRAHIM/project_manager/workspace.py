# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Per-project working folders inside the workspace directory."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

import config
from security.validator import slugify, validate_project_id


class Workspace:
    def __init__(self, base: Optional[Path] = None):
        self.base = Path(base or config.WORKSPACE_DIR).resolve()

    def create(self, project_id: str, name: str) -> Path:
        validate_project_id(project_id)
        root = (self.base / project_id / slugify(name)).resolve()
        if self.base not in root.parents:
            raise ValueError("Invalid workspace path")
        root.mkdir(parents=True, exist_ok=True)
        return root

    def root_of(self, project_id: str) -> Optional[Path]:
        validate_project_id(project_id)
        folder = self.base / project_id
        if not folder.is_dir():
            return None
        children = [p for p in folder.iterdir() if p.is_dir()]
        return children[0] if children else None

    def remove(self, project_id: str) -> None:
        validate_project_id(project_id)
        folder = (self.base / project_id).resolve()
        if folder.parent == self.base and folder.is_dir():
            shutil.rmtree(folder, ignore_errors=True)
