"""Resolve repo root (skills/, system_prompt.md) for clone and editable installs."""
from __future__ import annotations

import os
from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    env = os.getenv("MCP_REPO_ROOT", "").strip()
    if env:
        return Path(env).resolve()
    current = (start or Path(__file__).resolve().parent)
    for candidate in (current, *current.parents):
        if (candidate / "skills").is_dir() and (candidate / "system_prompt.md").is_file():
            return candidate
    return current.parents[1]
