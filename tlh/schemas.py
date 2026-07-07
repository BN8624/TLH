# TLH MVP에서 주고받는 핵심 데이터 구조를 정의한다.

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass
class TaskCard:
    task_id: str
    run_id: str
    loop_index: int
    title: str
    goal: str
    worker_role: str
    input_context: list[str] = field(default_factory=list)
    expected_output: str = ""
    attach_point: str = ""
    dependencies: list[str] = field(default_factory=list)
    merge_key: str = ""
    topology_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkerResult:
    task_id: str
    worker_id: str
    summary: str
    findings: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    attach_notes: list[str] = field(default_factory=list)
    stub_generated: bool = True
    live_generated: bool = False
    backend: str = "stub"
    model: str = ""
    fallback_used: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MinimalityCheck:
    check_id: str
    target_type: str
    dropped: list[str] = field(default_factory=list)
    merged: list[str] = field(default_factory=list)
    deferred: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MergePacket:
    merge_id: str
    run_id: str
    loop_index: int
    merged_tasks: list[str] = field(default_factory=list)
    confirmed_points: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    dropped_items: list[str] = field(default_factory=list)
    attach_success: bool = False
    updated_artifact_version: int = 0
    continuity_check: str = ""
    minimality: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LoopDecision:
    run_id: str
    loop_index: int
    decision: Literal[
        "next_slice",
        "targeted_verifier",
        "user_question_needed",
        "stop_and_finalize",
        "failed_to_merge",
    ]
    reason: str
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FinalPacket:
    run_id: str
    goal: str
    current_state: str
    confirmed_assumptions: list[str] = field(default_factory=list)
    scope: list[str] = field(default_factory=list)
    out_of_scope: list[str] = field(default_factory=list)
    execution_steps: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)
    handoff_prompt: str = ""
    user_decision_points: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContextRequest:
    request_id: str
    run_id: str
    purpose: str
    target_paths: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContextPacket:
    packet_id: str
    request_id: str
    run_id: str
    summaries: list[str] = field(default_factory=list)
    source_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionHint:
    hint_id: str
    run_id: str
    command: str
    purpose: str
    expected_output: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def from_dict(model: type[Any], data: dict[str, Any]) -> Any:
    field_names = {field.name for field in model.__dataclass_fields__.values()}
    return model(**{key: value for key, value in data.items() if key in field_names})
