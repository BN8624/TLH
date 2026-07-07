# WorkerResult를 MergePacket과 누적 산출물로 통합한다.

from __future__ import annotations

from pathlib import Path

from .packet_writer import frontmatter_note, markdown_list, write_jsonl, write_text
from .ponytail_checker import check_merge
from .schemas import MergePacket, WorkerResult, from_dict
from .vault import note_meta, vault_root


def merge(root: Path, run_id: str, rows: list[dict]) -> MergePacket:
    results = [from_dict(WorkerResult, row) for row in rows]
    seen: set[str] = set()
    confirmed: list[str] = []
    risks: list[str] = []
    dropped: list[str] = []
    for result in results:
        for item in result.findings:
            if item in seen:
                dropped.append(f"Duplicate finding dropped: {item}")
            else:
                seen.add(item)
                confirmed.append(item)
        risks.extend(result.risks)
    minimality = check_merge(run_id, kept=confirmed, dropped=dropped)
    packet = MergePacket(
        merge_id=f"{run_id}-M001",
        run_id=run_id,
        loop_index=0,
        merged_tasks=[result.task_id for result in results],
        confirmed_points=confirmed,
        alternatives=[],
        conflicts=[],
        dropped_items=dropped,
        attach_success=bool(confirmed),
        updated_artifact_version=1,
        continuity_check="WorkerResults were structured and attachable to the accumulated artifact.",
        minimality=minimality.to_dict(),
    )
    run_dir = root / "machine" / "runs" / run_id
    write_jsonl(run_dir / "merge_packets.jsonl", [packet.to_dict()])
    _write_merge_note(root, packet)
    _write_minimality_note(root, run_id, minimality)
    _write_artifact_note(root, run_id, packet, risks)
    _write_folded_summary(root, run_id, packet)
    return packet


def _write_merge_note(root: Path, packet: MergePacket) -> None:
    note = frontmatter_note(
        note_meta("merge_packet", packet.merge_id, packet.run_id),
        {
            "Purpose": "Merge structured WorkerResults into attachable points.",
            "Current State": f"Attach success: {packet.attach_success}",
            "Inputs": markdown_list(packet.merged_tasks),
            "Outputs": markdown_list(packet.confirmed_points),
            "Links": f"- UPDATES: [[{packet.run_id}-artifact-v1]]\n- VALIDATES: [[{packet.run_id}-MIN001]]",
            "Do Next": "Run loop decision.",
            "Do Not": "Do not concatenate raw worker text.",
        },
    )
    write_text(vault_root(root) / "04_MergePackets" / f"{packet.merge_id}.md", note)


def _write_minimality_note(root: Path, run_id: str, minimality) -> None:
    note = frontmatter_note(
        note_meta("minimality_check", minimality.check_id, run_id),
        {
            "Purpose": "Record what stayed inside the MVP scope.",
            "Current State": minimality.reason,
            "Inputs": markdown_list(minimality.kept),
            "Outputs": f"Dropped:\n{markdown_list(minimality.dropped)}\n\nDeferred:\n{markdown_list(minimality.deferred)}",
            "Links": f"- VALIDATES: [[{run_id}-M001]]",
            "Do Next": "Use this check when finalizing scope.",
            "Do Not": "Do not add deferred integrations to the MVP output.",
        },
    )
    write_text(vault_root(root) / "11_MinimalityChecks" / f"{minimality.check_id}.md", note)


def _write_artifact_note(root: Path, run_id: str, packet: MergePacket, risks: list[str]) -> None:
    note = frontmatter_note(
        note_meta("accumulated_artifact", f"{run_id}-artifact-v1", run_id),
        {
            "Purpose": "Hold the current accumulated handoff artifact.",
            "Current State": "Version 1 contains merged scope, steps, risks, and verification points.",
            "Inputs": f"MergePacket: [[{packet.merge_id}]]",
            "Outputs": f"Confirmed points:\n{markdown_list(packet.confirmed_points)}\n\nRisks:\n{markdown_list(risks)}",
            "Links": f"- DERIVED_FROM: [[{packet.merge_id}]]",
            "Do Next": "Finalize if loop decision allows it.",
            "Do Not": "Do not bypass this artifact when creating FinalPacket.",
        },
    )
    write_text(vault_root(root) / "05_Artifacts" / f"{run_id}-artifact-v1.md", note)


def _write_folded_summary(root: Path, run_id: str, packet: MergePacket) -> None:
    note = frontmatter_note(
        note_meta("folded_summary", f"{run_id}-folded-summary-v1", run_id),
        {
            "Purpose": "Compact the current run state for future reading.",
            "Current State": "One loop has produced an attachable artifact.",
            "Inputs": f"MergePacket: [[{packet.merge_id}]]",
            "Outputs": markdown_list(packet.confirmed_points[:5]),
            "Links": f"- DERIVED_FROM: [[{packet.merge_id}]]\n- UPDATES: [[{run_id}-artifact-v1]]",
            "Do Next": "Use this summary before reading raw worker outputs.",
            "Do Not": "Do not expand this into a raw log.",
        },
    )
    write_text(vault_root(root) / "05_Artifacts" / f"{run_id}-folded-summary-v1.md", note)
