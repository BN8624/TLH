# TLH live routing policy의 안전 기본값과 결정 metadata를 검증한다.

from __future__ import annotations

import json
from pathlib import Path

from test_smoke_cli import run_tlh

from tlh.live_routing import build_live_routing_policy, decide_worker_backend
from tlh.schemas import TaskCard
from tlh.worker_pool import run_worker


def card(task_id: str = "T001") -> TaskCard:
    return TaskCard(
        task_id=task_id,
        run_id="run-policy",
        loop_index=0,
        title=f"Policy task {task_id}",
        goal="Validate routing policy.",
        worker_role="builder",
        expected_output="WorkerResult",
        attach_point="FinalPacket.Scope",
        merge_key="s4_limit_policy",
    )


def decisions(env: dict[str, str], count: int = 3) -> list:
    policy = build_live_routing_policy(env)
    used = 0
    output = []
    for index in range(count):
        decision = decide_worker_backend(
            worker_index=index,
            requested=env.get("TLH_WORKER_BACKEND", "auto"),
            live_workers_used=used,
            policy=policy,
            env=env,
        )
        if decision.selected_backend == "live":
            used += 1
        output.append(decision)
    return output


def test_default_policy_is_safe() -> None:
    policy = build_live_routing_policy({})

    assert policy.mode != "full_live"
    assert policy.mode == "one_live"
    assert policy.max_live_workers == 1
    assert policy.cost_guard_enabled is True


def test_limited_live_limit_two_routes_two_live_and_one_policy_stub() -> None:
    output = decisions({"TLH_WORKER_BACKEND": "auto", "TLH_GEMMA_API_KEY": "SECRET_VALUE", "TLH_LIVE_WORKER_LIMIT": "2"})

    assert [decision.selected_backend for decision in output] == ["live", "live", "stub"]
    assert [decision.fallback_used for decision in output] == [False, False, False]
    assert output[2].routing_reason == "live worker limit reached"
    assert output[2].policy_mode == "limited_live"


def test_stub_only_policy_routes_all_stub_without_fallback() -> None:
    output = decisions({"TLH_WORKER_BACKEND": "live", "TLH_LIVE_ROUTING_MODE": "stub_only", "TLH_GEMMA_API_KEY": "SECRET_VALUE"})

    assert [decision.selected_backend for decision in output] == ["stub", "stub", "stub"]
    assert all(decision.fallback_used is False for decision in output)
    assert all("stub_only" in decision.routing_reason for decision in output)


def test_one_live_policy_routes_only_first_live() -> None:
    output = decisions({"TLH_WORKER_BACKEND": "auto", "TLH_LIVE_ROUTING_MODE": "one_live", "TLH_GEMMA_API_KEY": "SECRET_VALUE"})

    assert [decision.selected_backend for decision in output] == ["live", "stub", "stub"]
    assert output[0].live_worker_index == 1
    assert output[1].routing_reason == "live worker limit reached"


def test_full_live_requires_explicit_opt_in() -> None:
    policy = build_live_routing_policy({"TLH_LIVE_ROUTING_MODE": "full_live"})

    assert policy.mode == "one_live"
    assert policy.max_live_workers == 1
    assert "explicit opt-in" in policy.reason


def test_force_backend_has_priority() -> None:
    output = decisions(
        {
            "TLH_WORKER_BACKEND": "auto",
            "TLH_FORCE_WORKER_BACKEND": "stub",
            "TLH_LIVE_WORKER_LIMIT": "2",
            "TLH_GEMMA_API_KEY": "SECRET_VALUE",
        }
    )

    assert [decision.selected_backend for decision in output] == ["stub", "stub", "stub"]
    assert all(decision.routing_source == "env:TLH_FORCE_WORKER_BACKEND" for decision in output)
    assert all("force backend" in decision.routing_reason for decision in output)


def test_worker_result_metadata_records_policy_decision() -> None:
    env = {"TLH_WORKER_BACKEND": "live", "TLH_LIVE_WORKER_LIMIT": "1", "TLH_GEMMA_API_KEY": "SECRET_VALUE"}
    policy = build_live_routing_policy(env)
    decision = decide_worker_backend(worker_index=0, requested="live", live_workers_used=0, policy=policy, env=env)

    def fake_generate(_prompt: str):
        from tlh import gemma_client

        return gemma_client.GemmaResponse(
            success=True,
            text=json.dumps(
                {
                    "summary": "Live result.",
                    "findings": ["scope: Use policy metadata."],
                    "risks": [],
                    "assumptions": [],
                    "open_questions": [],
                    "attach_notes": ["target: FinalPacket.Scope | content: Use policy metadata."],
                }
            ),
            model="mock-gemma",
        )

    result = run_worker(card(), env=env, live_generate=fake_generate, routing_decision=decision)

    assert result.metadata["policy_mode"] == "limited_live"
    assert result.metadata["max_live_workers"] == 1
    assert result.metadata["requested_backend"] == "live"
    assert result.metadata["selected_backend"] == "live"
    assert result.metadata["routing_reason"] == "within live worker limit"
    assert result.metadata["fallback_used"] is False


def test_final_and_codex_prompt_include_policy_summary(tmp_path: Path) -> None:
    env = {"TLH_WORKER_BACKEND": "stub", "TLH_LIVE_WORKER_LIMIT": "2"}
    result = run_tlh(tmp_path, "init")
    assert result.returncode == 0
    mission = tmp_path / "vault" / "00_Inbox" / "policy.md"
    mission.write_text("# Mission\n\nCreate a handoff for live worker limit policy.\n", encoding="utf-8", newline="\n")

    run_id = run_tlh(tmp_path, "run", "--mission", str(mission)).stdout.strip().splitlines()[-1]
    answers = tmp_path / "vault" / "01_Runs" / f"{run_id}_answers.md"
    answers.write_text("# Answers\n\nUse at most two live workers.\n", encoding="utf-8", newline="\n")

    for command in [
        ("answer", "--run", run_id, "--answers", str(answers)),
        ("dispatch", "--run", run_id),
        ("merge", "--run", run_id),
        ("loop", "--run", run_id),
        ("finalize", "--run", run_id),
    ]:
        run_tlh_with_env(tmp_path, env, *command)

    final_packet = (tmp_path / "vault" / "06_Handoff" / f"{run_id}-final-packet.md").read_text(encoding="utf-8")
    codex_prompt = (tmp_path / "vault" / "06_Handoff" / f"{run_id}-codex-prompt.md").read_text(encoding="utf-8")

    assert "## Backend Mix" in final_packet
    assert "## Routing Policy" in final_packet
    assert "policy mode: limited_live" in final_packet
    assert "max live workers: 2" in codex_prompt


def run_tlh_with_env(cwd: Path, extra_env: dict[str, str], *args: str):
    import os
    import subprocess
    import sys

    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(extra_env)
    return subprocess.run([sys.executable, "-m", "tlh", *args], cwd=cwd, env=env, check=True, text=True, capture_output=True)
