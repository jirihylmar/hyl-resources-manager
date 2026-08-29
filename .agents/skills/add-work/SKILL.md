---
name: add-work
description: Add an explicitly authorized phase or task to a syndicate project's progress.json, including sizing, verification, authorship, assignment, task-file and session-note updates. Use when the operator asks to track or add work; do not use merely because an idea was discussed.
---

# Add tracked work

Read `.claude/commands/add-work.md` completely and execute it as the canonical procedure, translating
Claude tool names to available Codex capabilities. Preserve its approval gate and four-destination
routing contract. Every new phase/task must include non-empty `authored_by` and `assigned_to`; they
may differ. Invoke named slash workflows as their corresponding `$skill-name` when available.
