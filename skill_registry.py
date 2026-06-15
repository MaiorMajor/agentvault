"""Discover skill manifests and expose them as typed MCP tools."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class SkillManifest:
    name: str
    skill_dir: str
    description: str
    input_schema: dict[str, Any]
    annotations: dict[str, bool]
    argv_map: dict[str, dict[str, Any]]
    fixed_argv: list[str]
    argv_builder: str | None
    manifest_path: Path


def _load_manifest(path: Path) -> SkillManifest:
    raw = json.loads(path.read_text(encoding="utf-8"))
    name = str(raw["name"])
    skill_dir = str(raw.get("skill_dir") or path.parent.name)
    return SkillManifest(
        name=name,
        skill_dir=skill_dir,
        description=str(raw.get("description", "")),
        input_schema=dict(raw.get("inputSchema") or {}),
        annotations=dict(raw.get("annotations") or {}),
        argv_map=dict(raw.get("argv_map") or {}),
        fixed_argv=[str(x) for x in (raw.get("fixed_argv") or [])],
        argv_builder=raw.get("argv_builder"),
        manifest_path=path,
    )


def discover_manifests(skills_root: Path) -> list[SkillManifest]:
    manifests: list[SkillManifest] = []
    for path in sorted(skills_root.rglob("manifest.json")):
        if "_shared" in path.parts:
            continue
        manifests.append(_load_manifest(path))
    names = [m.name for m in manifests]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        raise RuntimeError(f"Duplicate skill manifest tool names: {sorted(dupes)}")
    return manifests


def manifest_to_mcp_tool(m: SkillManifest) -> dict[str, Any]:
    return {
        "name": m.name,
        "title": m.name.replace("_", " ").title(),
        "description": m.description,
        "annotations": m.annotations,
        "inputSchema": m.input_schema,
    }


def _append_flag(argv: list[str], flag: str, value: Any, spec: dict[str, Any]) -> None:
    if spec.get("boolean"):
        if value:
            argv.append(flag)
        return
    if value is None or value == "":
        return
    argv.extend([flag, str(value)])


def build_argv_vault_graph(args: dict[str, Any]) -> list[str]:
    sub = str(args.get("subcommand", "")).strip()
    if not sub:
        raise ValueError("subcommand is required")

    if sub == "build":
        argv: list[str] = []
        if args.get("dry_run"):
            argv.append("--dry-run")
        return argv

    argv = ["query", sub]
    note = args.get("note")
    tag = args.get("tag")
    pattern = args.get("pattern")
    from_note = args.get("from_note")
    to_note = args.get("to_note")

    if sub in {"backlinks", "forward", "neighbors", "node"}:
        if not note:
            raise ValueError(f"note is required for subcommand {sub}")
        argv.append(str(note))
    elif sub == "tag":
        if not tag:
            raise ValueError("tag is required for tag subcommand")
        argv.append(str(tag))
    elif sub == "find":
        if not pattern:
            raise ValueError("pattern is required for find subcommand")
        argv.append(str(pattern))
    elif sub == "path":
        if not from_note or not to_note:
            raise ValueError("from_note and to_note are required for path subcommand")
        argv.extend([str(from_note), str(to_note)])

    argv.append("--json")

    if args.get("top") is not None:
        argv.extend(["--top", str(int(args["top"]))])
    if args.get("limit") is not None:
        argv.extend(["--limit", str(int(args["limit"]))])
    if args.get("depth") is not None:
        argv.extend(["--depth", str(int(args["depth"]))])
    if args.get("direction"):
        argv.extend(["--direction", str(args["direction"])])
    return argv


_ARGV_BUILDERS: dict[str, Callable[[dict[str, Any]], list[str]]] = {
    "vault_graph": build_argv_vault_graph,
}


def args_to_argv(manifest: SkillManifest, args: dict[str, Any]) -> list[str]:
    if manifest.argv_builder:
        builder = _ARGV_BUILDERS.get(manifest.argv_builder)
        if builder is None:
            raise ValueError(f"Unknown argv_builder: {manifest.argv_builder}")
        argv = builder(args or {})
    else:
        argv = []
        positional: list[tuple[int, str]] = []
        for key, spec in manifest.argv_map.items():
            value = (args or {}).get(key)
            if spec.get("positional"):
                if value is not None and str(value) != "":
                    positional.append((int(spec.get("order", 0)), str(value)))
                continue
            flag = spec.get("flag") or f"--{key.replace('_', '-')}"
            _append_flag(argv, flag, value, spec)
        for _, val in sorted(positional):
            argv.insert(0, val)
    return manifest.fixed_argv + argv


def skill_dir_for(manifests: list[SkillManifest], tool_name: str) -> str | None:
    for m in manifests:
        if m.name == tool_name:
            return m.skill_dir
    return None
