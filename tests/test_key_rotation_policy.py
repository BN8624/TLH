# live key health pool과 retry rotation 정책을 검증한다.

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tlh import gemma_client
from tlh.key_pool import KeyHealthPool
from tlh.live_routing import LiveRoutingDecision
from tlh.merge_harness import _routing_lines, _routing_summary
from tlh.schemas import TaskCard, WorkerResult
from tlh.worker_pool import run_worker


REPO_ROOT = Path(__file__).resolve().parents[1]


def card(task_id: str = "T001") -> TaskCard:
    return TaskCard(
        task_id=task_id,
        run_id="run-key-rotation",
        loop_index=0,
        title="Key rotation test",
        goal="Return structured output.",
        worker_role="builder",
        expected_output="WorkerResult",
        attach_point="FinalPacket.Scope",
        merge_key="s23_key_rotation",
    )


def decision(worker_index: int = 0) -> LiveRoutingDecision:
    return LiveRoutingDecision(
        worker_index=worker_index,
        requested_backend="auto",
        selected_backend="live",
        policy_mode="limited_live",
        max_live_workers=5,
        live_worker_index=worker_index + 1,
        fallback_allowed=True,
        fallback_used=False,
        routing_reason="within live worker limit",
        routing_source="policy",
        policy_source="env:TLH_LIVE_WORKER_LIMIT",
        require_explicit_live=False,
        cost_guard_enabled=True,
    )


def env() -> dict[str, str]:
    return {
        "TLH_WORKER_BACKEND": "live",
        "TLH_GEMMA_KEY_POOL_AVAILABLE_SLOTS": "22",
        "TLH_GEMMA_MAX_RETRY_ATTEMPTS": "2",
        "TLH_GEMMA_RETRY_BACKOFF_SECONDS": "0,0",
        "TLH_GEMMA_RETRY_JITTER_ENABLED": "false",
        "TLH_GEMMA_RETRY_BUDGET_WORKERS": "5",
        "TLH_GEMMA_RETRY_BUDGET_REMAINING": "5",
    }


def key_slots(count: int = 22) -> dict[int, str]:
    return {slot: f"SECRET_{slot}" for slot in range(1, count + 1)}


def success_response(summary: str = "Live summary") -> gemma_client.GemmaResponse:
    return gemma_client.GemmaResponse(
        success=True,
        text=json.dumps(
            {
                "summary": summary,
                "findings": ["scope: Live result."],
                "risks": [],
                "assumptions": [],
                "open_questions": [],
                "attach_notes": ["target: FinalPacket.Scope | content: Live result."],
            }
        ),
        model="mock-gemma",
    )


def fail(error: str) -> gemma_client.GemmaResponse:
    return gemma_client.GemmaResponse(success=False, error=error, model="mock-gemma")


def sequence(*responses: gemma_client.GemmaResponse):
    remaining = list(responses)

    def generate(_prompt: str) -> gemma_client.GemmaResponse:
        return remaining.pop(0)

    return generate


def run_route(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    route_env = os.environ.copy()
    route_env["PYTHONPATH"] = str(REPO_ROOT)
    route_env["PYTHONDONTWRITEBYTECODE"] = "1"
    route_env.pop("TLH_GEMMA_API_KEY", None)
    return subprocess.run(
        [sys.executable, "-m", "tlh", "route-dry-run", *args],
        cwd=cwd,
        env=route_env,
        text=True,
        capture_output=True,
    )


def test_round_robin_uses_multiple_keys_over_sequential_live_calls() -> None:
    pool = KeyHealthPool(key_slots())
    leases = [pool.select_key(worker_index=index) for index in range(10)]

    assert [lease.key_slot for lease in leases if lease] == list(range(1, 11))
    assert pool.snapshot_summary()["fixed_worker_assignment"] is False
    assert "SECRET_" not in json.dumps(pool.snapshot_summary())


def test_429_rotates_to_different_healthy_key() -> None:
    pool = KeyHealthPool(key_slots())
    result = run_worker(
        card(),
        env=env(),
        live_generate=sequence(fail("429 rate limit"), success_response()),
        routing_decision=decision(),
        retry_sleep=lambda _seconds: None,
        retry_jitter=lambda _low, _high: 0.0,
        key_health_pool=pool,
    )

    assert result.backend == "live"
    assert result.metadata["attempt_key_slots"][0] != result.metadata["attempt_key_slots"][1]
    assert result.metadata["key_rotation_count"] == 1
    assert result.metadata["key_rotation_reason"] == "api_429_rate_limit"
    assert result.metadata["key_cooldown_applied"] is True
    assert "SECRET_" not in json.dumps(result.to_dict())


def test_auth_error_disables_key_for_run() -> None:
    pool = KeyHealthPool(key_slots())
    lease = pool.select_key(worker_index=0)
    assert lease is not None

    pool.record_failure(lease.key_slot, "api_auth_error")
    next_lease = pool.select_key(worker_index=1)

    assert next_lease is not None
    assert next_lease.key_slot != lease.key_slot
    assert pool.snapshot_summary()["disabled_key_count"] == 1
    assert "SECRET_" not in json.dumps(pool.snapshot_summary())


def test_500_and_503_can_rotate_key() -> None:
    for error in ("500 internal error", "503 high demand"):
        pool = KeyHealthPool(key_slots())
        result = run_worker(
            card(),
            env=env(),
            live_generate=sequence(fail(error), success_response()),
            routing_decision=decision(),
            retry_sleep=lambda _seconds: None,
            retry_jitter=lambda _low, _high: 0.0,
            key_health_pool=pool,
        )

        assert result.backend == "live"
        assert result.metadata["attempt_key_slots"][0] != result.metadata["attempt_key_slots"][1]
        assert result.metadata["key_rotation_count"] == 1


def test_schema_error_does_not_poison_key() -> None:
    pool = KeyHealthPool(key_slots())
    lease = pool.select_key(worker_index=0)
    assert lease is not None

    pool.record_failure(lease.key_slot, "schema_error")
    summary = pool.snapshot_summary()

    assert summary["disabled_key_count"] == 0
    assert summary["cooldown_key_count"] == 0


def test_key_pool_thread_safe_under_concurrent_selection() -> None:
    pool = KeyHealthPool(key_slots())

    def select(index: int) -> int:
        lease = pool.select_key(worker_index=index)
        assert lease is not None
        return lease.key_slot

    with ThreadPoolExecutor(max_workers=22) as executor:
        selected = list(executor.map(select, range(44)))

    summary = pool.snapshot_summary()
    assert len(selected) == 44
    assert sum(summary["lease_count_by_slot"].values()) == 44
    assert "SECRET_" not in json.dumps(summary)


def test_route_dry_run_shows_pooled_key_mode(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(f"GOOGLE_API_KEY_{slot}=SECRET_{slot}" for slot in range(1, 23)),
        encoding="utf-8",
    )

    result = run_route(tmp_path, "--workers", "22", "--mode", "limited_live", "--live-limit", "5", "--json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["key_pool"]["pooled"] is True
    assert payload["key_pool"]["fixed_worker_assignment"] is False
    assert payload["key_pool"]["selection_policy"] == "round_robin_health_aware"
    assert "SECRET_" not in result.stdout


def test_final_packet_and_codex_prompt_key_rotation_summary() -> None:
    result = WorkerResult(
        task_id="T001",
        worker_id="live-builder",
        summary="live result",
        findings=["scope: live result"],
        backend="live",
        stub_generated=False,
        live_generated=True,
        metadata={
            "available_key_slots": 22,
            "key_pool_mode": "rotating_health_pool",
            "key_selection_policy": "round_robin_health_aware",
            "key_rotation_enabled": True,
            "key_cooldown_enabled": True,
            "key_values_recorded": False,
            "key_slot": 2,
            "attempt_key_slots": [1, 2],
            "key_rotation_count": 1,
            "lease_count_by_slot": {"1": 1, "2": 1},
            "error_count_by_slot": {"1": 1},
        },
    )

    summary = _routing_summary([result])
    lines = _routing_lines(summary)

    assert summary["key_pool"]["key_pool_mode"] == "rotating_health_pool"
    assert summary["key_pool"]["key_rotation_enabled"] is True
    assert summary["key_pool"]["key_values_recorded"] is False
    assert any("key rotation enabled: True" in line for line in lines)


def test_all_keys_unavailable_returns_no_lease_without_leaking_values() -> None:
    pool = KeyHealthPool(key_slots(2))
    for slot in (1, 2):
        pool.record_failure(slot, "api_auth_error")

    assert pool.select_key(worker_index=0) is None
    assert pool.snapshot_summary()["disabled_key_count"] == 2
    assert "SECRET_" not in json.dumps(pool.snapshot_summary())


def test_secret_safety_in_worker_metadata() -> None:
    pool = KeyHealthPool(key_slots())
    result = run_worker(
        card(),
        env=env(),
        live_generate=sequence(fail("429 rate limit"), success_response()),
        routing_decision=decision(),
        retry_sleep=lambda _seconds: None,
        retry_jitter=lambda _low, _high: 0.0,
        key_health_pool=pool,
    )

    serialized = json.dumps(result.to_dict())
    assert "SECRET_" not in serialized
    assert "key_slot" in serialized
    assert "attempt_key_slots" in serialized
