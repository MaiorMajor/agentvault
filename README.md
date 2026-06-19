# AgentVault

> A bounded, deterministic MCP runtime for Obsidian and Markdown knowledge bases.

[![status](https://img.shields.io/badge/status-public%20beta%20v1.16.0-success)](./CHANGELOG.md)
[![protocol](https://img.shields.io/badge/MCP-2025--11--25-blue)](https://modelcontextprotocol.io)
[![python](https://img.shields.io/badge/python-3.11+-3776ab)](https://www.python.org)
![transport](https://img.shields.io/badge/transport-SSE%20%2B%20Streamable%20HTTP-orange)
[![license](https://img.shields.io/badge/license-MIT-lightgrey)](./LICENSE)

AgentVault turns a Markdown folder into operational infrastructure for AI agents. Instead of letting a model rummage through an entire vault, it exposes narrow tools for finding, reading, routing, editing and querying links — with bounded responses and deterministic operations where reasoning is unnecessary.

The repository is the reusable runtime extracted from a larger private system that has run in production for six months across roughly 6,000 notes and 47 domain skills.

> Repository and CLI names remain `mcp-starter` for backwards compatibility. **AgentVault** is the product name and positioning.

## The problem

Most Obsidian MCP servers expose generic filesystem actions such as `read_file`, `write_file` and `search`. The model must then decide:

- which folder matters;
- which files are safe or useful to read;
- how much content to load;
- where new information belongs;
- whether a graph query requires loading the graph itself.

That creates unnecessary tool calls, context pollution and inconsistent filing.

AgentVault moves deterministic work out of the model and into Python:

| Generic vault connector | AgentVault |
|---|---|
| Broad file reads and full-text search | Purpose-specific, bounded read tools |
| Model guesses where notes belong | `vault_dispatch` routes against explicit hints without an LLM call |
| Large responses silently consume context | Hard caps plus a hint naming the cheaper next tool |
| Link graph loaded into context | `vault_graph` returns only the requested subgraph answer |
| Behaviour embedded in application code | Versioned `system_prompt.md` and `skill_hints.json` |
| New capabilities require server edits | Typed skills discovered from manifests |

**The claim is not that reasoning can be eliminated.** AgentVault uses deterministic operations where deterministic operations are enough, preserving model context for tasks that actually require judgment.

## Who this is for

AgentVault is designed for developers and advanced knowledge-management users who:

- keep substantial knowledge in Obsidian or plain Markdown;
- use Claude, ChatGPT, VS Code or another MCP client as an agent;
- care about predictable writes, bounded context and inspectable behaviour;
- are comfortable running Python locally and optionally deploying a small service.

It is not a polished desktop app, a hosted SaaS, or the easiest option for someone who only wants basic chat-with-notes.

## What ships

- **14 core MCP tools** for bounded reads, surgical edits, movement, search and session context;
- **3 typed skill tools**: `vault_dispatch`, `vault_find`, `vault_graph`;
- Streamable HTTP and SSE transports;
- static bearer authentication and OAuth 2.0 PKCE;
- protected paths, tool annotations and configurable response caps;
- a CLI for initialising a vault, serving the runtime and building the link graph;
- deployment guidance for nginx, systemd and Syncthing.

## Try it locally

No VPS, nginx, OAuth registration or Syncthing is required to evaluate the runtime.

```bash
git clone https://github.com/MaiorMajor/mcp-starter.git
cd mcp-starter

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

mcp-starter init ./demo-vault
mcp-starter serve
```

Check the service:

```bash
curl http://localhost:8000/health
```

Point an MCP client at the local endpoint using `Authorization: Bearer $MCP_API_KEY`. The generated `.env` contains development secrets; replace them before any public deployment.

## Adapt it to your vault

The default layout is deliberately small and replaceable:

```text
inbox/           immutable capture zone: read and promote, never edit in place
work/            active projects
personal/        life administration
research/        reading and references
meta/            graph snapshot, changelog and operating rules
_PRIVADO/        hidden from MCP tools
```

1. Set `VAULT_PATH` in `.env`.
2. Edit `skill_hints.json` at the repository root to map your vocabulary to folders and skills.
3. Edit `system_prompt.md` to define agent behaviour without changing server code.
4. Optionally run `mcp-starter graph-build` to create the link snapshot.

The **repository is the source of truth for runtime behaviour**: code, skills, routing hints and the system prompt are versioned here. The vault is the source of truth for your content. This separation keeps personal notes out of the codebase while making agent behaviour auditable.

## Core tools

`session_start` · `list_folder` · `find_files` · `read_note` · `read_frontmatter` · `bulk_read` · `read_json` · `read_jsonl` · `write_note` · `edit_note` · `move_note` · `search_notes` · `get_current_datetime` · `run_skill`

Read paths are intentionally specialised because each represents a different point on the cost/precision curve. The write surface stays small and inspectable. MCP annotations identify read-only, destructive and idempotent actions so compatible clients can make safer approval decisions.

## Typed skills

Each typed skill includes a `manifest.json` with an input schema. MCP clients see a first-class tool such as `vault_dispatch(query, top)` rather than a generic subprocess wrapper.

| MCP tool | Purpose |
|---|---|
| `vault_dispatch` | Suggest a destination from explicit routing hints without an LLM call |
| `vault_find` | Scan file metadata without loading note bodies |
| `vault_graph` | Query backlinks, hubs, orphans and paths without exposing the full graph |

Extension skills can still be called through `run_skill`. Add a directory under `skills/` containing `main.py` and, for a first-class typed tool, a `manifest.json`.

## Architecture

```text
MCP client
    │ JSON-RPC over Streamable HTTP or SSE
    ▼
AgentVault runtime (Starlette + uvicorn)
    │ authentication, tool schemas, caps, hints, protected paths
    ├── core vault tools
    ├── typed skill discovery
    └── system_prompt.md + skill_hints.json
            │
            ▼
Markdown vault (VAULT_PATH)
    ├── notes and frontmatter
    ├── private excluded paths
    └── optional link-graph snapshot
```

The graph snapshot may be megabytes on disk, but the model only receives the bounded result of a requested query. When a tool truncates a response, it returns an explicit hint such as “refine the query” or “use `vault_find` for recent files” rather than silently dropping data.

## Production deployment

Production deployment is a separate concern from local evaluation.

```ini
# /etc/systemd/system/agentvault.service
[Service]
ExecStart=/home/you/mcp-env/bin/mcp-starter serve
Restart=always
EnvironmentFile=/home/you/mcp-server/.env
```

```bash
sudo systemctl enable --now agentvault
curl https://your-host/mcp-health
```

A typical deployment uses nginx for TLS and proxies `/sse`, `/messages` and `/mcp`. Disable proxy buffering for SSE. Syncthing can keep a vault available across laptop, phone and VPS without turning note capture into a Git workflow.

### Security boundary

OAuth clients are persisted. Redirect URIs are exact-match validated, PKCE is S256-only, access tokens expire, SSE requires authentication and allowed origins are restrictive by default. `_PRIVADO` and configured protected paths are excluded below the skill layer.

This remains a self-hosted beta. Use strong secrets, review exposed paths and test with a non-sensitive vault before placing it on the public internet.

## Evidence, not magic

The private production system behind this extraction currently includes:

- roughly 6,000 Markdown notes;
- 47 skills across personal, career, work, media and infrastructure domains;
- a 2,383-node link graph queried without loading the full snapshot into model context;
- 66 generated CV variants and 20 tracked job applications;
- a voice-ingestion pipeline, activity context and scheduled digests.

Those private domain skills are **not included** in this repository. What ships here is the reusable runtime, three representative skills and the extension contract. See [CASE-STUDY.md](./CASE-STUDY.md) for the engineering decisions and failures behind it.

## Current limitations

- Routing quality depends on explicit, maintained hints and a reasonably stable taxonomy.
- There is no graphical interface or hosted service.
- The included skills demonstrate the architecture; they do not reproduce the author's private 47-skill system.
- Production deployment still requires infrastructure knowledge.
- Cross-client MCP behaviour can vary, particularly around connector state and OAuth registration.

## Roadmap

The next product-level improvements are:

- a reproducible benchmark comparing tool calls and returned context against a generic vault connector;
- a small realistic example vault for safe evaluation;
- a `skill new` scaffolding command with manifest, schema and tests;
- clearer adapters between the runtime core and Obsidian-specific conventions;
- deployment recipes that are tested independently from the local quickstart.

## Links

- [Case study](./CASE-STUDY.md)
- [Changelog](./CHANGELOG.md)
- [Author: Jorge MM Marques](https://github.com/MaiorMajor) — AI Engineer · Agentic Systems · Python Automation

MIT licensed.