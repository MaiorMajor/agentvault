# vault-find — AGENT.md

> Scan do vault por **timestamp, nome, extensão, tipo ou tamanho** — todos os tipos de ficheiro.
> Em sessões MCP: preferir tool nativa `find_files` (mesmos filtros). Esta skill é fallback CLI/subprocess.

---

## Quando usar

| Situação | Comando |
|---|---|
| PDF/docx/código no vault (MCP) | `find_files(ext=".pdf")` ou `find_files(type="docs", exclude_md=true)` |
| "o que criei hoje / esta manhã" | `find_files(today=true, sort_by="created")` ou `run_skill("vault-find", ["--today", "--sort-by", "created"])` |
| "o que criei ontem" | `run_skill("vault-find", ["--yesterday", "--sort-by", "created"])` |
| "ficheiros da última hora" | `run_skill("vault-find", ["--created-after", "YYYY-MM-DDTHH:MM", "--sort-by", "created"])` |
| "ficheiros modificados hoje" | `run_skill("vault-find", ["--modified-after", "YYYY-MM-DD"])` |
| encontrar ficheiro por nome | `run_skill("vault-find", ["*nome*"])` |
| encontrar por extensão | `run_skill("vault-find", ["--ext", ".pdf,.epub"])` |
| encontrar por tipo | `run_skill("vault-find", ["--type", "audio"])` |
| filtrar ruído (ficheiros pequenos) | adicionar `["--min-size", "2000"]` |

**REGRA CRÍTICA:** Quando o utilizador pergunta "o que fiz hoje", "o que criei", "que notas novas tenho", "mostra-me o que trabalhei" — PRIMEIRO chama `vault-find --today --sort-by created`. Não uses `search_notes`. Notas novas não têm conteúdo indexado útil para texto-search.

---

## Flags (v2 — atual)

```
vault-find [query] [flags]

query                         substring no nome (atalho para --name)
--name GLOB                   padrão glob no nome (ex: *pesquisa*, *.epub)
--ext EXTENSIONS              extensões separadas por vírgula (ex: .md,.pdf)
--type TYPE                   ebooks | docs | images | audio | video | code | data | archives
--path-contains STRING        substring no path relativo
--modified-after  YYYY-MM-DD[THH:MM]
--modified-before YYYY-MM-DD[THH:MM]
--created-after   YYYY-MM-DD[THH:MM]   filtra por ctime >=
--created-before  YYYY-MM-DD[THH:MM]   filtra por ctime <=
--today                       atalho: created-after + modified-after = hoje
--yesterday                   atalho: ontem
--sort-by modified|created|name|size   (default: created com --today/--yesterday, modified caso contrário)
--min-size BYTES
--max-size BYTES
--limit N                     default 100, 0 = sem limite
--vault PATH                  raiz do vault (auto-detect se omitido)
--output table|json|brief     default: table
--brief                       atalho para --output brief
```

---

## Modo `--brief` (preferido para agentes)

Output compacto: 1 linha por ficheiro, `<path>\t<title-do-frontmatter-ou-H1>`. Reduz output em ~40% e dá ao modelo o sinal necessário para decidir o que ler sem ter de fazer N `read_note` defensivos.

```bash
python main.py --today --sort-by created --brief
```

```text
40_life/diario/20260526.md   26 mai — GF-BOT retomado, prompt Codex Mod.092, ...
99_meta/AGENT_INSTRUCTIONS.md   Instruções para Agentes — SSOT
50_infra/skills/meta/vault-graph/AGENT.md   vault-graph — Guia para Agentes
```

Usa `--brief` por defeito em queries temporais. `table` só quando precisas mesmo de ver mtime/ctime/size.

---

## Output JSON

```json
{
  "path": "30_research/context-engineering/pesquisa.md",
  "name": "pesquisa.md",
  "ext": ".md",
  "size_bytes": 19091,
  "modified": "2026-05-18T14:32:11",
  "created": "2026-05-18T09:15:04"
}
```

---

## Limitações conhecidas

- `ctime` no Linux é "inode change time", não "birth time" verdadeiro. Proxy razoável para ficheiros criados localmente. Syncthing preserva `mtime` mas reseta `ctime` ao sincronizar — por isso `ctime` é mais fiável para "quando apareceu nesta máquina".
- Ficheiros pequenos do tipo `_index.md` ou `README.md` criam ruído. Filtra com `--min-size 2000` se necessário.
- Para queries de conteúdo usa `search_notes`. Para ficheiros usa `vault-find`.
- Pastas sempre excluídas: `_PRIVADO/`, `.git/`, `node_modules/`, `__pycache__/`, `.venv/`, `.cache/`, `.obsidian/`.
