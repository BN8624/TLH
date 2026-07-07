---
name: loop-audit
description: Use when a task has repeated iterations, unclear progress, a growing run log, or multiple agents producing similar outputs. Determines whether to continue, stop, merge, or ask the user.
---

# Loop Audit

## Purpose

Detect whether a loop is producing real progress or just repeating work.

## Check

1. What changed since the previous loop?
2. Did the accumulated artifact grow?
3. Did conflicts decrease?
4. Did new evidence appear?
5. Are workers repeating the same points?
6. Is finalization already possible?
7. Is a user decision needed?

## Output

Return one of:

- CONTINUE_NEXT_SLICE.
- TARGETED_VERIFIER.
- MERGE_AND_FINALIZE.
- ASK_USER.
- STOP_OVERBUILD.

Include a short reason.
