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
Use `route-dry-run` as a preflight and add regression tests before any new routing mode.
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
