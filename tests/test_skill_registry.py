#!/usr/bin/env python3
"""Tests for skill manifest registry."""
from __future__ import annotations

import unittest
from pathlib import Path

from mcp_starter import skill_registry


class TestSkillRegistry(unittest.TestCase):
    def test_discover_manifests_in_repo(self) -> None:
        root = Path(__file__).resolve().parents[1] / "skills"
        manifests = skill_registry.discover_manifests(root)
        names = {m.name for m in manifests}
        self.assertEqual(names, {"vault_dispatch", "vault_find", "vault_graph"})

    def test_vault_dispatch_argv(self) -> None:
        root = Path(__file__).resolve().parents[1] / "skills"
        manifest = next(m for m in skill_registry.discover_manifests(root) if m.name == "vault_dispatch")
        argv = skill_registry.args_to_argv(manifest, {"query": "routing test", "top": 2, "output": "json"})
        self.assertEqual(argv, ["routing test", "--top", "2", "--output", "json"])

    def test_vault_graph_query_argv(self) -> None:
        root = Path(__file__).resolve().parents[1] / "skills"
        manifest = next(m for m in skill_registry.discover_manifests(root) if m.name == "vault_graph")
        argv = skill_registry.args_to_argv(
            manifest, {"subcommand": "backlinks", "note": "PROFILE", "limit": 10}
        )
        self.assertEqual(argv, ["query", "backlinks", "PROFILE", "--json", "--limit", "10"])


if __name__ == "__main__":
    unittest.main()
