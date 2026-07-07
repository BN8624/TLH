# Gemini API key pool slot을 안전하게 수집하고 live worker에 배정한다.

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Mapping


KEY_SLOT_PATTERN = re.compile(r"^GOOGLE_API_KEY_(\d+)$")


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
