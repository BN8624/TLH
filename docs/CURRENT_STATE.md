# CURRENT_STATE.md

## Status

TLH MVP skeleton is implemented.

S-0 stabilization is in progress.
Stub worker end-to-end flow has passed once.
Live Gemma is not integrated yet.

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

Stabilize the implemented TLH MVP skeleton before live worker work.

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
Live Gemma worker adapter.
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

```text
Finish S-0 stabilization.
Keep generated run artifacts out of source commits.
Run compile, help, init, and smoke verification.
```

After S-0, choose one of these S-1 paths.

```text
S-1 live Gemma adapter.
S-1 real task dry run with stub workers.
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

No blocking decision for S-0.

Later decisions.

```text
Whether to use live Gemma workers or stub workers first.
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
Run S-1 real task dry run with stub workers.
Then decide whether to implement the live Gemma adapter.
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
