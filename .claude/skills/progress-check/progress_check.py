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
                    with a warning about a value the framework itself put there. Substituting it is
                    the project's own job at bootstrap — nothing outside the project may fill it in
                    — and once the project has a committed base the required-root-metadata rule in
                    check() blocks the token outright instead of merely tolerating it here.
    Calling either malformed would put a false warning on a large share of the estate, and a checker
    that cries wolf is a checker that gets switched off.
    """
    if v is None:
        return True
    return isinstance(v, str) and v.startswith("{{") and v.endswith("}}")


def unresolved_template(v):
    """True only for a whole unresolved template token, not ordinary literal braces.

    The character class matches the collector's own placeholder rule (`collector/src/progress.ts`
    nulls the anchored pattern {{[A-Z0-9_]+}}), so a token this checker calls substituted is
    never a token the dashboard calls unset. The two disagreed on a leading digit only —
    `{{2ND_NAME}}` — which no live file carries; ordinary prose braces are unaffected either way
    because they are lower-case.
    """
    return isinstance(v, str) and bool(re.fullmatch(r"\{\{[A-Z0-9_]+\}\}", v.strip()))


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


def parse_base(base_text):
    """The base document, or None when there is no usable one.

    None means "no ground to judge against" and covers all three ways that happens: no base was
    supplied (`--base none`, or a first commit), the base does not parse (a file committed with
    `--no-verify`), or its root is not an object. Every prospective rule that blocks must consult
    this and DOWNGRADE to a warning when it is None: a base nobody can read may not ground a block,
    because the alternative is a project whose last commit is broken being unable to commit the fix.

    The two older ad-hoc re-parses below are deliberately left alone; they answer different
    questions and rewriting them is not this change.
    """
    if base_text is None:
        return None
    try:
        base_doc, _ = parse_strict(base_text)
    except ValueError:
        return None
    return base_doc if isinstance(base_doc, dict) else None


# --- the declared relations block (2026-09-04) ------------------------------
#: The collector truncates a published note at this length
#: (`syndicate-dashboard/collector/src/progress.ts`, NOTE_LIMIT).
RELATIONS_NOTE_LIMIT = 200

#: The collector publishes at most this many members and silently drops the rest
#: (`syndicate-dashboard/collector/src/progress.ts`, MEMBER_LIMIT).
RELATIONS_MEMBER_LIMIT = 100

#: The scp-style remote (`git@host:org/repo.git`) — the one git URL shape that is not a URL.
#: Mirrors the expression in `syndicate-dashboard/contracts/src/identity.ts` (normalizeOrigin).
_SCP_REMOTE = re.compile(r"^(?:[^@/\s]+@)?([^:/\s]+):(.+)$")


def _typename(v):
    """The value's type as it reads inside a sentence: 'a list', 'an int'."""
    n = type(v).__name__
    return f"{'an' if n[:1].lower() in 'aeiou' else 'a'} {n}"


def origin_joins(text):
    """False only when an origin provably normalizes to NOTHING, and so can join to nothing.

    Mirrors `normalizeOrigin` (syndicate-dashboard/contracts/src/identity.ts), which needs both a
    host and a repository path — `<host>/<path>`, `<scheme>://<host>/<path>`, or the scp form
    `[user@]<host>:<path>`. It is deliberately NOT a URL validator: the vocabulary of git remotes
    is open, nothing local can resolve a remote, and a complaint that fires on a working origin is
    exactly the noise the DESIGN RULE at the top of this file forbids. It answers the one narrow
    question the dashboard also asks, and it only ever produces a warning.
    """
    s = text.strip()
    if not s:
        return False
    if "://" not in s:
        m = _SCP_REMOTE.match(s)
        if m:
            return bool(m.group(1).strip()) and bool(m.group(2).strip().strip("/"))
    rest = s.split("://", 1)[1] if "://" in s else s
    host, sep, path = rest.rsplit("@", 1)[-1].partition("/")
    return bool(host.strip()) and bool(sep) and bool(path.strip().strip("/"))


def origin_key(text):
    """One remote's two spellings folded together, for the duplicate comparison ONLY.

    Lower-cased, trailing '/' and '.git' dropped — the same three foldings normalizeHostPath does,
    so `…/repo.git` and `…/repo` are recognised as the one member they are.
    """
    s = text.strip().lower().rstrip("/")
    return s[:-4] if s.endswith(".git") else s


def relations_findings(doc):
    """(failures, warnings) for the OPTIONAL root `relations` block a MANAGER declares.

    THE CONTRACT, as implemented in `syndicate-dashboard/collector/src/progress.ts`
    (parseRelations, declaredMember, declaredPath) and carried on the wire by
    `contracts/src/schema.ts` (validateMember): a manager names its members DOWNWARD, in its own
    progress.json, and a member never names its manager — so exactly one repository writes each
    edge and two hosts can never contradict each other about it. `origin` joins across hosts;
    `path` joins on a host that holds the manager.

    ABSENCE IS SILENT, and that silence is load-bearing. No block at all — and an explicit `null`,
    which the collector reads as absent — says NOTHING about what this repository manages, while
    `"members": []` is a positive claim that it manages nothing. The dashboard keeps those two
    apart and will never render silence as a claim; so does this check, by having no opinion
    whatsoever about a file that does not declare.

    The failures are STRICT rather than prospective, on the `unattended` precedent above: no
    progress.json in the estate carried this key before 2026-09-03, so there is no historical
    vocabulary to tolerate and no project can be blocked by a shape it already committed. Measured
    2026-09-04 across all 15 local progress.json files — 2 declare, 13 do not, and every rule below
    is silent on all 15.

    NOT checked, deliberately: the relation WORD (the vocabulary is the operator's — the collector
    carries it verbatim and so does the wire schema, so a closed set here would reject a word they
    chose on purpose); whether a declared `path` exists on disk (that is a per-host observation the
    collector makes, and a member may legitimately be absent from this clone); and whether an
    `origin` resolves to a real repository (nothing local can prove that).
    """
    fail, warn = [], []
    declared = doc.get("relations")
    # Absent, and null-as-absent: the collector reads both as "this file declares nothing", which
    # is a different fact from declaring emptiness and is never a defect.
    if declared is None:
        return fail, warn

    if not isinstance(declared, dict):
        fail.append(
            f"relations is {_typename(declared)}, not an object. The block is "
            f"{{\"version\": 1, \"members\": [...]}} — a block the collector cannot read is "
            f"published as MALFORMED, and every member named inside it goes unpublished."
        )
        return fail, warn

    version = declared.get("version")
    if not (isinstance(version, (int, float)) and not isinstance(version, bool) and version == 1):
        shown = repr(version) if "version" in declared else "missing"
        fail.append(
            f"relations.version is {shown}, not 1. The collector accepts version 1 and discards "
            f"the whole block otherwise, so every member declared here would go unpublished."
        )

    members = declared.get("members")
    if not isinstance(members, list):
        shown = _typename(members) if "members" in declared else "missing"
        fail.append(
            f"relations.members is {shown}, not an array. `\"members\": []` is how a repository "
            f"states that it manages nothing; a block whose members cannot be read states nothing "
            f"at all and is published as MALFORMED."
        )
        return fail, warn

    if len(members) > RELATIONS_MEMBER_LIMIT:
        warn.append(
            f"relations.members declares {len(members)} members and the collector publishes the "
            f"first {RELATIONS_MEMBER_LIMIT}, so the rest are never seen and the count on the "
            f"board is a cap rather than a total. Split the family, or declare the members that "
            f"matter."
        )

    seen_origin, seen_path = {}, {}
    for i, member in enumerate(members):
        at = f"relations.members[{i}]"
        if not isinstance(member, dict):
            fail.append(
                f"{at} is {_typename(member)}, not an object. Each member is an object "
                f"naming a 'relation' plus an 'origin' and/or a 'path'."
            )
            continue

        origin_raw, path_raw = member.get("origin"), member.get("path")
        origin = origin_raw.strip() if isinstance(origin_raw, str) else ""
        path = path_raw.strip() if isinstance(path_raw, str) else ""
        # Locate the finding by what the member NAMES, not only by its index: an index moves when a
        # member is inserted above it, and the operator is reading this in a commit message.
        where = origin or path
        located = f"{at} ({where})" if where else at

        # The reader nulls any value that is still a bare {{TEMPLATE_TOKEN}}, exactly as it does
        # for project metadata — so an unsubstituted token in a member's relation or locator makes
        # the member vanish with no error anywhere. Caught here, where it can be fixed.
        for field in ("relation", "origin", "path", "note"):
            value = member.get(field)
            if unresolved_template(value):
                fail.append(
                    f"{located}: '{field}' still contains the unsubstituted template token "
                    f"{value.strip()!r}. The collector reads a bare token as no value at all, so "
                    f"this member is silently dropped and its edge is never published. Substitute "
                    f"it, or remove the key."
                )

        relation = member.get("relation")
        if not isinstance(relation, str) or not relation.strip():
            fail.append(
                f"{located} has no non-empty 'relation' string. The word itself is yours — "
                f"'nested', 'governed', 'metadata-governed' and 'orchestrated' are in use, and a "
                f"new one is legal — but a member without one is dropped by the collector and the "
                f"edge is never published."
            )

        if not origin and not path:
            fail.append(
                f"{located} declares neither an 'origin' nor a 'path', so it names nothing that "
                f"can be joined to anything and the collector drops it. Give it the member's "
                f"remote URL as 'origin' (it joins across hosts) or its directory inside this "
                f"repository as 'path' (it joins on a host that holds this clone)."
            )
        elif origin_raw is not None and not origin:
            shown = (
                "empty"
                if isinstance(origin_raw, str)
                else f"{_typename(origin_raw)}, not a string"
            )
            warn.append(
                f"{located}: 'origin' is {shown}, so the collector reads no origin here and this "
                f"member can only ever be joined on a host that holds this clone. Give the remote "
                f"URL as a string, or drop the key."
            )
        # The same fact about the other locator, reported the same way: the reader nulls a
        # non-string path exactly as it nulls a non-string origin.
        if path_raw is not None and not path:
            shown = "empty" if isinstance(path_raw, str) else f"{_typename(path_raw)}, not a string"
            warn.append(
                f"{located}: 'path' is {shown}, so the collector reads no path here. Give the "
                f"member's directory inside this repository as a string, or drop the key."
            )

        # An unusable path costs the member ONLY when it is the member's only locator. Beside a
        # usable origin the collector still publishes the member (it reports dropped: 0), so
        # failing here would block a commit the reader accepts — the one mistake this guard may
        # never make, because it runs on every commit of progress.json in every project.
        bad_path = None
        if path.startswith("/"):
            bad_path = (
                f"'path' {path_raw!r} is absolute. A path names a location INSIDE this repository "
                f"— relative, no leading '/' — because one repository may only declare what it "
                f"contains."
            )
        elif ".." in path.split("/"):
            bad_path = (
                f"'path' {path_raw!r} contains a '..' segment, which points OUTSIDE this "
                f"repository. A manager may only declare what it contains."
            )
        if bad_path and not origin:
            fail.append(
                f"{at}: {bad_path} The collector discards it, and with no 'origin' beside it "
                f"the member names nothing at all and goes unpublished. Give the member's remote "
                f"URL as 'origin' for a repository that is not inside this one."
            )
        elif bad_path:
            warn.append(
                f"{located}: {bad_path} The collector ignores the path and joins this member by "
                f"its origin instead, so nothing is lost — but the path claims something untrue "
                f"about where the member lives. Remove it, or correct it to a directory inside "
                f"this repository."
            )

        if origin:
            key = origin_key(origin)
            if key in seen_origin:
                warn.append(
                    f"{located} repeats the origin already declared by "
                    f"relations.members[{seen_origin[key]}]. Both entries are published, so one "
                    f"member is drawn twice — keep one entry per member and let its 'relation' "
                    f"say what the tie is."
                )
            else:
                seen_origin[key] = i
            if not origin_joins(origin):
                warn.append(
                    f"{located}: 'origin' {origin_raw!r} does not resolve to a host plus a "
                    f"repository path, so it matches no repository on the board and the member "
                    f"renders as an unresolved declaration. Not blocking — nothing here can reach "
                    f"a remote to prove otherwise; use the URL git itself reports (`git remote "
                    f"get-url origin`)."
                )

        if path and not path.startswith("/") and ".." not in path.split("/"):
            key = path.rstrip("/")
            if key in seen_path:
                warn.append(
                    f"{located} repeats the path already declared by "
                    f"relations.members[{seen_path[key]}]. Both entries are published, so one "
                    f"member is drawn twice — keep one entry per member and let its 'relation' "
                    f"say what the tie is."
                )
            else:
                seen_path[key] = i

        note = member.get("note")
        # The reader trims before it truncates, so a note that is only long because of trailing
        # whitespace loses nothing.
        if isinstance(note, str) and len(note.strip()) > RELATIONS_NOTE_LIMIT:
            note = note.strip()
            warn.append(
                f"{located}: 'note' is {len(note)} characters and the collector truncates it at "
                f"{RELATIONS_NOTE_LIMIT}, so the published note stops mid-sentence. Nothing in "
                f"this file is lost — shorten it if the published half must read as a whole one."
            )

    return fail, warn


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

    # 3a. An unattended operation is described completely, or it is not described at all.
    #
    # PROJECT_CHARTER.md section 11 makes the difference between a watched operation and an
    # unwatched one a fact about recorded state plus a live probe. That only works if the state is
    # there and well-formed, so this blocks at the commit where the block enters history.
    #
    # It is strict rather than prospective, and that is deliberate: no task in the estate carried an
    # `unattended` block before 2026-09-02, so there is no historical vocabulary to tolerate. The
    # rule this file states in its own DESIGN RULE — tolerate every shape that really exists — is
    # satisfied by strictness here precisely because nothing else exists yet. That is the one moment
    # a schema can be imposed without breaking anybody, and it does not come back.
    UNATTENDED_REQUIRED = ("operation_id", "supervisor_id", "supervisor_mode", "state_ref",
                           "started_at", "last_observed_at", "next_action_at", "deadline_at",
                           "retry_count", "retry_limit", "delivery_state", "cleanup_state",
                           "cleanup_owner", "notification_state")
    UNATTENDED_MODES = ("session-watched", "durably-supervised", "unmonitored")
    UNATTENDED_DELIVERY = ("pending", "delivered", "capacity-exhausted", "workload-failed",
                           "controller-crashed", "cleanup-failed", "deadline-missed")
    # These travel between hosts inside progress.json, so a path true on one machine is a lie on
    # the next. `state_ref` and `liveness_check` are deliberately NOT here: they are host-owned.
    UNATTENDED_TRAVELS = ("operation_id", "supervisor_id", "supervisor_mode", "started_at",
                          "last_observed_at", "next_action_at", "deadline_at", "delivery_state",
                          "cleanup_state", "cleanup_owner", "notification_state")
    _hostpath = re.compile(r"(^|[\s\"'])(/home/|/Users/|/root/|[A-Za-z]:\\)")

    for pkey, pobj in iter_phases(doc):
        for tkey, task in iter_tasks_keyed(pobj):
            if not isinstance(task, dict):
                continue
            op = task.get("unattended")
            if op is None:
                continue
            tid = task_id_of(tkey, task)
            if not isinstance(op, dict):
                fail.append(f"task {tid!r}: 'unattended' must be an object describing the "
                            f"operation, not {type(op).__name__}.")
                continue
            for field in UNATTENDED_REQUIRED:
                v = op.get(field)
                if isinstance(v, int) and field in ("retry_count", "retry_limit"):
                    continue
                if not isinstance(v, str) or not v.strip():
                    fail.append(f"task {tid!r}: unattended.{field} is missing or empty. An "
                                f"operation that cannot be reconciled by a later session is the "
                                f"failure this block exists to prevent.")
            mode = op.get("supervisor_mode")
            if isinstance(mode, str) and mode.strip() and mode.strip() not in UNATTENDED_MODES:
                fail.append(f"task {tid!r}: unattended.supervisor_mode {mode!r} is not one of "
                            f"{', '.join(UNATTENDED_MODES)}.")
            if isinstance(mode, str) and mode.strip() == "durably-supervised" \
                    and not str(op.get("liveness_check") or "").strip():
                fail.append(f"task {tid!r}: unattended claims 'durably-supervised' but declares no "
                            f"'liveness_check', so the supervisor can never be proved alive. A "
                            f"claim that cannot be checked is the thing being forbidden.")
            dstate = op.get("delivery_state")
            if isinstance(dstate, str) and dstate.strip() and dstate.strip() not in UNATTENDED_DELIVERY:
                fail.append(f"task {tid!r}: unattended.delivery_state {dstate!r} is not one of "
                            f"{', '.join(UNATTENDED_DELIVERY)}. Delivery is not a process exit "
                            f"status and must not borrow its vocabulary.")
            for field in UNATTENDED_TRAVELS:
                v = op.get(field)
                if isinstance(v, str) and _hostpath.search(v):
                    fail.append(f"task {tid!r}: unattended.{field} carries a host-specific absolute "
                                f"path. This field travels between hosts in progress.json — use a "
                                f"portable identifier; host paths belong in 'state_ref' or "
                                f"'liveness_check', which do not travel.")

    # 3b. The declared relations block — OPTIONAL, and absence stays silent. See
    #     relations_findings() for the contract it enforces and for why it is strict rather than
    #     prospective. It is placed here, beside the other root-key rules, because it is a fact
    #     about this document alone: no comparison with the base commit can say anything about it.
    rfail, rwarn = relations_findings(doc)
    fail.extend(rfail)
    warn.extend(rwarn)

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

            # A task becoming terminal in this candidate commit should record WHEN, in the same
            # boundary — /update-progress already instructs it. This is a WARNING, and the reason
            # is arithmetic rather than taste: measured 2026-09-02, 415 of ~2872 terminal tasks
            # estate-wide (14%) carry no completed_at/completed, including 24 of 319 in this repo's
            # own file. A phase becomes terminal rarely; a task becomes terminal in nearly every
            # /update-progress commit, so failing here would block roughly one commit in seven —
            # the "disabled within a day" signature this module's DESIGN RULE was written against.
            #
            # PROMOTION CRITERION, so this does not sit as a warning forever by default: promote to
            # FAIL once two consecutive full-estate probe runs show ZERO new dateless terminal
            # transitions. At that point the rule costs nobody a commit and blocks a real gap.
            dateless = []
            for (pk, tid), task in sorted(at_new.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
                if not is_terminal(task):
                    continue
                before_task = bt_new.get((pk, tid))
                if isinstance(before_task, dict) and is_terminal(before_task):
                    continue          # already history — not this commit's doing
                raw = next((task[k] for k in COMPLETION_KEYS if k in task), None)
                if iso_date(raw) is None:
                    dateless.append((pk, tid))
            for pk, tid in dateless[:DRIFT_SHOWN]:
                warn.append(
                    f"phase {pk}: task {tid!r} becomes TERMINAL in this commit but records no "
                    f"valid completed_at/completed ISO date. Not blocking — 14% of the estate's "
                    f"terminal tasks predate the rule; set the date /update-progress asks for so "
                    f"the freshness comparison and the phase's closure date have something to read."
                )
            if len(dateless) > DRIFT_SHOWN:
                rest = "; ".join(f"{pk}:{tid}" for pk, tid in dateless[DRIFT_SHOWN:])
                warn.append(
                    f"+{len(dateless) - DRIFT_SHOWN} more task(s) become TERMINAL with no "
                    f"completion date, same rule: {rest}"
                )

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
    # The root current-work pointer. Severity is bounded by what the estate is PERMITTED and able
    # to fix, which splits this field into three outcomes rather than one:
    #
    #   dict / list  — only machinery writes a container here, and every reader stringifies the
    #                  value, so the project publishes a current task nobody can resolve ("[object
    #                  Object]" on the dashboard, no id ever matching). Prospective: it blocks at
    #                  the commit where it ENTERS history, and warns where the base already carried
    #                  one (one live offender, since 2026-07-07) or where no base can be read.
    #   scalar that matches no id — a warning. It costs readability, not data, and the estate has
    #                  shapes where no task is identifiable at all; with no ids to match against,
    #                  the comparison has nothing to say and says nothing.
    #   null / absent — SILENT, and this is not politeness. `/start-session` forbids modifying
    #                  `current_task` or `current_phase`, and `/open-work` calls a null pointer a
    #                  legitimate state at a clean close. Nobody is permitted to fill it, so no
    #                  severity above silence could ever be acted on. Measured 2026-09-02: 6 of 15
    #                  local projects are parked this way.
    ct = doc.get("current_task")
    if isinstance(ct, (dict, list)):
        kind = "dict" if isinstance(ct, dict) else "list"
        message = (f"current_task is a {kind}, not a task id. Readers stringify this field, so the "
                   f"dashboard shows '[object Object]' and no task id can ever match it — the "
                   f"project reports a current task that resolves to nothing. Put the task id here "
                   f"as a string and record the detail on the task itself.")
        base_doc_for_pointer = parse_base(base_text)
        base_ct = base_doc_for_pointer.get("current_task") if base_doc_for_pointer is not None else None
        already_broken = isinstance(base_ct, (dict, list))
        (warn if (base_doc_for_pointer is None or already_broken) else fail).append(message)
    elif ct:
        every = {i for ids in task_ids(doc).values() for i in ids}
        # `every` empty means no task in the file is identifiable, not that the pointer is wrong.
        if every and str(ct) not in every:
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
