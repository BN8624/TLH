# TaskCard를 worker에 전달하고 WorkerResult를 저장한다.

from __future__ import annotations

import os
from pathlib import Path

from .key_pool import assign_key_slot_for_live_worker, collect_gemini_key_slots
from .live_routing import build_live_routing_policy, build_live_wave_plan, decide_worker_backend, live_wave_size, requested_backend
from .packet_writer import frontmatter_note, markdown_list, write_jsonl, write_text
from .schemas import TaskCard, WorkerResult, from_dict
from .vault import note_meta, vault_root
from .worker_pool import run_worker


def dispatch(root: Path, run_id: str, card_rows: list[dict]) -> list[WorkerResult]:
    cards = [from_dict(TaskCard, row) for row in card_rows]
    results: list[WorkerResult] = []
    policy = build_live_routing_policy(os.environ)
    key_slots = collect_gemini_key_slots(os.environ, root / ".env")
    live_count = 0
    retry_budget_limit = _retry_budget_limit(os.environ)
    retry_budget_remaining = retry_budget_limit
    planned = []
    key_slots_by_worker: dict[int, int] = {}
    for worker_index, card in enumerate(cards):
        card_env = os.environ.copy()
        card_env["TLH_GEMMA_KEY_POOL_AVAILABLE_SLOTS"] = str(len(key_slots))
        card_env["TLH_GEMMA_RETRY_BUDGET_WORKERS"] = str(retry_budget_limit)
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
            key_slot = assign_key_slot_for_live_worker(live_count, key_slots)
            if key_slot is not None:
                card_env["TLH_GEMMA_API_KEY"] = key_slots[key_slot]
                card_env["TLH_GEMMA_KEY_SLOT"] = str(key_slot)
                card_env["TLH_GEMMA_KEY_POOL_MODE"] = "pooled"
                key_slots_by_worker[worker_index] = key_slot
            else:
                card_env["TLH_GEMMA_KEY_POOL_MODE"] = "single_key" if card_env.get("TLH_GEMMA_API_KEY") else "unavailable"
        planned.append((worker_index, card, card_env, decision))

    wave_plan = build_live_wave_plan([item[3] for item in planned], live_wave_size(os.environ), key_slots_by_worker)
    wave_by_worker = _wave_by_worker(wave_plan)
    for _worker_index, card, card_env, decision in sorted(
        planned,
        key=lambda item: (wave_by_worker.get(item[0], 0), item[0]),
    ):
        card_env["TLH_GEMMA_RETRY_BUDGET_REMAINING"] = str(retry_budget_remaining)
        _attach_wave_env(card_env, decision.worker_index, wave_plan, wave_by_worker)
        result = run_worker(card, env=card_env, routing_decision=decision)
        if result.metadata.get("retry_budget_consumed"):
            retry_budget_remaining = max(0, retry_budget_remaining - 1)
        results.append(result)
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


def _retry_budget_limit(env) -> int:
    try:
        return max(0, int(env.get("TLH_GEMMA_RETRY_BUDGET_WORKERS", "5")))
    except (TypeError, ValueError):
        return 5


def _wave_by_worker(wave_plan) -> dict[int, int]:
    return {
        worker_index: wave.wave_index
        for wave in wave_plan.waves
        for worker_index in wave.worker_indices
    }


def _attach_wave_env(card_env: dict[str, str], worker_index: int, wave_plan, wave_by_worker: dict[int, int]) -> None:
    card_env["TLH_LIVE_WAVE_ENABLED"] = "true" if wave_plan.enabled else "false"
    card_env["TLH_LIVE_WAVE_COUNT"] = str(wave_plan.wave_count)
    card_env["TLH_LIVE_WAVE_TARGET_LIVE_WORKERS"] = str(wave_plan.target_live_workers)
    card_env["TLH_LIVE_WAVE_MAX_CONCURRENT"] = str(wave_plan.max_concurrent_live_workers)
    card_env["TLH_LIVE_WAVE_SUCCESSFUL_WORKERS_RERUN"] = "false"
    card_env["TLH_LIVE_WAVE_RETRY_WITHIN_WAVE"] = "true"
    card_env["TLH_LIVE_WAVE_PRESERVE_KEY_SLOT"] = "true"
    if wave_plan.wave_size:
        card_env["TLH_LIVE_WAVE_SIZE"] = str(wave_plan.wave_size)
    if worker_index in wave_by_worker:
        card_env["TLH_LIVE_WAVE_INDEX"] = str(wave_by_worker[worker_index])
