# worker backend 선택과 stub/live WorkerResult 생성을 관리한다.

from __future__ import annotations

import json
import os
import random
import time
from typing import Callable, Mapping

from . import gemma_client
from .live_routing import LiveRoutingDecision
from .schemas import TaskCard, WorkerResult


class WorkerBackendError(RuntimeError):
    pass


GemmaGenerate = Callable[[str], gemma_client.GemmaResponse]
RetrySleep = Callable[[float], None]
RetryJitter = Callable[[float, float], float]
DEFAULT_MAX_RETRY_ATTEMPTS = 2
DEFAULT_RETRY_BACKOFF_SCHEDULE = [5.0, 15.0]
DEFAULT_RETRY_BUDGET_LIMIT = 5
RETRYABLE_ERROR_TYPES = {"timeout", "api_503_high_demand", "api_500_internal", "api_429_rate_limit"}


def run_worker(
    card: TaskCard,
    env: Mapping[str, str] | None = None,
    live_generate: GemmaGenerate | None = None,
    routing_decision: LiveRoutingDecision | None = None,
    retry_sleep: RetrySleep | None = None,
    retry_jitter: RetryJitter | None = None,
) -> WorkerResult:
    env = env or os.environ
    mode = routing_decision.selected_backend if routing_decision else _backend_mode(card, env)
    if live_generate is None:
        live_generate = _generate_with_env(env)

    if mode == "stub":
        telemetry = _telemetry_without_live_attempt(env, routing_decision, final_backend="stub", fallback_used=False)
        return _stub_result(card, backend="stub", env=env, routing_decision=routing_decision, telemetry=telemetry)

    if mode == "auto" and not gemma_client.is_configured(env):
        telemetry = _telemetry_without_live_attempt(
            env,
            routing_decision,
            final_backend="stub",
            fallback_used=True,
            error_type="api_auth_error",
            error_message="Live Gemma is not configured; auto used stub.",
        )
        return _stub_result(
            card,
            backend="stub",
            fallback_used=True,
            error="Live Gemma is not configured; auto used stub.",
            env=env,
            routing_decision=routing_decision,
            telemetry=telemetry,
        )

    if mode not in {"live", "auto"}:
        telemetry = _telemetry_without_live_attempt(
            env,
            routing_decision,
            final_backend="stub",
            fallback_used=True,
            error_type="unknown",
            error_message=f"Unsupported backend `{mode}`; used stub.",
        )
        return _stub_result(
            card,
            backend="stub",
            fallback_used=True,
            error=f"Unsupported backend `{mode}`; used stub.",
            env=env,
            routing_decision=routing_decision,
            telemetry=telemetry,
        )

    prompt = gemma_client.build_worker_prompt(card)
    response, telemetry = _run_live_with_retry(
        prompt,
        env,
        routing_decision,
        live_generate,
        retry_sleep=retry_sleep,
        retry_jitter=retry_jitter,
    )
    if response.success:
        return _normalize_live_result(card, response, env, routing_decision, telemetry=telemetry)

    error = telemetry.get("error_message_safe") or _redact_error(response.error, env)
    fallback = routing_decision.fallback_allowed if routing_decision else _fallback_enabled(env, default=(mode == "auto"))
    if fallback:
        return _stub_result(
            card,
            backend="stub",
            fallback_used=True,
            error=str(error),
            env=env,
            routing_decision=routing_decision,
            telemetry=telemetry,
        )
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


def _run_live_with_retry(
    prompt: str,
    env: Mapping[str, str],
    routing_decision: LiveRoutingDecision | None,
    live_generate: GemmaGenerate,
    retry_sleep: RetrySleep | None = None,
    retry_jitter: RetryJitter | None = None,
) -> tuple[gemma_client.GemmaResponse, dict]:
    started = time.monotonic()
    max_retries = _max_retry_attempts(env)
    backoff_schedule = _retry_backoff_schedule(env, max_retries)
    budget_limit = _retry_budget_limit(env)
    budget_remaining = _retry_budget_remaining(env, budget_limit)
    budget_consumed = False
    sleep = retry_sleep or time.sleep
    jitter = retry_jitter or random.uniform
    attempts: list[dict] = []
    first_error_type = "none"
    last_error_type = "none"
    response = gemma_client.GemmaResponse(success=False, error="unknown live worker failure")
    for attempt_index in range(max_retries + 1):
        attempt_started = time.monotonic()
        response = live_generate(prompt)
        attempt_latency_ms = _latency_ms(attempt_started, time.monotonic())
        if response.success:
            attempts.append(_attempt_metadata(attempt_index + 1, True, attempt_latency_ms, env, "none", ""))
            telemetry = _finish_live_telemetry(
                env=env,
                routing_decision=routing_decision,
                started=started,
                attempts=attempts,
                final_backend="live",
                fallback_used=False,
                fallback_cause="none",
                first_error_type=first_error_type,
                last_error_type=last_error_type,
                final_error_type="none",
                error_message="",
                max_retries=max_retries,
                backoff_schedule=backoff_schedule,
                budget_limit=budget_limit,
                budget_remaining=budget_remaining,
                budget_consumed=budget_consumed,
                retry_skipped_reason="",
            )
            return response, telemetry

        safe_error = _safe_error_message(response.error, env)
        error_type = classify_error(safe_error)
        if first_error_type == "none":
            first_error_type = error_type
        last_error_type = error_type
        can_retry = attempt_index < max_retries and _retryable(error_type)
        retry_skipped_reason = ""
        delay_seconds = 0.0
        if can_retry:
            if budget_remaining <= 0 and not budget_consumed:
                can_retry = False
                retry_skipped_reason = "retry budget exhausted"
            else:
                if not budget_consumed:
                    budget_consumed = True
                    budget_remaining -= 1
                delay_seconds = backoff_schedule[min(attempt_index, len(backoff_schedule) - 1)] if backoff_schedule else 0.0
                jitter_seconds = _retry_jitter_seconds(env, jitter)
                delay_seconds += jitter_seconds
        attempts.append(
            _attempt_metadata(
                attempt_index + 1,
                False,
                attempt_latency_ms,
                env,
                error_type,
                safe_error,
                scheduled_retry_delay_seconds=delay_seconds if can_retry else 0.0,
            )
        )
        if can_retry:
            if delay_seconds > 0:
                sleep(delay_seconds)
            continue
        telemetry = _finish_live_telemetry(
            env=env,
            routing_decision=routing_decision,
            started=started,
            attempts=attempts,
            final_backend="stub",
            fallback_used=True,
            fallback_cause=error_type,
            first_error_type=first_error_type,
            last_error_type=last_error_type,
            final_error_type=error_type,
            error_message=safe_error,
            max_retries=max_retries,
            backoff_schedule=backoff_schedule,
            budget_limit=budget_limit,
            budget_remaining=budget_remaining,
            budget_consumed=budget_consumed,
            retry_skipped_reason=retry_skipped_reason,
        )
        return response, telemetry
    return response, _telemetry_without_live_attempt(env, routing_decision, "stub", True, "unknown", "unknown")


def classify_error(error: str) -> str:
    lowered = error.lower()
    if "timeout" in lowered or "timed out" in lowered:
        return "timeout"
    if "503" in lowered and ("high demand" in lowered or "unavailable" in lowered):
        return "api_503_high_demand"
    if "500" in lowered and ("internal" in lowered or "internal error" in lowered):
        return "api_500_internal"
    if "429" in lowered or "quota" in lowered or "rate limit" in lowered or "rate_limit" in lowered:
        return "api_429_rate_limit"
    if "auth" in lowered or "api key" in lowered or "permission" in lowered or "unauthorized" in lowered:
        return "api_auth_error"
    if "schema" in lowered or "validation" in lowered:
        return "schema_error"
    if "invalid model response" in lowered or "invalid response" in lowered or "parse" in lowered:
        return "invalid_model_response"
    if "api" in lowered or "unavailable" in lowered or "internal" in lowered:
        return "unknown_api_error"
    if not lowered.strip():
        return "unknown"
    return "unknown"


def _retryable(error_type: str) -> bool:
    return error_type in RETRYABLE_ERROR_TYPES


def _max_retry_attempts(env: Mapping[str, str]) -> int:
    try:
        return max(0, int(env.get("TLH_GEMMA_MAX_RETRY_ATTEMPTS", DEFAULT_MAX_RETRY_ATTEMPTS)))
    except (TypeError, ValueError):
        return DEFAULT_MAX_RETRY_ATTEMPTS


def _retry_backoff_schedule(env: Mapping[str, str], max_retries: int) -> list[float]:
    raw = env.get("TLH_GEMMA_RETRY_BACKOFF_SECONDS", "")
    values: list[float] = []
    if raw.strip():
        for item in raw.split(","):
            try:
                values.append(max(0.0, float(item.strip())))
            except ValueError:
                continue
    if not values:
        values = DEFAULT_RETRY_BACKOFF_SCHEDULE.copy()
    if max_retries <= 0:
        return []
    while len(values) < max_retries:
        values.append(values[-1])
    return values[:max_retries]


def _retry_jitter_enabled(env: Mapping[str, str]) -> bool:
    raw = env.get("TLH_GEMMA_RETRY_JITTER_ENABLED")
    if raw is None:
        return True
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _retry_jitter_seconds(env: Mapping[str, str], jitter: RetryJitter) -> float:
    if not _retry_jitter_enabled(env):
        return 0.0
    try:
        max_jitter = max(0.0, float(env.get("TLH_GEMMA_RETRY_JITTER_MAX_SECONDS", "2")))
    except ValueError:
        max_jitter = 2.0
    return max(0.0, float(jitter(0.0, max_jitter))) if max_jitter else 0.0


def _retry_budget_enabled(env: Mapping[str, str]) -> bool:
    raw = env.get("TLH_GEMMA_RETRY_BUDGET_ENABLED")
    if raw is None:
        return True
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _retry_budget_limit(env: Mapping[str, str]) -> int:
    if not _retry_budget_enabled(env):
        return DEFAULT_RETRY_BUDGET_LIMIT
    try:
        return max(0, int(env.get("TLH_GEMMA_RETRY_BUDGET_WORKERS", DEFAULT_RETRY_BUDGET_LIMIT)))
    except (TypeError, ValueError):
        return DEFAULT_RETRY_BUDGET_LIMIT


def _retry_budget_remaining(env: Mapping[str, str], budget_limit: int) -> int:
    if not _retry_budget_enabled(env):
        return budget_limit
    raw = env.get("TLH_GEMMA_RETRY_BUDGET_REMAINING")
    if raw is None:
        return budget_limit
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return budget_limit


def _redact_error(error: str, env: Mapping[str, str]) -> str:
    api_key = env.get("TLH_GEMMA_API_KEY", "")
    if api_key:
        return error.replace(api_key, "[REDACTED]")
    return error


def _safe_error_message(error: str, env: Mapping[str, str]) -> str:
    redacted = _redact_error(error or "", env)
    redacted = " ".join(redacted.split())
    return redacted[:240]


def _normalize_live_result(
    card: TaskCard,
    response: gemma_client.GemmaResponse,
    env: Mapping[str, str],
    routing_decision: LiveRoutingDecision | None,
    telemetry: dict | None = None,
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
        metadata=_worker_metadata(
            env,
            backend="live",
            fallback_used=False,
            routing_decision=routing_decision,
            telemetry=telemetry,
        ),
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
    telemetry: dict | None = None,
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
        error=_safe_error_message(error, env or {}),
        metadata=_worker_metadata(
            env,
            backend=backend,
            fallback_used=fallback_used,
            routing_decision=routing_decision,
            telemetry=telemetry,
        ),
    )


def _worker_metadata(
    env: Mapping[str, str] | None,
    backend: str,
    fallback_used: bool,
    routing_decision: LiveRoutingDecision | None,
    telemetry: dict | None = None,
) -> dict:
    env = env or {}
    if routing_decision:
        metadata = routing_decision.to_metadata()
        metadata["backend"] = backend
        metadata["selected_backend"] = backend
        metadata["fallback_used"] = fallback_used
        _attach_key_pool_metadata(metadata, env, backend)
        if telemetry:
            metadata.update(telemetry)
        _attach_wave_metadata(metadata, env)
        if fallback_used:
            metadata["routing_reason"] = f"live call failed; stub fallback used: {metadata['routing_reason']}"
        return metadata

    metadata: dict = {
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
    if telemetry:
        metadata.update(telemetry)
    _attach_wave_metadata(metadata, env)
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


def _attach_wave_metadata(metadata: dict, env: Mapping[str, str]) -> None:
    enabled_raw = env.get("TLH_LIVE_WAVE_ENABLED")
    if enabled_raw is None:
        return
    enabled = enabled_raw.strip().lower() in {"1", "true", "yes", "on"}
    metadata["wave_enabled"] = enabled
    metadata["wave_index"] = _int_metadata(env.get("TLH_LIVE_WAVE_INDEX", "0")) or None
    metadata["wave_size"] = _int_metadata(env.get("TLH_LIVE_WAVE_SIZE", "0")) or None
    metadata["wave_count"] = _int_metadata(env.get("TLH_LIVE_WAVE_COUNT", "0"))
    metadata["target_live_workers"] = _int_metadata(env.get("TLH_LIVE_WAVE_TARGET_LIVE_WORKERS", "0"))
    metadata["max_concurrent_live_workers"] = _int_metadata(env.get("TLH_LIVE_WAVE_MAX_CONCURRENT", "0"))
    metadata["wave_preserve_key_slot"] = env.get("TLH_LIVE_WAVE_PRESERVE_KEY_SLOT", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    metadata["retry_within_wave"] = env.get("TLH_LIVE_WAVE_RETRY_WITHIN_WAVE", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    metadata["successful_workers_rerun"] = env.get(
        "TLH_LIVE_WAVE_SUCCESSFUL_WORKERS_RERUN", "false"
    ).strip().lower() in {"1", "true", "yes", "on"}


def _telemetry_without_live_attempt(
    env: Mapping[str, str],
    routing_decision: LiveRoutingDecision | None,
    final_backend: str,
    fallback_used: bool,
    error_type: str = "none",
    error_message: str = "",
) -> dict:
    started = time.monotonic()
    return _finish_live_telemetry(
        env=env,
        routing_decision=routing_decision,
        started=started,
        attempts=[],
        final_backend=final_backend,
        fallback_used=fallback_used,
        fallback_cause=error_type if fallback_used else "none",
        first_error_type=error_type if fallback_used else "none",
        last_error_type=error_type,
        final_error_type=error_type,
        error_message=error_message,
        max_retries=_max_retry_attempts(env),
        backoff_schedule=_retry_backoff_schedule(env, _max_retry_attempts(env)),
        budget_limit=_retry_budget_limit(env),
        budget_remaining=_retry_budget_remaining(env, _retry_budget_limit(env)),
        budget_consumed=False,
        retry_skipped_reason="",
    )


def _finish_live_telemetry(
    *,
    env: Mapping[str, str],
    routing_decision: LiveRoutingDecision | None,
    started: float,
    attempts: list[dict],
    final_backend: str,
    fallback_used: bool,
    fallback_cause: str,
    first_error_type: str,
    last_error_type: str,
    final_error_type: str,
    error_message: str,
    max_retries: int,
    backoff_schedule: list[float],
    budget_limit: int,
    budget_remaining: int,
    budget_consumed: bool,
    retry_skipped_reason: str,
) -> dict:
    ended = time.monotonic()
    attempt_count = len(attempts)
    retry_count = max(0, attempt_count - 1)
    return {
        "worker_index": routing_decision.worker_index if routing_decision else None,
        "requested_backend": routing_decision.requested_backend if routing_decision else _backend_mode_from_env(env),
        "selected_backend": routing_decision.selected_backend if routing_decision else _backend_mode_from_env(env),
        "final_backend": final_backend,
        "key_slot": _int_metadata(env.get("TLH_GEMMA_KEY_SLOT", "0")) or None,
        "policy_mode": routing_decision.policy_mode if routing_decision else "legacy",
        "live_limit": routing_decision.max_live_workers if routing_decision else _int_metadata(env.get("TLH_LIVE_WORKER_LIMIT", "0")),
        "started_monotonic": round(started, 6),
        "ended_monotonic": round(ended, 6),
        "latency_ms": _latency_ms(started, ended),
        "attempt_count": attempt_count,
        "retry_count": retry_count,
        "attempts": attempts,
        "retry_policy_enabled": max_retries > 0,
        "max_retry_attempts": max_retries,
        "retry_backoff_enabled": bool(backoff_schedule),
        "retry_backoff_schedule": backoff_schedule,
        "retry_jitter_enabled": _retry_jitter_enabled(env),
        "retry_budget_enabled": _retry_budget_enabled(env),
        "retry_budget_applied": _retry_budget_enabled(env),
        "retry_budget_limit": budget_limit,
        "retry_budget_remaining": budget_remaining,
        "retry_budget_consumed": budget_consumed,
        "retry_skipped_reason": retry_skipped_reason,
        "successful_workers_rerun": False,
        "key_slot_preserved": _key_slot_preserved(attempts),
        "fallback_used": fallback_used,
        "fallback_cause": fallback_cause,
        "first_error_type": first_error_type,
        "last_error_type": last_error_type,
        "final_error_type": final_error_type,
        "error_type": final_error_type,
        "fallback_after_retry": fallback_used and retry_count > 0,
        "error_message_safe": _safe_error_message(error_message, env),
    }


def _attempt_metadata(
    attempt_number: int,
    success: bool,
    latency_ms: int,
    env: Mapping[str, str],
    error_type: str,
    error_message: str,
    scheduled_retry_delay_seconds: float = 0.0,
) -> dict:
    return {
        "attempt": attempt_number,
        "success": success,
        "key_slot": _int_metadata(env.get("TLH_GEMMA_KEY_SLOT", "0")) or None,
        "latency_ms": latency_ms,
        "error_type": error_type,
        "error_message_safe": _safe_error_message(error_message, env),
        "scheduled_retry_delay_seconds": scheduled_retry_delay_seconds,
    }


def _latency_ms(started: float, ended: float) -> int:
    return max(0, int((ended - started) * 1000))


def _key_slot_preserved(attempts: list[dict]) -> bool:
    slots = {attempt.get("key_slot") for attempt in attempts if attempt.get("key_slot") is not None}
    return len(slots) <= 1
