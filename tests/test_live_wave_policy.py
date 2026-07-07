# live worker wave 실행 계획과 metadata를 검증한다.

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tlh import dispatcher, gemma_client
from tlh.live_routing import build_live_wave_plan, simulate_routing_decisions
from tlh.schemas import TaskCard, WorkerResult
from tlh.vault import init_project
from tlh.worker_pool import run_worker


REPO_ROOT = Path(__file__).resolve().parents[1]


def card(task_id: str = "T001") -> TaskCard:
    return TaskCard(
        task_id=task_id,
        run_id="run-wave",
        loop_index=0,
        title=f"Wave task {task_id}",
        goal="Validate live wave policy.",
        worker_role="builder",
        expected_output="WorkerResult",
        attach_point="FinalPacket.Scope",
        merge_key="s17_wave_policy",
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


def wave_plan(worker_count: int, wave_size: int):
    simulation = simulate_routing_decisions(
        worker_count,
        {
            "TLH_WORKER_BACKEND": "live",
            "TLH_LIVE_WORKER_LIMIT": str(worker_count),
            "TLH_LIVE_WAVE_SIZE": str(wave_size),
        },
        requested="live",
    )
    key_slots = {index: index + 1 for index in range(worker_count)}
    return build_live_wave_plan(simulation.decisions, wave_size, key_slots)


def test_wave_plan_22_with_wave_size_11() -> None:
    plan = wave_plan(22, 11)

    assert plan.enabled is True
    assert plan.wave_count == 2
    assert plan.max_concurrent_live_workers == 11
    assert plan.waves[0].worker_indices == list(range(0, 11))
    assert plan.waves[1].worker_indices == list(range(11, 22))
    assert plan.waves[0].key_slots == list(range(1, 12))
    assert plan.waves[1].key_slots == list(range(12, 23))


def test_wave_plan_22_with_wave_size_8() -> None:
    plan = wave_plan(22, 8)

    assert plan.wave_count == 3
    assert [len(wave.worker_indices) for wave in plan.waves] == [8, 8, 6]
    assert plan.max_concurrent_live_workers == 8


def test_wave_execution_does_not_rerun_successful_workers(monkeypatch, tmp_path: Path) -> None:
    init_project(tmp_path)
    rows = [card(f"T{index:03d}").to_dict() for index in range(4)]
    (tmp_path / ".env").write_text(
        "\n".join(f"GOOGLE_API_KEY_{slot}=SECRET_{slot}" for slot in range(1, 5)),
        encoding="utf-8",
    )
    monkeypatch.setenv("TLH_WORKER_BACKEND", "live")
    monkeypatch.setenv("TLH_LIVE_WORKER_LIMIT", "4")
    monkeypatch.setenv("TLH_LIVE_WAVE_SIZE", "2")
    call_counts = {f"T{index:03d}": 0 for index in range(4)}

    def fake_run_worker(task_card: TaskCard, env=None, routing_decision=None) -> WorkerResult:
        assert env is not None
        call_counts[task_card.task_id] += 1
        fallback = task_card.task_id == "T002"
        return WorkerResult(
            task_id=task_card.task_id,
            worker_id="live-builder",
            summary="wave result",
            findings=["scope: wave result"],
            backend="stub" if fallback else "live",
            fallback_used=fallback,
            metadata={
                "backend": "stub" if fallback else "live",
                "requested_backend": "live",
                "selected_backend": "live",
                "wave_enabled": env.get("TLH_LIVE_WAVE_ENABLED") == "true",
                "wave_index": int(env.get("TLH_LIVE_WAVE_INDEX", "0")),
                "wave_size": int(env.get("TLH_LIVE_WAVE_SIZE", "0")),
                "wave_count": int(env.get("TLH_LIVE_WAVE_COUNT", "0")),
                "key_slot": int(env.get("TLH_GEMMA_KEY_SLOT", "0")),
            },
        )

    monkeypatch.setattr(dispatcher, "run_worker", fake_run_worker)

    results = dispatcher.dispatch(tmp_path, "run-wave", rows)

    assert call_counts == {f"T{index:03d}": 1 for index in range(4)}
    assert [result.metadata["wave_index"] for result in results] == [1, 1, 2, 2]
    assert results[2].fallback_used is True


def test_retry_preserves_key_slot_inside_wave() -> None:
    responses = [gemma_client.GemmaResponse(success=False, error="503 high demand"), _success_response()]

    def generate(_prompt: str) -> gemma_client.GemmaResponse:
        return responses.pop(0)

    result = run_worker(
        card("T006"),
        env={
            "TLH_WORKER_BACKEND": "live",
            "TLH_GEMMA_API_KEY": "SECRET_VALUE",
            "TLH_GEMMA_KEY_SLOT": "6",
            "TLH_GEMMA_MAX_RETRY_ATTEMPTS": "1",
            "TLH_GEMMA_RETRY_BACKOFF_SECONDS": "0",
            "TLH_GEMMA_RETRY_JITTER_ENABLED": "false",
            "TLH_LIVE_WAVE_ENABLED": "true",
            "TLH_LIVE_WAVE_INDEX": "1",
            "TLH_LIVE_WAVE_SIZE": "11",
            "TLH_LIVE_WAVE_COUNT": "2",
            "TLH_LIVE_WAVE_TARGET_LIVE_WORKERS": "22",
            "TLH_LIVE_WAVE_MAX_CONCURRENT": "11",
        },
        live_generate=generate,
    )

    assert [attempt["key_slot"] for attempt in result.metadata["attempts"]] == [6, 6]
    assert result.metadata["key_slot"] == 6
    assert result.metadata["wave_index"] == 1
    assert "SECRET_VALUE" not in json.dumps(result.to_dict())


def test_fallback_only_after_retry_failure_inside_wave() -> None:
    result = run_worker(
        card("T007"),
        env={
            "TLH_WORKER_BACKEND": "live",
            "TLH_GEMMA_API_KEY": "SECRET_VALUE",
            "TLH_GEMMA_KEY_SLOT": "7",
            "TLH_GEMMA_MAX_RETRY_ATTEMPTS": "1",
            "TLH_GEMMA_RETRY_BACKOFF_SECONDS": "0",
            "TLH_GEMMA_RETRY_JITTER_ENABLED": "false",
            "TLH_GEMMA_FALLBACK_TO_STUB": "true",
            "TLH_LIVE_WAVE_ENABLED": "true",
            "TLH_LIVE_WAVE_INDEX": "1",
            "TLH_LIVE_WAVE_SIZE": "11",
            "TLH_LIVE_WAVE_COUNT": "2",
            "TLH_LIVE_WAVE_TARGET_LIVE_WORKERS": "22",
            "TLH_LIVE_WAVE_MAX_CONCURRENT": "11",
        },
        live_generate=lambda _prompt: gemma_client.GemmaResponse(success=False, error="503 high demand"),
    )

    assert result.backend == "stub"
    assert result.metadata["retry_count"] == 1
    assert result.metadata["fallback_after_retry"] is True
    assert result.metadata["fallback_cause"] == "api_503_high_demand"


def test_route_dry_run_wave_text(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(f"GOOGLE_API_KEY_{slot}=SECRET_{slot}" for slot in range(1, 23)),
        encoding="utf-8",
    )
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
    assert "wave_enabled: YES" in result.stdout
    assert "wave_size: 11" in result.stdout
    assert "wave_count: 2" in result.stdout
    assert "max_concurrent_live_workers: 11" in result.stdout
    assert "actual API call: NO" in result.stdout
    assert "SECRET_" not in result.stdout


def test_route_dry_run_wave_json(tmp_path: Path) -> None:
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
        "--json",
    )

    payload = json.loads(result.stdout)
    assert payload["wave_policy"]["enabled"] is True
    assert payload["wave_policy"]["wave_size"] == 11
    assert payload["wave_policy"]["wave_count"] == 2
    assert len(payload["waves"]) == 2


def test_no_wave_by_default(tmp_path: Path) -> None:
    result = run_route(tmp_path, "--workers", "22", "--mode", "limited_live", "--live-limit", "22", "--json")

    payload = json.loads(result.stdout)
    assert payload["backend_mix"]["live"] == 22
    assert payload["wave_policy"]["enabled"] is False
    assert payload["waves"] == []


def test_invalid_wave_size_fails_without_artifacts(tmp_path: Path) -> None:
    result = run_route(tmp_path, "--workers", "22", "--live-wave-size", "0")

    assert result.returncode != 0
    assert "must be greater than 0" in result.stderr
    assert not (tmp_path / "machine").exists()
    assert not (tmp_path / "vault").exists()


def test_wave_secret_safety(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(f"GOOGLE_API_KEY_{slot}=SECRET_{slot}" for slot in range(1, 23)),
        encoding="utf-8",
    )

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
        "--json",
    )

    assert result.returncode == 0
    assert "SECRET_" not in result.stdout
    assert "key_slots" in result.stdout


def _success_response() -> gemma_client.GemmaResponse:
    return gemma_client.GemmaResponse(
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
    )
