# live wave runtime이 실제 동시 실행 제한으로 동작하는지 검증한다.

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tlh import dispatcher, gemma_client
from tlh.live_routing import LiveRoutingDecision
from tlh.schemas import TaskCard, WorkerResult
from tlh.vault import init_project
from tlh.worker_pool import RetryBudget, run_worker


REPO_ROOT = Path(__file__).resolve().parents[1]


def card(task_id: str) -> TaskCard:
    return TaskCard(
        task_id=task_id,
        run_id="run-wave-runtime",
        loop_index=0,
        title=f"Runtime wave task {task_id}",
        goal="Validate true concurrent wave execution.",
        worker_role="builder",
        expected_output="WorkerResult",
        attach_point="FinalPacket.Scope",
        merge_key="s17r_wave_runtime",
    )


def decision(worker_index: int) -> LiveRoutingDecision:
    return LiveRoutingDecision(
        worker_index=worker_index,
        requested_backend="live",
        selected_backend="live",
        policy_mode="limited_live",
        max_live_workers=22,
        live_worker_index=worker_index + 1,
        fallback_allowed=True,
        fallback_used=False,
        routing_reason="within live worker limit",
        routing_source="policy",
        policy_source="env:TLH_LIVE_WORKER_LIMIT",
        require_explicit_live=False,
        cost_guard_enabled=True,
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


def prepare_runtime_env(monkeypatch, tmp_path: Path, worker_count: int, wave_size: int | None = 11) -> list[dict]:
    init_project(tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(f"GOOGLE_API_KEY_{slot}=SECRET_{slot}" for slot in range(1, worker_count + 1)),
        encoding="utf-8",
    )
    monkeypatch.setenv("TLH_WORKER_BACKEND", "live")
    monkeypatch.setenv("TLH_LIVE_WORKER_LIMIT", str(worker_count))
    monkeypatch.setenv("TLH_GEMMA_RETRY_BUDGET_WORKERS", "5")
    if wave_size is None:
        monkeypatch.delenv("TLH_LIVE_WAVE_SIZE", raising=False)
    else:
        monkeypatch.setenv("TLH_LIVE_WAVE_SIZE", str(wave_size))
    return [card(f"T{index:03d}").to_dict() for index in range(worker_count)]


def result_for(task_card: TaskCard, env: dict[str, str], backend: str = "live", fallback: bool = False) -> WorkerResult:
    return WorkerResult(
        task_id=task_card.task_id,
        worker_id=f"{backend}-{task_card.worker_role}",
        summary=f"{backend} runtime result",
        findings=[f"scope: {backend} runtime result"],
        backend=backend,
        stub_generated=backend != "live",
        live_generated=backend == "live",
        fallback_used=fallback,
        metadata={
            "backend": backend,
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
            "fallback_used": fallback,
            "fallback_cause": "api_503_high_demand" if fallback else "none",
            "error_type": "api_503_high_demand" if fallback else "none",
        },
    )


def test_wave_size_limits_actual_concurrent_run_worker_calls(monkeypatch, tmp_path: Path) -> None:
    rows = prepare_runtime_env(monkeypatch, tmp_path, worker_count=22, wave_size=11)
    lock = threading.Lock()
    active = 0
    max_active = 0

    def fake_run_worker(task_card: TaskCard, env=None, routing_decision=None, retry_budget=None) -> WorkerResult:
        nonlocal active, max_active
        assert env is not None
        with lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.02)
        with lock:
            active -= 1
        return result_for(task_card, env)

    monkeypatch.setattr(dispatcher, "run_worker", fake_run_worker)

    dispatcher.dispatch(tmp_path, "run-wave-runtime", rows)

    assert max_active <= 11
    assert max_active > 1


def test_wave_2_starts_only_after_wave_1_completes(monkeypatch, tmp_path: Path) -> None:
    rows = prepare_runtime_env(monkeypatch, tmp_path, worker_count=22, wave_size=11)
    lock = threading.Lock()
    wave_1_started = 0
    wave_1_finished = 0
    wave_2_started = 0
    wave_1_all_started = threading.Event()
    release_wave_1 = threading.Event()

    def fake_run_worker(task_card: TaskCard, env=None, routing_decision=None, retry_budget=None) -> WorkerResult:
        nonlocal wave_1_started, wave_1_finished, wave_2_started
        assert env is not None
        wave_index = int(env.get("TLH_LIVE_WAVE_INDEX", "0"))
        with lock:
            if wave_index == 1:
                wave_1_started += 1
                if wave_1_started == 11:
                    wave_1_all_started.set()
            elif wave_index == 2:
                wave_2_started += 1
        if wave_index == 1:
            release_wave_1.wait(timeout=2)
            with lock:
                wave_1_finished += 1
        return result_for(task_card, env)

    monkeypatch.setattr(dispatcher, "run_worker", fake_run_worker)
    thread = threading.Thread(target=lambda: dispatcher.dispatch(tmp_path, "run-wave-runtime", rows))
    thread.start()

    assert wave_1_all_started.wait(timeout=2)
    time.sleep(0.05)
    with lock:
        assert wave_2_started == 0
        assert wave_1_finished == 0
    release_wave_1.set()
    thread.join(timeout=5)

    assert not thread.is_alive()
    with lock:
        assert wave_1_finished == 11
        assert wave_2_started == 11


def test_result_order_remains_deterministic_when_completion_order_differs(monkeypatch, tmp_path: Path) -> None:
    rows = prepare_runtime_env(monkeypatch, tmp_path, worker_count=8, wave_size=8)

    def fake_run_worker(task_card: TaskCard, env=None, routing_decision=None, retry_budget=None) -> WorkerResult:
        assert env is not None
        worker_index = int(task_card.task_id[-3:])
        time.sleep((8 - worker_index) * 0.005)
        return result_for(task_card, env)

    monkeypatch.setattr(dispatcher, "run_worker", fake_run_worker)

    results = dispatcher.dispatch(tmp_path, "run-wave-runtime", rows)

    assert [result.task_id for result in results] == [f"T{index:03d}" for index in range(8)]


def test_successful_workers_are_not_rerun(monkeypatch, tmp_path: Path) -> None:
    rows = prepare_runtime_env(monkeypatch, tmp_path, worker_count=4, wave_size=2)
    call_counts = {f"T{index:03d}": 0 for index in range(4)}

    def fake_run_worker(task_card: TaskCard, env=None, routing_decision=None, retry_budget=None) -> WorkerResult:
        assert env is not None
        call_counts[task_card.task_id] += 1
        fallback = task_card.task_id == "T002"
        return result_for(task_card, env, backend="stub" if fallback else "live", fallback=fallback)

    monkeypatch.setattr(dispatcher, "run_worker", fake_run_worker)

    dispatcher.dispatch(tmp_path, "run-wave-runtime", rows)

    assert call_counts == {f"T{index:03d}": 1 for index in range(4)}


def test_retry_budget_is_thread_safe_and_run_scoped() -> None:
    retry_budget = RetryBudget(5)

    def live_generate(_prompt: str) -> gemma_client.GemmaResponse:
        return gemma_client.GemmaResponse(success=False, error="503 high demand", model="mock-gemma")

    def run(index: int):
        return run_worker(
            card(f"T{index:03d}"),
            env={
                "TLH_WORKER_BACKEND": "live",
                "TLH_GEMMA_API_KEY": "SECRET_VALUE",
                "TLH_GEMMA_KEY_SLOT": str(index + 1),
                "TLH_GEMMA_FALLBACK_TO_STUB": "true",
                "TLH_GEMMA_MAX_RETRY_ATTEMPTS": "1",
                "TLH_GEMMA_RETRY_BACKOFF_SECONDS": "0",
                "TLH_GEMMA_RETRY_JITTER_ENABLED": "false",
                "TLH_GEMMA_RETRY_BUDGET_WORKERS": "5",
            },
            live_generate=live_generate,
            routing_decision=decision(index),
            retry_budget=retry_budget,
        )

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(run, range(10)))

    retried = sum(1 for result in results if result.metadata["retry_count"] > 0)
    exhausted = sum(1 for result in results if result.metadata["retry_skipped_reason"] == "retry budget exhausted")
    assert retried == 5
    assert exhausted == 5
    assert retry_budget.remaining == 0


def test_retry_preserves_key_slot_under_concurrency() -> None:
    retry_budget = RetryBudget(5)
    responses = [
        gemma_client.GemmaResponse(success=False, error="503 high demand", model="mock-gemma"),
        gemma_client.GemmaResponse(
            success=True,
            text=json.dumps(
                {
                    "summary": "Live result.",
                    "findings": ["scope: Live result."],
                    "risks": [],
                    "assumptions": [],
                    "open_questions": [],
                    "attach_notes": ["target: FinalPacket.Scope | content: Live result."],
                }
            ),
            model="mock-gemma",
        ),
    ]

    result = run_worker(
        card("T006"),
        env={
            "TLH_WORKER_BACKEND": "live",
            "TLH_GEMMA_API_KEY": "SECRET_VALUE",
            "TLH_GEMMA_KEY_SLOT": "6",
            "TLH_GEMMA_MAX_RETRY_ATTEMPTS": "1",
            "TLH_GEMMA_RETRY_BACKOFF_SECONDS": "0",
            "TLH_GEMMA_RETRY_JITTER_ENABLED": "false",
        },
        live_generate=lambda _prompt: responses.pop(0),
        routing_decision=decision(5),
        retry_budget=retry_budget,
    )

    assert [attempt["key_slot"] for attempt in result.metadata["attempts"]] == [6, 6]
    assert "SECRET_VALUE" not in json.dumps(result.to_dict())


def test_fallback_only_after_retry_failure(monkeypatch, tmp_path: Path) -> None:
    rows = prepare_runtime_env(monkeypatch, tmp_path, worker_count=3, wave_size=3)

    def fake_run_worker(task_card: TaskCard, env=None, routing_decision=None, retry_budget=None) -> WorkerResult:
        assert env is not None
        fallback = task_card.task_id == "T001"
        return result_for(task_card, env, backend="stub" if fallback else "live", fallback=fallback)

    monkeypatch.setattr(dispatcher, "run_worker", fake_run_worker)

    results = dispatcher.dispatch(tmp_path, "run-wave-runtime", rows)

    assert [result.fallback_used for result in results] == [False, True, False]


def test_no_wave_by_default_preserves_sequential_behavior(monkeypatch, tmp_path: Path) -> None:
    rows = prepare_runtime_env(monkeypatch, tmp_path, worker_count=4, wave_size=None)
    lock = threading.Lock()
    active = 0
    max_active = 0

    def fake_run_worker(task_card: TaskCard, env=None, routing_decision=None, retry_budget=None) -> WorkerResult:
        nonlocal active, max_active
        assert env is not None
        with lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.01)
        with lock:
            active -= 1
        return result_for(task_card, env)

    monkeypatch.setattr(dispatcher, "run_worker", fake_run_worker)

    results = dispatcher.dispatch(tmp_path, "run-wave-runtime", rows)

    assert max_active == 1
    assert all(result.metadata["wave_enabled"] is False for result in results)


def test_route_dry_run_text_and_json_report_concurrent_wave_semantics(tmp_path: Path) -> None:
    result = run_route(
        tmp_path,
        "--workers",
        "22",
        "--mode",
        "limited_live",
        "--live-limit",
        "22",
        "--live-wave-size",
        "11",
    )
    assert result.returncode == 0
    assert "runtime_execution_model: concurrent_wave" in result.stdout
    assert "planned_max_concurrent_live_workers: 11" in result.stdout
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
        "11",
        "--json",
    )
    payload = json.loads(json_result.stdout)
    assert payload["wave_policy"]["runtime_execution_model"] == "concurrent_wave"
    assert payload["wave_policy"]["planned_max_concurrent_live_workers"] == 11
    assert payload["wave_policy"]["actual_concurrency_limited"] is True


def test_secret_safety_for_wave_runtime(monkeypatch, tmp_path: Path) -> None:
    rows = prepare_runtime_env(monkeypatch, tmp_path, worker_count=2, wave_size=2)

    def fake_run_worker(task_card: TaskCard, env=None, routing_decision=None, retry_budget=None) -> WorkerResult:
        assert env is not None
        return result_for(task_card, env)

    monkeypatch.setattr(dispatcher, "run_worker", fake_run_worker)

    dispatcher.dispatch(tmp_path, "run-wave-runtime", rows)

    written = (tmp_path / "machine" / "runs" / "run-wave-runtime" / "worker_results.jsonl").read_text(
        encoding="utf-8"
    )
    assert "SECRET_" not in written
    assert "key_slot" in written
