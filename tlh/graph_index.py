# Vault note의 frontmatter와 typed link를 읽어 graph index를 만든다.

from __future__ import annotations

import json
import re
from pathlib import Path

from .packet_writer import write_text
from .vault import vault_root

EDGE_TYPES = {
    "DEPENDS_ON",
    "PRODUCES",
    "MERGED_INTO",
    "UPDATES",
    "SUPERSEDES",
    "CONFLICTS_WITH",
    "DERIVED_FROM",
    "VALIDATES",
    "DROPPED_BY",
    "HANDOFF_TO",
    "USES_CONTEXT",
}


def generate(root: Path) -> dict:
    vault = vault_root(root)
    nodes: list[dict] = []
    edges: list[dict] = []
    for path in sorted(vault.rglob("*.md")):
        if path.name == "_GRAPH_INDEX.md":
            continue
        text = path.read_text(encoding="utf-8")
        meta = _frontmatter(text)
        node_id = meta.get("id") or path.stem
        nodes.append(
            {
                "id": node_id,
                "type": meta.get("type", "note"),
                "path": str(path.relative_to(vault)).replace("\\", "/"),
                "status": meta.get("status", ""),
            }
        )
        for edge_type, target in _typed_links(text):
            edges.append({"from": node_id, "to": target, "type": edge_type})
    graph = {"nodes": nodes, "edges": edges}
    (vault / "_GRAPH_INDEX.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Graph Index", "", "## Nodes", ""]
    lines.extend(f"- {node['id']} ({node['type']}): {node['path']}" for node in nodes)
    lines.extend(["", "## Edges", ""])
    lines.extend(f"- {edge['from']} --{edge['type']}--> {edge['to']}" for edge in edges)
    write_text(vault / "_GRAPH_INDEX.md", "\n".join(lines).rstrip() + "\n")
    return graph


def _frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta


def _typed_links(text: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    pattern = re.compile(r"-\s+([A-Z_]+):\s+\[\[([^\]]+)\]\]")
    for match in pattern.finditer(text):
        edge_type, target = match.groups()
        if edge_type in EDGE_TYPES:
            links.append((edge_type, target))
    return links
