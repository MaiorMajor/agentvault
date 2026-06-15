---
title: vault-dispatch — Especificação
type: skill-spec
created: 2026-04-14
version: 1
---

# vault-dispatch

> Resolver keywords/queries → destino no vault + contexto relevante.
> Determinístico, pure Python, 0 tokens LLM.

## O que faz

Recebe uma string livre (query, keywords, frase) e devolve:
- Destino no vault (pasta)
- Ficheiros de contexto relevantes para o agente carregar
- Skills aplicáveis à tarefa
- Keywords que fizeram match

## Inputs

| Parâmetro | Tipo | Obrigatório | Default | Descrição |
|---|---|---|---|---|
| `query` | string (positional) | sim | — | Texto livre, keywords, frase descritiva |
| `--vault` | path | não | auto-detect | Caminho raiz do vault |
| `--output` | `markdown` \| `json` | não | `json` | Formato do output |
| `--top` | int | não | 3 | Número máximo de destinos a devolver |

## Output (JSON)

```json
{
  "query": "DRAPN automação bug",
  "matches": [
    {
      "destination": "10_work/castelform/",
      "confidence": 0.92,
      "keywords_matched": ["DRAPN", "automação", "castelform"],
      "context_files": [
        "10_work/castelform/CONTEXT.md",
        "10_work/castelform/_index.md"
      ],
      "applicable_skills": ["web-research"],
      "has_runtime": false,
      "graph_hints": ["query", "neighbors", "10_work/castelform/", "--depth", "1"],
      "context_digest": ["Formação e operações Castelform."],
      "context_files_optional": true,
      "context_read_hint": "Lê CONTEXT.md só se confidence < 0.7 ou Jorge pediu estrutura da área."
    }
  ],
  "fallback": false
}
```

### graph_hints / context_digest (2026-06-01)

- `graph_hints` — argv para `vault-graph` (vizinhança do destino).
- `context_digest` — até 3 bullets do CONTEXT slim.
- `context_files_optional: true` quando `confidence >= 0.7` sem `_runtime`.

CLI: `--explain` acrescenta `index_size` ao JSON.

Se nenhum keyword match ≥ threshold → `fallback: true`, `destination: "00_inbox/"`.

## Fontes de keywords

1. **Frontmatter `keywords:`** de todos os `CONTEXT.md` encontrados no vault
2. **Routing tables** do `CONTEXT.md` raiz (coluna Task → Destino)
3. **Nomes de pastas L1/L2** como keywords implícitos
4. **`skill_hints.json`** — `50_infra/vault/agents/skill_hints.json`, carregado em runtime. Adicionar hints de novos skills aqui, nunca no `main.py`.

> `_index.md` é estrutural (gerado pelo routing-audit) e **não** é usado como fonte de keywords.
> Continua a aparecer em `context_files` quando existe, para o agente poder ler a estrutura.

## Matching

- Case-insensitive substring match
- Cada keyword match soma score ao destino correspondente
- Destino com score mais alto ganha
- Threshold mínimo: 1 keyword match
- Se empate: destino mais específico (L2 > L1 > L0) ganha

## Dependências

Nenhuma externa. Python 3.8+ stdlib only.

## Exemplos

```bash
python main.py "DRAPN automação bug"
python main.py "dopamina hábitos neuroplasticidade"
python main.py "letra nova rap beat"
python main.py "CV remote work candidatura" --output markdown
python main.py "algo completamente random"  # → fallback 00_inbox/
```
