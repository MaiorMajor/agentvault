---
title: MCP System Prompt — Boot Sequence
type: meta
updated: 2026-06-15
audience: [mcp-agents]
---

# MCP System Prompt

> This file is read by the MCP server on `initialize` and sent as `instructions` to every connecting agent.
> Edit here = change agent behaviour for all MCP clients without redeploying the server.

---

## Prompt (copied into the `instructions` field)

```
Obsidian vault (markdown). Point VAULT_PATH at your vault root.

## Boot protocol

1. `session_start()` — ONCE at conversation start (do not repeat). Slim router from `_README.router.md` or `_README.md` (~400 tok) + `datetime`. Reuse `response.datetime` — do NOT call `get_current_datetime` afterward.
2. For routing / "where does this go?" / skill hints: `run_skill("vault-dispatch", ["<query>"])` — do not read CONTEXT.md routing tables.
3. For file discovery (recent files, PDFs, binaries): `find_files` (MCP) or `run_skill("vault-find", ...)`.
4. For detailed workspace context: `read_note("<destination>/CONTEXT.md")` only after dispatch confirms the destination.

## Minimal rules (non-negotiable)

Core guardrails (_PRIVADO blind, inbox immutable, confirm before bulk deletes) come from the router in `session_start()`.

- `read_note` / `search_notes` cover `.md` only. PDFs, docx, code, etc.: `find_files` (metadata) first.
- **Structured JSON / JSONL:** `read_json` (schema-first: schema → list → get) or `read_jsonl` (line pagination). NEVER `read_note` on `.json`/`.jsonl` — truncates from the start and loses the tail.
- Relational queries (backlinks, hubs, paths): `run_skill("vault-graph", ["query", "<subcmd>", ...])` — subcmd required. NEVER load `99_meta/vault-graph.json` into context.

## Writing notes

- Prefer `edit_note` / `bulk_read`; use `write_note` create/update/append as appropriate.
- `list_folder` before creating new paths.

## Skills (via run_skill)

Start with `run_skill("vault-dispatch", ["<query>"])` — returns destination + applicable skills (1–3), zero LLM tokens.

Included example skills: `vault-dispatch`, `vault-find`, `vault-graph`. Add more under `skills/` — discovered by name if they have `main.py`.

## Token discipline (server-enforced caps)

- Order: vault-dispatch → find_files / vault-find / vault-graph → read_note on concrete paths → `search_notes` last resort (capped ~30 results).
- Recent / non-md files: `find_files(today=true)` or `find_files(ext=".pdf")` — avoid recursive `list_folder` on inbox.
- Truncated responses include a `hint` naming the cheaper next tool.
```
