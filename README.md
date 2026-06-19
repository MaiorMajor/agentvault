# AgentVault

> A bounded, deterministic MCP runtime for Obsidian and Markdown knowledge bases.

AgentVault turns a Markdown folder into operational infrastructure for AI agents. Instead of letting a model rummage through an entire vault, it exposes narrow tools for finding, reading, routing, editing and querying links, with bounded responses and deterministic operations where reasoning is unnecessary.

The repository is the reusable runtime extracted from a private system that has run in production for six months across roughly 6,000 notes and 47 domain skills.

## Why it exists

Most vault connectors expose generic file actions and leave the model to decide which folders matter, which files to inspect, how much content to load and where new information belongs. That produces unnecessary tool calls, context pollution and inconsistent filing.

| Generic vault connector | AgentVault |
|---|---|
| Broad reads and full-text search | Purpose-specific, bounded read tools |
| Model guesses destinations | `vault_dispatch` routes against explicit hints |
| Large responses consume context | Hard caps plus hints naming a narrower next tool |
| Full graph exposed to the model | `vault_graph` returns only the requested answer |
| Behaviour embedded in code | Versioned `system_prompt.md` and `skill_hints.json` |
| Capabilities registered centrally | Typed skills discovered from manifests |

AgentVault does not replace model reasoning. It moves explicit lookups and mechanical decisions into deterministic code so the context window remains available for judgment.

## Who it is for

AgentVault is for developers and advanced knowledge-management users who keep substantial knowledge in Obsidian or plain Markdown, use MCP-compatible agents, and care about predictable writes, bounded context and inspectable behaviour.

It is not a desktop Obsidian plugin, hosted SaaS or one-click consumer product.

## What ships

- 14 core MCP tools for bounded reads, surgical edits, movement, search and session context;
- 3 typed skills: `vault_dispatch`, `vault_find`, `vault_graph`;
- Streamable HTTP and SSE transports;
- bearer and OAuth 2.0 PKCE authentication;
- protected paths, tool annotations and configurable response caps;
- a CLI for initialising a vault, serving the runtime and building the link graph;
- deployment guidance for nginx, systemd and Syncthing.

## Try it locally

```bash
git clone https://github.com/MaiorMajor/agentvault.git
cd agentvault
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
agentvault init ./demo-vault
agentvault serve
```

On Windows, activate with `.venv\Scripts\activate`.

## Adapt it to your vault

The default layout is deliberately small and replaceable:

```text
inbox/           capture zone
work/            active projects
personal/        life administration
research/        reading and references
meta/            graph snapshot and operating rules
_PRIVADO/        excluded from MCP tools
```

1. Set `VAULT_PATH`.
2. Edit `skill_hints.json` to map your vocabulary to folders and skills.
3. Edit `system_prompt.md` to define agent behaviour.
4. Optionally run `agentvault graph-build`.

The repository is the source of truth for runtime behaviour. The vault is the source of truth for content.

## Core tools

`session_start` · `list_folder` · `find_files` · `read_note` · `read_frontmatter` · `bulk_read` · `read_json` · `read_jsonl` · `write_note` · `edit_note` · `move_note` · `search_notes` · `get_current_datetime` · `run_skill`

## Typed skills

| Tool | Purpose |
|---|---|
| `vault_dispatch` | Suggest a destination from explicit routing hints |
| `vault_find` | Scan file metadata without loading note bodies |
| `vault_graph` | Query backlinks, hubs, orphans and paths without exposing the graph |

Additional skills live under `skills/` and can expose first-class MCP tools through a `manifest.json` input schema.

## Architecture

```text
MCP client
    │
    ▼
AgentVault runtime
    ├── core vault tools
    ├── typed skill discovery
    ├── response caps and hints
    └── protected paths
            │
            ▼
Markdown vault
    ├── notes and frontmatter
    └── optional link-graph snapshot
```

## Production deployment

```ini
[Service]
ExecStart=/home/you/agentvault-env/bin/agentvault serve
Restart=always
EnvironmentFile=/home/you/agentvault/.env
```

A typical deployment uses nginx for TLS, systemd for process supervision and optionally Syncthing to keep the vault available across devices.

This remains a self-hosted beta. Review exposed paths and test with a non-sensitive vault before public deployment.

## Evidence, not magic

The private production system behind this extraction includes roughly 6,000 Markdown notes, 47 domain skills, a 2,383-node link graph, 66 generated CV variants, 20 tracked job applications, voice ingestion, activity context and scheduled digests.

Those private skills are not included. This repository ships the reusable runtime, three representative skills and the extension contract. See [CASE-STUDY.md](./CASE-STUDY.md).

## Current limitations

- Routing depends on explicit, maintained hints and a reasonably stable taxonomy.
- There is no graphical interface or hosted service.
- The included skills do not reproduce the private 47-skill system.
- Production deployment requires infrastructure knowledge.
- MCP client behaviour can vary.

## Roadmap

- reproducible comparison against a generic vault connector;
- a small realistic example vault;
- an `agentvault skill new` scaffolding command;
- clearer separation between runtime core and Obsidian conventions;
- independently tested deployment recipes.

## Links

- [Case study](./CASE-STUDY.md)
- [Changelog](./CHANGELOG.md)
- [Jorge MM Marques](https://github.com/MaiorMajor)

MIT licensed.