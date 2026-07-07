# S6 Controlled Routing Dry Run Review

## Goal

Validate S-5 routing policy behavior across worker counts 3, 5, and 11, harden force-live guards, and remove stale stub-only output language.

## Base Commit

`1c8fdac centralize live worker routing policy`

## Modified Files

- `tlh/live_routing.py`
- `tlh/worker_pool.py`
- `tlh/merge_harness.py`
- `tlh/cli.py`
- `tests/test_live_routing_policy.py`
- `docs/CURRENT_STATE.md`
- `docs/S6_CONTROLLED_ROUTING_DRY_RUN_REVIEW.md`

## Dry Run Worker Counts

- worker_count=3, `limited_live`, max_live_workers=2 -> live 2, stub 1, fallback 0.
- worker_count=5, `limited_live`, max_live_workers=2 -> live 2, stub 3, fallback 0.
- worker_count=11, `limited_live`, max_live_workers=2 -> live 2, stub 9, fallback 0.
- worker_count=11, `one_live` -> live 1, stub 10, fallback 0.
- worker_count=11, `stub_only` -> live 0, stub 11, fallback 0.

All worker-count checks are routing dry runs and do not call the live API.

## Force-Live Guard

- `TLH_FORCE_WORKER_BACKEND=stub` remains absolute and routes every worker to stub.
- `TLH_FORCE_WORKER_BACKEND=live` is treated as a live request, not as permission to bypass policy.
- With `TLH_FORCE_WORKER_BACKEND=live`, `limited_live`, and max_live_workers=2, worker_count=11 routes to live 2 and stub 9.
- Over-limit force-live decisions record `force live requested, downgraded to stub by live limit`.
- `TLH_FORCE_WORKER_BACKEND=live` alone does not imply `full_live`; default policy remains `one_live`.

## Full-Live Explicit Opt-In

- `full_live` is still downgraded to safe `one_live` without explicit opt-in.
- The test-only explicit path requires `TLH_LIVE_ROUTING_MODE=full_live` and `TLH_ALLOW_FULL_LIVE=1`.
- Metadata records the explicit source through `policy_source`.

## Stale Phrase Cleanup

FinalPacket and CodexPrompt no longer render stale mixed-mode phrases that imply a purely stub-generated skeleton or a single stub-worker slice.

Replacement language describes a `policy-routed worker mix`.

## Metadata Status

### WorkerResult

WorkerResult metadata preserves:

- requested backend.
- selected backend.
- policy mode.
- max live workers.
- live worker index.
- routing source.
- routing reason.
- fallback allowed.
- fallback used.

### FinalPacket

FinalPacket includes Backend Mix and Routing Policy sections.

### CodexPrompt

CodexPrompt includes Backend Mix and Routing Policy sections, including full_live explicit opt-in status.

## S-5 Behavior Preserved

- `TLH_LIVE_WORKER_LIMIT=2` still routes live 2 and remaining workers to policy-routed stub.
- Policy-routed stubs are not fallback stubs.
- `fallback_used` remains false for limit-based stub routing.
- default safe mode remains `one_live`.
- full_live default remains disabled.

## Verification

- `python -m compileall tlh` -> PASS.
- `python -m pytest` -> PASS, 30 tests passed.
- `python -m tlh --help` -> PASS.
- `python -m tlh init` -> PASS.
- secret value scan over docs, source, and tests -> PASS, 0 matches.

## Safety Review

- API key committed: NO.
- API key printed: NO.
- raw env dumped: NO.
- `.env` committed: NO.
- raw run artifacts committed: NO.

## Quality Decision

S-6 PASS candidate. Routing dry runs pass across 3, 5, and 11 workers; force-live cannot bypass live limits or imply full_live; stale mixed-mode wording is removed from generated handoff outputs.

## Next Recommended Step

Run an S-7 policy-only scale simulation or implement a CLI-visible dry-run command that reports routing decisions without invoking live workers.
