"""Conversor markdown → HTML self-contained, sem deps externas.

Cobre o subset suficiente para descriptions de tasks Vikunja (Tiptap):
- headings #, ##, ###, ####
- bullets `-` e `*`
- numbered lists `1.`, `2.`, ...
- fenced code blocks ```...```
- inline `**bold**`, `*italic*`, `` `code` ``
- parágrafos
- detecção de input já-HTML (passa direto)

Usado por skills/vikunja-tasks/main.py em cmd_add e cmd_update.
"""

import re
from typing import Optional


def md_to_html(text: Optional[str]) -> Optional[str]:
    """Converte markdown em HTML compatível com Tiptap.

    Se a string já parece HTML estrutural, devolve sem alteração.
    """
    if not text:
        return text
    stripped = text.lstrip()
    html_markers = (
        "<p", "<h1", "<h2", "<h3", "<h4",
        "<ul", "<ol", "<pre", "<div", "<blockquote", "<table",
    )
    if stripped.startswith(html_markers):
        return text
    return _convert(text)


def _convert(text: str) -> str:
    # 1. Extract fenced code blocks first to protect from inline processing.
    code_blocks: list[str] = []

    def _code_repl(m):
        code = m.group(1)
        code = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        idx = len(code_blocks)
        code_blocks.append(code)
        return f"\x00CODE{idx}\x00"

    text = re.sub(r"```[^\n]*\n(.*?)```", _code_repl, text, flags=re.DOTALL)

    # 2. Process line by line for block-level structures.
    lines = text.split("\n")
    out: list[str] = []
    in_list = False
    list_type: Optional[str] = None
    para: list[str] = []

    def flush_para():
        if para:
            out.append(f"<p>{_inline(' '.join(para))}</p>")
            para.clear()

    def flush_list():
        nonlocal in_list, list_type
        if in_list:
            out.append(f"</{list_type}>")
            in_list = False
            list_type = None

    for line in lines:
        stripped_line = line.strip()

        m = re.fullmatch(r"\x00CODE(\d+)\x00", stripped_line)
        if m:
            flush_para()
            flush_list()
            idx = int(m.group(1))
            out.append(f"<pre><code>{code_blocks[idx]}</code></pre>")
            continue

        m = re.match(r"^(#{1,4})\s+(.+)$", stripped_line)
        if m:
            flush_para()
            flush_list()
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            continue

        if not stripped_line:
            flush_para()
            flush_list()
            continue

        m = re.match(r"^[-*]\s+(.+)$", stripped_line)
        if m:
            flush_para()
            if not in_list or list_type != "ul":
                flush_list()
                out.append("<ul>")
                in_list = True
                list_type = "ul"
            out.append(f"<li>{_inline(m.group(1))}</li>")
            continue

        m = re.match(r"^\d+\.\s+(.+)$", stripped_line)
        if m:
            flush_para()
            if not in_list or list_type != "ol":
                flush_list()
                out.append("<ol>")
                in_list = True
                list_type = "ol"
            out.append(f"<li>{_inline(m.group(1))}</li>")
            continue

        flush_list()
        para.append(stripped_line)

    flush_para()
    flush_list()

    return "".join(out)


def _inline(text: str) -> str:
    """Aplica formatações inline: bold, italic, inline code."""
    parts: list[str] = []

    def _code_repl(m):
        code = m.group(1).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        idx = len(parts)
        parts.append(f"<code>{code}</code>")
        return f"\x01INL{idx}\x01"

    text = re.sub(r"`([^`]+)`", _code_repl, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\s][^*]*[^*\s]|[^*\s])\*(?!\*)", r"<em>\1</em>", text)

    def _restore(m):
        return parts[int(m.group(1))]
    text = re.sub(r"\x01INL(\d+)\x01", _restore, text)

    return text


if __name__ == "__main__":
    sample = """## Teste

Parágrafo.

- bullet 1
- bullet 2

```python
print('hello')
```

**bold** e `inline`."""
    print(md_to_html(sample))
