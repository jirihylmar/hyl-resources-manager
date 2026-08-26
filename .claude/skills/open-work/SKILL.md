---
name: open-work
description: Render the operator's open-work tables — current phase, stuck elsewhere, deferred — from this project's progress.json, with every mechanical column filled and only the plain-words column left to write. Also reports a stale or non-existent current_task/current_phase pointer. Invoke when presenting session handoff or a progress summary, or when asked what is open, what is stuck, what is deferred, or where a phase stands.
---

# open-work

Deterministic rendering of the three tables `/start-session` Step 4 and `/update-progress`
Step 12 must show the operator.

## The design rule

> **Which rows exist is computed. What they mean is written. Never the other way round.**

Every mechanical column — task id, state, phase label, open counts, stuck-since date, one row
per deferred phase — comes from `progress.json`. The one column a script cannot produce, *"In
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

The script reads **one file**: `progress.json`. No dependencies, no network, no writes.

**It used to read a second, and that was the mistake.** Until 2026-08-26 it also read
`consult_notes.md` beside it and rendered an **Open consult cycles** table, reasoning that a cycle
closed `agreed-proposed` or `disputed` exists nowhere else. What that actually created was a second
open-work channel with no closure rule. `agreed-proposed` is the *success* outcome — the reviewer
proposed work and the operator approved it — so the better a review went, the more permanently it
sat under "awaits the operator". One cycle whose proposal had been approved, delivered and
completed as an entire phase was still being rendered as open at every session start, and every
future successful review would have added another row that nothing could ever remove. That is the
retired `backlog` array in a different file.

The operator's direction, 2026-08-26: *"creating growing track of issues separatelly is a polution.
we have progress json to govern the project. consultation is in > discusions > task updated in
progress > end."* So the table was **deleted** rather than given a disposition grammar. A consult
that produces work produces *tasks*, through `/add-work`, in `progress.json` — which this renderer
already reads. `consult_notes.md` remains the full evidence trail, committed and pushed with the
project: every word the reviewer wrote is in it, and it is read by opening it, not by this script.

## Exit codes

| Code | Meaning | What to do |
|---|---|---|
| `0` | tables rendered | paste, fill, show |
| `2` | `progress.json` missing, unreadable, or **structurally unrenderable** — no recognisable `phases`, an **empty** `phases`, a `tasks` value that is not a list, duplicate derived phase keys in a list-shaped file, or a `backlog` that is not a list | **report it to the operator verbatim** — this is a real defect in that project's tracking file, and it is why the code is not `0`-with-empty-output: *"no open work"* and *"I could not read the file"* must never look the same. Each of those five shapes used to render as *"No open work"* at exit 0 while holding real tasks, or crash with a traceback outside this contract entirely (consult cycle `20260825-173617-18311a2`) |

## Open work is tasks and phases. Nothing else.

Until 2026-08-25 this renderer also read a top-level `backlog` array and printed every open entry
under **Deferred work** with an **Open** count. That array was an untyped string list with no
owner, no authorization, no closure and no phase — `/add-work` offered *"just noting"* and defined
no home for it — so findings accumulated there instead of becoming tasks, estate notices, or
nothing. In the estate's own central repository it reached **43 entries against 0–4 everywhere
else**, and an operator reading this renderer's output saw *"20+ opened tasks"* in a project whose
247 tasks were all terminal.

The channel is retired. Where a recorded concern goes is now `/add-work` § *The Four Destinations*.
A project whose `progress.json` still carries the key is **told so once**, in a note that names the
contract — not a table and not a count, because presenting untriaged records as work is the defect,
and silence about them would be the other half of it.

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
| a legacy `backlog` key | **reported once as a retired channel, never rendered as work.** It was an untyped array with no owner, no authorization and no closure; see § *Open work is tasks and phases* below |

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
