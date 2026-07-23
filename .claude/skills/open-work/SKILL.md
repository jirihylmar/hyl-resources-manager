---
name: open-work
description: Render the operator's open-work tables — current phase, stuck elsewhere, deferred, plus every backlog item — from this project's progress.json, with every mechanical column filled and only the plain-words column left to write. Also reports a stale or non-existent current_task/current_phase pointer. Invoke when presenting session handoff or a progress summary, or when asked what is open, what is stuck, what is deferred, or where a phase stands.
---

# open-work

Deterministic rendering of the three tables `/start-session` Step 4 and `/update-progress`
Step 12 must show the operator.

## The design rule

> **Which rows exist is computed. What they mean is written. Never the other way round.**

Every mechanical column — task id, state, phase label, open counts, stuck-since date, one row
per backlog item — comes from `progress.json`. The one column a script cannot produce, *"In
plain words"*, is emitted as a `<FILL: …>` token that **must** be replaced before the operator
sees it. A surviving `<FILL:` in a report means output was pasted and never read.

## Why it is a script and not a paragraph

The three tables were specified in prose, inside a fenced template block, ~180 lines into a
report spec. Twice in two days, on two different hosts, sessions rendered them as prose instead:
an 11-task phase collapsed to a single sentence, and deferred phases printed as bare numbers
(`Phase 66 (1)`) — precisely the *"an ID alone is not a description"* failure the section exists
to prevent. Both hosts held the correct file; one was `overlay-ok` with zero drift. Delivery was
never the problem, and neither was capability: **rendering was a judgement call, so it got
judged away.** A row that a script emits is a row that cannot be dropped for brevity.

## Procedure

```
python3 .claude/skills/open-work/open_work.py            # from the project root
python3 .claude/skills/open-work/open_work.py --file <path to a progress.json>
```

Paste the output verbatim into the report, then replace **every** `<FILL: …>` token. Do not
summarise the tables into prose, and do not drop rows because a phase "isn't relevant right
now" — deferred work being invisible is the condition this exists to end.

The script reads one file. No dependencies, no network, no writes.

## Exit codes

| Code | Meaning | What to do |
|---|---|---|
| `0` | tables rendered | paste, fill, show |
| `2` | `progress.json` missing, unreadable, or carrying no recognisable `phases` | **report it to the operator verbatim** — this is a real defect in that project's tracking file, and it is why the code is not `0`-with-empty-output: *"no open work"* and *"I could not read the file"* must never look the same |

## What it tolerates, and why that is deliberate

Measured across 34 live projects, `progress.json` is **not** one schema. The renderer therefore
accepts what exists rather than what the template prescribes:

| Variant found live | Handling |
|---|---|
| `phases` as an **object** (template shape) | keys used as phase keys |
| `phases` as a **list** | key taken from `key`/`id`/`phase`/`name`, else position |
| `tasks` holding **bare strings** | skipped, and the count is **reported** in the pointer-check block — never silently dropped |
| `current_phase` as a **number** against string keys | compared as strings, so the renderer does not invent a defect out of its own type mismatch |
| `current_task` holding **prose** instead of an id | reported as *"not a task id"* — a pointer that is a paragraph points at nothing |
| `backlog` items as **objects** carrying `resolved`/`resolution`/closed status | the open ones are listed by title; the closed ones are counted in one line, not rendered as open work |

A renderer that assumed the template's shape would crash on the projects that need it most: the
old ones, which are exactly where work goes invisible.

## What it will not do

- **Judge the quality of the plain-words column.** A lazy restatement of the task name still
  passes. The script removes *invisibility*, not carelessness.
- **Fix a stale pointer.** It names it. Editing `progress.json` is `/update-progress`'s job and
  the operator's decision.
- **Decide what "stuck" means for your project.** `in_progress`/`blocked` outside the current
  phase is the rule, applied uniformly.

## Related

- `/start-session` Step 4 — presents the handoff; calls this before rendering.
- `/update-progress` Step 12 — the same tables at session close; calls this too.
