---
title: vault-graph — Guia para Agentes
type: skill-agent
created: 2026-05-26
updated: 2026-05-27
has_learnings: true
---

# vault-graph

> Extrai e consulta o grafo de wikilinks + tags do vault.
> Dois modos: **geração** (escreve `99_meta/vault-graph.json`) e **query** (responde sem carregar o JSON inteiro).

## REGRA CRÍTICA

**NUNCA leias `99_meta/vault-graph.json` via `read_note`/`Read`/`cat`.** São 800KB+ que enchem o context window. Usa sempre `query <subcmd>` — devolve só o pedaço relevante.

---

## Quando regenerar

**Automático (cron):** 07:30 e 18:00 todos os dias (configurado em `crontab -l`). Garante que o graph nunca tem mais que ~10h de atraso entre sessões.

**Automático (lazy via stale flag):** writes via MCP (`write_note`, `edit_note`, `move_note`, etc.) tocam `99_meta/.vault-graph-stale`. A próxima `query` desta skill detecta o flag, regenera, apaga o flag, e só depois responde. O agente vê uma linha no stderr: `[vault-graph] auto-regenerated (X nodes, Y edges)`. Não precisas de regen manual entre escrever e consultar via MCP.

**Manual obrigatório — corre `run_skill("vault-graph")` (sem argv) após:**

- `bulk-move` ou batch-rename de >5 ficheiros (skill, não toca o flag)
- Promoções massivas hot → cold
- Corrida de `semantic-linker`, `graph-weaver` ou outro skill que injecta wikilinks (não tocam o flag)
- Reorganização de `99_meta/`, `CONTEXT.md`, `_README.md` ou qualquer SSOT via filesystem direto
- Audit / migração que mexe na taxonomia (`routing-audit` com `--apply`)
- Edits ao vault feitos pelo Jorge no telefone/desktop entre cron runs, se queres precisão imediata

**Regra simples:** se a mudança *invalida* a resposta de queries relacionais (backlinks, hubs, paths) e não foi feita via tool MCP, regenera **antes** de qualquer query.

```bash
python main.py              # regenera 99_meta/vault-graph.json
python main.py --dry-run    # stats sem escrever
python main.py --json       # output JSON estruturado
```

Via MCP: `run_skill("vault-graph")` (sem argv).

Nos restantes casos (escrever uma nota, editar conteúdo, mexer em tags) **não** regeneres — espera o cron.

---

## Queries disponíveis

Todos os subcomandos aceitam `--json` para output estruturado. Por defeito devolvem texto human-readable.

### `query backlinks <nota>` — quem aponta para uma nota
```bash
python main.py query backlinks PROFILE
python main.py query backlinks 99_meta/PROFILE.md --limit 100
```
Resolução tolerante: aceita basename (`PROFILE`), basename.md, ou path completo. Em colisões devolve o 1º e avisa em stderr.

### `query forward <nota>` — para onde uma nota aponta
```bash
python main.py query forward CONSTITUTION
```

### `query neighbors <nota>` — vizinhança N-hops
```bash
python main.py query neighbors AGENT_INSTRUCTIONS --depth 2 --direction both
python main.py query neighbors PROFILE --depth 1 --direction in   # só backlinks
```
`--direction` ∈ `in | out | both` (default both).

### `query hubs` — top autoridades por in-degree
```bash
python main.py query hubs --top 20
```
Alias: `query authorities`.

### `query orphans` — notas sem nenhum link (in nem out)
```bash
python main.py query orphans --limit 50
```
Útil para weekly-review: candidatos a promover, linkar ou arquivar.

### `query tag <tag>` — notas com tag específica
```bash
python main.py query tag prompt
python main.py query tag #castelform   # # opcional
```

### `query node <nota>` — ficha completa
```bash
python main.py query node SIGO
```
Devolve folder, tags, in/out degree, e samples de 5 backlinks + 5 forward.

### `query path <from> <to>` — caminho mais curto (BFS undirected)
```bash
python main.py query path 99_meta/PROFILE.md 99_meta/CONSTITUTION.md
```
Devolve `"Sem caminho"` se os nodes não estiverem conectados.

### `query find <pattern>` — fuzzy match em paths
```bash
python main.py query find vault-graph
```
Quando não sabes o path exacto de uma nota. Útil antes de `backlinks`/`node`.

### `query stats` — meta global
```bash
python main.py query stats
```
Devolve `generated_at`, contagens, max degrees, orphan count, e `files_at_root_of_non_leaf_folder` (violations `no_root_files` do `folder-schema`).

---

## Casos típicos

| Pergunta do agente | Comando |
|---|---|
| "Quem cita esta nota?" | `query backlinks <nota>` |
| "Esta nota está isolada?" | `query node <nota>` |
| "Quais são as notas centrais do vault?" | `query hubs --top 20` |
| "Que notas posso arquivar/promover?" | `query orphans` |
| "Estas duas ideias estão ligadas?" | `query path <a> <b>` |
| "Onde está a nota X?" | `query find <padrão>` |
| "Tudo o que tem tag Y" | `query tag Y` |
| "Cluster relacionado a Z" | `query neighbors Z --depth 2` |

---

## Garantias

- **Read-only sobre o vault.** Geração e queries nunca tocam em notas.
- **Idempotente.** Correr `main.py` N vezes = N vezes o mesmo output (módulo `generated_at`).
- **Sem dependências externas** além de stdlib.
- **Output limitado.** Nenhum query devolve >50 linhas sem `--limit` explícito.

## Limitações conhecidas

- Resolução por **basename** (convenção Obsidian). Em colisões devolve o 1º match (avisa em stderr).
- Wikilinks `[[X|alias]]` e `[[X#heading]]` são suportados, mas o target é sempre X.
- Tags em prosa (`#foo` no corpo) **não** são extraídas — só frontmatter.
- Links Markdown nativos `[texto](path.md)` **não** são extraídos. Só wikilinks `[[...]]`.
- Graph é snapshot. Notas criadas depois de `generated_at` não aparecem — regenera se preciso.

## Output

`99_meta/vault-graph.json`:

```json
{
  "generated_at": "ISO datetime",
  "vault_root": "/path/to/your/vault",
  "node_count": N,
  "edge_count": N,
  "nodes": [{"id": "path/relativo.md", "tags": [...], "folder": "..."}],
  "edges": [{"source": "a.md", "target": "b.md", "type": "wikilink"}]
}
```

Geração escreve este ficheiro. Queries lêem-no (sem expor ao agente).
