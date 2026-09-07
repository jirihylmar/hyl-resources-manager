---
name: start-session
description: Start or resume work in a syndicate playbook project by synchronizing repositories, reading progress.json, verifying prior work, resolving the current task, and presenting the required session-start checkpoint. Use at the beginning of a project session or when asked to continue tracked work.
---

# Start a playbook session

Read `PROJECT_CHARTER.md`, `AGENTS.md` and `CLAUDE.md` completely when they exist. Then read
`.claude/commands/start-session.md` completely and execute its procedure as the canonical workflow.

**When they conflict, `PROJECT_CHARTER.md` governs.** It is the executor-neutral delivery contract
and it is centrally maintained; a project's own `CLAUDE.md` is older prose that no one updates when
the contract changes. Claude's copy of this procedure has carried that precedence rule since it was
written; this one did not, and the gap is not hypothetical.

> **Measured 2026-09-07.** Eleven project `CLAUDE.md` files across both hosts carry a section
> *"No Virtual Environments"* whose prescribed remedy is `pip3 install package` — a bare user-site
> install. That is not the cure for a venv, it is a venv you cannot see: it lands in
> `~/.local/lib/pythonX.Y/site-packages`, global to the interpreter, shadowing every environment on
> the host. On the box it had accumulated 153 packages including `mcp` 2.0.0 and `boto3` 1.43.62 —
> and when a container mounted that home, the host's packages won and the MCP server died with
> `ImportError: FastMCP server support is not installed`. Charter § 9 now states the actual rule
> (containers, by content address). Without this precedence line you would read both and have no
> instruction about which one to follow.

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
- An operation that outlives this turn is governed by `PROJECT_CHARTER.md` section 11,
  *Unattended operations*: every such operation is session-watched, durably-supervised or
  unmonitored; a final response requires the supervisor proof recorded there; process exit status
  never means delivery; and a watcher owns its next transition, not merely the observation. The
  bullet above covers a job you are still watching inside this turn. The charter covers the case it
  cannot: a supervisor that dies, stalls, misses its deadline or reaches a non-delivery terminal
  state AFTER you have yielded. Read it there — do not restate its rules here, because four copies
  of one contract is how they diverge.
- A queued or running asynchronous job is ongoing work, not a blocker or session boundary. Retain
  its job/session handle and wait or poll in bounded intervals no longer than 60 seconds, using
  commentary for interim updates. A final response ends active execution: never claim to be monitoring after sending one,
  and never send one while a required job remains non-terminal.
- Continue through the terminal result: inspect and proceed after success; collect evidence and
  fix/retry in scope or report a genuine blocker after failure. Use Codex's durable goal mechanism
  only when the operator explicitly creates or requests a persistent goal; ordinary waiting stays
  in the current turn.
