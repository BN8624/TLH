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


@dataclass
class LiveRoutingSimulation:
    worker_count: int
    policy: LiveRoutingPolicy
    decisions: list[LiveRoutingDecision]

    def backend_mix(self) -> dict[str, int]:
        return {
            "live": sum(1 for decision in self.decisions if decision.selected_backend == "live"),
            "stub": sum(1 for decision in self.decisions if decision.selected_backend == "stub"),
            "fallback": sum(1 for decision in self.decisions if decision.fallback_used),
        }

    def guards(self) -> dict[str, bool]:
        mix = self.backend_mix()
        force_live_requested = any(
            decision.routing_source == "env:TLH_FORCE_WORKER_BACKEND+policy" for decision in self.decisions
        )
        return {
            "force_live_bypassed_limit": force_live_requested and mix["live"] > self.policy.max_live_workers,
            "force_live_implied_full_live": force_live_requested and self.policy.mode == "full_live",
            "full_live_requires_explicit_opt_in": True,
        }

    def to_dict(self) -> dict:
        return {
            "worker_count": self.worker_count,
            "policy": {
                "mode": self.policy.mode,
                "max_live_workers": self.policy.max_live_workers,
                "source": self.policy.source,
                "full_live_enabled": self.policy.mode == "full_live",
                "allow_full_live": self.policy.mode == "full_live" and "TLH_ALLOW_FULL_LIVE" in self.policy.source,
                "reason": self.policy.reason,
            },
            "backend_mix": self.backend_mix(),
            "guards": self.guards(),
            "decisions": [
                {
                    "worker_index": decision.worker_index,
                    "requested_backend": decision.requested_backend,
                    "selected_backend": decision.selected_backend,
                    "reason": decision.routing_reason,
                    "source": decision.routing_source,
                    "live_worker_index": decision.live_worker_index,
                    "fallback_used": decision.fallback_used,
                }
                for decision in self.decisions
            ],
        }


def build_live_routing_policy(env: Mapping[str, str]) -> LiveRoutingPolicy:
    raw_mode = env.get("TLH_LIVE_ROUTING_MODE", "").strip().lower()
    raw_limit = env.get("TLH_LIVE_WORKER_LIMIT", "").strip()
    mode_source = env.get("TLH_LIVE_ROUTING_MODE_SOURCE", "env:TLH_LIVE_ROUTING_MODE")
    limit_source = env.get("TLH_LIVE_WORKER_LIMIT_SOURCE", "env:TLH_LIVE_WORKER_LIMIT")
    full_live_source = env.get("TLH_ALLOW_FULL_LIVE_SOURCE", "TLH_ALLOW_FULL_LIVE")
    allow_fallback = _truthy(env.get("TLH_GEMMA_FALLBACK_TO_STUB"), default=True)

    if raw_mode == "full_live" and not _truthy(env.get("TLH_ALLOW_FULL_LIVE"), default=False):
        return LiveRoutingPolicy(
            mode=SAFE_DEFAULT_MODE,
            max_live_workers=SAFE_DEFAULT_MAX_LIVE_WORKERS,
            require_explicit_live=True,
            allow_fallback=allow_fallback,
            cost_guard_enabled=True,
            source=mode_source,
            reason="full_live requires explicit opt-in; downgraded to one_live",
        )

    if raw_mode == "stub_only":
        return LiveRoutingPolicy(
            mode="stub_only",
            max_live_workers=0,
            require_explicit_live=False,
            allow_fallback=allow_fallback,
            cost_guard_enabled=True,
            source=mode_source,
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
            source=limit_source,
            reason=f"live worker limit set to {limit}",
        )

    if raw_mode == "one_live":
        return LiveRoutingPolicy(
            mode="one_live",
            max_live_workers=1,
            require_explicit_live=False,
            allow_fallback=allow_fallback,
            cost_guard_enabled=True,
            source=mode_source,
            reason="one_live policy selected",
        )

    if raw_mode == "full_live":
        return LiveRoutingPolicy(
            mode="full_live",
            max_live_workers=10_000,
            require_explicit_live=True,
            allow_fallback=allow_fallback,
            cost_guard_enabled=False,
            source=f"{mode_source}+{full_live_source}",
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
    force_live_requested = force_backend == "live"
    if force_backend and force_backend != "live":
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

    effective_requested = "live" if force_live_requested else requested

    if policy.mode == "stub_only":
        reason = "force live rejected by stub_only policy" if force_live_requested else "stub_only policy selected"
        return _decision(
            worker_index=worker_index,
            requested=effective_requested,
            selected="stub",
            policy=policy,
            live_worker_index=None,
            fallback_allowed=fallback_allowed,
            reason=reason,
            source="env:TLH_FORCE_WORKER_BACKEND+policy" if force_live_requested else policy.source,
        )

    wants_live = _requests_live(effective_requested, env)
    if not wants_live:
        return _decision(
            worker_index=worker_index,
            requested=effective_requested,
            selected="stub",
            policy=policy,
            live_worker_index=None,
            fallback_allowed=fallback_allowed,
            reason="requested backend does not require live",
            source="request",
        )

    if live_workers_used >= policy.max_live_workers:
        reason = "force live requested, downgraded to stub by live limit" if force_live_requested else "live worker limit reached"
        return _decision(
            worker_index=worker_index,
            requested=effective_requested,
            selected="stub",
            policy=policy,
            live_worker_index=None,
            fallback_allowed=fallback_allowed,
            reason=reason,
            source="env:TLH_FORCE_WORKER_BACKEND+policy" if force_live_requested else "policy",
        )

    reason = "force live requested, allowed within policy limit" if force_live_requested else "within live worker limit"
    return _decision(
        worker_index=worker_index,
        requested=effective_requested,
        selected="live",
        policy=policy,
        live_worker_index=live_workers_used + 1,
        fallback_allowed=fallback_allowed,
        reason=reason,
        source="env:TLH_FORCE_WORKER_BACKEND+policy" if force_live_requested else policy.source,
    )


def simulate_routing_decisions(worker_count: int, env: Mapping[str, str], requested: str | None = None) -> LiveRoutingSimulation:
    policy = build_live_routing_policy(env)
    live_workers_used = 0
    decisions: list[LiveRoutingDecision] = []
    requested_backend_value = requested or env.get("TLH_WORKER_BACKEND", "auto").strip().lower() or "auto"
    for worker_index in range(worker_count):
        decision = decide_worker_backend(
            worker_index=worker_index,
            requested=requested_backend_value,
            live_workers_used=live_workers_used,
            policy=policy,
            env=env,
        )
        if decision.selected_backend == "live":
            live_workers_used += 1
        decisions.append(decision)
    return LiveRoutingSimulation(worker_count=worker_count, policy=policy, decisions=decisions)


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
        return bool(env.get("TLH_GEMMA_API_KEY", "").strip()) or _parse_limit(
            env.get("TLH_GEMMA_KEY_POOL_AVAILABLE_SLOTS", "0")
        ) > 0
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
