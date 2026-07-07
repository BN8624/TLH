# MVP용 worker 실행 인터페이스와 stub worker를 제공한다.

from __future__ import annotations

from .schemas import TaskCard, WorkerResult


def run_worker(card: TaskCard) -> WorkerResult:
    if card.worker_role == "critic":
        findings = [
            "Keep the handoff bounded to a small CLI implementation.",
            "Require concrete verification commands in the final packet.",
            "Preserve user constraints and avoid global workflow automation.",
        ]
        risks = [
            "The mission may hide file format edge cases.",
            "The final handoff can become too broad if optional integrations are included.",
        ]
        attach_notes = [
            "Attach verification requirements to AccumulatedArtifact.risks_and_verification.",
            "Attach out-of-scope items to FinalPacket.out_of_scope.",
        ]
    else:
        findings = [
            "Create a concise implementation sequence from input parsing to JSONL writing.",
            "Include expected files, commands, and success checks.",
            "Use plain CLI behavior before adding integrations.",
        ]
        risks = ["Assume no external services are required for the handoff target."]
        attach_notes = [
            "Attach scope to AccumulatedArtifact.scope_and_steps.",
            "Attach execution steps to FinalPacket.execution_steps.",
        ]
    return WorkerResult(
        task_id=card.task_id,
        worker_id=f"stub-{card.worker_role}",
        summary=f"stub-generated {card.worker_role} result for {card.title}",
        findings=findings,
        risks=risks,
        assumptions=["stub_generated: true", "No live model configured for MVP skeleton."],
        open_questions=[],
        attach_notes=attach_notes,
        stub_generated=True,
    )
