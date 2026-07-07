# Merge 결과를 보고 다음 loop action을 결정한다.

from __future__ import annotations

from pathlib import Path

from .packet_writer import frontmatter_note, write_json, write_text
from .schemas import LoopDecision, MergePacket, from_dict
from .vault import note_meta, vault_root


def decide(root: Path, run_id: str, packet_row: dict) -> LoopDecision:
    packet = from_dict(MergePacket, packet_row)
    if packet.attach_success and not packet.conflicts:
        decision = LoopDecision(
            run_id=run_id,
            loop_index=packet.loop_index,
            decision="stop_and_finalize",
            reason="The first slice attached cleanly and FinalPacket can be generated.",
            next_actions=["Run `python -m tlh finalize --run <run_id>`."],
        )
    elif packet.conflicts:
        decision = LoopDecision(
            run_id=run_id,
            loop_index=packet.loop_index,
            decision="targeted_verifier",
            reason="Conflicts remain after merge.",
            next_actions=["Create a verifier TaskCard for the conflicts."],
        )
    else:
        decision = LoopDecision(
            run_id=run_id,
            loop_index=packet.loop_index,
            decision="failed_to_merge",
            reason="No attachable confirmed points were produced.",
            next_actions=["Review WorkerResults and mission constraints."],
        )
    write_json(root / "machine" / "runs" / run_id / "loop_decision.json", decision.to_dict())
    note = frontmatter_note(
        note_meta("loop_decision", f"{run_id}-loop-0", run_id),
        {
            "Purpose": "Record the loop controller decision.",
            "Current State": decision.decision,
            "Inputs": f"MergePacket: [[{packet.merge_id}]]",
            "Outputs": decision.reason,
            "Links": f"- DERIVED_FROM: [[{packet.merge_id}]]",
            "Do Next": "\n".join(f"- {item}" for item in decision.next_actions),
            "Do Not": "Do not run an unbounded loop.",
        },
    )
    write_text(vault_root(root) / "09_Decisions" / f"{run_id}-loop-0.md", note)
    return decision
