# TaskCard를 worker에 전달하고 WorkerResult를 저장한다.

from __future__ import annotations

import os
from pathlib import Path

from .packet_writer import frontmatter_note, markdown_list, write_jsonl, write_text
from .schemas import TaskCard, WorkerResult, from_dict
from .vault import note_meta, vault_root
from .worker_pool import run_worker


def dispatch(root: Path, run_id: str, card_rows: list[dict]) -> list[WorkerResult]:
    cards = [from_dict(TaskCard, row) for row in card_rows]
    results: list[WorkerResult] = []
    live_limit = _live_worker_limit(os.environ)
    live_count = 0
    for card in cards:
        card_env = os.environ.copy()
        requested = _requested_backend(card, card_env)
        if _requests_live(requested, card_env):
            if live_limit is not None and live_count >= live_limit:
                card_env["TLH_FORCE_WORKER_BACKEND"] = "stub"
            else:
                live_count += 1
                card_env["TLH_WORKER_BACKEND"] = "live"
                card_env["TLH_LIVE_WORKER_INDEX"] = str(live_count)
        if live_limit is not None:
            card_env["TLH_LIVE_WORKER_LIMIT"] = str(live_limit)
        results.append(run_worker(card, env=card_env))
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


def _live_worker_limit(env: dict[str, str]) -> int | None:
    raw = env.get("TLH_LIVE_WORKER_LIMIT")
    if raw is None or not raw.strip():
        return None
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def _requested_backend(card: TaskCard, env: dict[str, str]) -> str:
    return card.backend_hint.strip().lower() or env.get("TLH_WORKER_BACKEND", "stub").strip().lower() or "stub"


def _requests_live(requested: str, env: dict[str, str]) -> bool:
    if requested == "live":
        return True
    if requested == "auto":
        return bool(env.get("TLH_GEMMA_API_KEY", "").strip())
    return False


def _metadata_lines(result: WorkerResult) -> list[str]:
    return [f"{key}: {value}" for key, value in result.metadata.items()]
