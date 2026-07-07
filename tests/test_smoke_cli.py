# TLH CLI가 임시 작업공간에서 MVP 흐름을 완주하는지 검증한다.

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_tlh(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["TLH_WORKER_BACKEND"] = "stub"
    return subprocess.run(
        [sys.executable, "-m", "tlh", *args],
        cwd=cwd,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )


def test_mvp_cli_flow_uses_temp_workspace(tmp_path: Path) -> None:
    run_tlh(tmp_path, "init")
    mission = tmp_path / "vault" / "00_Inbox" / "mission.md"
    mission.write_text(
        "# Mission\n\nCreate a Codex handoff prompt for a small markdown-to-JSONL CLI.\n",
        encoding="utf-8",
        newline="\n",
    )

    run_result = run_tlh(tmp_path, "run", "--mission", str(mission))
    run_id = run_result.stdout.strip().splitlines()[-1]
    answers = tmp_path / "vault" / "01_Runs" / f"{run_id}_answers.md"

    run_tlh(tmp_path, "answer", "--run", run_id, "--answers", str(answers))
    run_tlh(tmp_path, "dispatch", "--run", run_id)
    run_tlh(tmp_path, "merge", "--run", run_id)
    loop_result = run_tlh(tmp_path, "loop", "--run", run_id)
    run_tlh(tmp_path, "finalize", "--run", run_id)

    run_dir = tmp_path / "machine" / "runs" / run_id
    assert (run_dir / "state.json").exists()
    assert (run_dir / "task_cards.jsonl").exists()
    assert (run_dir / "worker_results.jsonl").exists()
    assert (run_dir / "merge_packets.jsonl").exists()
    assert (tmp_path / "vault" / "06_Handoff" / f"{run_id}-final-packet.md").exists()
    assert (tmp_path / "vault" / "06_Handoff" / f"{run_id}-codex-prompt.md").exists()
    assert (tmp_path / "vault" / "_GRAPH_INDEX.json").exists()
    assert loop_result.stdout.strip().endswith("stop_and_finalize")
