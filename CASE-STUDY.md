# Case Study — Building an Agent-Native Runtime for a 6,000-Note Vault

**Six months. One VPS. One Markdown vault. Fourteen MCP tools, 47 private domain skills, and deterministic routing for operations that do not require an LLM.**

AgentVault is the reusable runtime extracted from that system. This case study describes the larger private deployment, including capabilities that are not shipped in the public repository.

## The problem

The starting point was ordinary: a large Obsidian vault and several LLM clients. Capture was not the problem. Retrieval and operation were.

A generic filesystem connector made the model repeatedly decide which folder to inspect, which files to read, how much context to load and where new information belonged. Defensive exploration could turn one simple action into many tool calls while still producing inconsistent results.

The architectural principle became:

> Use deterministic code where deterministic code is enough, and preserve model context for decisions that require judgment.

That principle shaped routing, graph queries, bounded reads, surgical edits and context bundles.

## What the public repository contains

The public AgentVault runtime includes:

- 14 bounded core MCP tools;
- typed skill discovery through manifests and input schemas;
- three representative skills: `vault_dispatch`, `vault_find` and `vault_graph`;
- Streamable HTTP and SSE transports;
- bearer authentication and OAuth 2.0 PKCE;
- protected paths, response caps, truncation hints and tool annotations;
- a CLI for initialisation, serving and graph generation.

The private production deployment contains 47 domain-specific skills. Those skills include personal data and organisation-specific workflows, so they are evidence of the extension model rather than part of the open-source package.

## Scale of the private deployment

- approximately 6,000 Markdown notes;
- 47 skills across eight domains;
- 14 core MCP tools;
- a link graph of 2,383 nodes and 1,892 edges;
- 66 generated CV variants;
- 20 job applications tracked through the vault;
- one Hetzner VPS and one systemd service;
- six months of append-only implementation history.

These are operating figures from one system, not benchmark results or universal performance claims.

## Architecture decisions

### Separate content from runtime behaviour

The vault is the source of truth for personal content. The repository is the source of truth for runtime behaviour: application code, skills, routing hints and `system_prompt.md`.

This is the current architecture. Earlier iterations stored parts of the runtime inside the vault, which made deployment convenient but allowed the VPS copy to drift from an auditable codebase. The public extraction deliberately corrected that boundary.

### Route explicit taxonomies without an LLM call

`vault_dispatch` matches a query against maintained routing hints, folder conventions and skill metadata. It is useful when the destination taxonomy is explicit and reasonably stable.

This is not semantic understanding and it does not replace reasoning. Ambiguous cases still belong with the model. The value is avoiding model calls for routine lookups that can be represented as data.

### Hide the graph and expose queries

The link graph is stored as a snapshot on disk. Giving the complete snapshot to a model would waste context, so `vault_graph` exposes bounded operations such as backlinks, hubs, orphans and paths.

The model receives the answer to a graph question rather than the graph dataset.

### Cap every response and teach the next move

Large tool responses are truncated, but truncation is not silent. The response includes a hint naming a narrower or cheaper operation, such as refining a query or switching from full-text search to metadata search.

This turns context discipline into runtime behaviour rather than relying entirely on prompt compliance.

### Keep writes narrow

Read operations are specialised because they serve different precision and cost profiles. Writes remain deliberately limited: create or update a note, perform a surgical edit, and move a note.

A smaller write surface is easier to audit and safer to approve automatically.

### Discover typed skills dynamically

A skill can expose a first-class MCP tool by shipping a `manifest.json` with its input schema. This allows new capabilities without editing a central tool registry.

The private single-user deployment accepts the velocity/security trade-off of dynamic discovery. Protected paths and authentication remain enforced below the skill layer.

## What failed

### Weak models confidently solved nonexistent problems

One model proposed a substantial refactor of an audio-ingestion pipeline. A stronger model first checked the premise and found that the desired unified output already existed; the extra files were obsolete artefacts. The correct fix was deletion, not architecture.

The resulting operating rule is simple: use strong models to validate architecture and problem existence; use cheaper models for mechanical execution after the plan is sound.

### Connector failures looked like server failures

During development, client-side MCP connector state occasionally became stale. Valid resources failed and then worked again without a server change. Without structured logs, the obvious reaction was to patch the wrong layer.

The runtime gained per-call structured logging so transport, client and server failures could be distinguished before code changed.

### Completed infrastructure work was invisible

The vault represented pending work more clearly than completed work. Any agent reading the state produced a distorted picture: a large backlog and little evidence of execution.

Append-only change history, activity context and completion digests made progress legible. Infrastructure only becomes useful operational context when its effects are recorded.

### A correct patch was placed in dead code

An OAuth registration route was added below a blocking `uvicorn.run()` path. It appeared correct during import-based testing but never executed when the service launched as a script.

The lesson was not specific to OAuth: deployment entry points are part of program semantics. Tests must exercise the process the same way production starts it.

## Practical impact

The private system now supports workflows such as:

- assembling a daily-diary context bundle in one skill call instead of repeated defensive reads;
- querying links without loading a multi-megabyte graph snapshot;
- generating tailored CV variants and tracking applications from the same source of truth;
- turning voice recordings into structured Markdown notes;
- answering organisation-specific questions through domain skills that return narrow, cited context packs.

The public repository does not claim that every user will reproduce the same savings. A reproducible comparison against a generic vault connector remains roadmap work.

## Why open-source the runtime

The useful contribution is not the author's private folder structure or personal automation catalogue. It is the reusable set of constraints:

- bounded context by default;
- deterministic operations for explicit lookups;
- narrow and auditable writes;
- typed extension skills;
- graph queries without graph exposure;
- local-first Markdown as the content layer;
- production authentication and transport support.

That makes AgentVault both a practical starting point for advanced users and a concrete engineering case study in agent infrastructure.

## Current boundary

AgentVault is a developer tool, not a consumer Obsidian plugin. It requires Python and, for public deployment, ordinary infrastructure work. Routing requires maintained hints. The included skills demonstrate the architecture but do not recreate the private system.

Those constraints are intentional and should be visible rather than hidden behind a “three-step” promise.

— **Jorge MM Marques** · Python Developer · Automation & Internal Tools