# CURRENT_STATE.md

## Status

TLH MVP skeleton is implemented.

S-0 stabilization is complete.
S-1 stub dry run completed with PARTIAL quality.
S-1Q merge and final quality fix completed with PASS quality.
S-2 live Gemma adapter is implemented with stub-safe fallback.
S-3 controlled one-live-worker run completed with PASS quality.

The project direction is defined.
AICO is deprecated and must not be used as the architecture base.
AI_WORKFLOW_KIT exists as a separate global workflow layer and must not be duplicated inside TLH.

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

Prepare for the next controlled multi-live dry run.

S-3 proved that one TaskCard can run live with `gemma-4-31b-it` while the remaining TaskCard stays stub-safe.

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
Fenced JSON live output normalization.
Stub fallback for missing or failed live configuration.
Mock live adapter tests.
One-live-worker live dry run review.
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

Run a controlled multi-live dry run only after setting an explicit live-worker count limit.

```text
S-4 controlled multi-live dry run.
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

## Open Decisions

User approval is required before increasing the live worker count.

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
Run a controlled multi-live dry run with an explicit live-worker count limit.
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
