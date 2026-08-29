---
name: progress-check
description: Check progress.json for corruption that destroys data, enforce append-only history, and require authored_by plus assigned_to on every newly added phase/task. Also warns when a started task's name or verify changes. Invoke before committing progress.json or investigating missing, changed, malformed, stale, or unattributed work.
---

# progress-check

`progress.json` is the single source of truth for a project's state, and until 2026-07-30 nothing
verified it. **Five of 34 live projects were already damaged**, and no check anywhere could see it.

## Run it

```bash
python3 .claude/skills/progress-check/progress_check.py              # working tree
python3 .claude/skills/progress-check/progress_check.py --staged     # the bytes that would be committed
python3 .claude/skills/progress-check/progress_check.py --base none  # skip the append-only comparison
```

Exit `0` ok · `1` **FAIL, do not commit** · `2` could not check (file missing/unreadable).

It also runs at commit time, within three limits worth knowing. `.claude/hooks/pre-commit` invokes
it only when `progress.json` is **staged** for the commit being made (`git diff --cached
--name-only` lists it) — an edit that sits unstaged in the working tree is never checked, and
neither is a commit in which `progress.json` is not among the staged files, whatever else is. And
the hook **fails open**: if `python3` is not on `PATH`, or
`.claude/skills/progress-check/progress_check.py` is not at the repo's top level, it skips the
check silently and the commit goes through. That is deliberate — blocking every commit because an
interpreter is absent would be a worse failure than the one being prevented — but it means a host
without either gets no check and no message saying so. And the hook runs only in a clone whose
`core.hooksPath` is `.claude/hooks` — `/distribute-defaults` sets that per clone (`arm_hookspath`);
a fresh clone has no hook until then. When it matters, run it by hand.

## What it fails on — three corruptions that lose data at read time, plus two prospective rules

| Failure | Why it matters |
|---|---|
| **Does not parse** | Every reader gets nothing. `Extra data` specifically means content was appended *after* the closing brace — usually a whole phase written outside `phases`. The text is in the file; the document does not contain it. |
| **Duplicate key in one object** | **This is valid JSON.** `json.load` keeps the last and drops the first, silently. A parse check passes and the value is already gone. |
| **Duplicate task id in a phase** | Two records claim to be the same task; which one any tool reads is arbitrary. |
| **A task or phase present in the last commit is absent** | Not necessarily data loss — the previous commit still holds a removed task's text, and an empty phase has none to lose: this is the framework's oldest rule — *never remove a task, mark it superseded* — the **append-only policy**, enforced mechanically instead of by prose. It compares ids only, so it refuses the removal of an **empty** phase exactly as it refuses a full one (`phase 'x' existed in the previous commit and is now GONE (0 task(s) with it)`). Uniform on purpose: the checker cannot judge whether what vanished mattered, so it does not try. — And, since 2026-08-06, an `estate_notice` marker stripped from a task that kept its id, for the same reason: the next central run would append a second copy. |
| **A newly added phase or task lacks `authored_by` or `assigned_to`** | Operator decision 2026-08-29: the record must say who wrote an entry and whose job execution is. This is prospective, detected by comparison with the previous commit; historical work is not rewritten to adopt a new schema. The two values may differ. |

## Plus one thing it warns about: a stale `last_updated`

Since 2026-08-25 the check also compares `last_updated` against the newest completion date it can
find, and **warns** if the file reports itself as older than the work inside it. Found here on
2026-08-21: `last_updated: 2026-08-21` while phase 30's tasks carried `completed_at: 2026-08-25`.
Nothing anywhere compared the two.

It is a **warning, never a failure** — exit stays `0` and commits are not blocked. A stale date
destroys nothing, and this checker is armed as a pre-commit hook across the whole estate; a fifth
failure would stop commits everywhere over a cosmetic field. The remedy is `/update-progress`,
which refreshes `last_updated` when it closes a task.

What it looks at, and what it stays quiet about:

- Both `completed_at` **and** the older `completed`, on tasks **and** on phases. In this repo's own
  file, 158 tasks use the first spelling and 58 use the second, and the two sets are disjoint.
- Dates truncated to `YYYY-MM-DD`, so `2026-08-25` and `2025-12-20T10:00:00Z` compare alike.
- **Absence is not staleness.** No `last_updated`, a `null` placeholder, an unsubstituted
  `{{CREATION_DATE}}` template placeholder, or no completion date anywhere means the check simply
  does not apply and says nothing. (`progress.json.bootstrap` ships `{{CREATION_DATE}}`, so without
  that second carve-out every freshly bootstrapped project would open its life complaining about a
  value the framework itself wrote.)
- A value that is not shaped like an ISO date is reported in a **separate** warning that names the
  offenders (first three, plus a count) and is left out of the comparison. If one of them is a
  compaction sidecar pointer (`archived: docs/_archive/progress-sidecars/…`) the warning says so —
  the date now lives in the sidecar and this file no longer states when the work finished.
- Status is not consulted: a task marked `superseded` that carries a completion date still counts.
  This checker enforces no vocabulary, here as everywhere else.

**You will see it at commit time.** `--quiet` suppresses the all-clear line and nothing else:
warnings go to stderr, and the pre-commit hook prints them under *"progress-check notes; NOT
blocking this commit"*. Until 2026-08-25 `--quiet` swallowed warnings outright, and the hook —
the only automated caller — passes `--quiet`, so a warning was in practice printed to nobody at
the one moment it was written for.

Pinned by `scripts/test-progress-check-freshness.sh` in the central repo (16 cases, including the
shipped bootstrap and both example playbooks staying silent).

## Plus one more warning since 2026-08-26: started-task drift

Since 2026-08-26 the append-only comparison also looks at tasks present in **both** the last commit
and the candidate, and **warns** when one that has *started* carries a different `name` or `verify`
than it did. Started means: a non-empty `started_at` that is not an unsubstituted `{{placeholder}}`,
or a `status` outside the pre-start set — `pending`, `not_started`, `planned`, `todo`, `to_do`,
`unstarted`, `deferred`, `postponed`, `backlog`, `on_hold`, `queued`, `new`, `ready`, `future`,
`tbd`, empty — case-insensitive, with separator spellings folded (`not started` reads as
`not_started`). `blocked` is deliberately outside the pre-start set: a task is as often blocked
mid-flight as before beginning. `started_at` is tested first and wins, so a task parked in any
status still counts as started once it carries a real start timestamp. Either version counts, so a
task rewritten and started in the same commit warns by design. One warning
per field, naming phase, id and field — the first three in full, then one line naming the rest, so
a bulk edit cannot bury the message in its own repetitions. An **unstarted** task may be refined in place — `name`,
`description`, `notes`, a stricter `verify` — and the checker says nothing: not everything can be
planned correctly, and findings are allowed to change work nobody has begun. Scope, dependency and
looser-`verify` changes still supersede, even unstarted (`/update-progress` states the rule).

A **warning, never a failure** — exit stays `0`, for the same reason as freshness: a reworded task
destroys no bytes, and this checker is a pre-commit hook estate-wide. It compares raw field values
and cannot tell a stricter `verify` from a weaker one. If what changed was a change of plan — a
different scope, different dependencies (which the checker does not compare), a looser `verify` —
restore the started task's fields, mark it `superseded` with a reason, and add the replacement
under a new id. If it was a legitimate edit, whoever reviews the commit judges that; the checker
only says it happened. Until 2026-08-26 same-id rewrites were never detected at all (consult cycle
20260826-094406-418e380), so the old blanket never-modify wording was never enforced by this
checker either; this warning is the first mechanical signal a same-id rewrite has ever produced.

Pinned by `scripts/test-progress-check-mutability.sh` in the central repo.

## What it deliberately does NOT enforce

No retrospective schema migration, no status vocabulary and no style policing. Measured across 34 real projects: `phases` is a dict in 30 and a
**list** in 2; `tasks` is a list in most and a **dict** in one; some tasks are bare strings; status
values include both `complete` and `completed`. All of that is tolerated.

**A checker that enforced the template's shape would block commits in real projects and be switched
off within a day** — which is worse than no checker. It fails only on things that lose data, plus
the append-only and new-entry identity rules above.

## The three corruptions it was built from

1. **A phase appended outside the document** — found in two projects, committed **2026-03-11** and
   **2026-03-26**, invisible for four months. An agent wrote a phase, committed it, and reported
   success; the phase has never existed as far as any tool is concerned.
2. **A duplicate key from an orphaned field** — an edit spliced one task's tail into its neighbour,
   leaving two `verify` keys in one object. Valid JSON. The real value was silently replaced.
3. **A missing comma** — the cheap one; it does not parse, so it is loud.

Only (3) announces itself. (1) is loud but was never checked. **(2) is invisible even to a parse
check**, which is why the checker parses with `object_pairs_hook` instead of plain `json.load`.

## If it fails

Fix the file and re-stage it. The repair is never blocked — only the damage is. `--no-verify`
exists, but using it commits state you have been told is broken.

An **already-damaged** file does not hold the repo hostage — the guard fires only on a staged
`progress.json` (above), so unrelated work still commits. It stops the next person who writes the file.

## Related

- `/update-progress` — the conservative edit rules this enforces mechanically (append-only, never
  remove, never change ids; since 2026-08-26, a warning when a started task's `name` or `verify`
  drifts). Reordering is forbidden there and not detected here.
- `/open-work` — renders the tables from this file; exits 2 when it cannot read it. If `open-work`
  reports it cannot read `progress.json`, run this to find out why.
