# wave-aware retry budget과 adaptive pacing 정책을 검증한다.

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tlh import dispatcher
from tlh.merge_harness import _routing_lines, _routing_summary
from tlh.schemas import TaskCard, WorkerResult
from tlh.vault import init_project
from tlh.worker_pool import RetryBudget


REPO_ROOT = Path(__file__).resolve().parents[1]


def card(task_id: str) -> TaskCard:
    return TaskCard(
        task_id=task_id,
        run_id="run-wave-budget",
        loop_index=0,
        title=f"Wave budget task {task_id}",
        goal="Validate wave-aware retry budget.",
        worker_role="builder",
        expected_output="WorkerResult",
        attach_point="FinalPacket.Scope",
        merge_key="s21_wave_budget",
    )


def prepare_rows(monkeypatch, tmp_path: Path, worker_count: int, wave_size: int, cooldown_seconds: float = 0) -> list[dict]:
    init_project(tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(f"GOOGLE_API_KEY_{slot}=SECRET_{slot}" for slot in range(1, worker_count + 1)),
        encoding="utf-8",
    )
    monkeypatch.setenv("TLH_WORKER_BACKEND", "live")
    monkeypatch.setenv("TLH_LIVE_WORKER_LIMIT", str(worker_count))
    monkeypatch.setenv("TLH_LIVE_WAVE_SIZE", str(wave_size))
    monkeypatch.setenv("TLH_GEMMA_RETRY_BUDGET_WORKERS", "5")
    if cooldown_seconds:
        monkeypatch.setenv("TLH_LIVE_WAVE_COOLDOWN_SECONDS", str(cooldown_seconds))
    else:
        monkeypatch.delenv("TLH_LIVE_WAVE_COOLDOWN_SECONDS", raising=False)
    return [card(f"T{index:03d}").to_dict() for index in range(worker_count)]


def result_for(task_card: TaskCard, env: dict[str, str], first_error_type: str = "none") -> WorkerResult:
    return WorkerResult(
        task_id=task_card.task_id,
        worker_id="live-builder",
        summary="wave budget result",
        findings=["scope: wave budget result"],
        backend="live",
        live_generated=True,
        metadata={
            "backend": "live",
            "requested_backend": "live",
            "selected_backend": "live",
            "wave_enabled": env.get("TLH_LIVE_WAVE_ENABLED") == "true",
            "wave_index": int(env.get("TLH_LIVE_WAVE_INDEX", "0")),
            "wave_size": int(env.get("TLH_LIVE_WAVE_SIZE", "0")),
            "wave_count": int(env.get("TLH_LIVE_WAVE_COUNT", "0")),
            "runtime_execution_model": env.get("TLH_LIVE_RUNTIME_EXECUTION_MODEL"),
            "actual_concurrency_limited": env.get("TLH_LIVE_ACTUAL_CONCURRENCY_LIMITED") == "true",
            "max_concurrent_live_workers": int(env.get("TLH_LIVE_WAVE_MAX_CONCURRENT", "0")),
            "key_slot": int(env.get("TLH_GEMMA_KEY_SLOT", "0")),
            "retry_count": 0,
            "fallback_used": False,
            "fallback_cause": "none",
            "first_error_type": first_error_type,
            "final_error_type": "none",
            "error_type": "none",
        },
    )


def run_route(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("TLH_GEMMA_API_KEY", None)
    return subprocess.run(
        [sys.executable, "-m", "tlh", "route-dry-run", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
    )


def test_wave_aware_budget_prevents_later_wave_starvation() -> None:
    budget = RetryBudget(5, wave_count=3)

    wave_1_claims = [budget.claim(wave_index=1) for _ in range(5)]
    wave_2_claims = [budget.claim(wave_index=2) for _ in range(3)]
    wave_3_claims = [budget.claim(wave_index=3) for _ in range(3)]

    assert wave_1_claims == [True, True, True, False, False]
    assert wave_2_claims == [True, False, False]
    assert wave_3_claims == [True, False, False]
    assert budget.claimed_total == 5
    assert budget.remaining == 0
    assert budget.claimed_by_wave == {1: 3, 2: 1, 3: 1}


def test_wave_size_8_budget_allocation() -> None:
    budget = RetryBudget(5, wave_count=3)

    assert budget.wave_remaining_allowance(1) == 3
    assert [budget.claim(wave_index=1) for _ in range(3)] == [True, True, True]
    assert budget.wave_remaining_allowance(1) == 0
    assert budget.wave_remaining_allowance(2) == 1
    assert budget.claim(wave_index=2) is True
    assert budget.wave_remaining_allowance(3) == 1
    assert budget.claim(wave_index=3) is True
    assert budget.claimed_total == 5


def test_wave_size_11_budget_allocation() -> None:
    budget = RetryBudget(5, wave_count=2)

    assert [budget.claim(wave_index=1) for _ in range(5)] == [True, True, True, True, False]
    assert budget.remaining == 1
    assert budget.claim(wave_index=2) is True
    assert budget.claimed_by_wave == {1: 4, 2: 1}


def test_budget_remains_thread_safe_under_concurrent_failures() -> None:
    budget = RetryBudget(5, wave_count=1)
    lock = threading.Lock()
    results: list[bool] = []

    def claim() -> None:
        claimed = budget.claim(wave_index=1)
        with lock:
            results.append(claimed)

    with ThreadPoolExecutor(max_workers=11) as executor:
        list(executor.map(lambda _: claim(), range(11)))

    assert sum(1 for item in results if item) == 5
    assert budget.claimed_total == 5
    assert budget.exhausted_count == 6


def test_unused_reserve_carries_forward() -> None:
    budget = RetryBudget(5, wave_count=3)

    assert budget.wave_remaining_allowance(1) == 3
    assert budget.wave_remaining_allowance(2) == 4
    assert [budget.claim(wave_index=2) for _ in range(4)] == [True, True, True, True]
    assert budget.claim(wave_index=2) is False
    assert budget.claim(wave_index=3) is True
    assert budget.claimed_by_wave == {2: 4, 3: 1}


def test_429_triggers_adaptive_pacing_when_enabled(monkeypatch, tmp_path: Path) -> None:
    rows = prepare_rows(monkeypatch, tmp_path, worker_count=4, wave_size=2, cooldown_seconds=30)
    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def fake_run_worker(task_card: TaskCard, env=None, routing_decision=None, retry_budget=None) -> WorkerResult:
        assert env is not None
        first_error = "api_429_rate_limit" if env.get("TLH_LIVE_WAVE_INDEX") == "1" and task_card.task_id == "T000" else "none"
        return result_for(task_card, env, first_error_type=first_error)

    monkeypatch.setattr(dispatcher, "run_worker", fake_run_worker)
    monkeypatch.setattr(dispatcher.time, "sleep", fake_sleep)

    results = dispatcher.dispatch(tmp_path, "run-wave-budget", rows)

    assert sleeps == [30.0]
    assert all(result.metadata["adaptive_pacing_enabled"] is True for result in results)
    assert all(result.metadata["cooldown_applied_between_waves"] is True for result in results)
    assert results[0].metadata["cooldown_by_wave"] == {"1": 30.0}
    assert results[0].metadata["adaptive_pacing_reason"] == "api_429_rate_limit"


def test_no_cooldown_by_default(monkeypatch, tmp_path: Path) -> None:
    rows = prepare_rows(monkeypatch, tmp_path, worker_count=4, wave_size=2)
    sleeps: list[float] = []

    def fake_run_worker(task_card: TaskCard, env=None, routing_decision=None, retry_budget=None) -> WorkerResult:
        assert env is not None
        return result_for(task_card, env, first_error_type="api_429_rate_limit")

    monkeypatch.setattr(dispatcher, "run_worker", fake_run_worker)
    monkeypatch.setattr(dispatcher.time, "sleep", lambda seconds: sleeps.append(seconds))

    results = dispatcher.dispatch(tmp_path, "run-wave-budget", rows)

    assert sleeps == []
    assert all(result.metadata["wave_cooldown_enabled"] is False for result in results)
    assert all(result.metadata["cooldown_applied_between_waves"] is False for result in results)


def test_route_dry_run_shows_budget_pacing_policy(tmp_path: Path) -> None:
    result = run_route(
        tmp_path,
        "--workers",
        "22",
        "--mode",
        "limited_live",
        "--live-limit",
        "22",
        "--live-wave-size",
        "8",
        "--live-wave-cooldown-seconds",
        "30",
    )

    assert result.returncode == 0
    assert "retry_budget_policy: wave_aware_reserve" in result.stdout
    assert "retry_budget_limit: 5" in result.stdout
    assert "wave_cooldown_seconds: 30.0" in result.stdout
    assert "adaptive_pacing_enabled: YES" in result.stdout
    assert "actual API call: NO" in result.stdout

    json_result = run_route(
        tmp_path,
        "--workers",
        "22",
        "--mode",
        "limited_live",
        "--live-limit",
        "22",
        "--live-wave-size",
        "8",
        "--live-wave-cooldown-seconds",
        "30",
        "--json",
    )
    payload = json.loads(json_result.stdout)
    assert payload["wave_policy"]["retry_budget_policy"] == "wave_aware_reserve"
    assert payload["wave_policy"]["retry_budget_limit"] == 5
    assert payload["wave_policy"]["wave_cooldown_seconds"] == 30.0
    assert payload["wave_policy"]["adaptive_pacing_enabled"] is True


def test_result_order_remains_deterministic(monkeypatch, tmp_path: Path) -> None:
    rows = prepare_rows(monkeypatch, tmp_path, worker_count=6, wave_size=3)

    def fake_run_worker(task_card: TaskCard, env=None, routing_decision=None, retry_budget=None) -> WorkerResult:
        assert env is not None
        return result_for(task_card, env)

    monkeypatch.setattr(dispatcher, "run_worker", fake_run_worker)

    results = dispatcher.dispatch(tmp_path, "run-wave-budget", rows)

    assert [result.task_id for result in results] == [f"T{index:03d}" for index in range(6)]


def test_final_summary_lines_include_budget_and_pacing() -> None:
    result = WorkerResult(
        task_id="T001",
        worker_id="live-builder",
        summary="summary",
        findings=["scope: summary"],
        backend="live",
        live_generated=True,
        metadata={
            "backend": "live",
            "requested_backend": "live",
            "selected_backend": "live",
            "policy_mode": "limited_live",
            "max_live_workers": 22,
            "available_key_slots": 22,
            "key_slot": 1,
            "retry_count": 1,
            "max_retry_attempts": 2,
            "retry_backoff_enabled": True,
            "retry_backoff_schedule": [5.0, 15.0],
            "retry_jitter_enabled": True,
            "retry_budget_enabled": True,
            "retry_budget_limit": 5,
            "retry_budget_policy": "wave_aware_reserve",
            "retry_budget_claimed_total": 1,
            "retry_budget_claimed_by_wave": {"1": 1},
            "retry_budget_exhausted_by_wave": {},
            "first_error_type": "api_429_rate_limit",
            "fallback_used": False,
            "fallback_cause": "none",
            "key_slot_preserved": True,
            "wave_enabled": True,
            "wave_size": 8,
            "wave_count": 3,
            "runtime_execution_model": "concurrent_wave",
            "actual_concurrency_limited": True,
            "max_concurrent_live_workers": 8,
            "target_live_workers": 22,
            "wave_index": 1,
            "wave_cooldown_enabled": True,
            "wave_cooldown_seconds": 30.0,
            "adaptive_pacing_enabled": True,
            "cooldown_applied_between_waves": True,
            "cooldown_total_seconds": 30.0,
            "cooldown_by_wave": {"1": 30.0},
        },
    )

    lines = _routing_lines(_routing_summary([result]))

    assert "retry budget policy: wave_aware_reserve" in lines
    assert "retry budget claimed by wave: {'1': 1}" in lines
    assert "wave cooldown seconds: 30.0" in lines
    assert "adaptive pacing enabled: True" in lines
    assert "cooldown by wave: {'1': 30.0}" in lines


def test_secret_safety_for_wave_budget_policy(monkeypatch, tmp_path: Path) -> None:
    rows = prepare_rows(monkeypatch, tmp_path, worker_count=2, wave_size=2, cooldown_seconds=30)

    def fake_run_worker(task_card: TaskCard, env=None, routing_decision=None, retry_budget=None) -> WorkerResult:
        assert env is not None
        return result_for(task_card, env)

    monkeypatch.setattr(dispatcher, "run_worker", fake_run_worker)

    dispatcher.dispatch(tmp_path, "run-wave-budget", rows)

    written = (tmp_path / "machine" / "runs" / "run-wave-budget" / "worker_results.jsonl").read_text(
        encoding="utf-8"
    )
    assert "SECRET_" not in written
    assert "key_slot" in written
