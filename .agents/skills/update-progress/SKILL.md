---
name: update-progress
description: Publish a completed task or close a syndicate project session by verifying work, updating progress.json, committing scoped changes, and pushing at the defined boundary. A task-boundary update continues directly into the next authorized task; use full handoff only when the session is actually ending.
---

# Update playbook progress

Read `AGENTS.md` and `CLAUDE.md` completely when they exist. Then read
`.claude/commands/update-progress.md` completely and execute its procedure as the canonical
workflow.

The canonical file is shared with existing Claude executors. Ignore its YAML `allowed-tools` list
and translate Claude-specific tool identifiers to equivalent available Codex capabilities. A slash
command named in that procedure means its corresponding repository skill when one exists.

Preserve these boundaries:

- First classify the invocation as `TASK_BOUNDARY` or `SESSION_CLOSE`. Completing, verifying,
  committing, pushing, or advancing from one task to the next is `TASK_BOUNDARY`; it is never by
  itself a reason to yield.
- In `TASK_BOUNDARY`, run the task verification/progress/publication steps, announce the result in
  one concise transition, and immediately work on the next ready authorized task in the same turn.
  Do not produce the Step 12 handoff or end the response unless a declared approval checkpoint,
  genuine blocker, explicit stop request, or absence of safe authorized work makes this a real
  `SESSION_CLOSE`.
- Run session-only consolidation, knowledge extraction, handoff notes, and the final summary only
  for `SESSION_CLOSE` (or when closing a phase explicitly requires its hygiene gate).
- A queued or running asynchronous job is ongoing work, not a blocker or session boundary. Retain
  its job/session handle and wait or poll in bounded intervals no longer than 60 seconds, using
  commentary for interim updates. A final response ends active execution: never claim to be monitoring after sending one,
  and never send one while a required job remains non-terminal.
- Continue through the terminal result: inspect and proceed after success; collect evidence and
  fix/retry in scope or report a genuine blocker after failure. Use Codex's durable goal mechanism
  only when the operator explicitly creates or requests a persistent goal; ordinary waiting stays
  in the current turn.

- Re-read `progress.json` immediately before editing because another executor may have changed it.
- Complete a task only after its concrete verification passes; record the actual result.
- Never delete tasks. Follow the established started/unstarted mutability rule.
- Every newly added phase/task needs `authored_by` and `assigned_to`.
- Stage and commit only work in scope; the shipped Git hook is the mechanical integrity backstop.
- Push only at the project's defined boundary and never force a remote branch.
- Task 0.5 cannot complete without explicit operator approval of the implementation specification.
- An operation that outlives this turn is governed by `PROJECT_CHARTER.md` section 11,
  *Unattended operations*: every such operation is session-watched, durably-supervised or
  unmonitored; a final response requires the supervisor proof recorded there; process exit status
  never means delivery; and a watcher owns its next transition, not merely the observation. The
  bullet above covers a job you are still watching inside this turn. The charter covers the case it
  cannot: a supervisor that dies, stalls, misses its deadline or reaches a non-delivery terminal
  state AFTER you have yielded. Read it there — do not restate its rules here, because four copies
  of one contract is how they diverge.
