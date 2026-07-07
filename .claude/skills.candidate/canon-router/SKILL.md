---
name: canon-router
description: Use before reading a long PROJECT_CANON.md or similar canon document. Reads AI_INDEX.md first and selects only relevant CANON-ID sections instead of loading the full canon.
---

# Canon Router

## Purpose

Avoid reading huge canon files unnecessarily.

## Protocol

1. Read `AI_INDEX.md` first if present.
2. Identify the current task type.
3. Select only the relevant CANON-ID sections.
4. Read only those sections from `PROJECT_CANON.md`.
5. Do not load the entire canon unless the user explicitly asks for a full audit.

## Output

Report:

- Task type.
- Selected CANON-ID sections.
- Sections intentionally skipped.
- Any missing index entries.
