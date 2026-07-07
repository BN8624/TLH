# worker backend 선택과 stub/live WorkerResult 생성을 관리한다.

from __future__ import annotations

import json
import os
from typing import Callable, Mapping

from . import gemma_client
from .live_routing import LiveRoutingDecision
from .schemas import TaskCard, WorkerResult


class WorkerBackendError(RuntimeError):
    pass


GemmaGenerate = Callable[[str], gemma_client.GemmaResponse]


def run_worker(
    card: TaskCard,
    env: Mapping[str, str] | None = None,
    live_generate: GemmaGenerate | None = None,
    routing_decision: LiveRoutingDecision | None = None,
) -> WorkerResult:
    env = env or os.environ
    mode = routing_decision.selected_backend if routing_decision else _backend_mode(card, env)
    if live_generate is None:
        live_generate = _generate_with_env(env)

    if mode == "stub":
        return _stub_result(card, backend="stub", env=env, routing_decision=routing_decision)

    if mode == "auto" and not gemma_client.is_configured(env):
        return _stub_result(
            card,
            backend="stub",
            fallback_used=True,
            error="Live Gemma is not configured; auto used stub.",
            env=env,
            routing_decision=routing_decision,
        )

    if mode not in {"live", "auto"}:
        return _stub_result(
            card,
            backend="stub",
            fallback_used=True,
            error=f"Unsupported backend `{mode}`; used stub.",
            env=env,
            routing_decision=routing_decision,
        )

    prompt = gemma_client.build_worker_prompt(card)
    response = live_generate(prompt)
    if response.success:
        return _normalize_live_result(card, response, env, routing_decision)

    error = _redact_error(response.error, env)
    fallback = routing_decision.fallback_allowed if routing_decision else _fallback_enabled(env, default=(mode == "auto"))
    if fallback:
        return _stub_result(card, backend="stub", fallback_used=True, error=error, env=env, routing_decision=routing_decision)
    raise WorkerBackendError(error or "Live Gemma worker failed.")


def _backend_mode(card: TaskCard, env: Mapping[str, str]) -> str:
    forced = env.get("TLH_FORCE_WORKER_BACKEND", "").strip().lower()
    if forced:
        return forced
    hint = card.backend_hint.strip().lower()
    if hint:
        return hint
    return env.get("TLH_WORKER_BACKEND", "stub").strip().lower() or "stub"


def _generate_with_env(env: Mapping[str, str]) -> GemmaGenerate:
    def generate(prompt: str) -> gemma_client.GemmaResponse:
        try:
            config = gemma_client.load_config(env)
        except gemma_client.GemmaUnavailable as exc:
            return gemma_client.GemmaResponse(success=False, error=str(exc), model="")
        return gemma_client.generate(prompt, config=config)

    return generate


def _fallback_enabled(env: Mapping[str, str], default: bool) -> bool:
    raw = env.get("TLH_GEMMA_FALLBACK_TO_STUB")
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _redact_error(error: str, env: Mapping[str, str]) -> str:
    api_key = env.get("TLH_GEMMA_API_KEY", "")
    if api_key:
        return error.replace(api_key, "[REDACTED]")
    return error


def _normalize_live_result(
    card: TaskCard,
    response: gemma_client.GemmaResponse,
    env: Mapping[str, str],
    routing_decision: LiveRoutingDecision | None,
) -> WorkerResult:
    data = _parse_live_text(response.text)
    missing: list[str] = []

    summary = str(data.get("summary") or "").strip()
    if not summary:
        summary = f"live-generated result for {card.title}"
        missing.append("summary")

    findings = _findings_field(data)
    if not findings:
        findings = [line for line in response.text.splitlines() if line.strip()] or [summary]
        missing.append("findings")

    risks = _list_field(data, "risks")
    assumptions = _list_field(data, "assumptions")
    open_questions = _list_field(data, "open_questions")
    attach_notes = _list_field(data, "attach_notes")
    if not attach_notes:
        attach_notes = [f"target: {card.attach_point or 'FinalPacket.Scope'} | content: Live result normalized for merge."]
        missing.append("attach_notes")

    if missing:
        assumptions.append(f"normalized_missing_fields: {', '.join(missing)}")

    return WorkerResult(
        task_id=card.task_id,
        worker_id=f"live-{card.worker_role}",
        summary=summary,
        findings=findings,
        risks=risks,
        assumptions=assumptions,
        open_questions=open_questions,
        attach_notes=attach_notes,
        stub_generated=False,
        live_generated=True,
        backend="live",
        model=response.model,
        fallback_used=False,
        error="",
        metadata=_worker_metadata(env, backend="live", fallback_used=False, routing_decision=routing_decision),
    )


def _parse_live_text(text: str) -> dict:
    text = _extract_json_text(text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _extract_json_text(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    if stripped.startswith("{"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end > start:
        return stripped[start : end + 1]
    return stripped


def _findings_field(data: dict) -> list[str]:
    value = data.get("findings", [])
    if isinstance(value, dict):
        return _sectioned_findings(value)
    return _list_field(data, "findings")


def _sectioned_findings(values: dict) -> list[str]:
    prefixes = {
        "scope": "scope",
        "non_goal": "non_goal",
        "non_goals": "non_goal",
        "files_to_inspect": "file",
        "file": "file",
        "files": "file",
        "live_worker_limit_policy": "env",
        "live_worker_limit": "env",
        "backend_selection_policy": "env",
        "backend_selection_rules": "env",
        "backend_policy": "env",
        "live_limit_validation_plan": "step",
        "multi_live_validation_plan": "step",
        "one_live_worker_validation_plan": "step",
        "validation_plan": "step",
        "fallback_behavior": "fallback",
        "rollback_or_failure_handling": "failure",
        "rollback_failure_handling": "failure",
        "rollback": "failure",
        "secret_handling": "secret",
        "verification_commands": "verification",
        "verification": "verification",
        "report_format": "report",
        "implementation_steps": "step",
        "expected_changes": "change",
        "safety_rules": "safety",
    }
    findings: list[str] = []
    for raw_key, raw_value in values.items():
        prefix = prefixes.get(str(raw_key).strip().lower(), str(raw_key).strip().lower())
        if isinstance(raw_value, list):
            findings.extend(f"{prefix}: {item}" for item in raw_value if str(item).strip())
        elif isinstance(raw_value, dict):
            findings.extend(f"{prefix}: {key}: {value}" for key, value in raw_value.items() if str(value).strip())
        elif str(raw_value).strip():
            findings.append(f"{prefix}: {raw_value}")
    return findings


def _list_field(data: dict, key: str) -> list[str]:
    value = data.get(key, [])
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def _stub_result(
    card: TaskCard,
    backend: str,
    fallback_used: bool = False,
    error: str = "",
    env: Mapping[str, str] | None = None,
    routing_decision: LiveRoutingDecision | None = None,
) -> WorkerResult:
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
    elif card.merge_key == "s3_safety_verification":
        findings = [
            "non_goal: Do not implement full live rollout, multiple live workers, GUI, dashboard, Obsidian MCP write, RTK hook, or AI_WORKFLOW_KIT duplication.",
            "file: Inspect `docs/TLH_INDEX.md`, `docs/CURRENT_STATE.md`, `tlh/team_lead.py`, `tlh/dispatcher.py`, `tlh/worker_pool.py`, and `tests/test_live_adapter.py`.",
            "env: Use `TLH_GEMMA_API_KEY`, `TLH_GEMMA_MODEL`, `TLH_WORKER_BACKEND`, `TLH_GEMMA_FALLBACK_TO_STUB`, `TLH_GEMMA_TIMEOUT_SECONDS`, and `TLH_GEMMA_MAX_OUTPUT_TOKENS`.",
            "secret: Load API keys only into the current process, never print values, prefixes, lengths, or raw env dumps.",
            "fallback: Record `fallback_used` explicitly on every WorkerResult path.",
            "verification: Run `python -m compileall tlh`, `python -m pytest`, `python -m tlh --help`, and `python -m tlh init`.",
            "report: Include backend mix, fallback status, schema quality, merge quality, final prompt usability, safety, commit hash, and push status.",
            "safety: Commit only source and review docs; keep raw run artifacts ignored.",
        ]
        risks = [
            "A live WorkerResult may require normalization if the model emits prose instead of JSON.",
            "Global backend settings can accidentally turn all workers live unless per-card backend hints are honored.",
        ]
        attach_notes = [
            "target: FinalPacket.OutOfScope | content: Attach forbidden integrations and rollout boundaries.",
            "target: FinalPacket.SecretHandling | content: Attach key handling rules.",
            "target: FinalPacket.Verification | content: Attach concrete verification commands.",
            "target: FinalPacket.ReportFormat | content: Attach required S-3 report fields.",
        ]
    elif card.merge_key == "s4_limit_safety":
        findings = [
            "scope: Validate a controlled live-worker limit before any broader rollout.",
            "non_goal: Do not allow unlimited live workers or full production rollout.",
            "file: Inspect `tlh/dispatcher.py`, `tlh/worker_pool.py`, `tlh/schemas.py`, `tlh/team_lead.py`, and `tests/test_live_worker_limit.py`.",
            "env: Set `TLH_LIVE_WORKER_LIMIT=2` to cap live workers for the run.",
            "fallback: Cards beyond the live-worker limit must run as stub workers with `stub_generated: true`.",
            "secret: Never print API key values, prefixes, lengths, or raw environment dumps.",
            "verification: Run `python -m compileall tlh`, `python -m pytest`, `python -m tlh --help`, and `python -m tlh init`.",
            "failure: If live quality regresses or fallback breaks, stop scaling and fix live limit metadata or merge quality first.",
            "report: Include backend mix, live worker limit, fallback status, quality assessment, commit hash, and push status.",
        ]
        risks = [
            "Live output may vary across two workers and require section mapping.",
            "Limit metadata can drift if routing and WorkerResult creation are not kept together.",
        ]
        attach_notes = [
            "target: FinalPacket.Scope | content: Attach controlled live-worker limit validation.",
            "target: FinalPacket.StubFallback | content: Attach beyond-limit stub behavior.",
            "target: FinalPacket.SecretHandling | content: Attach no-secret-output rule.",
            "target: FinalPacket.ReportFormat | content: Attach S-4 reporting fields.",
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

    assumptions = ["stub_generated: true", "No live model configured for MVP skeleton."]
    if fallback_used:
        assumptions.append("fallback_used: true")
    return WorkerResult(
        task_id=card.task_id,
        worker_id=f"stub-{card.worker_role}",
        summary=f"stub-generated {card.worker_role} result for {card.title}",
        findings=findings,
        risks=risks,
        assumptions=assumptions,
        open_questions=[],
        attach_notes=attach_notes,
        stub_generated=True,
        live_generated=False,
        backend=backend,
        model="",
        fallback_used=fallback_used,
        error=error,
        metadata=_worker_metadata(env, backend=backend, fallback_used=fallback_used, routing_decision=routing_decision),
    )


def _worker_metadata(
    env: Mapping[str, str] | None,
    backend: str,
    fallback_used: bool,
    routing_decision: LiveRoutingDecision | None,
) -> dict[str, int | str | bool | None]:
    env = env or {}
    if routing_decision:
        metadata = routing_decision.to_metadata()
        metadata["backend"] = backend
        metadata["selected_backend"] = backend
        metadata["fallback_used"] = fallback_used
        _attach_key_pool_metadata(metadata, env, backend)
        if fallback_used:
            metadata["routing_reason"] = f"live call failed; stub fallback used: {metadata['routing_reason']}"
        return metadata

    metadata: dict[str, int | str | bool | None] = {
        "backend": backend,
        "requested_backend": _backend_mode_from_env(env),
        "selected_backend": backend,
        "policy_mode": "legacy",
        "fallback_used": fallback_used,
        "fallback_allowed": _fallback_enabled(env, default=True),
        "routing_reason": "legacy worker invocation without routing decision",
        "routing_source": "worker_pool",
        "policy_source": "legacy",
    }
    if env.get("TLH_LIVE_WORKER_LIMIT"):
        metadata["max_live_workers"] = _int_metadata(env.get("TLH_LIVE_WORKER_LIMIT", "0"))
        metadata["live_worker_limit"] = metadata["max_live_workers"]
    if backend == "live" and env.get("TLH_LIVE_WORKER_INDEX"):
        metadata["live_worker_index"] = _int_metadata(env.get("TLH_LIVE_WORKER_INDEX", "0"))
    _attach_key_pool_metadata(metadata, env, backend)
    return metadata


def _backend_mode_from_env(env: Mapping[str, str]) -> str:
    return env.get("TLH_WORKER_BACKEND", "stub").strip().lower() or "stub"


def _int_metadata(raw: str) -> int:
    try:
        return int(raw)
    except ValueError:
        return 0


def _attach_key_pool_metadata(metadata: dict[str, int | str | bool | None], env: Mapping[str, str], backend: str) -> None:
    available = _int_metadata(env.get("TLH_GEMMA_KEY_POOL_AVAILABLE_SLOTS", "0"))
    if available:
        metadata["available_key_slots"] = available
    mode = env.get("TLH_GEMMA_KEY_POOL_MODE", "")
    if mode:
        metadata["key_pool_mode"] = mode
        metadata["single_key_mode"] = mode == "single_key"
    if env.get("TLH_GEMMA_KEY_SLOT"):
        metadata["key_slot"] = _int_metadata(env.get("TLH_GEMMA_KEY_SLOT", "0"))
