# Gemini API key pool slot을 안전하게 수집하고 live worker에 배정한다.

from __future__ import annotations

from dataclasses import dataclass
import os
import re
import threading
import time
from pathlib import Path
from typing import Callable, Mapping


KEY_SLOT_PATTERN = re.compile(r"^GOOGLE_API_KEY_(\d+)$")
TRANSIENT_COOLDOWN_ERRORS = {"api_429_rate_limit", "api_503_high_demand", "api_500_internal", "timeout"}


@dataclass(frozen=True)
class KeyLease:
    key_slot: int
    key_value: str
    selection_reason: str


def collect_gemini_key_slots(env: Mapping[str, str] | None = None, env_file: Path | None = None) -> dict[int, str]:
    slots: dict[int, str] = {}
    if env_file and env_file.exists():
        slots.update(_read_env_file_slots(env_file))
    env = env or os.environ
    for name, value in env.items():
        slot = _slot_number(name)
        if slot is not None and value.strip():
            slots[slot] = value.strip()
    return dict(sorted(slots.items()))


def assign_key_slot_for_live_worker(live_worker_index: int, key_slots: Mapping[int, str]) -> int | None:
    if live_worker_index <= 0 or not key_slots:
        return None
    slots = sorted(key_slots)
    return slots[(live_worker_index - 1) % len(slots)]


def safe_key_pool_summary(available_slots: int, assigned_slots: list[int]) -> dict[str, int | bool | list[int]]:
    distinct = sorted(set(assigned_slots))
    return {
        "available_key_slots": available_slots,
        "assigned_key_slots": distinct,
        "distinct_key_slots_used": len(distinct),
        "single_key_mode": available_slots <= 1,
    }


class KeyHealthPool:
    def __init__(
        self,
        key_slots: Mapping[int, str],
        *,
        cooldown_seconds: float = 60.0,
        time_fn: Callable[[], float] | None = None,
    ) -> None:
        self._slots = sorted(slot for slot, value in key_slots.items() if value)
        self._values = {slot: key_slots[slot] for slot in self._slots}
        self._cooldown_seconds = max(0.0, cooldown_seconds)
        self._time_fn = time_fn or time.monotonic
        self._next_index = 0
        self._lock = threading.Lock()
        self._cooldown_until_by_slot: dict[int, float] = {}
        self._disabled_slots: set[int] = set()
        self._lease_count_by_slot: dict[int, int] = {}
        self._error_count_by_slot: dict[int, int] = {}
        self._last_used_at_by_slot: dict[int, float] = {}
        self._last_failure_by_slot: dict[int, str] = {}

    @property
    def pool_size(self) -> int:
        return len(self._slots)

    def select_key(
        self,
        *,
        worker_index: int | None = None,
        attempt_index: int = 1,
        avoid_slots: set[int] | None = None,
        error_context: str | None = None,
    ) -> KeyLease | None:
        del worker_index, attempt_index, error_context
        avoid_slots = avoid_slots or set()
        with self._lock:
            if not self._slots:
                return None
            slot = self._select_slot_locked(avoid_slots)
            if slot is None and avoid_slots:
                slot = self._select_slot_locked(set())
            if slot is None:
                return None
            self._lease_count_by_slot[slot] = self._lease_count_by_slot.get(slot, 0) + 1
            self._last_used_at_by_slot[slot] = self._time_fn()
            return KeyLease(key_slot=slot, key_value=self._values[slot], selection_reason="round_robin_health_aware")

    def record_success(self, key_slot: int | None) -> None:
        if not key_slot:
            return
        with self._lock:
            self._last_failure_by_slot.pop(key_slot, None)

    def record_failure(self, key_slot: int | None, error_type: str) -> None:
        if not key_slot:
            return
        with self._lock:
            self._error_count_by_slot[key_slot] = self._error_count_by_slot.get(key_slot, 0) + 1
            self._last_failure_by_slot[key_slot] = error_type
            if error_type == "api_auth_error":
                self._disabled_slots.add(key_slot)
                self._cooldown_until_by_slot.pop(key_slot, None)
            elif error_type in TRANSIENT_COOLDOWN_ERRORS:
                self._cooldown_until_by_slot[key_slot] = self._time_fn() + self._cooldown_seconds

    def snapshot_summary(self) -> dict:
        with self._lock:
            active_cooldowns = self._active_cooldown_slots_locked()
            return {
                "key_pool_mode": "rotating_health_pool",
                "key_selection_policy": "round_robin_health_aware",
                "key_rotation_enabled": True,
                "key_cooldown_enabled": True,
                "key_pool_size": len(self._slots),
                "available_key_slots": len(self._slots),
                "disabled_key_count": len(self._disabled_slots),
                "cooldown_key_count": len(active_cooldowns),
                "disabled_key_slots": sorted(self._disabled_slots),
                "cooldown_key_slots": active_cooldowns,
                "lease_count_by_slot": {str(key): self._lease_count_by_slot[key] for key in sorted(self._lease_count_by_slot)},
                "error_count_by_slot": {str(key): self._error_count_by_slot[key] for key in sorted(self._error_count_by_slot)},
                "key_values_recorded": False,
                "pooled": True,
                "fixed_worker_assignment": False,
                "single_key_mode": len(self._slots) <= 1,
            }

    def _select_slot_locked(self, avoid_slots: set[int]) -> int | None:
        active_cooldowns = set(self._active_cooldown_slots_locked())
        candidates = [
            slot
            for slot in self._slots
            if slot not in self._disabled_slots and slot not in active_cooldowns and slot not in avoid_slots
        ]
        if not candidates:
            return None
        for offset in range(len(self._slots)):
            candidate = self._slots[(self._next_index + offset) % len(self._slots)]
            if candidate in candidates:
                self._next_index = (self._slots.index(candidate) + 1) % len(self._slots)
                return candidate
        return candidates[0]

    def _active_cooldown_slots_locked(self) -> list[int]:
        now = self._time_fn()
        expired = [slot for slot, until in self._cooldown_until_by_slot.items() if until <= now]
        for slot in expired:
            self._cooldown_until_by_slot.pop(slot, None)
        return sorted(self._cooldown_until_by_slot)


def _read_env_file_slots(path: Path) -> dict[int, str]:
    slots: dict[int, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        slot = _slot_number(name.strip())
        value = _clean_value(value)
        if slot is not None and value:
            slots[slot] = value
    return slots


def _slot_number(name: str) -> int | None:
    match = KEY_SLOT_PATTERN.match(name)
    if not match:
        return None
    return int(match.group(1))


def _clean_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].strip()
    return value
