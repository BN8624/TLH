# MVP용 worker 실행 인터페이스와 stub worker를 제공한다.

from __future__ import annotations

from .schemas import TaskCard, WorkerResult


def run_worker(card: TaskCard) -> WorkerResult:
    if card.merge_key == "s2_scope":
        findings = [
            "scope: Add a live Gemma adapter behind the existing `tlh.gemma_client` boundary.",
            "scope: Keep `WorkerResult` output shape stable so merge code continues to consume structured results.",
            "non_goal: Do not implement Obsidian MCP write, RTK hooks, GUI, dashboard, or AI_WORKFLOW_KIT workflow tooling.",
            "file: Inspect `tlh/gemma_client.py`, `tlh/worker_pool.py`, `tlh/dispatcher.py`, `tests/test_smoke_cli.py`, and prompt files under `prompts/`.",
            "change: Add configuration detection and live generation in `tlh/gemma_client.py` while preserving the current stub path.",
            "change: Route worker execution through the adapter only when configuration is present.",
            "step: Start with tests for configured and unconfigured adapter modes before changing worker behavior.",
        ]
        risks = [
            "Live model response shape may not map cleanly into WorkerResult fields.",
            "Adapter changes can accidentally make tests require network access.",
        ]
        attach_notes = [
            "target: FinalPacket.Scope | content: Live Gemma adapter remains behind the existing worker boundary.",
            "target: FinalPacket.OutOfScope | content: Do not add GUI, MCP write, RTK hook, or AI_WORKFLOW_KIT duplication.",
            "target: FinalPacket.FilesToInspect | content: Inspect gemma_client, worker_pool, dispatcher, tests, and prompts.",
            "target: FinalPacket.ExpectedChanges | content: Preserve stub fallback and WorkerResult schema.",
        ]
    elif card.merge_key == "s2_safety_verification":
        findings = [
            "env: Use environment variables for live adapter configuration, for example `TLH_GEMMA_API_KEY` and `TLH_GEMMA_MODEL`.",
            "secret: Never write API keys, tokens, or raw `.env` contents into repo files, vault notes, run artifacts, or logs.",
            "fallback: If required configuration is missing or live generation fails, keep stub worker output with `stub_generated: true`.",
            "verification: Run `python -m compileall tlh`, `python -m pytest`, and a temp-workspace TLH dry run.",
            "failure: On API errors, record a structured risk or open question and continue with stub fallback instead of crashing the whole run.",
            "report: Report changed files, commands run, live mode status, fallback status, and remaining risks.",
            "safety: Do not push automatically after S-2 implementation.",
        ]
        risks = [
            "Secret handling can regress if exceptions include raw environment values.",
            "Fallback behavior can mask live adapter failures unless reported clearly.",
        ]
        attach_notes = [
            "target: FinalPacket.EnvironmentVariables | content: Use env vars and document missing-config behavior.",
            "target: FinalPacket.SecretHandling | content: Never persist secrets in repo, vault, machine artifacts, or logs.",
            "target: FinalPacket.StubFallback | content: Keep `stub_generated: true` fallback when live mode is unavailable.",
            "target: FinalPacket.Verification | content: Include compileall, pytest, and temp-workspace dry run.",
            "target: FinalPacket.ReportFormat | content: Include live status, fallback status, verification, and risks.",
        ]
    elif card.worker_role == "critic":
        findings = [
            "non_goal: Keep the handoff bounded to the requested implementation slice.",
            "verification: Require concrete verification commands in the final packet.",
            "safety: Preserve user constraints and avoid global workflow automation.",
        ]
        risks = [
            "The mission may hide file format edge cases.",
            "The final handoff can become too broad if optional integrations are included.",
        ]
        attach_notes = [
            "target: FinalPacket.Verification | content: Attach concrete verification commands.",
            "target: FinalPacket.OutOfScope | content: Attach forbidden integrations.",
        ]
    else:
        findings = [
            "step: Create a concise implementation sequence from the mission constraints.",
            "file: Include expected files, commands, and success checks.",
            "scope: Use plain CLI behavior before adding integrations.",
        ]
        risks = ["Assume no external services are required for the handoff target."]
        attach_notes = [
            "target: FinalPacket.Scope | content: Attach scope to the final packet.",
            "target: FinalPacket.ExecutionSteps | content: Attach execution steps.",
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
