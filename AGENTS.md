# AGENTS.md Template

## AI Workflow

Use the local project instructions first.

When reusable workflow guidance is needed, prefer installed skills:

- `ponytail-review`
- `canon-router`
- `handoff-pack`
- `loop-audit`
- `context-pack`
- `reentry-summary`

## Project Canon

At the start of each new agent session in this repo, read `docs\TLH_INDEX.md` if it exists.
Use it to select the relevant CANON-ID sections from `docs\TLH_CANON.md`.
Do not read the full `TLH_CANON.md` unless the user explicitly asks for a full canon audit.

If `docs\AI_INDEX.md` exists, read it before loading `docs\PROJECT_CANON.md`.

## Safety

- Do not overwrite user changes.
- Do not read secrets.
- Do not push or merge without explicit approval.

## Completion Reporting

For TLH task reports, include a short tooling block.

```text
Tooling.
- Used:
- Not used:
- Reason:
```

Record tools as `USED` only when they were actually used for the task. A status check such as `claude mcp list` means `AVAILABLE_ONLY`, not `USED`.
Use AI_WORKFLOW_KIT components only when they fit the task. Do not require TLH native MCP before using global skills, Serena MCP, RTK, Repomix, helper tools, or templates.
