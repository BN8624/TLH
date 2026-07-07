---
name: ponytail-review
description: Use before expanding scope, adding files, adding abstractions, or creating large implementation plans. Reviews a plan, diff, or proposal for overbuild and suggests keep, merge, drop, or defer decisions.
---

# Ponytail Review

## Purpose

Prevent overengineering.

Use this skill before expanding scope, adding files, adding abstractions, introducing new dependencies, creating process documents, or running extra loops.

## Review Questions

1. Is this change directly required by the user request?
2. Can the same goal be achieved by modifying existing code or docs?
3. Is a new file really necessary?
4. Is a new abstraction justified by repeated use?
5. Is this flexibility speculative?
6. Is this loop producing new information or repeating prior conclusions?
7. Can this be deferred until the need is proven?

## Output

Return one of:

- KEEP.
- MERGE_WITH_EXISTING.
- DROP.
- DEFER.

Include a short reason and the smallest safe alternative.
