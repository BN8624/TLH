# S5 Controlled Live-Worker Routing Policy Review

## Goal

Centralize live/stub/fallback routing decisions behind explicit policy and decision objects while preserving S-4 live limit behavior.

## Base Commit

`6fbac85 validate S-4 multi-live worker limit`

## Modified Files

- `tlh/live_routing.py`
- `tlh/dispatcher.py`
- `tlh/worker_pool.py`
- `tlh/merge_harness.py`
- `tlh/cli.py`
- `tests/test_live_routing_policy.py`
- `tests/test_live_worker_limit.py`
- `docs/CURRENT_STATE.md`
- `docs/S5_CONTROLLED_LIVE_ROUTING_POLICY_REVIEW.md`

## Policy

- policy mode: `limited_live` for S-4-compatible `TLH_LIVE_WORKER_LIMIT=2`.
- max live workers: 2.
- require explicit live: false for `limited_live`; true for allowed `full_live`.
- fallback allowed: true by default through `TLH_GEMMA_FALLBACK_TO_STUB`.
- policy source: `env:TLH_LIVE_WORKER_LIMIT`.
- default safe mode: `one_live`.
- full_live default: NO.

## Backend Mix

S-4 behavior is preserved by policy tests.

- live WorkerResults: 2.
- stub WorkerResults: 1.
- fallback used: NO.
- live worker limit: 2.
- policy routing stub count: 1.
- fallback stub count: 0.

## Metadata Locations

### WorkerResult

Each WorkerResult metadata records policy and decision fields.

- `policy_mode`
- `max_live_workers`
- `requested_backend`
- `selected_backend`
- `live_worker_index`
- `fallback_allowed`
- `fallback_used`
- `routing_reason`
- `routing_source`
- `policy_source`

### MergePacket

`minimality.routing` records backend mix, routing policy, policy-routed stubs, and fallback stubs.

### FinalPacket

FinalPacket renders `Backend Mix` and `Routing Policy` sections.

### CodexPrompt

CodexPrompt renders `Backend Mix` and `Routing Policy` sections so the next agent can see the policy mode and live/stub mix.

## S-4 Behavior Preserved

- `TLH_LIVE_WORKER_LIMIT=2` with three live-capable workers routes to live, live, stub.
- The third worker is policy-routed to stub with `fallback_used: false`.
- `TLH_FORCE_WORKER_BACKEND=stub` overrides policy and records the force reason.
- `full_live` is downgraded to safe `one_live` unless explicitly opted in with `TLH_ALLOW_FULL_LIVE`.

## Tests

- `python -m compileall tlh` -> PASS.
- `python -m pytest` -> PASS, 22 tests passed.
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

S-5 PASS candidate. Routing decisions are centralized, S-4 behavior is preserved, and fallback is distinct from policy-based stub routing.

## Next Recommended Step

Run a controlled policy dry run for more worker counts using the same policy object, without enabling default `full_live`.
