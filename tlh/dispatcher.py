# TaskCard를 worker에 전달하고 WorkerResult를 저장한다.

from __future__ import annotations

import os
from pathlib import Path

from .live_routing import build_live_routing_policy, decide_worker_backend, requested_backend
from .packet_writer import frontmatter_note, markdown_list, write_jsonl, write_text
from .schemas import TaskCard, WorkerResult, from_dict
from .vault import note_meta, vault_root
from .worker_pool import run_worker


def dispatch(root: Path, run_id: str, card_rows: list[dict]) -> list[WorkerResult]:
    cards = [from_dict(TaskCard, row) for row in card_rows]
    results: list[WorkerResult] = []
    policy = build_live_routing_policy(os.environ)
    live_count = 0
    for worker_index, card in enumerate(cards):
        card_env = os.environ.copy()
        requested = requested_backend(card, card_env)
        decision = decide_worker_backend(
            worker_index=worker_index,
            requested=requested,
            live_workers_used=live_count,
            policy=policy,
            env=card_env,
        )
        card_env["TLH_WORKER_BACKEND"] = decision.selected_backend
        if decision.selected_backend == "live":
            live_count += 1
        results.append(run_worker(card, env=card_env, routing_decision=decision))
    write_jsonl(root / "machine" / "runs" / run_id / "worker_results.jsonl", [result.to_dict() for result in results])
    for result in results:
        result_id = f"{result.task_id}-result"
        note = frontmatter_note(
            note_meta("worker_result", result_id, run_id),
            {
                "Purpose": f"Structured worker result for TaskCard {result.task_id}.",
                "Current State": result.summary,
                "Inputs": f"TaskCard: [[{result.task_id}]]",
                "Outputs": f"{markdown_list(result.findings)}\n\nMetadata:\n{markdown_list(_metadata_lines(result))}",
                "Links": f"- DERIVED_FROM: [[{result.task_id}]]\n- MERGED_INTO: [[{run_id}-M001]]",
                "Do Next": "Merge this result through MergeHarness.",
                "Do Not": "Do not treat this raw worker result as final.",
            },
        )
        write_text(vault_root(root) / "03_WorkerResults" / f"{result_id}.md", note)
    return results


def _metadata_lines(result: WorkerResult) -> list[str]:
    return [f"{key}: {value}" for key, value in result.metadata.items()]
