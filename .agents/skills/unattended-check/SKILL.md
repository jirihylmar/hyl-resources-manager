---
name: unattended-check
description: Decide whether an operation this project started is actually being watched — session-watched, durably supervised, or unmonitored — by probing the supervisor rather than trusting what was said about it. Use before ending a turn that leaves work depending on a future external state change, when resuming a project that claims a background job, or when asked whether something is still running.
---

# Unattended operation check

Read `.claude/skills/unattended-check/SKILL.md` completely and execute its procedure as the
canonical workflow. The implementation is single-owned there and is executor-neutral Python; run it
directly.

```bash
python3 .claude/skills/unattended-check/unattended_check.py --gate
python3 .claude/skills/unattended-check/unattended_check.py --reconcile
```

Preserve these boundaries:

- The rules are stated once, in `PROJECT_CHARTER.md` section 11, *Unattended operations*. Do not
  restate them here and do not let this adapter accumulate a second version of them.
- Exit 3 from `--gate` means the final response must not be sent. It is not advisory. Fix the
  operation, or state plainly that no watcher is running — never send a response describing the
  operation as monitored.
- Exit 3 from `--reconcile` means recovering that watcher is the first task of the session, ahead
  of unrelated work.
- Exit 2 means `progress.json` could not be read, so the state of every operation is unknown. That
  is not the same answer as none, and it must never be reported as one.
- A final response ends active execution. An operation that was only session-watched is unwatched
  the moment the turn ends, whatever was said about it beforehand.
