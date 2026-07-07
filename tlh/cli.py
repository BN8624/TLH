# TLH MVP 명령줄 인터페이스를 연결한다.

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from . import dispatcher, graph_index, merge_harness, team_lead
from .loop_controller import decide
from .packet_writer import frontmatter_note, markdown_list, read_json, read_jsonl, read_text, write_json, write_text
from .schemas import FinalPacket
from .task_card import save_task_cards
from .vault import init_project, note_meta, run_dir, state_path, vault_root, write_current_state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tlh")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--mission", required=True)
    answer_parser = sub.add_parser("answer")
    answer_parser.add_argument("--run", required=True)
    answer_parser.add_argument("--answers", required=True)
    dispatch_parser = sub.add_parser("dispatch")
    dispatch_parser.add_argument("--run", required=True)
    merge_parser = sub.add_parser("merge")
    merge_parser.add_argument("--run", required=True)
    loop_parser = sub.add_parser("loop")
    loop_parser.add_argument("--run", required=True)
    finalize_parser = sub.add_parser("finalize")
    finalize_parser.add_argument("--run", required=True)
    args = parser.parse_args(argv)
    root = Path.cwd()
    if args.command == "init":
        created = init_project(root)
        print(f"initialized TLH structure; created {len(created)} paths")
        return 0
    init_project(root)
    if args.command == "run":
        return _run(root, Path(args.mission))
    if args.command == "answer":
        return _answer(root, args.run, Path(args.answers))
    if args.command == "dispatch":
        return _dispatch(root, args.run)
    if args.command == "merge":
        return _merge(root, args.run)
    if args.command == "loop":
        return _loop(root, args.run)
    if args.command == "finalize":
        return _finalize(root, args.run)
    return 1


def _new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("run-%Y%m%d-%H%M%S")


def _load_state(root: Path, run_id: str) -> dict:
    path = state_path(run_id, root)
    if not path.exists():
        raise SystemExit(f"Unknown run: {run_id}")
    return read_json(path)


def _save_state(root: Path, state: dict) -> None:
    state["updated"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    write_json(state_path(state["run_id"], root), state)


def _run(root: Path, mission_path: Path) -> int:
    if not mission_path.exists():
        raise SystemExit(f"Mission file not found: {mission_path}")
    run_id = _new_run_id()
    mission = read_text(mission_path)
    questions = team_lead.clarify(mission)
    run_dir(run_id, root).mkdir(parents=True, exist_ok=True)
    state = {
        "run_id": run_id,
        "status": "awaiting_answers",
        "loop_index": 0,
        "mission_path": str(mission_path),
        "mission": mission,
        "clarification_questions": questions,
        "created": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "updated": "",
    }
    _save_state(root, state)
    _write_run_note(root, run_id, state)
    answers_path = vault_root(root) / "01_Runs" / f"{run_id}_answers.md"
    write_text(
        answers_path,
        "# Answers\n\n- Final output should be an executable Codex handoff prompt.\n- Preserve MVP scope and avoid global automation.\n- Verification should include CLI command examples.\n",
    )
    write_current_state(run_id, "awaiting_answers", "Clarification questions were generated.", root)
    print(run_id)
    return 0


def _answer(root: Path, run_id: str, answers_path: Path) -> int:
    state = _load_state(root, run_id)
    if not answers_path.exists():
        write_text(answers_path, "# Answers\n\nUse MVP defaults and keep scope minimal.\n")
    answers = read_text(answers_path)
    cards = team_lead.decompose(run_id, state["mission"], answers)
    save_task_cards(root, run_id, cards)
    state.update(
        {
            "status": "task_cards_created",
            "answers_path": str(answers_path),
            "concrete_mission": team_lead.concrete_mission(state["mission"], answers),
            "task_ids": [card.task_id for card in cards],
        }
    )
    _save_state(root, state)
    write_current_state(run_id, "task_cards_created", "TaskCards are ready for dispatch.", root)
    print(f"created {len(cards)} task cards")
    return 0


def _dispatch(root: Path, run_id: str) -> int:
    state = _load_state(root, run_id)
    rows = read_jsonl(run_dir(run_id, root) / "task_cards.jsonl")
    if not rows:
        raise SystemExit("No task cards found. Run answer first.")
    results = dispatcher.dispatch(root, run_id, rows)
    state.update({"status": "worker_results_created", "worker_result_ids": [f"{r.task_id}-result" for r in results]})
    _save_state(root, state)
    write_current_state(run_id, "worker_results_created", "WorkerResults are ready for merge.", root)
    print(f"created {len(results)} worker results")
    return 0


def _merge(root: Path, run_id: str) -> int:
    state = _load_state(root, run_id)
    rows = read_jsonl(run_dir(run_id, root) / "worker_results.jsonl")
    if not rows:
        raise SystemExit("No worker results found. Run dispatch first.")
    packet = merge_harness.merge(root, run_id, rows)
    state.update(
        {
            "status": "merged",
            "merge_ids": [packet.merge_id],
            "artifact_id": f"{run_id}-artifact-v1",
            "folded_summary_id": f"{run_id}-folded-summary-v1",
            "minimality_check_id": f"{run_id}-MIN001",
        }
    )
    _save_state(root, state)
    write_current_state(run_id, "merged", "MergePacket and AccumulatedArtifact were created.", root)
    print(packet.merge_id)
    return 0


def _loop(root: Path, run_id: str) -> int:
    state = _load_state(root, run_id)
    rows = read_jsonl(run_dir(run_id, root) / "merge_packets.jsonl")
    if not rows:
        raise SystemExit("No merge packet found. Run merge first.")
    decision = decide(root, run_id, rows[-1])
    state.update({"status": "ready_to_finalize", "loop_decision": decision.to_dict()})
    _save_state(root, state)
    write_current_state(run_id, "ready_to_finalize", f"Loop decision: {decision.decision}.", root)
    print(decision.decision)
    return 0


def _finalize(root: Path, run_id: str) -> int:
    state = _load_state(root, run_id)
    rows = read_jsonl(run_dir(run_id, root) / "merge_packets.jsonl")
    if not rows:
        raise SystemExit("No merge packet found. Run merge first.")
    packet = rows[-1]
    final = FinalPacket(
        run_id=run_id,
        goal=state.get("concrete_mission", state["mission"]),
        current_state="Ready for Codex handoff after one slice-and-attach loop.",
        confirmed_assumptions=["Worker outputs were stub-generated for MVP skeleton verification."],
        scope=packet.get("confirmed_points", []),
        out_of_scope=["GUI", "Obsidian plugin", "global workflow automation", "automatic Codex or Claude execution"],
        execution_steps=[
            "Read the mission and constraints.",
            "Implement the smallest CLI slice that satisfies the requested output.",
            "Write JSONL output and keep parsing behavior explicit.",
            "Run the listed verification commands.",
        ],
        risks=packet.get("conflicts", []),
        verification=["Run the target CLI on a small markdown sample.", "Confirm JSONL output has one record per task note."],
        handoff_prompt=_codex_prompt_text(state, packet),
        user_decision_points=[],
    )
    final_id = f"{run_id}-final-packet"
    codex_id = f"{run_id}-codex-prompt"
    _write_final_note(root, run_id, final_id, final)
    _write_codex_prompt(root, run_id, codex_id, final.handoff_prompt)
    graph_index.generate(root)
    state.update({"status": "finalized", "final_packet_id": final_id, "codex_prompt_id": codex_id})
    _save_state(root, state)
    write_current_state(run_id, "finalized", "FinalPacket and CodexPrompt were created.", root)
    print(final_id)
    return 0


def _write_run_note(root: Path, run_id: str, state: dict) -> None:
    note = frontmatter_note(
        note_meta("run", run_id, run_id, status="active"),
        {
            "Purpose": "Track one TLH MVP run.",
            "Current State": "Clarification questions generated.",
            "Inputs": state["mission"],
            "Outputs": markdown_list(state["clarification_questions"]),
            "Links": "None.",
            "Do Next": f"Answer questions in [[{run_id}_answers]].",
            "Do Not": "Do not skip TaskCards or workers.",
        },
    )
    write_text(vault_root(root) / "01_Runs" / f"{run_id}.md", note)


def _write_final_note(root: Path, run_id: str, final_id: str, final: FinalPacket) -> None:
    note = frontmatter_note(
        note_meta("final_packet", final_id, run_id),
        {
            "Purpose": "Executable final packet for handoff.",
            "Current State": final.current_state,
            "Inputs": f"AccumulatedArtifact: [[{run_id}-artifact-v1]]",
            "Outputs": final.handoff_prompt,
            "Links": f"- DERIVED_FROM: [[{run_id}-artifact-v1]]\n- HANDOFF_TO: [[{run_id}-codex-prompt]]",
            "Do Next": "Use the CodexPrompt when starting implementation work.",
            "Do Not": "Do not include deferred integrations in the MVP slice.",
        },
    )
    write_text(vault_root(root) / "06_Handoff" / f"{final_id}.md", note)


def _write_codex_prompt(root: Path, run_id: str, codex_id: str, prompt: str) -> None:
    note = frontmatter_note(
        note_meta("codex_prompt", codex_id, run_id),
        {
            "Purpose": "Prompt for Codex execution.",
            "Current State": "Ready to hand off.",
            "Inputs": f"FinalPacket: [[{run_id}-final-packet]]",
            "Outputs": prompt,
            "Links": f"- DERIVED_FROM: [[{run_id}-final-packet]]",
            "Do Next": "Run this prompt in a coding session.",
            "Do Not": "Do not run commands automatically from this note.",
        },
    )
    write_text(vault_root(root) / "06_Handoff" / f"{codex_id}.md", note)


def _codex_prompt_text(state: dict, packet: dict) -> str:
    return "\n".join(
        [
            "Implement the requested CLI with the smallest working slice.",
            "",
            "Mission.",
            state.get("mission", "").strip(),
            "",
            "Confirmed points.",
            markdown_list(packet.get("confirmed_points", [])),
            "",
            "Constraints.",
            "- Do not add global workflow automation.",
            "- Do not add GUI or external service dependencies.",
            "- Verify with concrete commands before reporting completion.",
        ]
    )
