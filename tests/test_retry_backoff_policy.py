# retry backoff, jitter, budget 정책을 검증한다.

from __future__ import annotations

import json

from tlh import gemma_client
from tlh.live_routing import LiveRoutingDecision
from tlh.merge_harness import _routing_summary
from tlh.schemas import TaskCard
from tlh.worker_pool import run_worker


def card(task_id: str = "T001") -> TaskCard:
    return TaskCard(
        task_id=task_id,
        run_id="run-retry-policy",
        loop_index=0,
        title="Retry policy test",
        goal="Return structured output.",
        worker_role="builder",
        expected_output="WorkerResult",
        attach_point="FinalPacket.Scope",
        merge_key="s15_retry_policy",
    )


def decision(worker_index: int = 0) -> LiveRoutingDecision:
    return LiveRoutingDecision(
        worker_index=worker_index,
        requested_backend="auto",
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


def env(key_slot: int = 1, budget_remaining: int = 5) -> dict[str, str]:
    return {
        "TLH_WORKER_BACKEND": "live",
        "TLH_GEMMA_API_KEY": "SECRET_VALUE",
        "TLH_GEMMA_KEY_SLOT": str(key_slot),
        "TLH_GEMMA_KEY_POOL_MODE": "pooled",
        "TLH_GEMMA_KEY_POOL_AVAILABLE_SLOTS": "22",
        "TLH_GEMMA_MAX_RETRY_ATTEMPTS": "2",
        "TLH_GEMMA_RETRY_BACKOFF_SECONDS": "5,15",
        "TLH_GEMMA_RETRY_JITTER_ENABLED": "true",
        "TLH_GEMMA_RETRY_JITTER_MAX_SECONDS": "2",
        "TLH_GEMMA_RETRY_BUDGET_WORKERS": "5",
        "TLH_GEMMA_RETRY_BUDGET_REMAINING": str(budget_remaining),
    }


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


def sequence(*responses: gemma_client.GemmaResponse):
    remaining = list(responses)

    def generate(_prompt: str) -> gemma_client.GemmaResponse:
        return remaining.pop(0)

    return generate


def fail(error: str) -> gemma_client.GemmaResponse:
    return gemma_client.GemmaResponse(success=False, error=error, model="mock-gemma")


def run_with_fake_wait(task: TaskCard, generate, key_slot: int = 1, budget_remaining: int = 5):
    sleeps: list[float] = []
    result = run_worker(
        task,
        env=env(key_slot, budget_remaining),
        live_generate=generate,
        routing_decision=decision(int(task.task_id[-3:]) if task.task_id[-3:].isdigit() else 0),
        retry_sleep=sleeps.append,
        retry_jitter=lambda _low, _high: 0.0,
    )
    return result, sleeps


def test_503_succeeds_on_second_retry() -> None:
    result, sleeps = run_with_fake_wait(
        card("T001"),
        sequence(fail("503 UNAVAILABLE high demand"), fail("503 high demand"), success_response()),
        key_slot=6,
    )

    assert result.backend == "live"
    assert result.metadata["attempt_count"] == 3
    assert result.metadata["retry_count"] == 2
    assert result.metadata["final_backend"] == "live"
    assert result.metadata["fallback_used"] is False
    assert result.metadata["key_slot_preserved"] is True
    assert result.metadata["successful_workers_rerun"] is False
    assert [attempt["key_slot"] for attempt in result.metadata["attempts"]] == [6, 6, 6]
    assert sleeps == [5.0, 15.0]


def test_500_succeeds_after_backoff() -> None:
    result, sleeps = run_with_fake_wait(
        card("T001"),
        sequence(fail("500 INTERNAL internal error"), success_response()),
        key_slot=7,
    )

    assert result.backend == "live"
    assert result.metadata["retry_count"] == 1
    assert result.metadata["final_backend"] == "live"
    assert result.metadata["fallback_used"] is False
    assert result.metadata["retry_backoff_schedule"] == [5.0, 15.0]
    assert sleeps == [5.0]


def test_timeout_fails_after_max_retries_then_fallback() -> None:
    result, sleeps = run_with_fake_wait(
        card("T001"),
        sequence(
            fail("Gemma call timed out after 300 seconds."),
            fail("timed out"),
            fail("timeout again"),
        ),
        key_slot=8,
    )

    assert result.backend == "stub"
    assert result.metadata["retry_count"] == 2
    assert result.metadata["final_backend"] == "stub"
    assert result.metadata["fallback_used"] is True
    assert result.metadata["fallback_after_retry"] is True
    assert result.metadata["fallback_cause"] == "timeout"
    assert sleeps == [5.0, 15.0]


def test_429_retry_preserves_key_slot() -> None:
    result, _sleeps = run_with_fake_wait(
        card("T001"),
        sequence(fail("429 rate limit"), success_response()),
        key_slot=9,
    )

    assert result.backend == "live"
    assert result.metadata["retry_count"] == 1
    assert [attempt["key_slot"] for attempt in result.metadata["attempts"]] == [9, 9]
    assert result.metadata["key_slot_preserved"] is True


def test_auth_error_is_not_retried() -> None:
    result, sleeps = run_with_fake_wait(
        card("T001"),
        sequence(fail("API key SECRET_VALUE unauthorized")),
        key_slot=10,
    )

    assert result.backend == "stub"
    assert result.metadata["retry_count"] == 0
    assert result.metadata["error_type"] == "api_auth_error"
    assert sleeps == []
    assert "SECRET_VALUE" not in json.dumps(result.to_dict())


def test_schema_error_is_not_retried() -> None:
    result, sleeps = run_with_fake_wait(card("T001"), sequence(fail("schema validation failure")), key_slot=11)

    assert result.metadata["retry_count"] == 0
    assert result.metadata["error_type"] == "schema_error"
    assert sleeps == []


def test_invalid_model_response_is_not_retried() -> None:
    result, sleeps = run_with_fake_wait(card("T001"), sequence(fail("invalid model response parse failed")), key_slot=12)

    assert result.metadata["retry_count"] == 0
    assert result.metadata["error_type"] == "invalid_model_response"
    assert sleeps == []


def test_retry_budget_limits_retried_workers() -> None:
    results = []
    budget_remaining = 5
    call_counts: dict[str, int] = {}
    for index in range(10):
        task = card(f"T{index:03d}")
        call_counts[task.task_id] = 0

        def generate(_prompt: str, task_id: str = task.task_id) -> gemma_client.GemmaResponse:
            call_counts[task_id] += 1
            return fail("503 high demand")

        result, _sleeps = run_with_fake_wait(task, generate, key_slot=index + 1, budget_remaining=budget_remaining)
        if result.metadata["retry_budget_consumed"]:
            budget_remaining -= 1
        results.append(result)

    summary = _routing_summary(results)["retry_policy"]
    assert summary["retryable_error_count"] == 10
    assert summary["retried_worker_count"] == 5
    assert summary["retry_budget_exhausted_count"] == 5
    assert summary["successful_workers_rerun"] is False
    assert all(call_counts[f"T{index:03d}"] == (3 if index < 5 else 1) for index in range(10))


def test_backoff_and_jitter_recorded_without_real_sleep() -> None:
    sleeps: list[float] = []
    result = run_worker(
        card("T001"),
        env=env(13),
        live_generate=sequence(fail("503 high demand"), success_response()),
        routing_decision=decision(),
        retry_sleep=sleeps.append,
        retry_jitter=lambda _low, _high: 1.25,
    )

    assert result.metadata["retry_jitter_enabled"] is True
    assert result.metadata["retry_backoff_enabled"] is True
    assert result.metadata["attempts"][0]["scheduled_retry_delay_seconds"] == 6.25
    assert sleeps == [6.25]


def test_secret_safety_in_retry_metadata_and_summary() -> None:
    result, _sleeps = run_with_fake_wait(
        card("T001"),
        sequence(fail("500 INTERNAL SECRET_VALUE"), success_response()),
        key_slot=14,
    )
    summary = _routing_summary([result])
    serialized = json.dumps({"result": result.to_dict(), "summary": summary})

    assert "SECRET_VALUE" not in serialized
    assert "key_slot" in serialized
