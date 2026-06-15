# Contributing

Thanks for improving mcp-starter. Keep changes focused and testable.

## Setup

```bash
git clone https://github.com/MaiorMajor/mcp-starter.git && cd mcp-starter
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
mcp-starter init /path/to/test-vault
```

## Layout

| Path | Role |
|------|------|
| `src/mcp_starter/` | Python package (server, security, registry) |
| `skills/` | Example skills + `manifest.json` for typed MCP tools |
| `system_prompt.md` | Agent instructions loaded on MCP `initialize` |
| `skill_hints.json` | Routing keywords for `vault-dispatch` |
| `tests/` | `unittest` regression suite |

## Adding a skill

1. Create `skills/my-skill/main.py` (CLI entry, stdout JSON/text).
2. Optional: `skills/my-skill/manifest.json` to expose a typed MCP tool.
3. Add routing hints in `skill_hints.json` if dispatch should find it.
4. Run `pytest` and `ruff check src tests`.

## Pull requests

- One logical change per PR when possible.
- Include tests for behaviour changes.
- Do not commit `.env`, `oauth_clients.json`, or `refresh_tokens.json`.

## Release

Version lives in `pyproject.toml` and `src/mcp_starter/__init__.py`. Tag after merging to `main`.
