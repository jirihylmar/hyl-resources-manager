---
name: unattended-check
description: Decide whether an operation this project started is actually being watched — session-watched, durably supervised, or unmonitored — by probing the supervisor rather than trusting what was said about it. Refuses a yield when a non-terminal operation has no proved watcher, and classifies every claimed operation at session start. Invoke before ending a turn that leaves work depending on a future external state change, when resuming a project that claims a background job, or when asked whether something is still running.
---

# Unattended operation check

One implementation of `PROJECT_CHARTER.md` § 11, *Unattended operations*. The rules live in the
charter, for both executors; this skill is what makes them decidable.

```bash
python3 .claude/skills/unattended-check/unattended_check.py --gate        # before a final response
python3 .claude/skills/unattended-check/unattended_check.py --reconcile   # at session start
```

Both read `progress.json` and act on the `unattended` block of every **non-terminal** task. A task
without one is not an unattended operation and is never reported.

**Exit codes.** `0` permitted / nothing to recover · `3` yield refused (`--gate`) or a watcher needs
recovery first (`--reconcile`) · `2` `progress.json` could not be read, which means the state of
every operation is **unknown** — never read that as *none*.

## The block

```json
"unattended": {
  "operation_id":      "capacity-p5en-2026-09-02",
  "supervisor_id":     "capacity-watch.timer",
  "supervisor_mode":   "durably-supervised",
  "state_ref":         "journal:capacity-watch",
  "started_at":        "2026-09-02T08:00:00Z",
  "last_observed_at":  "2026-09-02T08:40:00Z",
  "next_action_at":    "2026-09-02T09:40:00Z",
  "deadline_at":       "2026-09-03T08:00:00Z",
  "retry_count":       1,
  "retry_limit":       6,
  "delivery_state":    "pending",
  "cleanup_state":     "leased",
  "cleanup_owner":     "capacity-guardian.timer",
  "notification_state":"project-notice",
  "liveness_check":    "systemctl --user is-active capacity-watch.timer"
}
```

`supervisor_mode` is `session-watched`, `durably-supervised` or `unmonitored`. `delivery_state` is
`pending`, `delivered`, or one of the five non-delivery terminals — `capacity-exhausted`,
`workload-failed`, `controller-crashed`, `cleanup-failed`, `deadline-missed`. **Only `delivered`
means the outcome happened.**

**`liveness_check` and `state_ref` are host-owned; everything else travels.** The check runs
`liveness_check` and never interprets it, so a project may name a systemd unit, a launchd label, a
cron entry or a pid file without this skill knowing what any of those are. Every other field is read
on machines where a host path would mean nothing, so an absolute `/home/...` in one of them is
reported.

## What it will not do

It will not decide that an operation is fine because the task text says so, and it will not treat a
supervisor's exit status as delivery. Those are the two failures it exists for: a supervisor that
returned `0` on capacity exhaustion once made a failed delivery read as service success, and an
executor that said it was monitoring had already ended the turn that was doing the monitoring.

## Related

- `PROJECT_CHARTER.md` § 11 — the contract itself, and the only place its rules are stated.
- `/update-progress` Step 9a — runs `--gate`; `/start-session` Step 6a — runs `--reconcile`.
- `/open-work` — renders open work; this skill answers a different question about the same tasks.
