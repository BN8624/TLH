# TLH 산출물을 JSON과 Markdown 파일로 저장하는 도우미를 제공한다.

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text_if_missing(path: Path, content: str) -> bool:
    ensure_dir(path.parent)
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8", newline="\n")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_json(path: Path, data: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    text = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8", newline="\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def frontmatter_note(meta: dict[str, Any], sections: dict[str, str]) -> str:
    lines = ["---"]
    for key, value in meta.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif value is None:
            rendered = ""
        else:
            rendered = str(value)
        lines.append(f"{key}: {rendered}")
    lines.append("---")
    lines.append("")
    for title, body in sections.items():
        lines.append(f"## {title}")
        lines.append("")
        lines.append(body.rstrip() if body.strip() else "None.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def markdown_list(items: list[str]) -> str:
    if not items:
        return "None."
    return "\n".join(f"- {item}" for item in items)
