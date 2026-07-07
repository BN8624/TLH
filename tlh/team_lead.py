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
            title="Define the S-2 live Gemma adapter handoff scope",
            goal=(
                "Identify the implementation boundary, files to inspect, expected changes, "
                "and non-goals for live Gemma support without changing WorkerResult schema."
            ),
            worker_role="builder",
            input_context=[concrete],
            expected_output="scope, non-goals, files to inspect, expected changes, and implementation steps.",
            attach_point="FinalPacket.Scope",
            merge_key="s2_scope",
            topology_hint="parallel",
        ),
        TaskCard(
            task_id=f"{run_id}-T002",
            run_id=run_id,
            loop_index=0,
            title="Define S-2 safety, fallback, and verification requirements",
            goal=(
                "Specify environment variable handling, secret safety, stub fallback behavior, "
                "failure handling, verification commands, and report format for the S-2 handoff."
            ),
            worker_role="critic",
            input_context=[concrete],
            expected_output="environment variables, secret handling, fallback, verification, failure handling, risks, and report format.",
            attach_point="FinalPacket.Verification",
            dependencies=[f"{run_id}-T001"],
            merge_key="s2_safety_verification",
            topology_hint="parallel",
        ),
    ]
