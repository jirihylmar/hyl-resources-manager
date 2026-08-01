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

No dependencies, no network, no writes. Reads one file.

Usage:
    python3 open_work.py [--file progress.json]

Exit codes:
    0  tables rendered
    2  progress.json missing, unreadable, or carrying no recognisable phases
       (deliberately not 0-with-empty-output: "no open work" and "I could not read it"
        must never look identical to the reader)
"""

import collections
import json
import sys

DONE = ("complete", "superseded")


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
        return collections.OrderedDict(
            (str(k), v) for k, v in raw.items() if isinstance(v, dict)
        )
    if isinstance(raw, list):
        out = collections.OrderedDict()
        for i, phase in enumerate(raw):
            if not isinstance(phase, dict):
                continue
            key = (phase.get("key") or phase.get("id") or phase.get("phase")
                   or phase.get("name") or "phase_%d" % (i + 1))
            out[str(key)] = phase
        return out or None
    return None


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
    """Dict tasks only, plus a count of entries too malformed to render."""
    raw = phase.get("tasks") or []
    if not isinstance(raw, list):
        return [], 0
    good = [t for t in raw if isinstance(t, dict)]
    return good, len(raw) - len(good)


def _label_reads_closed(label):
    """A backlog entry that OPENS by announcing its own resolution is closed. The convention
    in these files is to keep the item and rewrite it as a record — 'RESOLVED <date> by ...' —
    rather than delete it, precisely so the history survives. Anchored to the start so an item
    that merely MENTIONS a resolution ('blocked until X is resolved') stays open."""
    return str(label).lstrip("*_# ").upper().startswith(("RESOLVED", "SUPERSEDED", "CLOSED", "DONE"))


def backlog_entry(item):
    """-> (label, is_open). A backlog item may be a plain string or an object. Objects
    carry their own closure signals; rendering a resolved item as open work is a false
    alarm, and false alarms train a reader to skim past the whole section.

    STRINGS GET THE SAME TEST AS OBJECTS. They used to return (item, True) unconditionally —
    open, always, no matter what they said — so an entry rewritten to 'RESOLVED 2026-08-01 by
    phase 16' kept rendering as open work in every session handoff forever. The closure test
    below already existed; strings simply returned before reaching it."""
    if isinstance(item, str):
        return item, not _label_reads_closed(item)
    if not isinstance(item, dict):
        return str(item), True
    label = item.get("title") or item.get("name") or json.dumps(item)[:160]
    status = str(item.get("status") or "").lower()
    closed = bool(item.get("resolved") or item.get("resolution")) or any(
        w in status for w in ("resolved", "superseded", "closed", "complete")
    ) or _label_reads_closed(label)
    return label, not closed


def phase_of(phases, task_id):
    for key, phase in phases.items():
        for task in tasks_of(phase)[0]:
            if task.get("id") == task_id:
                return key
    return None


def state_of(task, current_task):
    status = task.get("status", "pending")
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

    phases = normalize_phases(data.get("phases"))
    if phases is None:
        die("%s carries no recognisable 'phases' (expected an object or a list)" % path)

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
    resolved = phase_of(phases, current_task) if current_task else None
    if current_phase and current_phase not in phases:
        notes.append("current_phase '%s' does not exist in phases" % short(current_phase, 60))
        current_phase = None
    if current_phase and phases[current_phase].get("status") in DONE:
        notes.append("current_phase '%s' is marked %s — the pointer is stale"
                     % (current_phase, phases[current_phase]["status"]))
    if current_task and resolved is None:
        notes.append("current_task '%s' matches no task in any phase" % current_task)
    elif current_task:
        task = next(t for t in tasks_of(phases[resolved])[0] if t.get("id") == current_task)
        if task.get("status") in DONE:
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
        rows = [t for t in tasks_of(phase)[0] if t.get("status") not in DONE]
        out.append("**%s — %s** (%d open)"
                   % (phase_label(current_phase),
                      short(phase.get("name", current_phase)), len(rows)))
        out.append("")
        if rows:
            out.append("| Task | In plain words | State |")
            out.append("|------|----------------|-------|")
            for task in rows:
                out.append("| %s | %s | %s |"
                           % (task.get("id", "?"),
                              fill("what %s actually is, needing no other document open — "
                                   "NOT its name repeated: %s"
                                   % (task.get("id", "?"), short(task.get("name", "")))),
                              state_of(task, current_task)))
                rendered_rows += 1
        else:
            out.append("_No open tasks in the current phase — it is ready to close "
                       "(/update-progress Step 3a)._")
        out.append("")

    # --- bucket 2: stuck elsewhere ---
    stuck = [(t, p) for k, p in phases.items() if k != current_phase
             for t in tasks_of(p)[0] if t.get("status") in ("in_progress", "blocked")]
    if stuck:
        out.append("**Stuck elsewhere**")
        out.append("")
        out.append("| Task | In plain words | Stuck since | Why it's still here |")
        out.append("|------|----------------|-------------|---------------------|")
        for task, phase in stuck:
            out.append("| %s | %s | %s | %s |"
                       % (task.get("id", "?"),
                          fill("what %s is: %s"
                               % (task.get("id", "?"), short(task.get("name", "")))),
                          stuck_since(task, phase),
                          fill("blocked on what, or: abandoned mid-flight")))
            rendered_rows += 1
        out.append("")

    # --- bucket 3: deferred (pending elsewhere + every open backlog item) ---
    deferred = []
    for key, phase in phases.items():
        if key == current_phase or phase.get("status") in DONE:
            continue
        pending = [t for t in tasks_of(phase)[0] if t.get("status") == "pending"]
        if pending:
            deferred.append((phase_label(key), short(phase.get("name", key)), len(pending)))

    backlog, closed_backlog = [], 0
    for item in (data.get("backlog") or []):
        label, is_open = backlog_entry(item)
        if is_open:
            backlog.append(label)
        else:
            closed_backlog += 1

    if deferred or backlog:
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
        for label in backlog:
            out.append("| Backlog | %s | — |"
                       % fill("in plain words, no jargon: %s" % short(label, 160)))
            rendered_rows += 1
        out.append("")
    if closed_backlog:
        out.append("_%d further backlog item%s carr%s a resolution and %s not shown._"
                   % (closed_backlog, "" if closed_backlog == 1 else "s",
                      "ies" if closed_backlog == 1 else "y",
                      "is" if closed_backlog == 1 else "are"))
        out.append("")

    if rendered_rows == 0 and not current_block:
        # Explicit, because an empty render and a broken render must not look alike.
        out.append("_No open work in progress.json: every phase complete or superseded, "
                   "and no open backlog item._")

    print("\n".join(out).rstrip())
    print()
    print("<!-- Every <FILL: …> above MUST be replaced before this is shown to the "
          "operator. A surviving token is a rendering pasted but never read. -->")
    return 0


if __name__ == "__main__":
    sys.exit(main())
