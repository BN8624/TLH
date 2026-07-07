# S7 Routing Policy Dry-Run Command Review

## Goal

Add a policy-only CLI command that reports live/stub routing decisions before any worker execution or live API call.

## Base Commit

`0874679 harden live routing dry run guards`

## Modified Files

- `tlh/live_routing.py`
- `tlh/cli.py`
- `tests/test_route_dry_run_cli.py`
- `docs/CURRENT_STATE.md`
- `docs/S7_ROUTING_POLICY_DRY_RUN_COMMAND_REVIEW.md`

## Added CLI Command

```bash
python -m tlh route-dry-run
```

## Supported Options

- `--workers <count>`
- `--live-limit <count>`
- `--mode stub_only|one_live|limited_live|full_live`
- `--force-backend stub|live`
- `--allow-full-live`
- `--json`

CLI options take precedence over environment variables and safe defaults. CLI-provided policy sources are recorded as `cli:--mode`, `cli:--live-limit`, and `cli:--allow-full-live`.

## Text Output Example

```text
TLH Routing Policy Dry Run

worker_count: 11
policy_mode: limited_live
max_live_workers: 2
force_backend: none
full_live_enabled: false
allow_full_live: false
actual API call: NO
run artifacts created: NO

backend_mix:
- live: 2
- stub: 9
- fallback: 0
```

## JSON Output Example

```json
{
  "worker_count": 11,
  "policy": {
    "mode": "limited_live",
    "max_live_workers": 2,
    "source": "cli:--live-limit",
    "full_live_enabled": false,
    "allow_full_live": false
  },
  "backend_mix": {
    "live": 2,
    "stub": 9,
    "fallback": 0
  }
}
```

## Dry Run Results

- worker_count=11, `limited_live`, `--live-limit 2` -> live 2, stub 9, fallback 0.
- worker_count=11, `one_live` -> live 1, stub 10.
- worker_count=11, `stub_only` -> live 0, stub 11.
- `--force-backend stub` -> live 0, stub 11.
- `--force-backend live`, `limited_live`, `--live-limit 2` -> live 2, stub 9.
- `--mode full_live` without `--allow-full-live` -> downgraded to safe `one_live`.
- `--mode full_live --allow-full-live --workers 3` -> live 3, stub 0, dry-run only.

## Safety Review

- actual API call in `route-dry-run`: NO.
- run artifacts created: NO.
- force live bypasses limit: NO.
- force live implies full_live: NO.
- full_live default: disabled.
- invalid workers fail before artifact creation.

## S-6 Behavior Preserved

- 3/5/11 dry run tests: PASS.
- force-live guard: PASS.
- stale phrase cleanup: PASS.
- default safe mode: `one_live`.

## Verification

- `python -m compileall tlh` -> PASS.
- `python -m pytest` -> PASS, 41 tests passed.
- `python -m tlh --help` -> PASS.
- `python -m tlh init` -> PASS.
- `python -m tlh route-dry-run --workers 11 --mode limited_live --live-limit 2` -> PASS.
- `python -m tlh route-dry-run --workers 11 --mode limited_live --live-limit 2 --json` -> PASS.
- secret value scan over docs, source, and tests -> PASS, 0 matches.

## Generated Artifact Policy

- raw run artifacts committed: NO.
- API key committed: NO.
- `.env` committed: NO.

## Quality Decision

S-7 PASS candidate. The CLI exposes policy-only routing decisions in text and JSON without API calls or run artifacts.

## Next Recommended Step

Use `route-dry-run` as a preflight before future live-worker scaling runs, then add a narrow regression test for any new routing mode before enabling it.
