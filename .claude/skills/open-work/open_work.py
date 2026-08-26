#!/usr/bin/env python3
"""Render the operator's open-work tables from progress.json.

WHY THIS EXISTS
---------------
The three tables (current / stuck / deferred) were specified in prose inside a fenced
template block. Twice in two days, on two different hosts, a session rendered them as
prose instead: an 11-task phase collapsed to one sentence, and deferred phases printed
as bare numbers ("Phase 66 (1)") — the exact "an ID alone is not a description" failure
the section exists to prevent. Both hosts had the correct file; one was even `overlay-ok`
with zero drift. So the defect was never delivery and never capability: rendering the
table was left as a judgement call, made 180 lines into a fenced block.

This script removes the judgement. Which rows exist, and every mechanical column, is
computed from progress.json. What CANNOT be computed — what a task MEANS in plain words —
is emitted as an explicit <FILL: ...> token the agent must replace before the report is
shown. A missing row stops being a rendering choice, and an unreplaced token is visible
in the output rather than silently absent from it.

SHAPE TOLERANCE IS DELIBERATE. Measured across 34 live projects, `progress.json` is not
one schema: `phases` appears as both an object and a list, and one project's `tasks`
array holds bare strings. A renderer that assumes the template's shape crashes on the
projects that need it most — the old ones, which are exactly where work goes invisible.
Anything unreadable is REPORTED, never silently dropped.

OPEN WORK IS TASKS AND PHASES. NOTHING ELSE. Until 2026-08-25 this renderer also read a
top-level `backlog` array and printed every open entry under "Deferred work" with an "Open"
count. That array was an untyped string list with no owner, no authorization, no closure and
no phase — /add-work offered "just noting" and defined no home for it — so findings accumulated
there instead of becoming tasks, estate notices, or nothing. In the estate's own central repo it
reached 43 entries against 0-4 everywhere else, and an operator reading this renderer's output saw
"20+ opened tasks" in a project whose 247 tasks were ALL terminal. The channel is retired
(/add-work § Where a recorded concern goes). A legacy `backlog` key is REPORTED as a retired
channel and never rendered as work.

No dependencies, no network, no writes. Reads ONE file: progress.json.

Until 2026-08-26 it also read consult_notes.md beside it and rendered an "Open consult cycles"
table, on the reasoning that a cycle closed `agreed-proposed` or `disputed` lives only in that log.
That made the consult log a second open-work channel with no closure rule — a cycle whose proposal
the operator had approved, delivered and completed as a whole phase still rendered as "awaits the
operator", forever, and every future successful review added another permanent row. It was the
retired `backlog` in a different file. The operator's direction, 2026-08-26: "creating growing track
of issues separatelly is a polution. we have progress json to govern the project. consultation is in
> discusions > task updated in progress > end." So the table is gone rather than given a grammar:
progress.json governs, and consult_notes.md is evidence to read, not work to track.

Usage:
    python3 open_work.py [--file progress.json]

Exit codes:
    0  tables rendered
    2  progress.json missing, unreadable, or STRUCTURALLY UNRENDERABLE — no recognisable
       phases, an empty phases object, a `tasks` value that is not a list, duplicate derived
       phase keys in a list-shaped file, or a `backlog` key that is not a list.
       (deliberately not 0-with-empty-output: "no open work" and "I could not read it"
        must never look identical to the reader. Each of those five shapes used to render as
        "No open work" at exit 0 while holding real tasks, or crash with a traceback outside
        this contract entirely — found by consult cycle 20260825-173617-18311a2.)
"""

import collections
import json
import sys

# Terminal statuses — every spelling that means "this is finished", because the estate uses
# several and identity must not depend on spelling. MEASURED across 27 progress.json files
# (2026-08-06): `complete` and `completed` are both live, one project carrying 100 tasks spelt
# `completed`. With only two spellings terminal, those 100 finished tasks rendered as OPEN WORK
# in that project's current phase. The inverse cost the estate more: bucket 3 asked for
# `status == "pending"` and so hid 19 genuinely-open tasks spelt `postponed` or `deferred`.
DONE = ("complete", "completed", "superseded", "done", "closed", "dropped",
        "cancelled", "canceled", "resolved", "obsolete", "abandoned")

# Statuses bucket 2 owns. Named once, so bucket 3 can exclude exactly what bucket 2 took and
# the two cannot drift into double-rendering or into a gap between them.
ACTIVE = ("in_progress", "blocked")


def _st(obj):
    """A status, normalised. Spelling and whitespace vary across the estate; identity does not."""
    return str((obj or {}).get("status") or "").strip().lower()


def is_terminal(obj):
    return _st(obj) in DONE


def die(message):
    print("ERROR: %s" % message, file=sys.stderr)
    sys.exit(2)


def fill(what):
    return "<FILL: %s>" % what


def short(text, limit=110):
    """Table cells must stay scannable. Some projects store an essay as a phase name (one
    measured at ~1,400 characters); rendering it verbatim produces a table no operator can
    read — the same invisibility this script exists to remove, with the opposite cause.
    Cut at a sentence boundary where there is one, else hard-truncate."""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    stop = max(cut.rfind(". "), cut.rfind(" — "), cut.rfind("; "))
    return (cut[:stop] if stop > limit // 2 else cut).rstrip(" ,;:—-") + " …"


def normalize_phases(raw):
    """-> OrderedDict(key -> phase dict), from either shape. None if unrecognisable."""
    if isinstance(raw, dict):
        # `or None`, because an EMPTY OrderedDict is not None and used to sail through the
        # caller's `is None` guard: `{"phases": {}}` rendered "No open work" at exit 0, which is
        # the file's documented exit-2 case wearing the all-clear's clothes.
        return collections.OrderedDict(
            (str(k), v) for k, v in raw.items() if isinstance(v, dict)
        ) or None
    if isinstance(raw, list):
        out = collections.OrderedDict()
        for i, phase in enumerate(raw):
            if not isinstance(phase, dict):
                continue
            key = (phase.get("key") or phase.get("id") or phase.get("phase")
                   or phase.get("name") or "phase_%d" % (i + 1))
            key = str(key)
            if key in out:
                # Two phases deriving the same key silently overwrote the first — a whole phase
                # and every task in it disappearing while exit 0 reported success. Refuse instead.
                DUPLICATE_KEYS.append(key)
            out[key] = phase
        return out or None
    return None


#: Filled by normalize_phases when a list-shaped `phases` derives the same key twice. A module
#: global rather than a return value because normalize_phases has one job and three callers.
DUPLICATE_KEYS = []


def phase_label(key):
    """'phase_10_independent_hosts' -> 'Phase 10'; '7' -> 'Phase 7'. Falls back to the raw
    key, because a project free to name its phases anything must still get a row."""
    parts = str(key).split("_")
    if len(parts) >= 2 and parts[0].lower() == "phase" and parts[1].isdigit():
        return "Phase %s" % parts[1]
    if str(key).isdigit():
        return "Phase %s" % key
    return short(key, 40)


def tasks_of(phase):
    """Dict tasks only, plus a count of entries too malformed to render.

    A `tasks` value that is not a list is NOT handled here — `structural_problems()` refuses the
    whole file first. Returning ([], 0) for it, as this did until 2026-08-25, meant a phase whose
    tasks were stored as an object rendered as having none: real open work, invisible, exit 0."""
    raw = phase.get("tasks") or []
    if not isinstance(raw, list):
        return [], 0
    good = [t for t in raw if isinstance(t, dict)]
    return good, len(raw) - len(good)


def structural_problems(data, phases):
    """-> [str]. Shapes this renderer cannot honestly render. Any one of them exits 2.

    Shape TOLERANCE is deliberate and stays (see the module docstring): phases as an object or a
    list, tasks as a list holding bare strings, any status vocabulary. Shape SILENCE is the bug.
    The line between them is whether the renderer can still see every task: it can tolerate a task
    it cannot describe, and it cannot tolerate a container it cannot enumerate."""
    problems = []
    for key, phase in phases.items():
        raw = phase.get("tasks")
        if raw is not None and not isinstance(raw, list):
            problems.append(
                "phase '%s' stores `tasks` as %s, not a list — every task in it would be "
                "invisible, so nothing is rendered" % (short(key, 40), type(raw).__name__))
    for key in DUPLICATE_KEYS:
        problems.append(
            "two phases in the list-shaped `phases` derive the same key '%s' — the second "
            "overwrites the first and a whole phase disappears" % short(key, 40))
    legacy = data.get("backlog")
    if legacy is not None and not isinstance(legacy, list):
        problems.append(
            "`backlog` is %s, not a list — it is a retired channel, but a malformed one is a "
            "sign the file was edited by hand" % type(legacy).__name__)
    return problems


def cell(value, limit=110):
    """A value safe to interpolate into a Markdown table cell.

    Table values were interpolated raw, so a `|` in a task id or a phase name
    produced extra columns and a newline broke the row entirely — the deterministic table shape
    this script exists to guarantee, destroyed by its own content. Escape the delimiter, flatten
    whitespace, then shorten."""
    text = " ".join(str(value).split()).replace("|", "\\|")
    return short(text, limit)


def phase_of(phases, task_id):
    for key, phase in phases.items():
        for task in tasks_of(phase)[0]:
            if task.get("id") == task_id:
                return key
    return None


def state_of(task, current_task):
    status = _st(task) or "pending"
    if status == "blocked":
        return "blocked"
    if status == "in_progress":
        return "working on it now"
    if task.get("id") == current_task:
        return "next"
    return "not started"


def stuck_since(task, phase):
    for key in ("started_at", "added_at", "added_on"):
        if task.get(key):
            return task[key]
    return phase.get("started_at") or "unknown"


def main():
    path = "progress.json"
    argv = sys.argv[1:]
    for i, arg in enumerate(argv):
        if arg == "--file" and i + 1 < len(argv):
            path = argv[i + 1]
        elif arg.startswith("--file="):
            path = arg.split("=", 1)[1]

    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        die("%s not found — run this from the project root" % path)
    except (OSError, ValueError) as exc:
        die("%s unreadable: %s" % (path, exc))
    if not isinstance(data, dict):
        die("%s is not a JSON object" % path)

    del DUPLICATE_KEYS[:]           # module global; a second call in one process must not inherit
    phases = normalize_phases(data.get("phases"))
    if phases is None:
        die("%s carries no recognisable 'phases' — expected a non-empty object or list. An EMPTY "
            "`phases` is this case too: there is nothing to render and nothing to report as open, "
            "and saying 'no open work' about a file with no phases is a guess, not a reading."
            % path)
    problems = structural_problems(data, phases)
    if problems:
        die("%s cannot be rendered honestly:\n  - %s" % (path, "\n  - ".join(problems)))

    current_task = data.get("current_task")
    if isinstance(current_task, str) and len(current_task) <= 40:
        long_pointer = None
    else:
        # A pointer that is prose is not a pointer. Say so rather than matching nothing.
        long_pointer, current_task = current_task, None
    current_phase = data.get("current_phase")
    if current_phase is not None:
        # Keys are normalised to str, so a numeric pointer (measured live: `"current_phase": 9`
        # against a list-shaped file keyed "9") must be compared as one — otherwise the
        # renderer invents a "does not exist" defect that is purely its own type mismatch.
        current_phase = str(current_phase)

    # --- pointer sanity: a stale pointer silently redefines "current", so every bucket
    # below inherits the error. Say it before rendering anything. ---
    notes = []
    malformed = sum(tasks_of(p)[1] for p in phases.values())
    if malformed:
        notes.append("%d task entr%s in progress.json %s not objects and cannot be "
                     "rendered — inspect them by hand"
                     % (malformed, "y" if malformed == 1 else "ies",
                        "is" if malformed == 1 else "are"))
    if long_pointer:
        notes.append("current_task is not a task id (it holds %d characters) — nothing "
                     "can point at it" % len(str(long_pointer)))
    # ABSENT, not merely stale. /start-session § 4.0a promises a pointer report when either
    # pointer is "stale, absent, or not an id"; only the first two of those three were ever
    # emitted, so a file with both pointers null — the normal state at a clean session close, and
    # the state of this repo's own file — reported nothing at all and the reader could not tell
    # "deliberately parked" from "the pointer was lost".
    absent = [n for n in ("current_task", "current_phase") if data.get(n) in (None, "")]
    if absent:
        notes.append("%s %s absent — no task is scheduled. That is a legitimate state at a clean "
                     "close; it is reported so it cannot be mistaken for a lost pointer"
                     % (" and ".join(absent), "is" if len(absent) == 1 else "are"))
    resolved = phase_of(phases, current_task) if current_task else None
    if current_phase and current_phase not in phases:
        notes.append("current_phase '%s' does not exist in phases" % short(current_phase, 60))
        current_phase = None
    if current_phase and is_terminal(phases[current_phase]):
        notes.append("current_phase '%s' is marked %s — the pointer is stale"
                     % (current_phase, phases[current_phase]["status"]))
    if current_task and resolved is None:
        notes.append("current_task '%s' matches no task in any phase" % current_task)
    elif current_task:
        task = next(t for t in tasks_of(phases[resolved])[0] if t.get("id") == current_task)
        if is_terminal(task):
            notes.append("current_task '%s' is already %s — the pointer is stale"
                         % (current_task, task["status"]))
        if current_phase and resolved != current_phase:
            notes.append("current_task '%s' lives in '%s', but current_phase says '%s'"
                         % (current_task, resolved, current_phase))
    if not current_phase:
        current_phase = resolved

    out = []
    if notes:
        out.append("> **progress.json pointer check — report these, do not silently fix them:**")
        out.extend("> - %s" % n for n in notes)
        out.append("")

    rendered_rows = 0
    current_block = bool(current_phase and current_phase in phases)

    # --- bucket 1: the current phase ---
    if current_block:
        phase = phases[current_phase]
        rows = [t for t in tasks_of(phase)[0] if not is_terminal(t)]
        out.append("**%s — %s** (%d open)"
                   % (phase_label(current_phase),
                      short(phase.get("name", current_phase)), len(rows)))
        out.append("")
        if rows:
            out.append("| Task | In plain words | State |")
            out.append("|------|----------------|-------|")
            for task in rows:
                out.append("| %s | %s | %s |"
                           % (cell(task.get("id", "?"), 40),
                              fill("what %s actually is, needing no other document open — "
                                   "NOT its name repeated: %s"
                                   % (cell(task.get("id", "?"), 40), cell(task.get("name", "")))),
                              state_of(task, current_task)))
                rendered_rows += 1
        else:
            out.append("_No open tasks in the current phase — it is ready to close "
                       "(/update-progress Step 3a)._")
        out.append("")

    # --- bucket 2: stuck elsewhere ---
    stuck = [(t, p) for k, p in phases.items() if k != current_phase
             for t in tasks_of(p)[0] if _st(t) in ACTIVE]
    if stuck:
        out.append("**Stuck elsewhere**")
        out.append("")
        out.append("| Task | In plain words | Stuck since | Why it's still here |")
        out.append("|------|----------------|-------------|---------------------|")
        for task, phase in stuck:
            out.append("| %s | %s | %s | %s |"
                       % (cell(task.get("id", "?"), 40),
                          fill("what %s is: %s"
                               % (cell(task.get("id", "?"), 40), cell(task.get("name", "")))),
                          cell(stuck_since(task, phase), 40),
                          fill("blocked on what, or: abandoned mid-flight")))
            rendered_rows += 1
        out.append("")

    # --- bucket 3: deferred (pending tasks in a non-current phase) ---
    # EVERY non-current phase is examined, INCLUDING the ones marked complete. § 4.0a promises
    # "nothing tracked is ever invisible at session start"; skipping closed phases broke that
    # promise for 28 task rows across 7 projects, and in the no-current-phase case the renderer
    # went on to print "No open work in progress.json" while holding some. A phase that claims
    # completion while a child claims otherwise is not deferred work — it is a CONTRADICTION,
    # and it is labelled as one rather than folded in beside ordinary planned work.
    deferred = []
    for key, phase in phases.items():
        if key == current_phase:
            continue
        open_tasks = [t for t in tasks_of(phase)[0]
                      if not is_terminal(t) and _st(t) not in ACTIVE]
        if not open_tasks:
            continue
        label = phase_label(key)
        if is_terminal(phase):
            label += " ⚠ phase says %s" % _st(phase)
        deferred.append((label, cell(phase.get("name", key)), len(open_tasks)))

    if deferred:
        out.append("**Deferred work**")
        out.append("")
        out.append("| Where | In plain words | Open |")
        out.append("|-------|----------------|------|")
        for label, name, count in deferred:
            out.append("| %s — %s | %s | %d task%s |"
                       % (label, name,
                          fill("what this phase is FOR, one line — not its title again"),
                          count, "" if count == 1 else "s"))
            rendered_rows += 1
        out.append("")

    if rendered_rows == 0 and not current_block:
        # Explicit, because an empty render and a broken render must not look alike.
        out.append("_No open work in progress.json: every task carries a terminal status._")

    # A project that still carries the retired channel is TOLD, once, in the words of the contract.
    # Not a table and not a count: these records were never authorized, never owned and never
    # closable, so presenting them as work is the defect this task removed. Silence would be the
    # other half of it — 12 projects still hold entries, and their operators should know why they
    # stopped appearing.
    legacy = data.get("backlog")
    if isinstance(legacy, list) and legacy:
        out.append("")
        out.append("> **Retired channel:** this progress.json still carries a `backlog` array with "
                   "%d entr%s. It is not open work and is not rendered: it had no owner, no "
                   "authorization and no closure. Route each entry to one of the four destinations "
                   "in /add-work § Where a recorded concern goes, then remove the key."
                   % (len(legacy), "y" if len(legacy) == 1 else "ies"))

    print("\n".join(out).rstrip())
    print()
    print("<!-- Every <FILL: …> above MUST be replaced before this is shown to the "
          "operator. A surviving token is a rendering pasted but never read. -->")
    return 0


if __name__ == "__main__":
    sys.exit(main())
