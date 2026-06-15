"""
Structured JSON / JSONL reading for MCP — schema-first navigation without token burn.
Zero external dependencies (no jq / jsonpath_ng).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Caps (mirrored in MCP server descriptions)
READ_JSON_MAX_CHARS: int = 32_000
READ_JSON_MAX_BYTES: int = 25 * 1024 * 1024  # full .json parse ceiling
READ_JSON_LIST_DEFAULT_LIMIT: int = 20
READ_JSON_LIST_MAX_LIMIT: int = 50
READ_JSON_SCHEMA_DEFAULT_DEPTH: int = 2
READ_JSON_SCHEMA_MAX_DEPTH: int = 4
READ_JSONL_DEFAULT_LIMIT: int = 20
READ_JSONL_MAX_LIMIT: int = 50
READ_JSONL_SCHEMA_SAMPLE_LINES: int = 5
LARGE_STRING_PREVIEW: int = 80
CONTAINER_GET_MAX_ITEMS: int = 20  # above this, get returns hint not blob

_PATH_TOKEN_RE = re.compile(
    r"""
    (?:
        \[\s*(?P<index>-?\d+)\s*\]   # [0] or [-1]
      | \.(?P<dot>[a-zA-Z_][\w]*)    # .key
      | (?P<key>[a-zA-Z_][\w]*)      # bare key at start
    )
    """,
    re.VERBOSE,
)


def _parse_query(query: str | None) -> list[tuple[str, int | None]]:
    """Parse dotted/bracket path into steps: ('key', None) or ('__index__', idx)."""
    if not query or not str(query).strip():
        return []
    q = str(query).strip()
    if q.startswith("$."):
        q = q[2:]
    elif q.startswith("$"):
        q = q[1:]
    steps: list[tuple[str, int | None]] = []
    pos = 0
    while pos < len(q):
        if q[pos] == ".":
            pos += 1
            continue
        m = _PATH_TOKEN_RE.match(q, pos)
        if not m:
            raise ValueError(f"invalid query at position {pos}: {query!r}")
        if m.group("index") is not None:
            steps.append(("__index__", int(m.group("index"))))
        elif m.group("dot"):
            steps.append((m.group("dot"), None))
        elif m.group("key"):
            steps.append((m.group("key"), None))
        pos = m.end()
    return steps


def resolve_path(data: Any, query: str | None) -> Any:
    """Resolve a dotted/bracket path against parsed JSON data."""
    steps = _parse_query(query)
    cur = data
    for key, idx in steps:
        if key == "__index__":
            if not isinstance(cur, list):
                raise TypeError(f"expected array at index step, got {type(cur).__name__}")
            if idx < 0:
                idx = len(cur) + idx
            if idx < 0 or idx >= len(cur):
                raise IndexError(f"array index {idx} out of range (len={len(cur)})")
            cur = cur[idx]
        else:
            if not isinstance(cur, dict):
                raise TypeError(f"expected object for key {key!r}, got {type(cur).__name__}")
            if key not in cur:
                raise KeyError(f"key not found: {key!r}")
            cur = cur[key]
    return cur


def _type_label(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _summarize_value(value: Any, depth: int, max_depth: int) -> Any:
    """Build schema tree without large values."""
    t = _type_label(value)
    if t == "string":
        n = len(value)
        if n <= LARGE_STRING_PREVIEW:
            return {"type": "string", "chars": n, "preview": value}
        return {"type": "string", "chars": n}
    if t in ("integer", "number", "boolean", "null"):
        return {"type": t, "value": value}
    if t == "array":
        n = len(value)
        out: dict[str, Any] = {"type": "array", "length": n}
        if n == 0:
            return out
        if depth >= max_depth:
            first = _type_label(value[0])
            out["items"] = f"{first} (depth cap)"
            return out
        # Sample first element schema
        out["items"] = _summarize_value(value[0], depth + 1, max_depth)
        if n > 1:
            last_t = _type_label(value[-1])
            if last_t != _type_label(value[0]):
                out["items_last"] = _summarize_value(value[-1], depth + 1, max_depth)
        return out
    if t == "object":
        keys = list(value.keys())
        out = {"type": "object", "keys": keys[:30]}
        if len(keys) > 30:
            out["keys_truncated"] = len(keys)
        if depth >= max_depth:
            return out
        props: dict[str, Any] = {}
        for k in keys[:20]:
            props[k] = _summarize_value(value[k], depth + 1, max_depth)
        out["properties"] = props
        if len(keys) > 20:
            out["properties_truncated"] = len(keys) - 20
        return out
    return {"type": t}


def _shallow_entry(value: Any, fields: list[str] | None) -> Any:
    """Summarize one list/object entry for mode=list."""
    if fields:
        if not isinstance(value, dict):
            return {"_type": _type_label(value), "_value": _preview_scalar(value)}
        out: dict[str, Any] = {}
        for f in fields:
            if f in value:
                out[f] = _preview_scalar(value[f])
            else:
                out[f] = None
        return out
    if isinstance(value, dict):
        return {k: _preview_scalar(v) for k, v in value.items()}
    return _preview_scalar(value)


def _preview_scalar(value: Any) -> Any:
    if isinstance(value, str):
        n = len(value)
        if n <= LARGE_STRING_PREVIEW:
            return value
        return f"str({n})"
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return f"array[{len(value)}]"
    if isinstance(value, dict):
        return f"object{{{len(value)} keys}}"
    return str(value)


def _serialize_value(value: Any, max_chars: int) -> tuple[Any, bool, int]:
    """Serialize a get result; truncate strings, hint on large containers."""
    if isinstance(value, str):
        text, truncated = _truncate_str(value, max_chars)
        return text, truncated, len(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value, False, 0
    if isinstance(value, list):
        n = len(value)
        if n > CONTAINER_GET_MAX_ITEMS:
            return {
                "type": "array",
                "length": n,
                "hint": "Container too large for get. Use mode=list with query pointing here.",
            }, False, 0
        return value, False, 0
    if isinstance(value, dict):
        n = len(value)
        if n > CONTAINER_GET_MAX_ITEMS:
            return {
                "type": "object",
                "keys": len(value),
                "hint": "Container too large for get. Use mode=list with query pointing here.",
            }, False, 0
        return value, False, 0
    text = json.dumps(value, ensure_ascii=False)
    text, truncated = _truncate_str(text, max_chars)
    return text, truncated, len(text)


def _truncate_str(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def _load_json_file(path: Path) -> Any:
    size = path.stat().st_size
    if size > READ_JSON_MAX_BYTES:
        mb = round(size / (1024 * 1024), 1)
        raise ValueError(
            f"JSON file too large to parse fully ({mb}MB > {READ_JSON_MAX_BYTES // (1024*1024)}MB). "
            "Consider splitting or using JSONL."
        )
    raw = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON at line {e.lineno} col {e.colno}: {e.msg}") from e


def read_json(
    path: Path,
    *,
    mode: str = "schema",
    query: str | None = None,
    fields: list[str] | None = None,
    limit: int | None = None,
    offset: int = 0,
    depth: int | None = None,
    max_chars: int = READ_JSON_MAX_CHARS,
) -> dict[str, Any]:
    """Main entry for read_json MCP tool."""
    if not path.suffix.lower() == ".json":
        return {"error": f"read_json requires a .json file, got {path.suffix!r}"}
    if not path.exists():
        return {"error": f"File not found: {path}"}

    mode = (mode or "schema").lower()
    if mode not in ("schema", "get", "list"):
        return {"error": f"invalid mode {mode!r}; use schema, get, or list"}

    try:
        data = _load_json_file(path)
    except (OSError, ValueError) as e:
        return {"error": str(e)}

    out: dict[str, Any] = {"path": str(path), "mode": mode}
    if query:
        out["query"] = query

    try:
        target = resolve_path(data, query) if query else data
    except (ValueError, TypeError, KeyError, IndexError) as e:
        return {"error": str(e), "path": str(path), "query": query}

    if mode == "schema":
        d = depth if depth is not None else READ_JSON_SCHEMA_DEFAULT_DEPTH
        d = max(0, min(d, READ_JSON_SCHEMA_MAX_DEPTH))
        out["schema"] = _summarize_value(target, 0, d)
        out["hint"] = "Use mode=list to browse arrays/objects, mode=get for a specific path."
        return out

    if mode == "get":
        value, truncated, total_chars = _serialize_value(target, max_chars)
        out["value"] = value
        out["value_type"] = _type_label(target)
        if truncated:
            out["truncated"] = True
            out["content_chars"] = len(str(value))
            out["content_chars_total"] = total_chars
            out["hint"] = "Value truncated. Narrow query or use mode=list."
        return out

    # mode == list
    lim = limit if limit is not None else READ_JSON_LIST_DEFAULT_LIMIT
    lim = max(1, min(lim, READ_JSON_LIST_MAX_LIMIT))
    off = max(0, offset)

    if isinstance(target, list):
        total = len(target)
        slice_ = target[off : off + lim]
        items = []
        for i, v in enumerate(slice_):
            entry = _shallow_entry(v, fields)
            if isinstance(entry, dict):
                entry = {"_index": off + i, **entry}
            else:
                entry = {"_index": off + i, "_value": entry}
            items.append(entry)
        out["items"] = items
        out["total"] = total
        out["count"] = len(items)
        out["offset"] = off
        if off + len(items) < total:
            out["next_offset"] = off + len(items)
        out["hint"] = "Use mode=get with query including [index] for full content."
        return out

    if isinstance(target, dict):
        keys = list(target.keys())
        total = len(keys)
        page_keys = keys[off : off + lim]
        items = []
        for i, k in enumerate(page_keys):
            entry: dict[str, Any] = {"_key": k}
            if fields:
                sub = target[k]
                if isinstance(sub, dict):
                    for f in fields:
                        if f in sub:
                            entry[f] = _preview_scalar(sub[f])
                else:
                    entry["_value"] = _preview_scalar(sub)
            else:
                entry["_value"] = _preview_scalar(target[k])
            items.append(entry)
        out["items"] = items
        out["total"] = total
        out["count"] = len(items)
        out["offset"] = off
        if off + len(items) < total:
            out["next_offset"] = off + len(items)
        out["hint"] = "Use mode=get with query including the key for full content."
        return out

    return {
        "error": f"mode=list requires array or object at query path, got {_type_label(target)}",
        "path": str(path),
        "query": query,
    }


def _merge_schemas(schemas: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge object schemas from multiple JSONL lines."""
    if not schemas:
        return {"type": "object", "keys": []}
    all_keys: set[str] = set()
    props: dict[str, set[str]] = {}
    for s in schemas:
        if s.get("type") != "object":
            continue
        for k in s.get("keys", []):
            all_keys.add(k)
        for k, v in (s.get("properties") or {}).items():
            t = v.get("type", "?") if isinstance(v, dict) else "?"
            props.setdefault(k, set()).add(t)
    merged_props = {k: {"type": sorted(v)[0] if len(v) == 1 else f"union({','.join(sorted(v))})"} for k, v in props.items()}
    return {"type": "object", "keys": sorted(all_keys), "properties": merged_props}


def read_jsonl(
    path: Path,
    *,
    mode: str = "rows",
    offset: int = 0,
    limit: int | None = None,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Main entry for read_jsonl MCP tool."""
    suf = path.suffix.lower()
    if suf not in (".jsonl", ".ndjson"):
        return {"error": f"read_jsonl requires .jsonl or .ndjson, got {suf!r}"}
    if not path.exists():
        return {"error": f"File not found: {path}"}

    mode = (mode or "rows").lower()
    if mode not in ("rows", "schema"):
        return {"error": f"invalid mode {mode!r}; use rows or schema"}

    lim = limit if limit is not None else READ_JSONL_DEFAULT_LIMIT
    lim = max(1, min(lim, READ_JSONL_MAX_LIMIT))
    off = max(0, offset)

    lines_out: list[Any] = []
    line_errors: list[dict[str, Any]] = []
    total_lines = 0
    schema_samples: list[dict[str, Any]] = []

    try:
        with path.open(encoding="utf-8") as f:
            for line_no, raw_line in enumerate(f, 1):
                stripped = raw_line.strip()
                if not stripped:
                    continue
                total_lines += 1
                if mode == "schema" and len(schema_samples) < READ_JSONL_SCHEMA_SAMPLE_LINES:
                    try:
                        obj = json.loads(stripped)
                        schema_samples.append(_summarize_value(obj, 0, READ_JSON_SCHEMA_DEFAULT_DEPTH))
                    except json.JSONDecodeError:
                        pass
                    continue
                if total_lines <= off:
                    continue
                if len(lines_out) >= lim:
                    continue
                try:
                    obj = json.loads(stripped)
                    if fields and isinstance(obj, dict):
                        row = {f: _preview_scalar(obj.get(f)) for f in fields}
                    elif fields:
                        row = {"_line": line_no, "_value": _preview_scalar(obj)}
                    else:
                        row = obj if isinstance(obj, dict) else {"_line": line_no, "_value": obj}
                    if isinstance(row, dict):
                        row.setdefault("_line", line_no)
                    lines_out.append(row)
                except json.JSONDecodeError as e:
                    line_errors.append({"line": line_no, "error": e.msg})
    except OSError as e:
        return {"error": str(e)}

    out: dict[str, Any] = {
        "path": str(path),
        "mode": mode,
        "total_lines": total_lines,
    }

    if mode == "schema":
        out["schema"] = _merge_schemas(schema_samples)
        out["sample_lines"] = len(schema_samples)
        out["hint"] = "Use mode=rows with offset/limit to read lines."
        return out

    out["lines"] = lines_out
    out["count"] = len(lines_out)
    out["offset"] = off
    next_off = off + len(lines_out)
    if next_off < total_lines:
        out["next_offset"] = next_off
    if line_errors:
        out["line_errors"] = line_errors[:10]
    out["hint"] = "Paginate with offset/next_offset for more lines."
    return out
