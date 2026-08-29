---
name: start-session
description: Start or resume work in a syndicate playbook project by synchronizing repositories, reading progress.json, verifying prior work, resolving the current task, and presenting the required session-start checkpoint. Use at the beginning of a project session or when asked to continue tracked work.
---

# Start a playbook session

Read `AGENTS.md` and `CLAUDE.md` completely when they exist. Then read
`.claude/commands/start-session.md` completely and execute its procedure as the canonical workflow.

The canonical file is shared with existing Claude executors. Ignore its YAML `allowed-tools` list
and translate Claude-specific tool identifiers to equivalent available Codex capabilities. A slash
command named in that procedure means its corresponding repository skill when one exists; for
example, `/update-progress` means `$update-progress` in Codex.

Preserve these boundaries:

- `progress.json` is the work-state source of truth, but a task explicitly assigned by the user
  takes precedence over its current pointer.
- Synchronization is fast-forward-only. Never discard or overwrite local work to make a pull pass.
- Verify identities and live locations rather than trusting host-specific nicknames.
- Report the task identifier together with its plain-language meaning.
- The session-start status is a checkpoint. Continue immediately only when the user's current
  request already authorized that work.
- Every newly added phase/task needs `authored_by` and `assigned_to`.
