---
title: vault-dispatch — Guia para Agentes
type: skill-agent
created: 2026-04-14
---

# vault-dispatch

> Resolve uma query em linguagem natural para o destino correto no vault + contexto.
> **Usa isto ANTES de qualquer operação de escrita.** Poupa tokens e evita routing errado.

## Quando usar

- Antes de criar uma nota e não tens a certeza do destino
- Quando o Jorge menciona um tópico e precisas de saber onde vive no vault
- Para descobrir que skills são relevantes para uma tarefa
- Para obter a lista de ficheiros de contexto a carregar

## Como usar

```bash
# Básico — devolve destino + contexto em JSON
python main.py "DRAPN automação bug"

# Múltiplos resultados
python main.py "portfolio React Django" --top 3

# Output markdown (legível)
python main.py "letra nova rap" --output markdown

# Vault path explícito
python main.py "finanças orçamento" --vault /path/to/your/vault
```

## Via MCP

```
run_skill("vault-dispatch", ["DRAPN automação bug"])
run_skill("vault-dispatch", ["dopamina hábitos", "--output", "markdown"])
```

## Output

JSON com:
- `destination` — pasta destino (ex: `10_work/castelform/`)
- `confidence` — score do match (0-1)
- `keywords_matched` — que keywords fizeram match
- `context_files` — ficheiros que o agente deve ler para ter contexto
- `applicable_skills` — skills relevantes para a tarefa
- `has_runtime` — se existe `_runtime/state.md` no destino (ler se sim)
- `fallback` — `true` se nenhum match forte foi encontrado (destino = `00_inbox/`)

## Notas

- **Determinístico**: sem LLM, sem API, sem rede. Pure pattern matching.
- **Rápido**: <1s mesmo no vault completo.
- **Keywords vêm de**: frontmatter `keywords:` dos CONTEXT.md + routing tables + nomes de pastas.
- Se `fallback: true` → pede ao Jorge para clarificar o destino.
