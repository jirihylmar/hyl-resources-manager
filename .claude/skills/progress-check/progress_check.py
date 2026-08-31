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
Failures stay prospective where estate history varies: new records and newly terminal phases must
be complete, while historical terminal records receive a warning rather than a surprise migration.
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


def iter_tasks_keyed(phase_obj):
    """Yield (dict key or None, task object) for list- AND dict-shaped `tasks`; skip bare strings.

    The key is kept because it is the **id of last resort**. A `tasks` object keyed BY task id
    whose records carry no redundant inner `id` is a shape the estate really uses, and discarding
    the key made every id-based check silently inert on it — duplicate ids, append-only, the
    `estate_notice` marker and terminal-task drift all join on the id, and
    there was none. Inert is the worst failure mode this module has: it reports "ok" over a file
    it never examined. Measured 2026-08-26 by the phase-37 verification sweep.
    """
    if not isinstance(phase_obj, dict):
        return
    ts = phase_obj.get("tasks")
    if isinstance(ts, list):
        items = [(None, t) for t in ts]
    elif isinstance(ts, dict):
        items = list(ts.items())
    else:
        return
    for k, t in items:
        if isinstance(t, dict):
            yield k, t


def iter_tasks(phase_obj):
    """Yield task objects for list-shaped AND dict-shaped `tasks`; skip bare strings."""
    for _k, t in iter_tasks_keyed(phase_obj):
        yield t


def task_id_of(key, task):
    """The task's id: its own `id` when it has one, else the dict key it is filed under.

    Returns None only for a list-shaped task with no `id` — genuinely unidentifiable, and the
    callers skip it as they always did.
    """
    tid = task.get("id")
    if tid is not None:
        return str(tid)
    return None if key is None else str(key)


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


def unresolved_template(v):
    """True only for a whole unresolved template token, not ordinary literal braces."""
    return isinstance(v, str) and bool(re.fullmatch(r"\{\{[A-Z][A-Z0-9_]*\}\}", v.strip()))


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
        for k, t in iter_tasks_keyed(po):
            tid = task_id_of(k, t)
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
        for k, t in iter_tasks_keyed(po):
            tid = task_id_of(k, t)
            if tid is None:
                continue
            out[(pk, tid)] = t.get("estate_notice")
    return out


def task_ids(doc):
    """{phase_key: [task ids]} — the append-only invariant operates on these."""
    out = {}
    for pk, po in iter_phases(doc):
        ids = [i for i in (task_id_of(k, t) for k, t in iter_tasks_keyed(po)) if i is not None]
        out[pk] = ids
    return out


# --- terminal-task drift, for the mutability boundary (phase 40, 2026-08-30) -------------------
#: Every NON-TERMINAL task is editable planning state, including work that has started, is blocked
#: or is deferred. A task becomes immutable history only after it is committed in a terminal
#: status. This set is shared in meaning with open-work's terminal vocabulary; separator spellings
#: are normalised before lookup and the comparison is prospective, so historical vocabulary does
#: not need a schema migration.
TERMINAL_STATUSES = {
    "complete", "completed", "superseded", "done", "closed", "dropped", "cancelled", "canceled",
    "resolved", "obsolete", "abandoned",
}


def norm_status(st):
    """Fold separator spellings together: 'not started' / 'not-started' → 'not_started'."""
    return re.sub(r"[\s\-]+", "_", str(st).strip().lower())

#: Semantic fields frozen once the BASE commit records a terminal task. Lifecycle/archival fields
#: may still change mechanically (for example compaction pointers), but the declared outcome and
#: evidence may not be retold after closure.
DRIFT_FIELDS = ("name", "description", "verify", "verify_result", "dependencies", "depends_on")

#: How many drift warnings are printed in full before the rest are named in one line. Matches the
#: cap the malformed-date warning uses, for the same reason: the hook prints these into a commit.
DRIFT_SHOWN = 3

_ABSENT = object()   # so "field removed" and "field set to null" both read as a difference


def is_terminal(task):
    """True only when the task's status explicitly records a terminal state."""
    return norm_status(task.get("status") or "") in TERMINAL_STATUSES


def tasks_by_key(doc):
    """{(phase_key, task_id): task} for every task that has an id — the join the drift check runs on."""
    out = {}
    for pk, po in iter_phases(doc):
        for k, t in iter_tasks_keyed(po):
            tid = task_id_of(k, t)
            if tid is not None:
                out[(pk, tid)] = t
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

    # Required root identity must describe the project, not the template it came from. Limit this
    # to whole tokens in required metadata: braces in task prose and code examples are legitimate.
    for field in ("project", "description", "created_at"):
        if unresolved_template(doc.get(field)):
            message = (f"required root metadata {field!r} still contains unresolved template token "
                       f"{doc[field]!r}; project setup must substitute it before work is recorded")
            # Base-less checks are also used directly against the intentionally unsubstituted
            # bootstrap/example files. Once a project has a committed base, the same token blocks.
            (fail if base_text is not None else warn).append(message)

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
                after_set = set(after[pk])          # hoisted: rebuilt per id, this was quadratic
                missing = [i for i in ids if i not in after_set]
                for i in missing:
                    fail.append(f"phase {pk}: task {i!r} existed in the previous commit and is "
                                f"now GONE. Tasks are append-only — mark it superseded instead.")

            # 4a. Every NEW work record says who wrote it and whose job it is. Operator decision,
            #     2026-08-29: authorship and assignment are different facts, and progress.json must
            #     preserve both. Comparison makes this prospective: the estate's historical tasks
            #     are not rewritten merely to adopt a new field, while every addition from this
            #     point is checked at the staged commit where it enters history.
            bp = {pk: po for pk, po in iter_phases(base_doc)}
            ap = {pk: po for pk, po in iter_phases(doc)}

            def require_identity(label, obj):
                if not isinstance(obj, dict):
                    return
                for field in ("authored_by", "assigned_to"):
                    value = obj.get(field)
                    if not isinstance(value, str) or not value.strip():
                        fail.append(
                            f"{label} is NEW and has no non-empty {field!r}. Every new phase and "
                            f"task must record who authored the entry and whose job execution is."
                        )

            for pk, po in ap.items():
                if pk not in bp:
                    require_identity(f"phase {pk!r}", po)

            # A phase becoming terminal in this candidate commit must acquire a real completion
            # date in the same boundary. Historical terminal phases are not retroactively blocked.
            for pk, po in ap.items():
                if not isinstance(po, dict) or not is_terminal(po):
                    continue
                before_phase = bp.get(pk)
                was_terminal = isinstance(before_phase, dict) and is_terminal(before_phase)
                raw = next((po[k] for k in COMPLETION_KEYS if k in po), None)
                if not was_terminal and iso_date(raw) is None:
                    fail.append(f"phase {pk!r} becomes TERMINAL in this commit but has no valid "
                                f"completed_at/completed ISO date")

            bt_new, at_new = tasks_by_key(base_doc), tasks_by_key(doc)
            for (pk, tid), task in sorted(at_new.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
                if (pk, tid) not in bt_new:
                    require_identity(f"phase {pk}: task {tid!r}", task)

            # 4b. An `estate_notice` marker may not be stripped from a task that kept its id.
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

            # 4c. DRIFT on a task already TERMINAL in the base commit — a WARNING, never a failure.
            #     Open work is a living plan and may be reshaped even after it starts. Closure is
            #     the boundary: once a commit records a terminal task, its semantic description
            #     and evidence are historical references. Candidate-only terminal status does not
            #     warn, because the same commit may legitimately refine a task and then close it.
            #     Git preserves the prior version; this signal makes a later retelling visible.
            bt, at = tasks_by_key(base_doc), tasks_by_key(doc)
            drift = []
            for key, b in sorted(bt.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
                c = at.get(key)
                if c is None or not is_terminal(b):
                    continue
                pk, tid = key
                for field in DRIFT_FIELDS:
                    if b.get(field, _ABSENT) != c.get(field, _ABSENT):
                        drift.append((pk, tid, field))
            for pk, tid, field in drift[:DRIFT_SHOWN]:
                warn.append(
                    f"phase {pk}: task {tid!r} was TERMINAL in the previous commit and its "
                    f"{field!r} now differs. Not blocking — closed work is immutable reference "
                    f"history; restore the field and represent later action in non-terminal work."
                )
            if len(drift) > DRIFT_SHOWN:
                rest = "; ".join(f"{pk}:{tid} {field}" for pk, tid, field in drift[DRIFT_SHOWN:])
                warn.append(
                    f"+{len(drift) - DRIFT_SHOWN} more terminal task field(s) drifted, same rule: {rest}"
                )

    # Warnings: real but not destructive.
    for pk, po in iter_phases(doc):
        if isinstance(po, dict) and po.get("tasks") is None:
            warn.append(f"phase {pk}: no `tasks` key")
        if base_text is not None and isinstance(po, dict) and is_terminal(po):
            raw = next((po[k] for k in COMPLETION_KEYS if k in po), None)
            if iso_date(raw) is None:
                try:
                    base_doc_for_warning, _ = parse_strict(base_text)
                    old = dict(iter_phases(base_doc_for_warning)).get(pk)
                except ValueError:
                    old = None
                if isinstance(old, dict) and is_terminal(old):
                    warn.append(f"phase {pk!r} was already TERMINAL but has no valid completion "
                                f"date; historical compatibility leaves it unblocked")
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
