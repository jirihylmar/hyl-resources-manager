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
