# Skill: vault-find

## O que faz

Pesquisa ficheiros no vault por nome, extensão, tipo, data e tamanho; devolve caminhos relativos ao vault.

## Inputs

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `query` | string | não | Substring no nome (atalho para `--name`) |
| `--name` | string | não | Glob no nome do ficheiro |
| `--ext` | string | não | Extensões separadas por vírgula (`.epub,.pdf`) |
| `--type` | enum | não | Categoria: ebooks, docs, images, audio, video, code, data, archives |
| `--path-contains` | string | não | Substring no path relativo ao vault |
| `--modified-after` | YYYY-MM-DD | não | Data mínima de modificação |
| `--modified-before` | YYYY-MM-DD | não | Data máxima de modificação |
| `--min-size` | int (bytes) | não | Tamanho mínimo |
| `--max-size` | int (bytes) | não | Tamanho máximo |
| `--limit` | int | não | Máximo de resultados (default 100; 0 = sem limite) |
| `--output` | table\|json | não | Default `table` |

## Outputs

Lista de ficheiros com: `path` (relativo ao vault), `name`, `ext`, `size_bytes`, `modified` (YYYY-MM-DD).

## Exemplos

```bash
# Encontrar todos os epubs
python main.py --type ebooks

# Substring no nome
python main.py "show your work"

# PDFs numa subpasta
python main.py --ext .pdf --path-contains "30_research"

# Áudio recente, JSON
python main.py --type audio --modified-after 2025-01-01 --output json

# Sem limite
python main.py --ext .md --limit 0
```

## Dependências externas

Nenhuma. Stdlib only.

## Limitações conhecidas

- Não lê conteúdo — apenas filesystem walk.
- `_PRIVADO/` sempre excluído.
- `_PRIVADO/` e paths em `FORBIDDEN_PATHS` (vazio por defeito no starter) são excluídos.
- Sem pesquisa semântica dentro de Markdown.
