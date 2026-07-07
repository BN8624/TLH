# TLH route-dry-run CLI가 API 호출과 artifact 없이 routing decision만 출력하는지 검증한다.

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_route(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("TLH_GEMMA_API_KEY", None)
    return subprocess.run(
        [sys.executable, "-m", "tlh", "route-dry-run", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
    )


def test_cli_dry_run_limited_live_eleven_workers(tmp_path: Path) -> None:
    result = run_route(tmp_path, "--workers", "11", "--mode", "limited_live", "--live-limit", "2")

    assert result.returncode == 0
    assert "- live: 2" in result.stdout
    assert "- stub: 9" in result.stdout
    assert "- fallback: 0" in result.stdout
    assert "actual API call: NO" in result.stdout
    assert "run artifacts created: NO" in result.stdout


def test_cli_dry_run_one_live(tmp_path: Path) -> None:
    result = run_route(tmp_path, "--workers", "11", "--mode", "one_live")

    assert result.returncode == 0
    assert "- live: 1" in result.stdout
    assert "- stub: 10" in result.stdout


def test_cli_dry_run_stub_only(tmp_path: Path) -> None:
    result = run_route(tmp_path, "--workers", "11", "--mode", "stub_only")

    assert result.returncode == 0
    assert "- live: 0" in result.stdout
    assert "- stub: 11" in result.stdout


def test_cli_force_stub(tmp_path: Path) -> None:
    result = run_route(tmp_path, "--workers", "11", "--force-backend", "stub")

    assert result.returncode == 0
    assert "- live: 0" in result.stdout
    assert "- stub: 11" in result.stdout
    assert "force backend selected: stub" in result.stdout


def test_cli_force_live_cannot_bypass_limit(tmp_path: Path) -> None:
    result = run_route(
        tmp_path,
        "--workers",
        "11",
        "--mode",
        "limited_live",
        "--live-limit",
        "2",
        "--force-backend",
        "live",
    )

    assert result.returncode == 0
    assert "- live: 2" in result.stdout
    assert "- stub: 9" in result.stdout
    assert "force_live_bypasses_limit: NO" in result.stdout
    assert "force live requested, downgraded to stub by live limit" in result.stdout


def test_cli_force_live_cannot_imply_full_live(tmp_path: Path) -> None:
    result = run_route(tmp_path, "--workers", "11", "--force-backend", "live")

    assert result.returncode == 0
    assert "full_live_enabled: false" in result.stdout
    assert "force_live_implies_full_live: NO" in result.stdout
    assert "- live: 1" in result.stdout


def test_cli_full_live_requires_explicit_opt_in_safe_downgrade(tmp_path: Path) -> None:
    result = run_route(tmp_path, "--workers", "11", "--mode", "full_live")

    assert result.returncode == 0
    assert "policy_mode: one_live" in result.stdout
    assert "full_live_enabled: false" in result.stdout
    assert "- live: 1" in result.stdout


def test_cli_explicit_full_live_succeeds_in_dry_run_only(tmp_path: Path) -> None:
    result = run_route(tmp_path, "--workers", "3", "--mode", "full_live", "--allow-full-live")

    assert result.returncode == 0
    assert "policy_mode: full_live" in result.stdout
    assert "full_live_enabled: true" in result.stdout
    assert "- live: 3" in result.stdout
    assert "actual API call: NO" in result.stdout


def test_cli_json_output(tmp_path: Path) -> None:
    result = run_route(tmp_path, "--workers", "11", "--mode", "limited_live", "--live-limit", "2", "--json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["worker_count"] == 11
    assert payload["backend_mix"]["live"] == 2
    assert payload["backend_mix"]["stub"] == 9
    assert payload["backend_mix"]["fallback"] == 0
    assert payload["policy"]["mode"] == "limited_live"
    assert payload["policy"]["source"] == "cli:--live-limit"
    assert payload["guards"]["force_live_bypassed_limit"] is False


def test_cli_json_output_includes_safe_key_pool_summary(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(f"GOOGLE_API_KEY_{slot}=SECRET_{slot}" for slot in range(1, 23)),
        encoding="utf-8",
    )

    result = run_route(tmp_path, "--workers", "11", "--mode", "limited_live", "--live-limit", "11", "--json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["backend_mix"]["live"] == 11
    assert payload["key_pool"]["available_key_slots"] == 22
    assert payload["key_pool"]["assigned_key_slots"] == list(range(1, 12))
    assert payload["key_pool"]["distinct_key_slots_used"] == 11
    assert payload["key_pool"]["single_key_mode"] is False
    assert "SECRET_" not in result.stdout


def test_cli_invalid_workers_fails_without_artifacts(tmp_path: Path) -> None:
    result = run_route(tmp_path, "--workers", "0")

    assert result.returncode != 0
    assert "--workers must be greater than 0" in result.stderr
    assert not (tmp_path / "machine").exists()
    assert not (tmp_path / "vault").exists()


def test_route_dry_run_does_not_create_run_artifacts(tmp_path: Path) -> None:
    result = run_route(tmp_path, "--workers", "11", "--mode", "limited_live", "--live-limit", "2")

    assert result.returncode == 0
    assert not (tmp_path / "machine").exists()
    assert not (tmp_path / "vault").exists()
