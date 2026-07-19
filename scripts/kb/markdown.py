from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


FRONTMATTER_BOUNDARY = "---"
SCALAR_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?$")
LIST_ITEM_RE = re.compile(r"^\s*-\s+(.*)$")


@dataclass(frozen=True)
class MarkdownFile:
    path: Path
    frontmatter: dict[str, object]
    body: str


def read_markdown(path: Path) -> MarkdownFile:
    text = read_markdown_text(path)
    frontmatter: dict[str, object] = {}
    body = text
    if text.startswith(FRONTMATTER_BOUNDARY):
        parts = text.split(FRONTMATTER_BOUNDARY, 2)
        if len(parts) == 3:
            frontmatter = parse_frontmatter(parts[1])
            body = parts[2].lstrip("\r\n")
    return MarkdownFile(path=path, frontmatter=frontmatter, body=body)


def parse_frontmatter(raw: str) -> dict[str, object]:
    data: dict[str, object] = {}
    current_key: str | None = None

    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        scalar = SCALAR_RE.match(line)
        if scalar and not line.startswith((" ", "\t")):
            key, value = scalar.group(1), (scalar.group(2) or "").strip()
            current_key = key
            if value == "[]":
                data[key] = []
            elif value:
                data[key] = strip_quotes(value)
            else:
                data[key] = []
            continue

        item = LIST_ITEM_RE.match(line)
        if item and current_key:
            existing = data.setdefault(current_key, [])
            if isinstance(existing, list):
                existing.append(strip_quotes(item.group(1).strip()))

    return data


def strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def read_markdown_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def find_data_ids(path: Path) -> list[str]:
    if not path.exists():
        return []
    ids: list[str] = []
    for line in read_markdown_text(path).splitlines():
        match = re.match(r"^\s*-\s+id:\s*(.+?)\s*$", line)
        if match:
            ids.append(strip_quotes(match.group(1).strip()))
    return ids
