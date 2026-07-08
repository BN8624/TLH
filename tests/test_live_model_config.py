# live model 기본값과 CLI preflight 출력 정합성을 검증한다.

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tlh import gemma_client


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(cwd: Path, *args: str, env_overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("TLH_GEMMA_API_KEY", None)
    env.pop("TLH_GEMMA_MODEL", None)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-m", "tlh", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
    )


def test_default_live_model_is_canonical() -> None:
    model, source = gemma_client.model_from_env({})

    assert model == "gemma-4-31b-it"
    assert source == "default"
    assert gemma_client.DEFAULT_MODEL == "gemma-4-31b-it"


def test_env_override_is_respected() -> None:
    model, source = gemma_client.model_from_env({"TLH_GEMMA_MODEL": "custom-model"})

    assert model == "custom-model"
    assert source == "env"


def test_route_dry_run_reports_model_safely(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "route-dry-run", "--workers", "22", "--mode", "limited_live", "--live-limit", "5", "--json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["live_model"] == "gemma-4-31b-it"
    assert payload["model_source"] == "default"
    assert "API_KEY" not in result.stdout


def test_route_dry_run_reports_env_model_source(tmp_path: Path) -> None:
    result = run_cli(
        tmp_path,
        "route-dry-run",
        "--workers",
        "22",
        "--mode",
        "limited_live",
        "--live-limit",
        "5",
        "--json",
        env_overrides={"TLH_GEMMA_MODEL": "custom-model"},
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["live_model"] == "custom-model"
    assert payload["model_source"] == "env"


def test_help_and_init_do_not_mention_stale_default(tmp_path: Path) -> None:
    help_result = run_cli(tmp_path, "--help")
    init_result = run_cli(tmp_path, "init")

    assert help_result.returncode == 0
    assert init_result.returncode == 0
    combined = help_result.stdout + init_result.stdout
    assert "gemma-4-31b-it" in combined
    assert "gemma-3-27b-it" not in combined


def test_docs_stale_reference_only_historical() -> None:
    active_paths = [
        REPO_ROOT / "tlh",
        REPO_ROOT / "tests",
        REPO_ROOT / "docs",
    ]
    matches: list[tuple[Path, str]] = []
    for base in active_paths:
        for path in base.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if path.name == "test_live_model_config.py":
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                if "gemma-3-27b-it" in line:
                    matches.append((path, line.lower()))

    assert matches
    assert all(
        "outdated" in line or "stale" in line or "historical" in line or "model-not-found" in line
        for _path, line in matches
    )


def test_secret_safety() -> None:
    serialized = json.dumps({"model": gemma_client.DEFAULT_MODEL, "model_source": "default"})

    assert "gemma-4-31b-it" in serialized
    assert "API_KEY" not in serialized
