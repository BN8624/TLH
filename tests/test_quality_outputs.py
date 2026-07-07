# TLH dry run 산출물이 실행 가능한 handoff 품질 기준을 만족하는지 검증한다.

from __future__ import annotations

import json
from pathlib import Path

from test_smoke_cli import run_tlh


MISSION = """# Mission

Create a Codex handoff prompt for implementing the S-2 live Gemma adapter in TLH.
The handoff must define scope, non-goals, required files, environment variable handling, fallback behavior, verification, and report format.
"""


ANSWERS = """# Answers

## Target

S-2 live Gemma adapter handoff prompt only.

## Constraints

Do not implement live Gemma in this run.
Do not store secrets.
Keep stub fallback.
Use environment variables for configuration.
Keep worker interface stable.
Prefer minimal code changes in S-2.
"""


def test_handoff_quality_outputs_are_sectioned(tmp_path: Path) -> None:
    run_tlh(tmp_path, "init")
    mission = tmp_path / "vault" / "00_Inbox" / "s1q_mission.md"
    mission.write_text(MISSION, encoding="utf-8", newline="\n")

    run_id = run_tlh(tmp_path, "run", "--mission", str(mission)).stdout.strip().splitlines()[-1]
    answers = tmp_path / "vault" / "01_Runs" / f"{run_id}_answers.md"
    answers.write_text(ANSWERS, encoding="utf-8", newline="\n")

    run_tlh(tmp_path, "answer", "--run", run_id, "--answers", str(answers))
    run_tlh(tmp_path, "dispatch", "--run", run_id)
    run_tlh(tmp_path, "merge", "--run", run_id)
    run_tlh(tmp_path, "loop", "--run", run_id)
    run_tlh(tmp_path, "finalize", "--run", run_id)

    run_dir = tmp_path / "machine" / "runs" / run_id
    task_cards = _read_jsonl(run_dir / "task_cards.jsonl")
    worker_results = _read_jsonl(run_dir / "worker_results.jsonl")
    merge_packet = _read_jsonl(run_dir / "merge_packets.jsonl")[0]
    final_packet = (tmp_path / "vault" / "06_Handoff" / f"{run_id}-final-packet.md").read_text(encoding="utf-8")
    codex_prompt = (tmp_path / "vault" / "06_Handoff" / f"{run_id}-codex-prompt.md").read_text(encoding="utf-8")

    assert all(card["expected_output"] for card in task_cards)
    assert all(card["attach_point"] for card in task_cards)
    assert all(card["merge_key"] for card in task_cards)
    assert all(result["attach_notes"] for result in worker_results)
    assert all(result["stub_generated"] is True for result in worker_results)
    assert merge_packet["confirmed_points"]
    assert merge_packet["minimality"]["sections"]["Scope"]
    assert merge_packet["minimality"]["sections"]["Verification"]
    assert "## Scope" in final_packet
    assert "## Out of Scope" in final_packet
    assert "## Verification" in final_packet
    assert "## Scope" in codex_prompt
    assert "## Non-goals" in codex_prompt
    assert "## Verification Commands" in codex_prompt
    assert "## Report Format" in codex_prompt


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
