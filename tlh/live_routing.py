# TLH live/stub worker 라우팅 정책과 결정 결과를 계산한다.

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping

from .schemas import TaskCard


SAFE_DEFAULT_MODE = "one_live"
SAFE_DEFAULT_MAX_LIVE_WORKERS = 1


@dataclass
class LiveRoutingPolicy:
    mode: str
    max_live_workers: int
    require_explicit_live: bool
    allow_fallback: bool
    cost_guard_enabled: bool
    source: str
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LiveRoutingDecision:
    worker_index: int
    requested_backend: str
    selected_backend: str
    policy_mode: str
    max_live_workers: int
    live_worker_index: int | None
    fallback_allowed: bool
    fallback_used: bool
    routing_reason: str
    routing_source: str
    policy_source: str
    require_explicit_live: bool
    cost_guard_enabled: bool

    def to_metadata(self) -> dict:
        data = asdict(self)
        data["backend"] = self.selected_backend
        data["live_worker_limit"] = self.max_live_workers
        return data


def build_live_routing_policy(env: Mapping[str, str]) -> LiveRoutingPolicy:
    raw_mode = env.get("TLH_LIVE_ROUTING_MODE", "").strip().lower()
    raw_limit = env.get("TLH_LIVE_WORKER_LIMIT", "").strip()
    allow_fallback = _truthy(env.get("TLH_GEMMA_FALLBACK_TO_STUB"), default=True)

    if raw_mode == "full_live" and not _truthy(env.get("TLH_ALLOW_FULL_LIVE"), default=False):
        return LiveRoutingPolicy(
            mode=SAFE_DEFAULT_MODE,
            max_live_workers=SAFE_DEFAULT_MAX_LIVE_WORKERS,
            require_explicit_live=True,
            allow_fallback=allow_fallback,
            cost_guard_enabled=True,
            source="env:TLH_LIVE_ROUTING_MODE",
            reason="full_live requires explicit opt-in; downgraded to one_live",
        )

    if raw_mode == "stub_only":
        return LiveRoutingPolicy(
            mode="stub_only",
            max_live_workers=0,
            require_explicit_live=False,
            allow_fallback=allow_fallback,
            cost_guard_enabled=True,
            source="env:TLH_LIVE_ROUTING_MODE",
            reason="stub_only policy selected",
        )

    if raw_limit:
        limit = _parse_limit(raw_limit)
        return LiveRoutingPolicy(
            mode="stub_only" if limit == 0 else "limited_live",
            max_live_workers=limit,
            require_explicit_live=False,
            allow_fallback=allow_fallback,
            cost_guard_enabled=True,
            source="env:TLH_LIVE_WORKER_LIMIT",
            reason=f"live worker limit set to {limit}",
        )

    if raw_mode == "one_live":
        return LiveRoutingPolicy(
            mode="one_live",
            max_live_workers=1,
            require_explicit_live=False,
            allow_fallback=allow_fallback,
            cost_guard_enabled=True,
            source="env:TLH_LIVE_ROUTING_MODE",
            reason="one_live policy selected",
        )

    if raw_mode == "full_live":
        return LiveRoutingPolicy(
            mode="full_live",
            max_live_workers=10_000,
            require_explicit_live=True,
            allow_fallback=allow_fallback,
            cost_guard_enabled=False,
            source="env:TLH_LIVE_ROUTING_MODE+TLH_ALLOW_FULL_LIVE",
            reason="full_live explicitly enabled",
        )

    return LiveRoutingPolicy(
        mode=SAFE_DEFAULT_MODE,
        max_live_workers=SAFE_DEFAULT_MAX_LIVE_WORKERS,
        require_explicit_live=False,
        allow_fallback=allow_fallback,
        cost_guard_enabled=True,
        source="default",
        reason="safe default one_live policy",
    )


def requested_backend(card: TaskCard, env: Mapping[str, str]) -> str:
    return card.backend_hint.strip().lower() or env.get("TLH_WORKER_BACKEND", "stub").strip().lower() or "stub"


def decide_worker_backend(
    *,
    worker_index: int,
    requested: str,
    live_workers_used: int,
    policy: LiveRoutingPolicy,
    env: Mapping[str, str],
) -> LiveRoutingDecision:
    force_backend = env.get("TLH_FORCE_WORKER_BACKEND", "").strip().lower()
    fallback_allowed = policy.allow_fallback
    if force_backend:
        return _decision(
            worker_index=worker_index,
            requested=requested,
            selected=force_backend,
            policy=policy,
            live_worker_index=None,
            fallback_allowed=fallback_allowed,
            reason=f"force backend selected: {force_backend}",
            source="env:TLH_FORCE_WORKER_BACKEND",
        )

    if policy.mode == "stub_only":
        return _decision(
            worker_index=worker_index,
            requested=requested,
            selected="stub",
            policy=policy,
            live_worker_index=None,
            fallback_allowed=fallback_allowed,
            reason="stub_only policy selected",
            source=policy.source,
        )

    wants_live = _requests_live(requested, env)
    if not wants_live:
        return _decision(
            worker_index=worker_index,
            requested=requested,
            selected="stub",
            policy=policy,
            live_worker_index=None,
            fallback_allowed=fallback_allowed,
            reason="requested backend does not require live",
            source="request",
        )

    if live_workers_used >= policy.max_live_workers:
        return _decision(
            worker_index=worker_index,
            requested=requested,
            selected="stub",
            policy=policy,
            live_worker_index=None,
            fallback_allowed=fallback_allowed,
            reason="live worker limit reached",
            source="policy",
        )

    return _decision(
        worker_index=worker_index,
        requested=requested,
        selected="live",
        policy=policy,
        live_worker_index=live_workers_used + 1,
        fallback_allowed=fallback_allowed,
        reason="within live worker limit",
        source=policy.source,
    )


def _decision(
    *,
    worker_index: int,
    requested: str,
    selected: str,
    policy: LiveRoutingPolicy,
    live_worker_index: int | None,
    fallback_allowed: bool,
    reason: str,
    source: str,
) -> LiveRoutingDecision:
    return LiveRoutingDecision(
        worker_index=worker_index,
        requested_backend=requested,
        selected_backend=selected,
        policy_mode=policy.mode,
        max_live_workers=policy.max_live_workers,
        live_worker_index=live_worker_index,
        fallback_allowed=fallback_allowed,
        fallback_used=False,
        routing_reason=reason,
        routing_source=source,
        policy_source=policy.source,
        require_explicit_live=policy.require_explicit_live,
        cost_guard_enabled=policy.cost_guard_enabled,
    )


def _requests_live(requested: str, env: Mapping[str, str]) -> bool:
    if requested == "live":
        return True
    if requested == "auto":
        return bool(env.get("TLH_GEMMA_API_KEY", "").strip())
    return False


def _parse_limit(raw: str) -> int:
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def _truthy(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
