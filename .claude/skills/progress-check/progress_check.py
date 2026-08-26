#!/usr/bin/env python3
"""progress_check.py — mechanical integrity check for progress.json.

Exit 0 = OK (warnings may still print) · 1 = FAIL, do not commit · 2 = could not check.

WHY THIS EXISTS — three real corruptions, none of which any prior check could see:

  1. TRAILING PHASE (found live in 2 of 34 projects, committed 2026-03-11 and 2026-03-26,
     undetected for four months). A whole phase object was appended AFTER the closing brace of
     `phases`, landing outside the JSON document:  {...}  ,  "phase_11_x": {...}
     The agent wrote the phase, committed it, and reported success. Every reader since has seen a
     file that does not parse — or, where a reader guards with try/except, silently seen NOTHING.

  2. DUPLICATE KEY (2026-07-30). An insertion orphaned one task's fields into the next task, so a
     task object carried two "verify" keys. This is VALID JSON: json.load keeps the last and drops
     the first, silently. A parse check passes. The real value is simply gone. Nothing anywhere
     reports it.

  3. MISSING COMMA (2026-07-30, x3). The cheap one — it does not parse, so it is loud.

Only (3) is loud. (1) is loud but was never checked. (2) is SILENT even to a parse check, which is
why this file uses object_pairs_hook rather than plain json.load.

DESIGN RULE — tolerate every shape that really exists; fail only on what is unambiguously broken.
Measured across 34 live projects: `phases` is a dict in 30 and a LIST in 2; `tasks` is a list in
most and a DICT in one; some tasks are bare strings; status vocabularies disagree ("complete" vs
"completed"). A checker that enforced the template's shape would block commits in real projects and
be disabled within a day — which is worse than no checker. So: no schema, no vocabulary, no style.
Four failures only — three that destroy data, plus the append-only policy (a vanished task id
or phase key) enforced mechanically.
"""
import argparse
import datetime
import json
import re
import subprocess
import sys


# --- parse with duplicate-key detection -------------------------------------
class DuplicateKey(ValueError):
    pass


def _no_dup_pairs(path):
    """object_pairs_hook that records duplicate keys with their JSON path."""
    def hook(pairs):
        seen = {}
        for k, v in pairs:
            if k in seen:
                path.append(k)
            seen[k] = v
        return seen
    return hook


def parse_strict(text):
    """Return (obj, duplicate_key_names). Raises ValueError if it does not parse."""
    dups = []
    obj = json.loads(text, object_pairs_hook=_no_dup_pairs(dups))
    return obj, dups


# --- iteration helpers that tolerate every measured shape -------------------
def iter_phases(doc):
    """Yield (phase_key, phase_obj) for dict-shaped AND list-shaped `phases`."""
    ph = doc.get("phases") if isinstance(doc, dict) else None
    if isinstance(ph, dict):
        for k, v in ph.items():
            yield str(k), v
    elif isinstance(ph, list):
        for i, v in enumerate(ph):
            key = None
            if isinstance(v, dict):
                for cand in ("key", "id", "phase", "name"):
                    if v.get(cand):
                        key = str(v[cand])
                        break
            yield (key or f"[{i}]"), v


def iter_tasks(phase_obj):
    """Yield task objects for list-shaped AND dict-shaped `tasks`; skip bare strings."""
    if not isinstance(phase_obj, dict):
        return
    ts = phase_obj.get("tasks")
    if isinstance(ts, list):
        items = ts
    elif isinstance(ts, dict):
        items = list(ts.values())
    else:
        return
    for t in items:
        if isinstance(t, dict):
            yield t


# --- completion dates, for the freshness warning ----------------------------
# Anchored, and the calendar decides. A bare prefix test read '2026-08-25garbage' as a date by
# silently truncating it, and accepted '2026-99-99' — which is the worse of the two, because a bogus
# far-future value does not merely escape the malformed warning, it becomes the MAXIMUM of the
# comparison and slanders every real date in the file with a false staleness warning.
# Found by the reviewer, consult cycle 20260825-164306-1335b9f.
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ].*)?$")

#: BOTH spellings, on tasks AND on phases. Measured in this repo's own progress.json on
#: 2026-08-25: 158 tasks carry `completed_at`, 58 carry `completed`, and the two sets are
#: DISJOINT — an older vocabulary that is still live in the same file. 27 phases carry
#: `completed_at`. A check that read only `completed_at` would silently miss 58 real completion
#: dates in the very file it was written for. Same DESIGN RULE as the rest of this module:
#: tolerate every shape that really exists.
COMPLETION_KEYS = ("completed_at", "completed")


def iso_date(v):
    """'YYYY-MM-DD' if v is a string shaped like an ISO date, else None.

    Values in the wild are both bare dates ("2026-08-25") and timestamps
    ("2025-12-20T10:00:00Z" — the template's own example), so everything is truncated to its
    first 10 characters and compared as a string. Anything not matching the shape is not a date
    and is reported as malformed rather than guessed at.
    """
    if not isinstance(v, str) or not _ISO_DATE.match(v):
        return None
    try:
        datetime.date.fromisoformat(v[:10])
    except ValueError:
        return None
    return v[:10]


def is_absent(v):
    """True for a value that means "no date here", as opposed to a broken one.

    Two shapes mean absence and neither is malformed:
      None          the live placeholder for "not completed yet" — measured 2026-08-25, 23 of them
                    across 9 of 28 local projects.
      "{{...}}"     an unsubstituted template placeholder. progress.json.bootstrap ships
                    `{{CREATION_DATE}}` as last_updated and on task 0.1, and both example playbooks
                    carry it, so every freshly bootstrapped project would otherwise open its life
                    with a warning about a value the framework itself put there. /setup substitutes it.
    Calling either malformed would put a false warning on a large share of the estate, and a checker
    that cries wolf is a checker that gets switched off.
    """
    if v is None:
        return True
    return isinstance(v, str) and v.startswith("{{") and v.endswith("}}")


def completion_fields(doc):
    """Yield (label, key, raw_value) for every completion field on every phase and every task.

    Built on iter_phases/iter_tasks so every measured shape (phases as dict or list, tasks as
    list or dict, bare-string tasks) is tolerated exactly as it is everywhere else here.

    `status` is deliberately NOT consulted. This module enforces no vocabulary, and a task marked
    superseded that carries a completion date really was completed on that date — so its date
    counts like any other. Pinned by fixture F2 of scripts/test-progress-check-freshness.sh in
    the central repo, which fails loudly if that behaviour ever changes.
    """
    for pk, po in iter_phases(doc):
        if isinstance(po, dict):
            for k in COMPLETION_KEYS:
                if k in po:
                    yield f"phase {pk}", k, po[k]
        for t in iter_tasks(po):
            tid = t.get("id")
            label = f"phase {pk}: task {tid}" if tid is not None else f"phase {pk}: (task with no id)"
            for k in COMPLETION_KEYS:
                if k in t:
                    yield label, k, t[k]


def notice_markers(doc):
    """{(phase_key, task_id): estate_notice value or None} for every task that has an id.

    None means "the task is present and carries no marker", which is how a STRIPPED key is told
    apart from a task that never had one: the comparison is against the same key in the base
    version, so only a marker that existed and then vanished can fail.
    """
    out = {}
    for pk, po in iter_phases(doc):
        for t in iter_tasks(po):
            if t.get("id") is None:
                continue
            out[(pk, str(t["id"]))] = t.get("estate_notice")
    return out


def task_ids(doc):
    """{phase_key: [task ids]} — the append-only invariant operates on these."""
    out = {}
    for pk, po in iter_phases(doc):
        ids = [str(t["id"]) for t in iter_tasks(po) if t.get("id") is not None]
        out[pk] = ids
    return out


# --- started-task drift, for the mutability warning (phase 37, 2026-08-26) --
#: The task-mutability rule in /update-progress: a task is STARTED once it carries a real
#: `started_at` or a status outside this set; everything else is unstarted and may be refined in
#: place (scope, dependency and looser-verify changes still supersede — the rule bounds that, not
#: this module). This is a status vocabulary, which this module otherwise refuses to have — so it
#: is used only to decide whether to SAY something (check() § 4b), never whether to fail.
#: Case-insensitive.
UNSTARTED_STATUSES = {"pending", "not_started", "planned", "todo", ""}

#: The descriptive fields compared on a started task. The rule freezes `description` and the
#: dependency fields too, but these two are the ones every shipped task carries and the two that
#: change what "done" means — a drift check that compared everything would warn about the notes
#: field that the same rule explicitly allows to change.
DRIFT_FIELDS = ("name", "verify")

_ABSENT = object()   # so "field removed" and "field set to null" both read as a difference


def is_started(task):
    """True when the task has begun, by the same two signals the prose rule names.

    `started_at` counts when present, non-empty and not an unsubstituted `{{placeholder}}` — the
    bootstrap ships those, same carve-out as is_absent(). `status` counts when it is anything
    outside UNSTARTED_STATUSES: "in_progress", "completed", "complete", "superseded", "deferred",
    "blocked" all mean the task has a history worth keeping. Unknown spellings therefore lean
    towards STARTED, which errs on the side of a warning rather than of silence.
    """
    sa = task.get("started_at")
    if sa is not None and not (isinstance(sa, str) and (sa.strip() == "" or is_absent(sa))):
        return True
    st = task.get("status")
    if st is None:
        return False
    return str(st).strip().lower() not in UNSTARTED_STATUSES


def tasks_by_key(doc):
    """{(phase_key, task_id): task} for every task that has an id — the join the drift check runs on."""
    out = {}
    for pk, po in iter_phases(doc):
        for t in iter_tasks(po):
            if t.get("id") is not None:
                out[(pk, str(t["id"]))] = t
    return out


# --- the four checks --------------------------------------------------------
def check(text, base_text=None):
    """Return (failures, warnings). Empty failures == safe to commit."""
    fail, warn = [], []

    # 1. Parses at all — catches the missing comma AND the trailing phase.
    try:
        doc, dups = parse_strict(text)
    except ValueError as e:
        msg = str(e)
        fail.append(f"does not parse as JSON: {msg}")
        if "Extra data" in msg:
            fail.append(
                "  ^ 'Extra data' almost always means content was appended AFTER the final "
                "closing brace — typically a whole phase written outside the `phases` object. "
                "The content is still in the file; it is simply outside the document, so every "
                "reader sees nothing. Move it inside `phases` and re-run."
            )
        return fail, warn

    # 2. Duplicate keys — VALID JSON, silently drops a value. The invisible one.
    if dups:
        for k in sorted(set(dups)):
            fail.append(
                f"duplicate key {k!r} in one object — this parses, and json.load keeps only the "
                f"LAST value. The other one is already lost. Usually an edit that orphaned one "
                f"record's fields into its neighbour."
            )

    if not isinstance(doc, dict):
        fail.append(f"root of progress.json is {type(doc).__name__}, not an object")
        return fail, warn

    # 3. Duplicate task ids inside one phase — two records claiming to be the same task.
    for pk, ids in task_ids(doc).items():
        seen = set()
        for i in ids:
            if i in seen:
                fail.append(f"phase {pk}: task id {i!r} appears more than once")
            seen.add(i)

    # 4. Append-only: nothing that existed before may vanish. This is the framework's
    #    oldest written rule ("NEVER remove tasks — mark superseded instead"), and until now
    #    it was enforced by prose alone.
    if base_text is not None:
        try:
            base_doc, _ = parse_strict(base_text)
        except ValueError:
            warn.append("previous committed version does not parse — append-only not checked "
                        "against it (that is itself worth fixing)")
        else:
            before, after = task_ids(base_doc), task_ids(doc)
            for pk, ids in before.items():
                if pk not in after:
                    fail.append(f"phase {pk!r} existed in the previous commit and is now GONE "
                                f"({len(ids)} task(s) with it)")
                    continue
                missing = [i for i in ids if i not in set(after[pk])]
                for i in missing:
                    fail.append(f"phase {pk}: task {i!r} existed in the previous commit and is "
                                f"now GONE. Tasks are append-only — mark it superseded instead.")

            # 4a. An `estate_notice` marker may not be stripped from a task that kept its id.
            #     Reported by a receiving project 2026-08-06: /update-progress lists "remove the
            #     estate_notice key" under NEVER Do and states the consequence — the next central
            #     run appends a SECOND copy — while nothing checked it. Deleting the task was
            #     blocked by the id rule above; deleting just the key passed silently, which is
            #     the same data loss with a smaller blast radius and no alarm. This is inside
            #     this checker's charter: it destroys a marker other machinery depends on, and it
            #     is decided by comparing two committed versions — not by enforcing a schema.
            bn, an = notice_markers(base_doc), notice_markers(doc)
            for key, marker in bn.items():
                # BOTH halves are required and the first draft had only the second, which failed
                # every task that never carried a marker at all — caught by the control case in
                # the test, not by reading. Only a marker that EXISTED and then vanished is a loss.
                if marker is not None and key in an and an[key] is None:
                    pk, tid = key
                    fail.append(f"phase {pk}: task {tid!r} carried estate_notice "
                                f"{marker!r} in the previous commit and no longer does. That key "
                                f"is what makes re-notification a no-op — strip it and the next "
                                f"central run appends a second copy of the same notice. To "
                                f"DECLINE the check, mark the task superseded and add the probe "
                                f"name to .claude/estate-align.skip; do not remove the key.")

            # 4b. DRIFT on a STARTED task — a WARNING, never a failure (phase 37, 2026-08-26).
            #     The consult that reshaped the never-modify rule (cycle 20260826-094406-418e380)
            #     established that this checker had never seen a same-id rewrite at all: check 4
            #     fails when an id vanishes, and a task whose name and verify were replaced under
            #     the same id passed silently. The rule now says WHICH tasks that is allowed for —
            #     unstarted ones, so findings can reshape work nobody has begun ("not everything
            #     can be planned correctly", operator 2026-08-26) — and this is the other half:
            #     once a task has started, its descriptive fields are its history.
            #
            #     A warning: a rewrite destroys nothing — the previous commit still holds the old
            #     text — and "stricter" versus "weaker" cannot be told apart mechanically, so the
            #     charter (three data-destroying failures plus the append-only rule) and the
            #     pre-commit hook armed estate-wide both say the same thing: name it, exit 0, let
            #     the reviewer judge.
            #
            #     Started in EITHER version: a task that was in progress in the base and has been
            #     reset to pending had history too, and a task that starts in this very commit is
            #     the rewrite-and-start case — pending yesterday, in_progress with a new name
            #     today. That warns BY DESIGN: the commit that begins the work is the one that
            #     freezes its description, and a rewrite landing in the same commit cannot be told
            #     from one landing after it.
            #
            #     No estate_notice exemption: a notice is a request from central, and its text is
            #     what the estate believes it asked for. A notice rewritten in place, by anyone —
            #     the centre correcting its own text included — is a change to what the estate
            #     asked for; the warning names it either way, and the commit says why.
            bt, at = tasks_by_key(base_doc), tasks_by_key(doc)
            for key, b in bt.items():
                c = at.get(key)
                if c is None or not (is_started(b) or is_started(c)):
                    continue
                pk, tid = key
                for field in DRIFT_FIELDS:
                    if b.get(field, _ABSENT) != c.get(field, _ABSENT):
                        warn.append(
                            f"phase {pk}: task {tid!r} is STARTED and its {field!r} differs from "
                            f"the previous commit. Not blocking — a started task's name and verify "
                            f"are frozen by the task-mutability rule in /update-progress; if this "
                            f"was a change of plan, mark {tid!r} superseded and add the "
                            f"replacement under a new id."
                        )

    # Warnings: real but not destructive.
    for pk, po in iter_phases(doc):
        if isinstance(po, dict) and po.get("tasks") is None:
            warn.append(f"phase {pk}: no `tasks` key")
    ct = doc.get("current_task")
    if ct:
        every = {i for ids in task_ids(doc).values() for i in ids}
        if str(ct) not in every:
            warn.append(f"current_task {ct!r} does not match any task id")

    # FRESHNESS — `last_updated` older than the newest completion date recorded in the file.
    #
    # A WARNING, NEVER A FAILURE, and the reason is not taste: this module's charter is four
    # failures only — three that destroy data, plus the append-only rule (see the docstring) —
    # and a stale `last_updated` destroys nothing — every task, id and date is still there. It is
    # also armed as a pre-commit hook in ~28 projects across the estate, so a fifth failure would
    # block commits estate-wide over a field that is merely out of date. It goes in `warn`, exit
    # stays 0.
    #
    # Found 2026-08-21 in this repo: last_updated said 2026-08-21 while phase 30's tasks carried
    # completed_at 2026-08-25. Nothing anywhere reported it.
    malformed, newest, newest_label = [], None, None
    lu_raw = doc.get("last_updated")
    lu = iso_date(lu_raw)
    if lu is None and not is_absent(lu_raw):
        malformed.append(f"last_updated={lu_raw!r}")
    for label, key, raw in completion_fields(doc):
        # absence (null, or an unsubstituted {{placeholder}}) is not malformation — see is_absent()
        if is_absent(raw):
            continue
        d = iso_date(raw)
        if d is None:
            malformed.append(f"{label} {key}={raw!r}")
            continue
        if newest is None or d > newest:
            newest, newest_label = d, f"{label} ({key} {d})"

    if malformed:
        shown = "; ".join(malformed[:3])
        more = f" (+{len(malformed) - 3} more)" if len(malformed) > 3 else ""
        # The sidecar sentence is TRUE of a sidecar pointer and false of everything else, so it is
        # attached only when one is actually present. A fixed explanation appended to every offender
        # tells the reader something untrue about most of them.
        hint = ""
        if any("archived: " in m for m in malformed):
            hint = (" One of them is a compaction sidecar pointer ('archived: docs/_archive/"
                    "progress-sidecars/…') that landed in a date field: the date itself is in the "
                    "sidecar, and this file no longer states when that work finished.")
        warn.append(
            f"{len(malformed)} date field(s) are not ISO dates and were left out of the freshness "
            f"comparison: {shown}{more}.{hint}"
        )

    # Absence is not staleness: no last_updated, or no parseable completion date anywhere, means
    # the check simply does not apply and says nothing at all.
    if lu and newest and lu < newest:
        warn.append(
            f"STALE last_updated: the file says {lu}, but {newest_label} is newer — work recorded "
            f"here finished on {newest}. Nothing is lost; the file just reports itself as older "
            f"than the work it contains. /update-progress refreshes last_updated when it closes a "
            f"task; set it to {newest} or later."
        )
    return fail, warn


def read_staged(path):
    r = subprocess.run(["git", "show", f":{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def read_ref(ref, path):
    r = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def main():
    ap = argparse.ArgumentParser(description="Integrity check for progress.json")
    ap.add_argument("--file", default="progress.json", help="path (default: progress.json)")
    ap.add_argument("--staged", action="store_true",
                    help="check the STAGED content (what would enter history), not the worktree")
    ap.add_argument("--base", default="HEAD",
                    help="ref to enforce append-only against ('' or 'none' to skip)")
    ap.add_argument("--quiet", action="store_true",
                    help="suppress the all-clear line; failures and warnings are still reported")
    a = ap.parse_args()

    if a.staged:
        text = read_staged(a.file)
        src = f"{a.file} (staged)"
        if text is None:
            return 2
    else:
        try:
            text = open(a.file, encoding="utf-8").read()
        except OSError as e:
            print(f"progress-check: cannot read {a.file}: {e}", file=sys.stderr)
            return 2
        src = a.file

    base_text = None
    if a.base and a.base.lower() != "none":
        base_text = read_ref(a.base, a.file)   # None on first commit / untracked → skipped

    fail, warn = check(text, base_text)

    if fail:
        print(f"progress-check: FAIL — {src}", file=sys.stderr)
        for f in fail:
            print(f"  {f}", file=sys.stderr)
        if warn:
            for w in warn:
                print(f"  (warn) {w}", file=sys.stderr)
        return 1

    if not a.quiet:
        print(f"progress-check: ok — {src}")
        for w in warn:
            print(f"  (warn) {w}")
    elif warn:
        # --quiet used to swallow warnings, and the ONE automated consumer of this checker — the
        # pre-commit hook armed in every project — passes --quiet. So a warning was, in practice,
        # printed to nobody at the exact moment it was written for: commit time. Warnings now go to
        # stderr under --quiet, leaving stdout free for callers that read the verdict there.
        for w in warn:
            print(f"progress-check: (warn) {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
