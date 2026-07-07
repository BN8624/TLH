# S2 Live Gemma Adapter Review

## Goal

Add live Gemma worker adapter while preserving stub-safe MVP flow.

## Changed Files

- `tlh/gemma_client.py`
- `tlh/worker_pool.py`
- `tlh/schemas.py`
- `tests/test_smoke_cli.py`
- `tests/test_live_adapter.py`
- `docs/CURRENT_STATE.md`

## Backend Modes

- stub: Always uses deterministic stub WorkerResult generation.
- auto: Uses live Gemma when `TLH_GEMMA_API_KEY` is configured, otherwise falls back to stub. Live errors fall back to stub by default in auto mode.
- live: Uses live Gemma only. Missing configuration or live failure raises a worker backend error unless `TLH_GEMMA_FALLBACK_TO_STUB=true`.

## Environment Variables

- `TLH_WORKER_BACKEND`: Selects `stub`, `auto`, or `live`.
- `TLH_GEMMA_API_KEY`: Read from process environment only. Never stored in repo.
- `TLH_GEMMA_MODEL`: Optional model name. Defaults to `gemma-3-27b-it`.
- `TLH_GEMMA_TIMEOUT_SECONDS`: Optional live call timeout. Defaults to `60`.
- `TLH_GEMMA_MAX_OUTPUT_TOKENS`: Optional max output tokens. Defaults to `4096`.
- `TLH_GEMMA_FALLBACK_TO_STUB`: Allows stub fallback after live failure when true.

## Verification

- `python -m compileall tlh` -> PASS.
- `python -m pytest` -> PASS.
- `python -m tlh --help` -> PASS.
- `python -m tlh init` -> PASS.
- stub dry run -> PASS through existing smoke and quality tests.
- auto fallback dry run -> PASS with run `run-20260707-024852`.
- mock live adapter test -> PASS.
- real live smoke -> NOT RUN. No user approval for live smoke, and `TLH_GEMMA_API_KEY` was not present in the shell check.

## Safety Review

- API key stored in repo: NO.
- API key printed in logs: NO.
- tests require network: NO.
- stub fallback preserved: YES.
- AI_WORKFLOW_KIT duplicated: NO.

## Decision

S-2 PASS. Ready for one controlled live worker run.

## Next Recommended Step

Run S-3 controlled one-live-worker run only after the user provides explicit approval and confirms `TLH_GEMMA_API_KEY` is already set in the shell environment.
