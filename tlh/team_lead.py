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
    if "two live" in concrete.lower() or "multi-live" in concrete.lower() or "live worker limit" in concrete.lower():
        return [
            TaskCard(
                task_id=f"{run_id}-T001",
                run_id=run_id,
                loop_index=0,
                title="Define the S-4 live worker limit policy",
                goal=(
                    "Define scope, non-goals, files to inspect, and backend selection rules "
                    "for a future live worker rollout policy with a hard live-worker limit."
                ),
                worker_role="builder",
                input_context=[concrete],
                expected_output="scope, non-goals, files to inspect, live worker limit policy, and backend selection rules.",
                attach_point="FinalPacket.Scope",
                merge_key="s4_limit_policy",
                topology_hint="parallel",
            ),
            TaskCard(
                task_id=f"{run_id}-T002",
                run_id=run_id,
                loop_index=0,
                title="Define S-4 fallback and failure handling",
                goal=(
                    "Define fallback behavior, rollback or failure handling, secret handling, "
                    "verification commands, and report format for a limited multi-live dry run."
                ),
                worker_role="critic",
                input_context=[concrete],
                expected_output="fallback, rollback, secret handling, verification, risks, and report format.",
                attach_point="FinalPacket.Verification",
                dependencies=[f"{run_id}-T001"],
                merge_key="s4_fallback_quality",
                topology_hint="parallel",
            ),
            TaskCard(
                task_id=f"{run_id}-T003",
                run_id=run_id,
                loop_index=0,
                title="Review S-4 live limit safety",
                goal=(
                    "Check that exactly two live workers are allowed, remaining workers stay stub-safe, "
                    "metadata is recorded, and raw run artifacts remain uncommitted."
                ),
                worker_role="critic",
                input_context=[concrete],
                expected_output="section-mapped safety, metadata, verification, and report findings.",
                attach_point="FinalPacket.ReportFormat",
                dependencies=[f"{run_id}-T001", f"{run_id}-T002"],
                merge_key="s4_limit_safety",
                topology_hint="parallel",
            ),
        ]
    if "one live" in concrete.lower() or "one-live-worker" in concrete.lower():
        return [
            TaskCard(
                task_id=f"{run_id}-T001",
                run_id=run_id,
                loop_index=0,
                title="Draft the controlled multi-worker live rollout handoff",
                goal=(
                    "Produce the scope, non-goals, files to inspect, backend selection policy, "
                    "one-live-worker validation plan, fallback behavior, secret handling, "
                    "verification commands, and report format for a future controlled multi-worker live rollout."
                ),
                worker_role="builder",
                input_context=[concrete],
                expected_output="section-mapped findings for an executable Codex handoff prompt.",
                attach_point="FinalPacket.Scope",
                merge_key="s3_one_live_scope",
                topology_hint="parallel",
                backend_hint="live",
            ),
            TaskCard(
                task_id=f"{run_id}-T002",
                run_id=run_id,
                loop_index=0,
                title="Review S-3 one-live-worker safety and quality",
                goal=(
                    "Keep the run stub-safe by checking fallback behavior, secret handling, "
                    "verification commands, report format, and non-goals without adding multiple live workers."
                ),
                worker_role="critic",
                input_context=[concrete],
                expected_output="section-mapped safety, verification, and quality findings.",
                attach_point="FinalPacket.Verification",
                dependencies=[f"{run_id}-T001"],
                merge_key="s3_safety_verification",
                topology_hint="parallel",
            ),
        ]
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
