# Gemini key pool slot 수집과 live worker 배정을 검증한다.

from __future__ import annotations

from pathlib import Path

from tlh.key_pool import assign_key_slot_for_live_worker, collect_gemini_key_slots, safe_key_pool_summary


def test_collect_key_slots_from_env_file_without_printing_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "GOOGLE_API_KEY_2=SECRET_TWO",
                "GOOGLE_API_KEY_1='SECRET_ONE'",
                "IGNORED=value",
                "# GOOGLE_API_KEY_3=COMMENTED",
            ]
        ),
        encoding="utf-8",
    )

    slots = collect_gemini_key_slots({}, env_file)

    assert sorted(slots) == [1, 2]
    assert slots[1] == "SECRET_ONE"
    assert slots[2] == "SECRET_TWO"


def test_assign_key_slot_uses_distinct_slots_before_wrapping() -> None:
    slots = {slot: f"SECRET_{slot}" for slot in range(1, 23)}
    assigned = [assign_key_slot_for_live_worker(index, slots) for index in range(1, 12)]

    assert assigned == list(range(1, 12))
    summary = safe_key_pool_summary(len(slots), [slot for slot in assigned if slot is not None])
    assert summary["available_key_slots"] == 22
    assert summary["assigned_key_slots"] == list(range(1, 12))
    assert summary["distinct_key_slots_used"] == 11
    assert summary["single_key_mode"] is False
