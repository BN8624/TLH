# CURRENT_STATE.md

## Status

TLH MVP skeleton is implemented.

S-0 stabilization is complete.
S-1 stub dry run completed with PARTIAL quality.
S-1Q merge and final quality fix completed with PASS quality.
S-2 live Gemma adapter is implemented with stub-safe fallback.
S-3 controlled one-live-worker run completed with PASS quality.
S-4 controlled multi-live limit dry run completed with PASS quality.
S-5 controlled live-worker routing policy is implemented with PASS-candidate tests.
S-6 controlled routing policy dry run and guard hardening completed with PASS-candidate tests.
S-7 routing policy dry-run CLI command is implemented with PASS-candidate tests.

The project direction is defined.
AICO is deprecated and must not be used as the architecture base.
AI_WORKFLOW_KIT exists as a separate global workflow layer and must not be duplicated inside TLH.
TLH completion reports should include a short `Tooling` block that records which AI_WORKFLOW_KIT components were actually used, which were not used, and why.
Serena MCP is `USED` only when it is used for code structure, symbol, reference, or impact-range work; status checks are `AVAILABLE_ONLY`.

---

## Canon Files

Primary routing document.

```text
docs\TLH_INDEX.md
```

Primary canon document.

```text
docs\TLH_CANON.md
```

Implementation plan.

```text
docs\TLH_MVP_PLAN.md
```

Implementation prompt.

```text
docs\TLH_IMPLEMENTATION_PROMPT.md
```

---

## Current Goal

Prepare to use `route-dry-run` as a preflight before future live-worker scaling runs.

S-3 proved that one TaskCard can run live with `gemma-4-31b-it` while the remaining TaskCard stays stub-safe.
S-4 proved that two TaskCards can run live with `gemma-4-31b-it` while remaining TaskCards stay stub-safe under `TLH_LIVE_WORKER_LIMIT=2`.
S-5 centralizes live/stub decisions in `tlh.live_routing` and records policy decisions in WorkerResult, MergePacket, FinalPacket, and CodexPrompt outputs.
S-6 verifies worker counts 3, 5, and 11 without live API calls, hardens force-live so it cannot bypass live limits, and removes stale stub-only language from generated handoff outputs.
S-7 adds `python -m tlh route-dry-run` for policy-only text and JSON routing previews without live API calls or run artifacts.
S-9 Controlled Live-5 Trial completed with PARTIAL quality: run_id `run-20260707-080817`, preflight live 5 / stub 6 / fallback 0, actual live 3 / stub 8 / fallback 2, cause two live calls timed out at 120s, decision retry live-limit 5 with `TLH_GEMMA_TIMEOUT_SECONDS=300`, raw artifacts ignored and not committed.
S-9R Controlled Live-5 Retry with Extended Timeout completed with PASS quality: run_id `run-20260707-113239`, timeout 300s, preflight live 5 / stub 6 / fallback 0, actual live 5 / stub 6 / fallback 0, fallback cause none, decision live-limit 5 with `TLH_GEMMA_TIMEOUT_SECONDS=300` is the approved live scaling baseline, raw artifacts ignored and not committed.
S-11 Controlled Live-11 One-Shot Trial completed with PASS quality: run_id `run-20260707-115105`, timeout 300s, limited_live live-limit 11, preflight live 11 / stub 0 / fallback 0, actual live 11 / stub 0 / fallback 0, full_live-equivalent YES, native full_live mode not used, user approved beyond five YES, available key slots 22, distinct key slots used 11, single-key mode NO, raw artifacts ignored and not committed.
S-12 Controlled Live-22 Capacity Trial completed with PARTIAL quality: run_id `run-20260707-120538`, timeout 300s, limited_live live-limit 22, preflight live 22 / stub 0 / fallback 0, actual live 20 / stub 2 / fallback 2, available key slots 22, assigned key slots 1-22, distinct key slots used 22, single-key mode NO, fallback causes API 503 high demand and API 500 internal error, live-limit 22 is not promoted to baseline, raw artifacts ignored and not committed.
S-13 Per-worker Telemetry + Targeted Retry Policy completed with PASS-candidate tests: WorkerResult metadata records worker_index, key_slot, final_backend, latency_ms, attempt_count, retry_count, fallback_cause, error_type, and safe error messages; targeted retry applies once to timeout, API 503 high demand, API 500 internal error, and API 429 rate limit only; successful workers are not rerun; retry preserves key_slot; API key values are not recorded; live-limit 22 remains a capacity trial result, not a baseline.
S-14 Controlled Live-22 Retry Trial completed with PARTIAL quality: run_id `run-20260707-132504`, timeout 300s, limited_live live-limit 22, preflight live 22 / stub 0 / fallback 0, actual live 19 / stub 3 / fallback 3, available key slots 22, assigned key slots 1-22, distinct key slots used 22, single-key mode NO, retryable error count 5, retried worker count 5, retry success count 2, retry failure count 3, fallback after retry count 3, fallback causes API 503 high demand and API 500 internal error, baseline unchanged at live-limit 5 with timeout 300s, raw artifacts ignored and not committed.
S-15 Retry Backoff / Jitter / Retry Budget Policy completed with PASS-candidate tests: max retry attempts increased from 1 to 2 for retryable transient errors; retryable errors remain timeout, API 503 high demand, API 500 internal error, and API 429 rate limit; auth, schema, and invalid model response errors are not retried; backoff defaults to 5s and 15s with small jitter; tests inject fake sleep and jitter; retry budget defaults to 5 retried workers per run; successful workers are not rerun; retry preserves key_slot; API key values are not recorded; live-limit 22 remains a capacity/retry trial result, not a baseline.
S-16 Controlled Live-22 Backoff Retry Trial completed with PARTIAL quality: run_id `run-20260707-135313`, timeout 300s, limited_live live-limit 22, preflight live 22 / stub 0 / fallback 0, actual live 13 / stub 9 / fallback 9, available key slots 22, assigned key slots 1-22, distinct key slots used 22, single-key mode NO, max retry attempts 2, backoff and jitter enabled, retry budget 5 workers per run, retryable error count 11, retried worker count 5, retry success count 2, retry failure count 3, fallback after retry count 3, retry budget exhausted count 6, fallback causes API 503 high demand and API 500 internal error, baseline unchanged at live-limit 5 with timeout 300s, raw artifacts ignored and not committed.
S-17 Live Concurrency Wave Policy completed with PASS-candidate tests: wave policy can limit simultaneous live calls while preserving target live workers; `python -m tlh route-dry-run` supports `--live-wave-size`; worker_count 22 with live-limit 22 and wave-size 11 plans two waves with max concurrent live workers 11; key slots 1-22 remain distinctly assigned; WorkerResult, FinalPacket, and CodexPrompt summaries include wave metadata; successful workers are not rerun; retry remains worker-targeted and preserves key_slot; no actual live-22 wave run was executed; live-limit 22 remains a capacity/wave trial result, not a baseline.
S-18 Controlled Live-22 Wave Trial completed with FAIL-candidate quality: run_id `run-20260707-170719`, timeout 300s, limited_live live-limit 22, live-wave-size 11, preflight live 22 / stub 0 / fallback 0, wave-count 2, max concurrent live workers 11, actual live 10 / stub 12 / fallback 12, available key slots 22, assigned key slots 1-22, distinct key slots used 22, single-key mode NO, max retry attempts 2, backoff and jitter enabled, retry budget 5 workers per run, retryable error count 14, retried worker count 5, retry success count 2, retry failure count 3, fallback after retry count 3, retry budget exhausted count 9, fallback causes API 500 internal error and API 503 high demand, comparison vs S-16 worse, runtime semantics review found current dispatcher execution is sequential and wave-size affects execution order/metadata rather than actual concurrent API call count, baseline unchanged at live-limit 5 with timeout 300s, raw artifacts ignored and not committed.
S-17R/S-18R Runtime Wave Semantics Fix completed with PASS-candidate tests: previous wave policy affected execution order/metadata only; dispatcher now executes workers concurrently within each wave using `ThreadPoolExecutor`; wave-size limits actual concurrent `run_worker` calls; worker_count 22 with live-limit 22 and wave-size 11 plans two waves with max concurrent live workers 11; wave 2 starts after wave 1 completes; result order remains deterministic by worker_index; retry budget is run-scoped and thread-safe; successful workers are not rerun; retry preserves key_slot; route-dry-run text/JSON report `runtime_execution_model: concurrent_wave`; no actual live-22 wave run was executed; live-limit 22 remains a capacity/wave trial result, not a baseline.
S-19 Controlled Live-22 True Wave Trial completed with PARTIAL quality: run_id `run-20260707-173526`, timeout 300s, limited_live live-limit 22, live-wave-size 11, runtime execution model concurrent_wave, preflight live 22 / stub 0 / fallback 0, wave-count 2, planned max concurrent live workers 11, observed max concurrent run_worker calls 11, wave 2 started after wave 1, result order deterministic, actual live 19 / stub 3 / fallback 3, available key slots 22, assigned key slots 1-22, distinct key slots used 22, single-key mode NO, max retry attempts 2, backoff and jitter enabled, retry budget 5 workers per run, retry budget scope run, retryable error count 7, retried worker count 5, retry success count 4, retry failure count 1, fallback after retry count 1, retry budget exhausted count 2, fallback cause API 500 internal error, comparison vs S-16/S-18 improved but not stable, baseline unchanged at live-limit 5 with timeout 300s, raw artifacts ignored and not committed.
S-20 Controlled Live-22 True Wave-8 Trial completed with PARTIAL quality: run_id `run-20260707-174656`, timeout 300s, limited_live live-limit 22, live-wave-size 8, runtime execution model concurrent_wave, preflight live 22 / stub 0 / fallback 0, wave-count 3 with planned waves 8 + 8 + 6, planned max concurrent live workers 8, observed max concurrent run_worker calls 8, wave 2 started after wave 1, wave 3 started after wave 2, result order deterministic, actual live 17 / stub 5 / fallback 5, available key slots 22, assigned key slots 1-22, distinct key slots used 22, single-key mode NO, max retry attempts 2, backoff and jitter enabled, retry budget 5 workers per run, retry budget scope run, retryable error count 10, retried worker count 5, retry success count 5, retry failure count 0, fallback after retry count 0, retry budget exhausted count 5, fallback causes API 429 rate limit and API 500 internal error, comparison vs S-19 worse on final live count and fallback count because the run-scoped retry budget was consumed before wave 3, baseline unchanged at live-limit 5 with timeout 300s, raw artifacts ignored and not committed.
S-21 Wave-aware Retry Budget + Adaptive Pacing Policy completed with PASS-candidate tests: retry budget remains run-scoped with default limit 5, allocation is wave-aware with future-wave reserve to prevent later-wave starvation, unused reserve carries forward, retry budget claim/exhausted counts are thread-safe under concurrent wave execution, route-dry-run reports retry budget policy and optional pacing, `--live-wave-cooldown-seconds` / `TLH_LIVE_WAVE_COOLDOWN_SECONDS` can enable cooldown before the next wave after API 429 rate-limit signals, default cooldown remains 0 seconds, FinalPacket and CodexPrompt summaries include budget and pacing metadata, no actual live-22 run was executed, live-limit 22 remains a capacity/wave trial result and not a baseline.
S-22 Controlled Live-22 True Wave-8 Pacing Trial completed with FAIL-candidate live validation quality: run_id `run-20260708-000124`, timeout 300s, limited_live live-limit 22, live-wave-size 8, cooldown 30s, runtime execution model concurrent_wave, preflight live 22 / stub 0 / fallback 0, wave-count 3 with planned waves 8 + 8 + 6, planned max concurrent live workers 8, observed max concurrent run_worker calls 8, wave ordering and result order deterministic, retry budget policy wave_aware_reserve, retry budget limit 5, retry budget claimed by wave `{1: 3, 2: 1, 3: 1}`, retry budget exhausted by wave `{1: 4, 2: 3}`, actual live 14 / stub 8 / fallback 8, available key slots 22, assigned key slots 1-22, distinct key slots used 22, single-key mode NO, retryable error count 12, retried worker count 5, retry success count 4, retry failure count 1, fallback after retry count 1, retry budget exhausted count 7, fallback causes API 500 internal error and API 503 high demand, cooldown setting was visible but no cooldown was applied because the observed API 429 rate-limit signal occurred in wave 3 with no following wave, wave 3 starvation improved but early-wave fallback increased, comparison vs S-20 worse on final live count and fallback count, baseline unchanged at live-limit 5 with timeout 300s, raw artifacts ignored and not committed.

The MVP currently proves the following flow with stub workers.

```text
mission
→ clarification questions
→ user answers
→ TaskCards
→ WorkerResults
→ MergePacket
→ AccumulatedArtifact
→ FoldedSummary
→ LoopDecision
→ FinalPacket
→ CodexPrompt
```

---

## Current Scope

Included.

```text
Vault init.
TeamLead clarify.
TaskCard generation.
Worker dispatch.
WorkerResult collection.
MergePacket creation.
AccumulatedArtifact update.
FoldedSummary creation.
MinimalityCheck creation.
LoopDecision creation.
FinalPacket creation.
CodexPrompt creation.
Graph index generation.
Generated artifact ignore policy.
Temporary-workspace smoke test.
Quality tests for handoff outputs.
Section-mapped MergePacket material.
Structured FinalPacket and CodexPrompt rendering.
Env-based worker backend selection.
Live Gemma adapter with lazy SDK import.
Per-TaskCard backend hints for one-live-worker validation.
Run-level live worker limit with `TLH_LIVE_WORKER_LIMIT`.
WorkerResult metadata for `live_worker_limit` and `live_worker_index`.
Centralized `LiveRoutingPolicy` and `LiveRoutingDecision`.
FinalPacket and CodexPrompt backend mix and routing policy summaries.
Force-live guard that treats `TLH_FORCE_WORKER_BACKEND=live` as a live request subject to policy.
Routing dry-run coverage for worker counts 3, 5, and 11.
CLI-visible `route-dry-run` command with text and JSON output.
Fenced JSON live output normalization.
Stub fallback for missing or failed live configuration.
Gemini key pool slot assignment for live workers.
Per-worker live telemetry with latency, key_slot, backend, fallback, error, and retry metadata.
Targeted retry policy for transient live worker failures.
Retry backoff, jitter, and per-run retry budget policy for transient live worker failures.
Live concurrency wave policy and route-dry-run wave planning.
True concurrent wave execution with run-scoped retry budget locking.
Wave-aware retry budget allocation with optional adaptive wave pacing.
Mock live adapter tests.
One-live-worker live dry run review.
Multi-live limit dry run review.
Controlled live-worker routing policy review.
Controlled routing dry run and guard hardening review.
Routing policy dry-run command review.
```

Excluded.

```text
GUI.
Dashboard.
Obsidian plugin.
Obsidian MCP write.
Serena edit/write/refactor.
RTK global hook.
Claude/Codex automatic execution.
GitHub PR/merge automation.
Global AGENTS.md management.
Global CLAUDE.md management.
AI_WORKFLOW_KIT duplicate tooling.
Unbounded real live worker rollout.
```

---

## Current File Placement Decision

Project docs are under.

```text
C:\Users\USER\TLH\docs
```

The required docs are.

```text
C:\Users\USER\TLH\docs\TLH_INDEX.md
C:\Users\USER\TLH\docs\TLH_CANON.md
C:\Users\USER\TLH\docs\TLH_MVP_PLAN.md
C:\Users\USER\TLH\docs\TLH_IMPLEMENTATION_PROMPT.md
C:\Users\USER\TLH\docs\CURRENT_STATE.md
```

No README is required for now because this is a solo project.

---

## Next Action

Use the CLI-visible routing dry-run command before any future live-worker scaling run.
The approved baseline is live-limit 5 with `TLH_GEMMA_TIMEOUT_SECONDS=300`.

```text
python -m tlh route-dry-run --workers 11 --mode limited_live --live-limit 5
```

The next controlled scaling decision should not repeat live-limit 22 immediately. S-22 shows wave-aware reserve can protect wave 3, but with a fixed run budget of 5 it shifts retry starvation into earlier waves; review reserve allocation, cooldown trigger semantics, or per-wave pacing before any further approved live-limit 22 trial.

---

## Do Not

Do not do these.

```text
Do not resurrect AICO architecture.
Do not make TLH a no-call approval harness.
Do not build a dashboard.
Do not add Obsidian MCP write.
Do not add RTK global hook.
Do not add Serena write/edit/refactor.
Do not let TeamLead answer without workers.
Do not let workers directly edit files.
Do not make raw logs the source of truth.
Do not read the entire TLH_CANON.md by default.
Do not duplicate AI_WORKFLOW_KIT global features.
```

---

## Tooling Report Rule

Use this short block near the end of TLH completion reports.

```text
Tooling.
- Used:
- Not used:
- Reason:
```

Use AI_WORKFLOW_KIT components only when they fit the task.
Do not treat `claude mcp list` or availability checks as real Serena MCP use.
TLH native MCP is not required for current TLH work.

---

## Open Decisions

Live-limit 5 with `TLH_GEMMA_TIMEOUT_SECONDS=300` is approved as the current scaling baseline.
User approval is required before increasing the live worker count beyond five.
`full_live` must not be enabled without explicit opt-in.
`TLH_FORCE_WORKER_BACKEND=live` must not bypass live limits or imply full_live.
Route-dry-run preflight remains mandatory before every live-worker scaling run.
S-9R shows live-limit 5 can complete without fallback when `TLH_GEMMA_TIMEOUT_SECONDS=300`; do not infer that full_live 11 is safe.
S-11 was a user-approved one-shot live-limit 11 trial and does not change the approved baseline from live-limit 5.
S-12 showed the full 22-slot key pool can be assigned distinctly, but live-limit 22 remains a one-shot capacity result and does not change the approved baseline from live-limit 5.
S-13 adds targeted retry for transient API-side failures, but does not promote live-limit 22 or replace route-dry-run preflight.
S-14 shows live-limit 22 is still transient-sensitive even with one targeted retry; do not promote live-limit 22 to baseline.
S-15 improves retry resilience with two attempts, backoff, jitter, and a retry budget, but does not promote live-limit 22 to baseline.
S-16 shows live-limit 22 is still not stable under the current retry budget; do not promote live-limit 22 to baseline.
S-17 adds wave concurrency planning for live-limit 22, but does not promote live-limit 22 to baseline.
S-18 shows live-limit 22 with wave-size 11 is not stable and was worse than S-16 on live count, fallback count, retryable error count, and retry budget exhaustion; do not promote live-limit 22 or wave-size 11 to baseline. Treat S-18 as a wave metadata/order trial, not proof that a real concurrency limiter worsened API pressure.
S-17R/S-18R makes wave-size a real runtime concurrency limiter and keeps retry budget run-scoped; it does not promote live-limit 22 or wave-size 11 to baseline.
S-19 shows true concurrent wave-size 11 improves live-limit 22 behavior versus S-16 and S-18, but final live results remained below 22 and fallback after retry remained nonzero; do not promote live-limit 22 or wave-size 11 to baseline.
S-20 shows true concurrent wave-size 8 enforces observed max concurrency 8 with three waves, but final live results dropped to 17 because retryable API failures in wave 3 could not be retried after the run-scoped retry budget was consumed; do not promote live-limit 22 or wave-size 8 to baseline.
S-21 changes retry budget allocation to wave-aware reserve and adds optional adaptive wave cooldown, but it is mock/test validated only; do not infer live-limit 22 stability until a separate approved live trial runs.
S-22 shows wave-aware reserve and cooldown-visible wave-size 8 did not stabilize live-limit 22; wave 3 starvation improved, but early waves had more retry-denied fallback and final live results dropped to 14. Do not promote live-limit 22, wave-size 8, or cooldown 30s to baseline.

Later decisions.

```text
Where to store API key configuration.
Whether Serena read/search should be integrated after MVP.
Whether Obsidian MCP read-only should be considered after MVP.
Whether RTK hints should be added to CodexPrompt after MVP.
```

---

## Generated Artifact Policy

Generated run artifacts are not source canon.

Do not commit sample run outputs by default.
Keep vault base files and directory placeholders.

Ignored generated areas include.

```text
machine\runs
vault run notes
TaskCard notes
WorkerResult notes
MergePacket notes
AccumulatedArtifact notes
FinalPacket notes
CodexPrompt notes
MinimalityCheck notes
```

---

## Recommended Next Slice

```text
Run another live-limit 22 true wave trial only with explicit approval and route-dry-run wave preflight. Prefer testing smaller wave sizes or targeted API-pressure controls before repeating wave-size 11.
Keep API key values out of output, notes, logs, and commits.
```

---

## Current Risk

The main risk is overbuilding.

Watch for these failure patterns.

```text
Too many worker roles.
Too many schemas.
Too many docs.
Trying to integrate Serena live too early.
Trying to integrate Obsidian MCP write too early.
Trying to automate Claude/Codex execution too early.
Turning TLH into another AI_WORKFLOW_KIT.
```

Use Ponytail minimality whenever scope expands.
