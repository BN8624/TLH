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
    sections = _empty_sections()
    for result in results:
        for item in result.findings:
            if item in seen:
                dropped.append(f"Duplicate finding dropped: {item}")
            else:
                seen.add(item)
                confirmed.append(item)
                _attach_finding(sections, item)
        risks.extend(result.risks)
    sections["Risks"].extend(_dedupe(risks))
    unsupported = [item for item in confirmed if not _section_for(item)]
    dropped.extend(f"Unsupported finding did not map to FinalPacket section: {item}" for item in unsupported)
    minimality = check_merge(run_id, kept=confirmed, dropped=dropped)
    minimality_data = minimality.to_dict()
    minimality_data["sections"] = sections
    minimality_data["routing"] = _routing_summary(results)
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
        continuity_check="WorkerResults were structured, section-mapped, and attachable to the accumulated artifact.",
        minimality=minimality_data,
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
    sections = packet.minimality.get("sections", {})
    routing = packet.minimality.get("routing", {})
    outputs = [
        "Confirmed points:",
        markdown_list(packet.confirmed_points),
        "",
        "Routing Policy:",
        markdown_list(_routing_lines(routing)),
        "",
        "Scope:",
        markdown_list(sections.get("Scope", [])),
        "",
        "Out of Scope:",
        markdown_list(sections.get("OutOfScope", [])),
        "",
        "Verification:",
        markdown_list(sections.get("Verification", [])),
        "",
        "Risks:",
        markdown_list(sections.get("Risks", risks)),
    ]
    note = frontmatter_note(
        note_meta("accumulated_artifact", f"{run_id}-artifact-v1", run_id),
        {
            "Purpose": "Hold the current accumulated handoff artifact.",
            "Current State": "Version 1 contains merged scope, steps, risks, and verification points.",
            "Inputs": f"MergePacket: [[{packet.merge_id}]]",
            "Outputs": "\n".join(outputs),
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


def _empty_sections() -> dict[str, list[str]]:
    return {
        "Scope": [],
        "OutOfScope": [],
        "FilesToInspect": [],
        "ExpectedChanges": [],
        "ImplementationSteps": [],
        "EnvironmentVariables": [],
        "SecretHandling": [],
        "StubFallback": [],
        "Verification": [],
        "FailureHandling": [],
        "ReportFormat": [],
        "SafetyRules": [],
        "Risks": [],
    }


def _section_for(item: str) -> str | None:
    prefix = item.split(":", 1)[0].strip().lower() if ":" in item else ""
    return {
        "scope": "Scope",
        "non_goal": "OutOfScope",
        "file": "FilesToInspect",
        "change": "ExpectedChanges",
        "step": "ImplementationSteps",
        "env": "EnvironmentVariables",
        "secret": "SecretHandling",
        "fallback": "StubFallback",
        "verification": "Verification",
        "failure": "FailureHandling",
        "report": "ReportFormat",
        "safety": "SafetyRules",
        "risk": "Risks",
    }.get(prefix)


def _attach_finding(sections: dict[str, list[str]], item: str) -> None:
    section = _section_for(item)
    if not section:
        return
    content = item.split(":", 1)[1].strip()
    if content and content not in sections[section]:
        sections[section].append(content)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _routing_summary(results: list[WorkerResult]) -> dict:
    backend_mix = {"live": 0, "stub": 0}
    fallback_stub_count = 0
    policy_routing_stub_count = 0
    first_metadata = results[0].metadata if results else {}
    assigned_key_slots: list[int] = []
    available_key_slots = 0
    retryable_error_count = 0
    retried_worker_count = 0
    retry_success_count = 0
    retry_failure_count = 0
    fallback_after_retry_count = 0
    max_retry_attempts = 0
    for result in results:
        backend_mix[result.backend] = backend_mix.get(result.backend, 0) + 1
        requested = result.metadata.get("requested_backend")
        available_key_slots = max(available_key_slots, _int_value(result.metadata.get("available_key_slots")))
        key_slot = _int_value(result.metadata.get("key_slot"))
        if key_slot:
            assigned_key_slots.append(key_slot)
        max_retry_attempts = max(max_retry_attempts, _int_value(result.metadata.get("max_retry_attempts")))
        retry_count = _int_value(result.metadata.get("retry_count"))
        first_error_type = str(result.metadata.get("first_error_type", "none"))
        if first_error_type in {"timeout", "api_503_high_demand", "api_500_internal", "api_429_rate_limit"}:
            retryable_error_count += 1
        if retry_count:
            retried_worker_count += 1
            if result.backend == "live" and not result.fallback_used:
                retry_success_count += 1
            if result.fallback_used:
                retry_failure_count += 1
                fallback_after_retry_count += 1
        if result.backend == "stub" and requested in {"live", "auto"}:
            if result.fallback_used:
                fallback_stub_count += 1
            else:
                policy_routing_stub_count += 1
    return {
        "backend_mix": backend_mix,
        "routing_policy": {
            "mode": first_metadata.get("policy_mode", "unknown"),
            "max_live_workers": first_metadata.get("max_live_workers", first_metadata.get("live_worker_limit", 0)),
            "fallback_allowed": first_metadata.get("fallback_allowed", False),
            "source": first_metadata.get("policy_source", "unknown"),
            "require_explicit_live": first_metadata.get("require_explicit_live", False),
            "cost_guard_enabled": first_metadata.get("cost_guard_enabled", True),
            "full_live_explicit": first_metadata.get("policy_mode") == "full_live"
            and "TLH_ALLOW_FULL_LIVE" in str(first_metadata.get("policy_source", "")),
        },
        "key_pool": _key_pool_summary(available_key_slots, assigned_key_slots),
        "retry_policy": {
            "enabled": max_retry_attempts > 0,
            "max_retry_attempts": max_retry_attempts,
            "retryable_error_count": retryable_error_count,
            "retried_worker_count": retried_worker_count,
            "retry_success_count": retry_success_count,
            "retry_failure_count": retry_failure_count,
            "fallback_after_retry_count": fallback_after_retry_count,
        },
        "fallback_used": any(result.fallback_used for result in results),
        "policy_routing_stub_count": policy_routing_stub_count,
        "fallback_stub_count": fallback_stub_count,
    }


def _routing_lines(routing: dict) -> list[str]:
    policy = routing.get("routing_policy", {})
    mix = routing.get("backend_mix", {})
    retry = routing.get("retry_policy", {})
    return [
        f"policy mode: {policy.get('mode', 'unknown')}",
        f"max live workers: {policy.get('max_live_workers', 'unknown')}",
        f"fallback allowed: {policy.get('fallback_allowed', 'unknown')}",
        f"policy source: {policy.get('source', 'unknown')}",
        f"full_live explicit opt-in: {policy.get('full_live_explicit', False)}",
        f"live WorkerResults: {mix.get('live', 0)}",
        f"stub WorkerResults: {mix.get('stub', 0)}",
        f"policy routing stub count: {routing.get('policy_routing_stub_count', 0)}",
        f"fallback stub count: {routing.get('fallback_stub_count', 0)}",
        f"available key slots: {routing.get('key_pool', {}).get('available_key_slots', 0)}",
        f"assigned key slots: {_slot_list(routing.get('key_pool', {}).get('assigned_key_slots', []))}",
        f"distinct key slots used: {routing.get('key_pool', {}).get('distinct_key_slots_used', 0)}",
        f"single-key mode: {routing.get('key_pool', {}).get('single_key_mode', True)}",
        f"retry policy enabled: {retry.get('enabled', False)}",
        f"max retry attempts: {retry.get('max_retry_attempts', 0)}",
        f"retryable error count: {retry.get('retryable_error_count', 0)}",
        f"retried worker count: {retry.get('retried_worker_count', 0)}",
        f"retry success count: {retry.get('retry_success_count', 0)}",
        f"retry failure count: {retry.get('retry_failure_count', 0)}",
        f"fallback after retry count: {retry.get('fallback_after_retry_count', 0)}",
    ]


def _key_pool_summary(available_key_slots: int, assigned_key_slots: list[int]) -> dict:
    distinct = sorted(set(assigned_key_slots))
    return {
        "available_key_slots": available_key_slots,
        "assigned_key_slots": distinct,
        "distinct_key_slots_used": len(distinct),
        "single_key_mode": available_key_slots <= 1,
    }


def _slot_list(slots) -> str:
    return ",".join(str(slot) for slot in slots) if slots else "none"


def _int_value(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
