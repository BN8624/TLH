# Merge와 final 산출물의 과잉 범위를 점검한다.

from __future__ import annotations

from .schemas import MinimalityCheck


def check_merge(run_id: str, kept: list[str], dropped: list[str]) -> MinimalityCheck:
    return MinimalityCheck(
        check_id=f"{run_id}-MIN001",
        target_type="merge_packet",
        dropped=dropped,
        merged=[],
        deferred=["live Gemma integration", "Obsidian plugin", "automatic Codex execution"],
        kept=kept,
        reason="MVP keeps only items needed for an attachable handoff packet.",
    )
