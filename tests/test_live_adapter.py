# live Gemma adapter 선택, fallback, normalize 동작을 네트워크 없이 검증한다.

from __future__ import annotations

import json

import pytest

from tlh import gemma_client
from tlh.schemas import TaskCard
from tlh.worker_pool import WorkerBackendError, run_worker


def task_card() -> TaskCard:
    return TaskCard(
        task_id="T-live",
        run_id="run-live",
        loop_index=0,
        title="Live adapter test",
        goal="Return a structured WorkerResult.",
        worker_role="builder",
        expected_output="structured WorkerResult JSON",
        attach_point="FinalPacket.Scope",
        merge_key="s2_scope",
    )


def test_backend_hint_overrides_global_stub_for_one_card() -> None:
    live_card = task_card()
    live_card.backend_hint = "live"
    stub_card = task_card()
    stub_card.task_id = "T-stub"

    response_text = json.dumps(
        {
            "summary": "Live summary.",
            "findings": ["scope: Only this card is live."],
            "risks": [],
            "assumptions": [],
            "open_questions": [],
            "attach_notes": ["target: FinalPacket.Scope | content: Only this card is live."],
        }
    )

    def fake_generate(_prompt: str) -> gemma_client.GemmaResponse:
        return gemma_client.GemmaResponse(success=True, text=response_text, model="mock-gemma")

    env = {"TLH_WORKER_BACKEND": "stub", "TLH_GEMMA_API_KEY": "SECRET_VALUE"}
    live_result = run_worker(live_card, env=env, live_generate=fake_generate)
    stub_result = run_worker(stub_card, env=env, live_generate=fake_generate)

    assert live_result.backend == "live"
    assert live_result.live_generated is True
    assert stub_result.backend == "stub"
    assert stub_result.stub_generated is True


def test_stub_backend_forces_stub_without_key() -> None:
    result = run_worker(task_card(), env={"TLH_WORKER_BACKEND": "stub"})

    assert result.backend == "stub"
    assert result.stub_generated is True
    assert result.live_generated is False
    assert result.fallback_used is False


def test_auto_without_key_uses_stub_fallback() -> None:
    result = run_worker(task_card(), env={"TLH_WORKER_BACKEND": "auto"})

    assert result.backend == "stub"
    assert result.stub_generated is True
    assert result.fallback_used is True
    assert "not configured" in result.error


def test_live_without_key_fails_without_configured_fallback() -> None:
    with pytest.raises(WorkerBackendError, match="TLH_GEMMA_API_KEY"):
        run_worker(task_card(), env={"TLH_WORKER_BACKEND": "live"})


def test_live_without_key_can_fallback_when_enabled() -> None:
    result = run_worker(
        task_card(),
        env={"TLH_WORKER_BACKEND": "live", "TLH_GEMMA_FALLBACK_TO_STUB": "true"},
    )

    assert result.backend == "stub"
    assert result.fallback_used is True
    assert result.stub_generated is True


def test_mock_live_response_normalizes_to_worker_result() -> None:
    response_text = json.dumps(
        {
            "summary": "Live summary.",
            "findings": ["scope: Use live adapter."],
            "risks": ["risk: Live response may vary."],
            "assumptions": ["Mocked live response."],
            "open_questions": [],
            "attach_notes": ["target: FinalPacket.Scope | content: Use live adapter."],
        }
    )

    def fake_generate(_prompt: str) -> gemma_client.GemmaResponse:
        return gemma_client.GemmaResponse(success=True, text=response_text, model="mock-gemma")

    result = run_worker(
        task_card(),
        env={"TLH_WORKER_BACKEND": "live", "TLH_GEMMA_API_KEY": "SECRET_VALUE"},
        live_generate=fake_generate,
    )

    assert result.backend == "live"
    assert result.live_generated is True
    assert result.stub_generated is False
    assert result.model == "mock-gemma"
    assert result.findings == ["scope: Use live adapter."]
    assert "SECRET_VALUE" not in json.dumps(result.to_dict())


def test_default_live_generator_uses_worker_env(monkeypatch) -> None:
    response_text = json.dumps(
        {
            "summary": "Live summary.",
            "findings": ["scope: Use worker env key."],
            "risks": [],
            "assumptions": [],
            "open_questions": [],
            "attach_notes": ["target: FinalPacket.Scope | content: Use worker env key."],
        }
    )

    def fake_generate(_prompt: str, config=None, client_factory=None) -> gemma_client.GemmaResponse:
        assert config is not None
        assert config.api_key == "SECRET_VALUE"
        return gemma_client.GemmaResponse(success=True, text=response_text, model="mock-gemma")

    monkeypatch.setattr(gemma_client, "generate", fake_generate)

    result = run_worker(task_card(), env={"TLH_WORKER_BACKEND": "live", "TLH_GEMMA_API_KEY": "SECRET_VALUE"})

    assert result.backend == "live"
    assert result.findings == ["scope: Use worker env key."]
    assert "SECRET_VALUE" not in json.dumps(result.to_dict())


def test_incomplete_live_response_is_normalized() -> None:
    def fake_generate(_prompt: str) -> gemma_client.GemmaResponse:
        return gemma_client.GemmaResponse(success=True, text="scope: Normalize this plain text.", model="mock-gemma")

    result = run_worker(
        task_card(),
        env={"TLH_WORKER_BACKEND": "live", "TLH_GEMMA_API_KEY": "SECRET_VALUE"},
        live_generate=fake_generate,
    )

    assert result.backend == "live"
    assert result.summary
    assert result.findings
    assert result.attach_notes
    assert any("normalized_missing_fields" in item for item in result.assumptions)


def test_fenced_live_json_with_sectioned_findings_maps_to_merge_prefixes() -> None:
    response_text = """```json
{
  "summary": "Live structured summary.",
  "findings": {
    "scope": "Use one live worker.",
    "non_goals": ["Do not run multiple live workers."],
    "files_to_inspect": ["tlh/worker_pool.py"],
    "verification_commands": ["python -m pytest"]
  },
  "risks": [],
  "assumptions": [],
  "open_questions": [],
  "attach_notes": ["target: FinalPacket.Scope | content: Use one live worker."]
}
```"""

    def fake_generate(_prompt: str) -> gemma_client.GemmaResponse:
        return gemma_client.GemmaResponse(success=True, text=response_text, model="mock-gemma")

    result = run_worker(
        task_card(),
        env={"TLH_WORKER_BACKEND": "live", "TLH_GEMMA_API_KEY": "SECRET_VALUE"},
        live_generate=fake_generate,
    )

    assert result.summary == "Live structured summary."
    assert "scope: Use one live worker." in result.findings
    assert "non_goal: Do not run multiple live workers." in result.findings
    assert "file: tlh/worker_pool.py" in result.findings
    assert "verification: python -m pytest" in result.findings


def test_live_error_redacts_api_key_when_falling_back() -> None:
    def fake_generate(_prompt: str) -> gemma_client.GemmaResponse:
        return gemma_client.GemmaResponse(success=False, error="failed with SECRET_VALUE", model="mock-gemma")

    result = run_worker(
        task_card(),
        env={
            "TLH_WORKER_BACKEND": "live",
            "TLH_GEMMA_API_KEY": "SECRET_VALUE",
            "TLH_GEMMA_FALLBACK_TO_STUB": "true",
        },
        live_generate=fake_generate,
    )

    assert result.backend == "stub"
    assert result.fallback_used is True
    assert "[REDACTED]" in result.error
    assert "SECRET_VALUE" not in json.dumps(result.to_dict())
