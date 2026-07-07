# TaskCard를 worker에 전달하고 WorkerResult를 저장한다.

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import time

from .key_pool import assign_key_slot_for_live_worker, collect_gemini_key_slots
from .live_routing import build_live_routing_policy, build_live_wave_plan, decide_worker_backend, live_wave_size, requested_backend
from .packet_writer import frontmatter_note, markdown_list, write_jsonl, write_text
from .schemas import TaskCard, WorkerResult, from_dict
from .vault import note_meta, vault_root
from .worker_pool import RetryBudget, run_worker


def dispatch(root: Path, run_id: str, card_rows: list[dict]) -> list[WorkerResult]:
    cards = [from_dict(TaskCard, row) for row in card_rows]
    results: list[WorkerResult] = []
    policy = build_live_routing_policy(os.environ)
    key_slots = collect_gemini_key_slots(os.environ, root / ".env")
    live_count = 0
    retry_budget_limit = _retry_budget_limit(os.environ)
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
    retry_budget = RetryBudget(retry_budget_limit, wave_count=wave_plan.wave_count)
    wave_by_worker = _wave_by_worker(wave_plan)
    results = _execute_planned_workers(
        planned,
        wave_plan,
        wave_by_worker,
        retry_budget,
        cooldown_seconds=_wave_cooldown_seconds(os.environ),
    )
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


def _execute_planned_workers(
    planned: list,
    wave_plan,
    wave_by_worker: dict[int, int],
    retry_budget: RetryBudget,
    cooldown_seconds: float = 0.0,
    wave_sleep=None,
) -> list[WorkerResult]:
    results_by_worker: dict[int, WorkerResult] = {}
    cooldown_by_wave: dict[int, float] = {}
    if not wave_plan.enabled:
        for item in sorted(planned, key=lambda planned_item: planned_item[0]):
            worker_index, result = _run_planned_worker(item, wave_plan, wave_by_worker, retry_budget)
            results_by_worker[worker_index] = result
        _attach_run_policy_metadata(results_by_worker.values(), retry_budget, cooldown_seconds, cooldown_by_wave)
        return [results_by_worker[item[0]] for item in sorted(planned, key=lambda planned_item: planned_item[0])]

    no_wave_items = [item for item in planned if item[0] not in wave_by_worker]
    for item in sorted(no_wave_items, key=lambda planned_item: planned_item[0]):
        worker_index, result = _run_planned_worker(item, wave_plan, wave_by_worker, retry_budget)
        results_by_worker[worker_index] = result

    planned_by_worker = {item[0]: item for item in planned}
    sleep = wave_sleep or time.sleep
    for wave in wave_plan.waves:
        wave_items = [planned_by_worker[worker_index] for worker_index in wave.worker_indices]
        if not wave_items:
            continue
        max_workers = min(wave_plan.wave_size or len(wave_items), len(wave_items))
        wave_results: list[WorkerResult] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(_run_planned_worker, item, wave_plan, wave_by_worker, retry_budget)
                for item in wave_items
            ]
            for future in futures:
                worker_index, result = future.result()
                results_by_worker[worker_index] = result
                wave_results.append(result)
        if cooldown_seconds > 0 and wave.wave_index < wave_plan.wave_count and _wave_needs_cooldown(wave_results):
            cooldown_by_wave[wave.wave_index] = cooldown_seconds
            sleep(cooldown_seconds)

    _attach_run_policy_metadata(results_by_worker.values(), retry_budget, cooldown_seconds, cooldown_by_wave)
    return [results_by_worker[item[0]] for item in sorted(planned, key=lambda planned_item: planned_item[0])]


def _run_planned_worker(item, wave_plan, wave_by_worker: dict[int, int], retry_budget: RetryBudget) -> tuple[int, WorkerResult]:
    worker_index, card, card_env, decision = item
    card_env["TLH_GEMMA_RETRY_BUDGET_REMAINING"] = str(retry_budget.remaining)
    card_env["TLH_GEMMA_RETRY_BUDGET_POLICY"] = retry_budget.policy
    _attach_wave_env(card_env, decision.worker_index, wave_plan, wave_by_worker)
    wave_index = int(card_env.get("TLH_LIVE_WAVE_INDEX", "0") or "0")
    card_env["TLH_GEMMA_RETRY_BUDGET_WAVE_ALLOWANCE"] = str(retry_budget.wave_remaining_allowance(wave_index))
    try:
        result = run_worker(card, env=card_env, routing_decision=decision, retry_budget=retry_budget)
    except TypeError as exc:
        if "retry_budget" not in str(exc):
            raise
        result = run_worker(card, env=card_env, routing_decision=decision)
    return worker_index, result


def _attach_wave_env(card_env: dict[str, str], worker_index: int, wave_plan, wave_by_worker: dict[int, int]) -> None:
    card_env["TLH_LIVE_WAVE_ENABLED"] = "true" if wave_plan.enabled else "false"
    card_env["TLH_LIVE_WAVE_COUNT"] = str(wave_plan.wave_count)
    card_env["TLH_LIVE_WAVE_TARGET_LIVE_WORKERS"] = str(wave_plan.target_live_workers)
    card_env["TLH_LIVE_WAVE_MAX_CONCURRENT"] = str(wave_plan.max_concurrent_live_workers)
    card_env["TLH_LIVE_WAVE_SUCCESSFUL_WORKERS_RERUN"] = "false"
    card_env["TLH_LIVE_WAVE_RETRY_WITHIN_WAVE"] = "true"
    card_env["TLH_LIVE_WAVE_PRESERVE_KEY_SLOT"] = "true"
    card_env["TLH_LIVE_RUNTIME_EXECUTION_MODEL"] = "concurrent_wave" if wave_plan.enabled else "sequential"
    card_env["TLH_LIVE_ACTUAL_CONCURRENCY_LIMITED"] = "true" if wave_plan.enabled else "false"
    card_env["TLH_GEMMA_RETRY_BUDGET_SCOPE"] = "run"
    card_env["TLH_GEMMA_RETRY_BUDGET_POLICY"] = "wave_aware_reserve" if wave_plan.wave_count > 1 else "run_scoped_first_come"
    if wave_plan.wave_size:
        card_env["TLH_LIVE_WAVE_SIZE"] = str(wave_plan.wave_size)
    if worker_index in wave_by_worker:
        card_env["TLH_LIVE_WAVE_INDEX"] = str(wave_by_worker[worker_index])


def _wave_cooldown_seconds(env) -> float:
    try:
        return max(0.0, float(env.get("TLH_LIVE_WAVE_COOLDOWN_SECONDS", "0")))
    except (TypeError, ValueError):
        return 0.0


def _wave_needs_cooldown(results: list[WorkerResult]) -> bool:
    return any(
        result.metadata.get("first_error_type") == "api_429_rate_limit"
        or result.metadata.get("final_error_type") == "api_429_rate_limit"
        or result.metadata.get("error_type") == "api_429_rate_limit"
        for result in results
    )


def _attach_run_policy_metadata(
    results,
    retry_budget: RetryBudget,
    cooldown_seconds: float,
    cooldown_by_wave: dict[int, float],
) -> None:
    budget_metadata = retry_budget.metadata()
    cooldown_total = sum(cooldown_by_wave.values())
    cooldown_metadata = {
        "wave_cooldown_enabled": cooldown_seconds > 0,
        "wave_cooldown_seconds": cooldown_seconds,
        "adaptive_pacing_enabled": cooldown_seconds > 0,
        "adaptive_pacing_reason": "api_429_rate_limit" if cooldown_by_wave else "",
        "cooldown_applied_between_waves": bool(cooldown_by_wave),
        "cooldown_total_seconds": cooldown_total,
        "cooldown_by_wave": {str(key): cooldown_by_wave[key] for key in sorted(cooldown_by_wave)},
    }
    for result in results:
        result.metadata.update(budget_metadata)
        result.metadata.update(cooldown_metadata)
