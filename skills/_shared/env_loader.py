"""Shared env loader for vault skills.

Priority, without overriding variables already present in the process:
1. VAULT_SECRETS_FILE, when set.
2. <vault>/50_infra/secrets/.env.
3. ~/.vault-secrets.env.
4. <skill>/.env as a legacy fallback.

The loader only returns metadata about files and counts. It never returns
secret values.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def find_vault_root(start: Path) -> Path | None:
    """Find the vault root from a skill path."""
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "50_infra").is_dir() and (candidate / "99_meta").exists():
            return candidate
    return None


def _parse_env_line(raw: str) -> tuple[str, str] | None:
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None
    if line.startswith("export "):
        line = line[len("export ") :].strip()
    key, value = line.split("=", 1)
    key = key.strip()
    if not key:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def load_env_file(path: Path) -> dict[str, Any]:
    """Load KEY=VALUE pairs from path without overriding os.environ."""
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "read": False,
        "vars_seen": 0,
        "vars_set": 0,
        "vars_skipped_encrypted": 0,
    }
    if not path.exists():
        return result

    for raw in path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(raw)
        if not parsed:
            continue
        key, value = parsed
        result["vars_seen"] += 1
        if value.startswith("encrypted:"):
            result["vars_skipped_encrypted"] += 1
            continue
        if key not in os.environ:
            os.environ[key] = value
            result["vars_set"] += 1

    result["read"] = True
    return result


def load_skill_env(skill_dir: Path | str, include_legacy_local: bool = True) -> dict[str, Any]:
    """Load the shared vault secrets for a skill.

    Existing environment variables always win. Central secrets are preferred
    over per-skill .env files so rotation can happen in one place.
    """
    skill_path = Path(skill_dir).resolve()
    vault_root = find_vault_root(skill_path)

    candidates: list[tuple[str, Path]] = []
    explicit = os.environ.get("VAULT_SECRETS_FILE", "").strip()
    if explicit:
        candidates.append(("explicit", Path(explicit).expanduser()))
    if vault_root:
        candidates.append(("vault_central", vault_root / "50_infra" / "secrets" / ".env"))
    candidates.append(("home_central", Path.home() / ".vault-secrets.env"))
    if include_legacy_local:
        candidates.append(("local_legacy", skill_path / ".env"))

    seen: set[Path] = set()
    status: dict[str, Any] = {"vault_root": str(vault_root) if vault_root else None, "sources": {}}
    for label, path in candidates:
        resolved = path.resolve() if path.exists() else path.absolute()
        if resolved in seen:
            continue
        seen.add(resolved)
        status["sources"][label] = load_env_file(path)
    return status
