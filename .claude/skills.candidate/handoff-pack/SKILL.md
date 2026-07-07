---
name: handoff-pack
description: Use when preparing instructions for Codex, Claude Code, or another agent. Produces an executable handoff packet with goal, scope, constraints, steps, verification, and reporting format.
---

# Handoff Pack

## Purpose

Create a transfer-ready instruction packet for another AI agent.

## Required Sections

1. Goal.
2. Current state.
3. Scope.
4. Out of scope.
5. Files or areas to inspect.
6. Implementation steps.
7. Verification steps.
8. Safety rules.
9. Reporting format.
10. Known risks.

## Rules

- Do not include unnecessary background.
- Prefer concrete commands and file paths.
- Make the packet executable without another long conversation.
- Keep user decision points to three or fewer.
