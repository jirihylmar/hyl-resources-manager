---
name: update-progress
description: Close or hand off work in a syndicate playbook project by verifying the task, updating progress.json and session notes, committing scoped changes, and pushing at the repository's defined boundary. Use after completing tracked work or before ending a session.
---

# Update playbook progress

Read `AGENTS.md` and `CLAUDE.md` completely when they exist. Then read
`.claude/commands/update-progress.md` completely and execute its procedure as the canonical
workflow.

The canonical file is shared with existing Claude executors. Ignore its YAML `allowed-tools` list
and translate Claude-specific tool identifiers to equivalent available Codex capabilities. A slash
command named in that procedure means its corresponding repository skill when one exists.

Preserve these boundaries:

- Re-read `progress.json` immediately before editing because another executor may have changed it.
- Complete a task only after its concrete verification passes; record the actual result.
- Never delete tasks. Follow the established started/unstarted mutability rule.
- Every newly added phase/task needs `authored_by` and `assigned_to`.
- Stage and commit only work in scope; the shipped Git hook is the mechanical integrity backstop.
- Push only at the project's defined boundary and never force a remote branch.
- Task 0.5 cannot complete without explicit operator approval of the implementation specification.
