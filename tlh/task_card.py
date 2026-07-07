# TaskCard를 JSONL과 vault note로 저장한다.

from __future__ import annotations

from pathlib import Path

from .packet_writer import frontmatter_note, markdown_list, write_jsonl, write_text
from .schemas import TaskCard
from .vault import note_meta, vault_root


def save_task_cards(root: Path, run_id: str, cards: list[TaskCard]) -> None:
    run_dir = root / "machine" / "runs" / run_id
    write_jsonl(run_dir / "task_cards.jsonl", [card.to_dict() for card in cards])
    for card in cards:
        note = frontmatter_note(
            note_meta("task_card", card.task_id, run_id),
            {
                "Purpose": card.goal,
                "Current State": f"Assigned to worker role `{card.worker_role}` with backend hint `{card.backend_hint or 'default'}`.",
                "Inputs": markdown_list(card.input_context),
                "Outputs": card.expected_output,
                "Links": f"- PRODUCES: [[{card.task_id}-result]]",
                "Do Next": "Dispatch this TaskCard to a worker.",
                "Do Not": "Do not let the worker edit files or produce the final answer directly.",
            },
        )
        write_text(vault_root(root) / "02_TaskCards" / f"{card.task_id}.md", note)
