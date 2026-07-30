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
Four failures only, each one a thing that DESTROYS data.
"""
import argparse
import json
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


def task_ids(doc):
    """{phase_key: [task ids]} — the append-only invariant operates on these."""
    out = {}
    for pk, po in iter_phases(doc):
        ids = [str(t["id"]) for t in iter_tasks(po) if t.get("id") is not None]
        out[pk] = ids
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

    # Warnings: real but not destructive.
    for pk, po in iter_phases(doc):
        if isinstance(po, dict) and po.get("tasks") is None:
            warn.append(f"phase {pk}: no `tasks` key")
    ct = doc.get("current_task")
    if ct:
        every = {i for ids in task_ids(doc).values() for i in ids}
        if str(ct) not in every:
            warn.append(f"current_task {ct!r} does not match any task id")
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
    ap.add_argument("--quiet", action="store_true", help="print only on failure")
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
