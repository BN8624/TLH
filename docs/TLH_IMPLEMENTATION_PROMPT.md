# TLH_IMPLEMENTATION_PROMPT.md

## Instruction To Codex Or Claude Code

You are implementing the TLH MVP.

This is a new project.
Do not import AICO architecture.
Do not duplicate AI_WORKFLOW_KIT global workflow features.

The goal is to implement an Obsidian-first TeamLead Loop Harness.

---

## 1. Read Order

Read these files first.

```text
docs\TLH_INDEX.md
docs\TLH_MVP_PLAN.md
docs\CURRENT_STATE.md
```

Then use `docs\TLH_INDEX.md` to select only the relevant sections from.

```text
docs\TLH_CANON.md
```

Do not read the entire canon unless necessary.
Do not start by summarizing the whole canon.
Use the index as a router.

---

## 2. Project Goal

Implement the MVP where one user mission grows through this path.

```text
mission
→ clarification questions
→ user answers
→ concrete mission
→ TaskCards
→ WorkerResults
→ MergePacket
→ AccumulatedArtifact
→ FoldedSummary
→ LoopDecision
→ FinalPacket
→ CodexPrompt
```

The MVP must prove the slice-and-attach loop.

---

## 3. Non-Negotiable Boundary

Do not implement these.

```text
GUI.
Dashboard.
Obsidian plugin.
Obsidian MCP write.
Serena edit/write/refactor.
RTK global hook.
Claude/Codex automatic execution.
GitHub PR/merge automation.
Worker direct file edits.
Worker shell execution.
Global AGENTS.md management.
Global CLAUDE.md management.
Codex/Claude skills installer.
Repomix installer.
AI_WORKFLOW_KIT duplicate tooling.
```

If you think one of these is needed, do not implement it.
Write it as a future option.

---

## 4. Required Files And Directories

Create or verify this structure.

```text
TLH\
  AGENTS.md
  CLAUDE.md

  docs\
    TLH_INDEX.md
    TLH_CANON.md
    TLH_MVP_PLAN.md
    TLH_IMPLEMENTATION_PROMPT.md
    CURRENT_STATE.md

  tlh\
    __init__.py
    __main__.py
    cli.py
    schemas.py
    vault.py
    team_lead.py
    task_card.py
    worker_pool.py
    gemma_client.py
    dispatcher.py
    merge_harness.py
    loop_controller.py
    ponytail_checker.py
    graph_index.py
    packet_writer.py

  prompts\
    team_lead_clarify.v1.md
    team_lead_decompose.v1.md
    worker_base.v1.md
    worker_builder.v1.md
    worker_critic.v1.md
    merge_harness.v1.md
    continuity_check.v1.md
    final_packet.v1.md
    codex_prompt.v1.md

  vault\
    _AI_README.md
    _CURRENT_STATE.md
    _AI_INDEX.md
    _GRAPH_INDEX.json
    _GRAPH_INDEX.md

    00_Inbox\
    01_Runs\
    02_TaskCards\
    03_WorkerResults\
    04_MergePackets\
    05_Artifacts\
    06_Handoff\
    07_Patterns\
    08_Failures\
    09_Decisions\
    10_ContextPackets\
    11_MinimalityChecks\

  machine\
    runs\
```

Do not overwrite existing user files.
If a file already exists, preserve it unless the change is directly required.

---

## 5. Required CLI

Implement these commands.

```powershell
python -m tlh init
python -m tlh run --mission "vault\00_Inbox\mission.md"
python -m tlh answer --run "<run_id>" --answers "vault\01_Runs\<run_id>_answers.md"
python -m tlh dispatch --run "<run_id>"
python -m tlh merge --run "<run_id>"
python -m tlh loop --run "<run_id>"
python -m tlh finalize --run "<run_id>"
```

The commands may be simple in MVP, but they must produce real files.

---

## 6. Required Data Flow

The MVP must create these outputs during a sample run.

```text
machine\runs\<run_id>\state.json
machine\runs\<run_id>\task_cards.jsonl
machine\runs\<run_id>\worker_results.jsonl
machine\runs\<run_id>\merge_packets.jsonl

vault\01_Runs\<run_id>.md
vault\02_TaskCards\<task_id>.md
vault\03_WorkerResults\<worker_result_id>.md
vault\04_MergePackets\<merge_id>.md
vault\05_Artifacts\<artifact_id>.md
vault\06_Handoff\<final_packet_id>.md
vault\06_Handoff\<codex_prompt_id>.md
vault\11_MinimalityChecks\<check_id>.md
vault\_GRAPH_INDEX.json
vault\_GRAPH_INDEX.md
```

---

## 7. Required Schemas

Implement these in `tlh\schemas.py`.

```text
TaskCard.
WorkerResult.
MergePacket.
MinimalityCheck.
LoopDecision.
FinalPacket.
ContextRequest.
ContextPacket.
ExecutionHint.
```

Use dataclasses or pydantic only if already appropriate.
Do not overbuild.
Plain dataclasses are acceptable for MVP.

---

## 8. TeamLead Behavior

TeamLead must not directly produce the final answer.

TeamLead must.

```text
1. Read the mission.
2. Produce clarification questions.
3. Read user answers.
4. Produce a concrete mission.
5. Generate TaskCards.
6. Assign worker roles.
7. Request merge.
8. Update AccumulatedArtifact.
9. Produce FinalPacket.
```

TeamLead must not.

```text
1. Skip TaskCards.
2. Skip workers.
3. Hide conflicts.
4. Treat raw worker output as final.
5. Ignore AccumulatedArtifact.
```

---

## 9. Worker Behavior

Workers process TaskCards and return WorkerResults.

Workers must not.

```text
Ask the user questions directly.
Call other workers.
Modify files.
Run shell commands.
Write to canon.
Create final output directly.
```

MVP may use stub workers if live model access is unavailable.
If stub workers are used, mark the output as stub-generated.

At least two WorkerResults must be produced in the sample run.

---

## 10. Merge Behavior

MergeHarness must.

```text
Read WorkerResults.
Extract confirmed points.
Preserve alternatives.
Record conflicts.
Drop unsupported or duplicate items.
Update AccumulatedArtifact.
Create MergePacket.
Create MinimalityCheck.
```

Do not simply concatenate WorkerResults.
Merge must produce a structured MergePacket.

---

## 11. Loop Behavior

LoopController must produce one of.

```text
next_slice.
targeted_verifier.
user_question_needed.
stop_and_finalize.
failed_to_merge.
```

The loop must not run forever.
For MVP, one slice-and-attach loop is enough if it proves the structure.

---

## 12. Graph Behavior

Graph index generation must read vault note metadata and links where possible.

Generate.

```text
vault\_GRAPH_INDEX.json
vault\_GRAPH_INDEX.md
```

For MVP, graph extraction can be simple.
It must at least include nodes for Run, TaskCard, WorkerResult, MergePacket, AccumulatedArtifact, FinalPacket.

---

## 13. Prompt Files

Create prompt files under `prompts\`.

Each prompt should be short and task-specific.

Required prompts.

```text
team_lead_clarify.v1.md
team_lead_decompose.v1.md
worker_base.v1.md
worker_builder.v1.md
worker_critic.v1.md
merge_harness.v1.md
continuity_check.v1.md
final_packet.v1.md
codex_prompt.v1.md
```

Do not make prompt files huge.
Put long project rules in docs canon, not in prompts.

---

## 14. Verification

After implementation, run at least this flow.

```powershell
python -m tlh init
```

Then create a simple mission file.

```text
vault\00_Inbox\mission.md
```

Example mission.

```text
Create a Codex handoff prompt for implementing a small CLI that converts markdown task notes into JSONL.
```

Then run.

```powershell
python -m tlh run --mission "vault\00_Inbox\mission.md"
python -m tlh answer --run "<run_id>" --answers "vault\01_Runs\<run_id>_answers.md"
python -m tlh dispatch --run "<run_id>"
python -m tlh merge --run "<run_id>"
python -m tlh loop --run "<run_id>"
python -m tlh finalize --run "<run_id>"
```

If answers file is needed, create a minimal one.
Do not block the MVP on interactive input.

---

## 15. Completion Criteria

The work is complete only if.

```text
1. CLI imports without error.
2. init creates vault and machine structure.
3. run creates run state and clarification output.
4. answer creates TaskCards.
5. dispatch creates at least two WorkerResults.
6. merge creates MergePacket and AccumulatedArtifact.
7. loop creates LoopDecision.
8. finalize creates FinalPacket and CodexPrompt.
9. graph index files are created.
10. no AI_WORKFLOW_KIT functionality is duplicated.
```

---

## 16. Report Format

When done, report in this format.

```text
TLH MVP Implementation Report.

Changed files.
- <file>

Created files.
- <file>

Implemented CLI.
- init: YES/NO.
- run: YES/NO.
- answer: YES/NO.
- dispatch: YES/NO.
- merge: YES/NO.
- loop: YES/NO.
- finalize: YES/NO.

Verification commands.
- <command> → <result>

Generated MVP artifacts.
- state.json: YES/NO.
- task_cards.jsonl: YES/NO.
- worker_results.jsonl: YES/NO.
- merge_packets.jsonl: YES/NO.
- TaskCard notes: YES/NO.
- WorkerResult notes: YES/NO.
- MergePacket notes: YES/NO.
- AccumulatedArtifact: YES/NO.
- FinalPacket: YES/NO.
- CodexPrompt: YES/NO.
- Graph index: YES/NO.

Skipped or deferred.
- <item>

Risks.
- <risk>

Next recommended step.
- <step>
```

---

## 17. Final Reminder

This MVP is not about making a perfect multi-agent platform.

It is about proving this core loop.

```text
TaskCard.
WorkerResult.
MergePacket.
AccumulatedArtifact.
LoopDecision.
FinalPacket.
```

Keep it small.
Make it real.
Verify with files.
