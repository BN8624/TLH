# TeamLead의 질문 생성과 TaskCard 분해 규칙을 구현한다.

from __future__ import annotations

from .schemas import TaskCard


def clarify(mission: str) -> list[str]:
    return [
        "What exact output should the final handoff enable?",
        "What inputs, file paths, or constraints must the workers preserve?",
        "What verification should prove the result is usable?",
    ]


def concrete_mission(mission: str, answers: str) -> str:
    return (
        "Mission:\n"
        f"{mission.strip()}\n\n"
        "User answers and constraints:\n"
        f"{answers.strip() if answers.strip() else 'No additional answers supplied. Use MVP defaults.'}"
    )


def decompose(run_id: str, mission: str, answers: str) -> list[TaskCard]:
    concrete = concrete_mission(mission, answers)
    return [
        TaskCard(
            task_id=f"{run_id}-T001",
            run_id=run_id,
            loop_index=0,
            title="Plan the concrete implementation handoff",
            goal="Extract the implementation steps, scope, and attachable output structure from the mission.",
            worker_role="builder",
            input_context=[concrete],
            expected_output="Structured findings for the handoff plan.",
            attach_point="AccumulatedArtifact.scope_and_steps",
            merge_key="implementation_plan",
            topology_hint="parallel",
        ),
        TaskCard(
            task_id=f"{run_id}-T002",
            run_id=run_id,
            loop_index=0,
            title="Review risks and verification",
            goal="Identify missing assumptions, risks, and verification checks before final handoff.",
            worker_role="critic",
            input_context=[concrete],
            expected_output="Structured findings for risks, assumptions, and verification.",
            attach_point="AccumulatedArtifact.risks_and_verification",
            merge_key="risk_review",
            topology_hint="parallel",
        ),
    ]
