# live worker telemetry와 targeted retry 정책을 검증한다.

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
        run_id="run-telemetry",
        loop_index=0,
        title="Telemetry test",
        goal="Return structured output.",
        worker_role="builder",
        expected_output="WorkerResult",
        attach_point="FinalPacket.Scope",
        merge_key="s13_telemetry",
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


def env(key_slot: int = 1) -> dict[str, str]:
    return {
        "TLH_WORKER_BACKEND": "live",
        "TLH_GEMMA_API_KEY": "SECRET_VALUE",
        "TLH_GEMMA_KEY_SLOT": str(key_slot),
        "TLH_GEMMA_KEY_POOL_MODE": "pooled",
        "TLH_GEMMA_KEY_POOL_AVAILABLE_SLOTS": "22",
        "TLH_GEMMA_MAX_RETRY_ATTEMPTS": "1",
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


def failing_then_success(error: str):
    responses = [gemma_client.GemmaResponse(success=False, error=error, model="mock-gemma"), success_response()]

    def generate(_prompt: str) -> gemma_client.GemmaResponse:
        return responses.pop(0)

    return generate


def always_fails(error: str):
    def generate(_prompt: str) -> gemma_client.GemmaResponse:
        return gemma_client.GemmaResponse(success=False, error=error, model="mock-gemma")

    return generate


def test_telemetry_metadata_completeness() -> None:
    result = run_worker(card(), env=env(3), live_generate=lambda _prompt: success_response(), routing_decision=decision())

    metadata = result.metadata
    for key in [
        "worker_index",
        "key_slot",
        "latency_ms",
        "attempt_count",
        "retry_count",
        "fallback_used",
        "error_type",
        "final_backend",
    ]:
        assert key in metadata
    assert metadata["key_slot"] == 3
    assert metadata["attempt_count"] == 1
    assert metadata["retry_count"] == 0
    assert metadata["final_backend"] == "live"
    assert metadata["error_type"] == "none"


def test_503_retry_succeeds() -> None:
    result = run_worker(
        card(),
        env=env(6),
        live_generate=failing_then_success("503 UNAVAILABLE high demand"),
        routing_decision=decision(),
    )

    assert result.backend == "live"
    assert result.fallback_used is False
    assert result.metadata["attempt_count"] == 2
    assert result.metadata["retry_count"] == 1
    assert result.metadata["first_error_type"] == "api_503_high_demand"
    assert result.metadata["final_error_type"] == "none"


def test_500_retry_succeeds() -> None:
    result = run_worker(
        card(),
        env=env(20),
        live_generate=failing_then_success("500 INTERNAL internal error"),
        routing_decision=decision(),
    )

    assert result.backend == "live"
    assert result.metadata["retry_count"] == 1
    assert result.metadata["first_error_type"] == "api_500_internal"
    assert result.fallback_used is False


def test_timeout_retry_fails_then_fallback() -> None:
    result = run_worker(
        card(),
        env=env(4),
        live_generate=always_fails("Gemma call timed out after 300 seconds."),
        routing_decision=decision(),
    )

    assert result.backend == "stub"
    assert result.metadata["attempt_count"] == 2
    assert result.metadata["retry_count"] == 1
    assert result.metadata["final_backend"] == "stub"
    assert result.metadata["fallback_used"] is True
    assert result.metadata["fallback_cause"] == "timeout"


def test_schema_error_is_not_retried() -> None:
    result = run_worker(
        card(),
        env=env(5),
        live_generate=always_fails("schema validation failure"),
        routing_decision=decision(),
    )

    assert result.backend == "stub"
    assert result.metadata["retry_count"] == 0
    assert result.metadata["error_type"] == "schema_error"


def test_auth_error_is_not_retried_and_redacts_secret() -> None:
    result = run_worker(
        card(),
        env=env(7),
        live_generate=always_fails("API key SECRET_VALUE unauthorized"),
        routing_decision=decision(),
    )

    serialized = json.dumps(result.to_dict())
    assert result.metadata["retry_count"] == 0
    assert result.metadata["error_type"] == "api_auth_error"
    assert "SECRET_VALUE" not in serialized
    assert "[REDACTED]" in serialized


def test_retry_only_failed_workers() -> None:
    call_counts = {"T001": 0, "T002": 0, "T003": 0}

    def success_for(task_id: str):
        def generate(_prompt: str) -> gemma_client.GemmaResponse:
            call_counts[task_id] += 1
            return success_response(task_id)

        return generate

    def transient_for(task_id: str):
        responses = [gemma_client.GemmaResponse(success=False, error="503 high demand"), success_response(task_id)]

        def generate(_prompt: str) -> gemma_client.GemmaResponse:
            call_counts[task_id] += 1
            return responses.pop(0)

        return generate

    results = [
        run_worker(card("T001"), env=env(1), live_generate=success_for("T001"), routing_decision=decision(0)),
        run_worker(card("T002"), env=env(2), live_generate=transient_for("T002"), routing_decision=decision(1)),
        run_worker(card("T003"), env=env(3), live_generate=success_for("T003"), routing_decision=decision(2)),
    ]

    assert call_counts == {"T001": 1, "T002": 2, "T003": 1}
    summary = _routing_summary(results)["retry_policy"]
    assert summary["retryable_error_count"] == 1
    assert summary["retried_worker_count"] == 1
    assert summary["retry_success_count"] == 1
    assert summary["fallback_after_retry_count"] == 0


def test_key_slot_preserved_on_retry() -> None:
    result = run_worker(
        card(),
        env=env(6),
        live_generate=failing_then_success("503 high demand"),
        routing_decision=decision(),
    )

    assert result.metadata["key_slot"] == 6
    assert [attempt["key_slot"] for attempt in result.metadata["attempts"]] == [6, 6]


def test_secret_safety_in_telemetry() -> None:
    result = run_worker(
        card(),
        env=env(8),
        live_generate=always_fails("500 INTERNAL SECRET_VALUE"),
        routing_decision=decision(),
    )

    serialized = json.dumps(result.to_dict())
    assert "SECRET_VALUE" not in serialized
    assert "key_slot" in serialized
