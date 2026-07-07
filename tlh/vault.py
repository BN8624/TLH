# Obsidian 호환 vault 구조와 공통 note 생성을 관리한다.

from __future__ import annotations

from pathlib import Path
from typing import Any

from .packet_writer import frontmatter_note, utc_now, write_json, write_text, write_text_if_missing


VAULT_DIRS = [
    "00_Inbox",
    "01_Runs",
    "02_TaskCards",
    "03_WorkerResults",
    "04_MergePackets",
    "05_Artifacts",
    "06_Handoff",
    "07_Patterns",
    "08_Failures",
    "09_Decisions",
    "10_ContextPackets",
    "11_MinimalityChecks",
]


def repo_root() -> Path:
    return Path.cwd()


def vault_root(root: Path | None = None) -> Path:
    return (root or repo_root()) / "vault"


def run_root(root: Path | None = None) -> Path:
    return (root or repo_root()) / "machine" / "runs"


def init_project(root: Path | None = None) -> list[Path]:
    root = root or repo_root()
    created: list[Path] = []
    vault = vault_root(root)
    for directory in VAULT_DIRS:
        path = vault / directory
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(path)
    runs = run_root(root)
    if not runs.exists():
        runs.mkdir(parents=True, exist_ok=True)
        created.append(runs)

    now = utc_now()
    defaults = {
        vault / "_AI_README.md": _base_note(
            "vault_readme",
            "AI agents should start with _CURRENT_STATE.md, then _AI_INDEX.md, then only the linked notes needed for the task.",
            now,
        ),
        vault / "_CURRENT_STATE.md": _base_note(
            "current_state",
            "No active run yet. Use `python -m tlh run --mission <path>` to start one.",
            now,
        ),
        vault / "_AI_INDEX.md": _base_note(
            "ai_index",
            "Runs live in 01_Runs. TaskCards live in 02_TaskCards. WorkerResults live in 03_WorkerResults. Handoff packets live in 06_Handoff.",
            now,
        ),
        vault / "_GRAPH_INDEX.md": "# Graph Index\n\nNo graph nodes yet.\n",
    }
    for path, content in defaults.items():
        if write_text_if_missing(path, content):
            created.append(path)
    graph_json = vault / "_GRAPH_INDEX.json"
    if not graph_json.exists():
        write_json(graph_json, {"nodes": [], "edges": []})
        created.append(graph_json)
    return created


def state_path(run_id: str, root: Path | None = None) -> Path:
    return run_root(root) / run_id / "state.json"


def run_dir(run_id: str, root: Path | None = None) -> Path:
    return run_root(root) / run_id


def write_current_state(run_id: str, status: str, summary: str, root: Path | None = None) -> None:
    now = utc_now()
    note = frontmatter_note(
        {
            "type": "current_state",
            "id": "vault-current-state",
            "run_id": run_id,
            "status": status,
            "created": now,
            "updated": now,
            "read_priority": "high",
            "ai_readable": True,
            "supersedes": "",
            "superseded_by": "",
            "source": "tlh",
        },
        {
            "Purpose": "Track the active TLH run.",
            "Current State": summary,
            "Inputs": f"Run: {run_id}",
            "Outputs": f"Status: {status}",
            "Links": f"- [[{run_id}]]",
            "Do Next": "Continue with the next CLI command for this run.",
            "Do Not": "Do not treat raw worker output as final.",
        },
    )
    write_text(vault_root(root) / "_CURRENT_STATE.md", note)


def note_meta(note_type: str, note_id: str, run_id: str, status: str = "done") -> dict[str, Any]:
    now = utc_now()
    return {
        "type": note_type,
        "id": note_id,
        "run_id": run_id,
        "status": status,
        "created": now,
        "updated": now,
        "read_priority": "normal",
        "ai_readable": True,
        "supersedes": "",
        "superseded_by": "",
        "source": "tlh",
    }


def _base_note(note_id: str, current_state: str, now: str) -> str:
    return frontmatter_note(
        {
            "type": note_id,
            "id": note_id,
            "run_id": "",
            "status": "active",
            "created": now,
            "updated": now,
            "read_priority": "high",
            "ai_readable": True,
            "supersedes": "",
            "superseded_by": "",
            "source": "tlh",
        },
        {
            "Purpose": "Support TLH MVP runs.",
            "Current State": current_state,
            "Inputs": "TLH CLI generated this file.",
            "Outputs": "AI-readable vault guidance.",
            "Links": "None.",
            "Do Next": "Follow the active run note.",
            "Do Not": "Do not overwrite user-authored notes without a direct reason.",
        },
    )
