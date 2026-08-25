---
name: progress-check
description: Check progress.json for corruption that destroys data — a file that does not parse, a duplicate key that silently drops a value, a repeated task id, or a task that existed in the last commit and has vanished. Checks the staged bytes or the working tree. Invoke before committing progress.json, when a task or phase seems to have disappeared, when progress.json will not load, or when a project's reported state looks older than the work actually done.
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

It also runs automatically: `.claude/hooks/pre-commit` invokes it whenever `progress.json` is
staged, so the check happens at the moment of writing whether or not anyone remembered.

## What it reports — four things, all of which destroy data

| Failure | Why it matters |
|---|---|
| **Does not parse** | Every reader gets nothing. `Extra data` specifically means content was appended *after* the closing brace — usually a whole phase written outside `phases`. The text is in the file; the document does not contain it. |
| **Duplicate key in one object** | **This is valid JSON.** `json.load` keeps the last and drops the first, silently. A parse check passes and the value is already gone. |
| **Duplicate task id in a phase** | Two records claim to be the same task; which one any tool reads is arbitrary. |
| **A task or phase that existed in the last commit is gone** | The framework's oldest rule — *never remove a task, mark it superseded* — enforced mechanically instead of by prose. |

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

## What it deliberately does NOT enforce

No schema, no vocabulary, no style. Measured across 34 real projects: `phases` is a dict in 30 and a
**list** in 2; `tasks` is a list in most and a **dict** in one; some tasks are bare strings; status
values include both `complete` and `completed`. All of that is tolerated.

**A checker that enforced the template's shape would block commits in real projects and be switched
off within a day** — which is worse than no checker. It fails only on things that lose data.

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

An **already-damaged** file does not hold the repo hostage: the guard fires only when `progress.json`
is staged, so unrelated work still commits. It stops the next person who writes the file.

## Related

- `/update-progress` — the conservative edit rules this enforces mechanically (append-only, never
  remove, never reorder, never change ids).
- `/open-work` — renders the tables from this file; exits 2 when it cannot read it. If `open-work`
  reports it cannot read `progress.json`, run this to find out why.
