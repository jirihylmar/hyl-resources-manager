---
description: Mark tasks complete with ultra-conservative update rules (project)
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash
  - mcp__aws-*__call_aws
---

<!--
  Centrally distributed by /distribute-defaults from syndicate-playbooks-examples.
  Project-specific additions go in .claude/local-overlays/<this-filename> as
  splice fragments (see /distribute-defaults for the overlay format).
  Direct edits to this file will be flagged on the next distribution.
-->

# Update Progress

Update progress tracking after completing tasks. Follow conservative rules strictly.

## Ultra-Conservative Update Rules (CRITICAL)

### ALLOWED Modifications to progress.json:
- Change task `status` (pending → in_progress → complete)
- Add `completed_at` timestamp
- Add `started_at` timestamp
- Add entries to `artifacts` array
- Add `notes` field to tasks
- Add `verify_result` field
- Add NEW tasks with NEW IDs
- Update `current_task` pointer
- Update `last_updated` timestamp
- Update `last_session_summary`

### NEVER Do:
- ❌ Remove tasks (mark as `superseded` instead)
- ❌ Reorder tasks
- ❌ Consolidate/merge tasks
- ❌ Rename task names (add note instead)
- ❌ Change task IDs
- ❌ Delete from `artifacts` array

### When Task Scope Changed During Work:
```json
// Mark OLD task as superseded (don't delete)
{"id": "2.1", "name": "Original task", "status": "superseded", "superseded_by": "2.1a", "notes": "Scope changed because..."}

// Add NEW task with new ID
{"id": "2.1a", "name": "Revised task description", "status": "pending", "added_reason": "Supersedes 2.1 due to..."}
```

### When New Task Discovered Mid-Work:

**First ask one question: does this serve the goal of the phase I am in?** The answer decides the
number, and the number decides whether the phase can ever close.

**The first digit carries ONE goal.** Every task under phase `N` must be work in service of phase
`N`'s objective. That is what makes `N` closable: when its goal is met, it is *done*. A phase that
accumulates whatever happened to be discovered while it was open has no single goal, therefore no
finish line, therefore never closes — and everything parked in it is never forced to a decision.

| The discovery… | Number it | Why |
|---|---|---|
| **is needed to finish 2.3 itself** | `2.3a`, `2.3b` — sub-ID, as below | It *is* the current work. Same goal. |
| **serves this phase's goal**, but is its own deliverable | `2.7` — next free ID in the phase | Same goal, new task. |
| **does NOT serve this phase's goal** | **`3.1` — a NEW phase** | However it was found, it is different work. Putting it here is what makes a phase uncloseable. |

**"But I found it while doing 2.3" is not a reason to number it 2.x.** Where work was *discovered*
says nothing about which goal it *serves*. That single confusion is what turns a focused phase into a
40-task drawer.

```json
// Serves the current work — sub-ID keeps logical order
{"id": "2.3a", "name": "New task found during 2.3", "status": "pending", "added_reason": "Discovered during implementation of 2.3"}

// Does NOT serve this phase's goal — new phase, and REWRITTEN TO STAND ALONE.
// Assume the reader has none of this session's context, because they will not.
{"id": "3.1", "name": "Feed serves stale prices up to 6h after a change (cache TTL: feed/cache.py:44)",
 "status": "pending",
 "added_reason": "Found while doing 2.3 (auth refactor); unrelated to that goal, so it starts phase 3 rather than making phase 2 uncloseable. Not investigated further."}
```

**A task in a new phase must be rewritten to stand alone.** The session that understood it is gone,
and by the time anyone reads it the surrounding context has moved. `"fix the thing we discussed"` is
already worthless. If you cannot restate it so a cold reader can act on it — what is wrong, where,
and how you know — that is evidence it should be **dropped**, not carried.

---

## Multi-Agent Discipline

When multiple agents work in the same repo simultaneously, shared files (`progress.json`, `session_notes.md`) become collision points. Follow these rules to prevent agents from overwriting each other's work.

### progress.json: Surgical Edits Only

- **ALWAYS use the Edit tool** (find-and-replace) to modify progress.json — **NEVER use Write** (full file overwrite)
- **Re-read progress.json immediately before each edit** — don't rely on what you read at session start
- **Only modify YOUR task entry** — never touch another task's fields
- **Never modify `current_task` or `current_phase`** unless you are the only agent working — in multi-agent setups, that's the orchestrator's responsibility
- **One Edit call per field change** — smaller edits reduce the collision window

### session_notes.md: Append-Only

- **Re-read the top of the file before appending** — another agent may have added an entry since you last read it
- **Insert your entry after the `---` below the title** — use unique header: `## Session: YYYY-MM-DD - Task X.Y`
- **Never rewrite, reorder, or edit existing entries** — treat other agents' entries as immutable

### Task-Scoped Identity

- **Your task is what the user assigned you** — not whatever `current_task` says in progress.json
- **Only report on and modify your assigned task** — leave other tasks untouched
- **Include task ID in commit messages** — so concurrent commits are traceable: `progress: complete task X.Y - [description]`

---

## Steps

### 1. Read Current State
- Read `progress.json` to understand current state
- Identify which tasks were just completed
- Note which repos were modified

### 2. Verify Completed Tasks
For each task being marked complete:
- Run its `verify` step if defined
- Confirm deliverables exist
- Check AWS resources if applicable

Record verification:
```json
{"id": "2.3", "status": "complete", "verify_result": "PASSED - API returns 200"}
```

### 2a. Grounding-at-Touch (sessions that edited skills or canonical docs)

Index-level hygiene cannot see content rot — a repo passes every clock/ref/index gate while its
skills cite CLI flags that don't exist and its docs describe retired resources. The fix is standing
and incremental: **the session that touches a claim verifies that claim.**

If this session edited any skill (`.claude/commands/*.md`) or canonical doc (`docs/` outside
`_archive/`), verify the operational claims **in the sections you touched** against the actual
implementation before marking the task complete:

| Claim type | Verification |
|---|---|
| Cited file path | Path resolves in the live tree |
| Cited CLI flag / subcommand | Exists in the tool's argument parser (`--help`, source) |
| Deployed-resource name | Appears in a **fresh** inventory, not a remembered one |
| Payload / query shape | Matches the deployed definition (schema, table model, API) |
| Command presented as runnable | Actually shell-runnable as written (multi-line included) |
| Tool handle / resource name inside a fenced EXAMPLE | Same verification as if it were prose — or visibly neutral (a `<placeholder>`, `{braces}`, or the reserved fictional `myproject-` prefix). Agents copy examples as the pattern, and nobody "touches" an illustration, so a retired handle or another project's real resource name survives every gate while teaching every reader the wrong thing. An example is an operational claim, not decoration. |

Also at touch: new/edited content uses the project's terminology-registry names if a registry
exists (no new synonyms, no banned bare words), and adds no phase/task/session numbers as
load-bearing content to canonical surfaces.

**An edit that leaves a touched claim unverified is incomplete work** — verify it, fix it, or
record it as an explicit deferral with a named reason. Scope is the sections you touched, not the
whole file (the standing full-file rotation is Step 2b below).

### 2b. Session-Close Consolidation Slice (EVERY session; one file; bounded)

Step 2a covers what this session changed; this step works off the **standing backlog** — the rot
already sitting in files nobody touched. It runs at every session close so consolidation debt is
paid continuously: one small slice per session beats a monthly rotation, which beats a yearly
crusade. Waiting for a periodic pass is how a repo passes every gate for 30 days while its skills
cite flags that don't exist.

1. **Read the rotation state**: `.claude/hygiene-state.json` → `grounded` map
   (`{"<file>": "<YYYY-MM-DD>"}`). If the file or map is absent, self-bootstrap: create it with
   `{"grounded": {}}` — and recommend the one-time `/repo-hygiene` baseline in the Step 12 report.
2. **Pick ONE file**: the least-recently-grounded live skill (`.claude/commands/*.md`) or canonical
   doc (`docs/` outside `_archive/`), never-grounded first. Files Step 2a fully verified this
   session count as grounded — stamp them in the map rather than re-picking them.
3. **Ground it** (claim types and verifications per the Step 2a table): extract the file's
   operational claims, verify each against the implementation, record claim / reality / fix in
   session_notes.

   **What you do with a defect depends on who owns the file — and there are only two answers:**

   | The file is… | Remedy |
   |---|---|
   | a **project-specific** skill or doc (anything you own) | **fix it in place.** Normal work. |
   | a **distributed default** (the 10 named in § 11.b) | **report it. Never fix it in place.** |

   **Keep grounding the defaults — just never edit them.** Reading them against reality is how
   framework defects get found at all; a real pass grounded them and surfaced four genuine engine
   bugs. That is this step working. But the remedy for a default is § 11.b's: **report requirements
   only**, and record it in session_notes and the Step 12 report as *reported, not fixed*.
   Fixing one in place does two kinds of damage: the next `/distribute-defaults` silently overwrites
   your edit (the fix is **lost**, and the defect returns to every project), or the engine classifies
   the file as changed-since-delivery, which **blocks distribution** — potentially for every project
   on the host, not just yours. Either way you have made things worse than reporting would have.
4. **Same file, naming + de-phasing**: flag synonyms against the terminology registry (registry
   name wins); strip leaked phase/session/task numbers (statement stays, process token goes).
   If NO registry exists yet, seed a minimal `terminology.md` under `docs/` from this file's
   concepts, marked DRAFT, and surface it for ratification in the Step 12 report.
5. **Stamp the map**: `"<file>": "<today>"` for the sliced file and any 2a-verified files. If the
   file was too large to finish, record `"partial": {"<file>": "<where you stopped>"}` in
   `hygiene-state.json` and stamp the map only when the file completes.

**Bounds and skips** (the bound is the point — this must stay cheap enough to never be worth
skipping): one file per session, roughly small-task effort. Skip ONLY when context is already
>60% at session close or the session is an emergency hotfix — record the skip + reason in
session_notes. Two consecutive skips make the slice MANDATORY at the next session close.

### 3. Update progress.json (Conservative)

**Only modify allowed fields:**

```json
{
  "last_updated": "2025-12-20T10:00:00Z",
  "last_session_summary": "Completed 2.3, API endpoint working",

  "current_task": "2.4",

  "phases": {
    "phase_2": {
      "tasks": [
        {
          "id": "2.3",
          "status": "complete",           // ✓ Changed
          "completed_at": "2025-12-20...", // ✓ Added
          "verify_result": "PASSED",       // ✓ Added
          "artifacts": ["arn:aws:..."]     // ✓ Added to array
        }
      ]
    }
  }
}
```

### 3a. Phase-Close Hygiene (runs whenever a phase's status flips to `complete`)

Repos rot at phase boundaries — a closed phase leaves a working dir, verbose progress bodies, and
stale index entries behind. When THIS update marks a phase `complete`:

**0. No phase closes with a task left hanging. Do this FIRST — it can stop the close.**

List every task in the closing phase that is not `complete` or `superseded`. **Each one gets an
explicit disposition. None may be left `pending` in a closed phase.**

> **Why this is a gate and not a tidy-up.** A task left pending is a task that never gets done. It
> outlives the session that understood it, and by the time anyone picks it up its content is stale —
> the code moved, the decision was made elsewhere, the reason is gone. It then sits there looking
> like tracked work while being nothing of the kind, and it makes the phase's completion a lie. The
> honest options are *finish it*, *re-home it*, or *drop it* — and "leave it" is not one of them.

| Disposition | When | What it takes |
|---|---|---|
| **Finished** | It's done | Normal completion + `verify_result`. |
| **Re-homed** | Real work that does **not** serve this phase's goal | A task in a **new phase**, **rewritten to stand alone** (see § When New Task Discovered Mid-Work). Mark the original `superseded` with `superseded_by`. Never move it verbatim — a note that made sense in-session is worthless out of it. |
| **Dropped** | Speculative, overtaken, or no longer justified | `superseded` with a **reason someone can disagree with**. "Not needed" is not a reason. "No measured problem; re-raise with a benchmark" is. |

**Propose all dispositions to the operator and get approval before closing the phase.** You may
recommend — you may not decide. Present them plainly:

```
### Phase 2 close — 2 tasks still open

2.7  Cache invalidation on the product feed
     Does NOT serve phase 2's goal (auth refactor).
     → RE-HOME to new phase 3, rewritten standalone:
       3.1 "The product feed serves stale prices for up to 6h after a price
            change. Cache TTL is set in feed/cache.py:44. Found while doing
            2.3; not investigated further."

2.8  Try the faster JSON parser
     Speculative, raised in passing, 5 weeks old.
     → DROP as superseded, reason: "no measured problem; re-raise with a benchmark."

Approve these dispositions to close phase 2?
```

**If a task cannot be honestly restated for a cold reader, that is evidence to drop it, not to carry
it.** Carrying it forward only moves the staleness somewhere it will be discovered later.

Then the sweeps:

1. **Working-dir sweep (extract-then-archive).** If `docs/<phase-dir>/` (or any working dir the
   phase created) exists: repoint/extract every live inbound reference FIRST (a "closed" dir can
   hold live dependencies — skill default paths, test fixtures, cited rules), then `git mv` the
   remainder to `docs/_archive/`. Never blind-move, never delete. A reference check after the move
   must show zero new broken refs.
2. **progress.json weight check.** If `progress.json` exceeds ~300KB, run the compaction step from
   `/repo-hygiene` (Step 4: dry-run, review, `--apply`) — verbose bodies of long-completed phases
   move to committed sidecars under `docs/_archive/progress-sidecars/`; tasks/ids/status/verify
   never change (append-only preserved).
3. **Index touch-up.** Any index the closed phase's files appeared in (CLAUDE.md pointers, skill
   picker, knowledge base) is reconciled to the post-sweep paths.
4. **Content check on what the phase leaves canonical.** Any doc/skill the phase promotes to (or
   leaves in) a canonical location gets the grounding-at-touch treatment (Step 2a table) and is
   de-phased: phase/task numbering stays with the archived working material, never as load-bearing
   content in the surviving canonical doc. Bounded to the phase's own files — this is a slice,
   not a tree-wide sweep.

This is the incremental half of repo hygiene; the periodic full pass is `/repo-hygiene`
(triggered by the clock gate in `/start-session` Step 2.7).

### 4. Update git_repos Status
For each repo in `git_repos`:
```bash
cd {repo_path}
git status --porcelain
```
- Uncommitted changes → `needs_push`
- Ahead of remote → `needs_push`
- Clean and pushed → `pushed`

### 5. Update session_notes.md

Insert a new entry using the **same header format and placement as the Multi-Agent Discipline
section above** (`## Session: YYYY-MM-DD - Task X.Y`, inserted after the `---` below the title):

```markdown
---

## Session: YYYY-MM-DD - Task X.Y

### Completed This Session
- Task 2.3: Add API endpoint (repo: backend) ✓

### Verification Results
| Task | Verify | Result |
|------|--------|--------|
| 2.3 | curl /api/endpoint | PASSED (200 OK) |

### New Tasks Added
- 2.3a: Handle edge case discovered during 2.3

### Artifacts Created
- arn:aws:lambda:eu-central-1:123456:function:my-function

### Key Decisions Made
- [Any architectural or design decisions]

### Issues Encountered
- [Any problems and how they were resolved]

### Context for Next Session
- Task 2.4 is next: [description]
- Note: [any gotchas or context]

### Git Status
| Repo | Status |
|------|--------|
| orchestration | pushed |
| backend | needs_push |

---
```

### 6. Sync Repository Meta-Docs (CRITICAL)

**These files MUST stay in sync with actual repository state:**

| File | Sync With | Check |
|------|-----------|-------|
| `CLAUDE.md` | `.claude/commands/*.md` | Command count and list matches |
| `README.md` | Actual playbooks, commands | Catalog and features accurate |

**When commands were added/removed this session:**
1. Count files in `.claude/commands/`
2. Compare to command list in CLAUDE.md
3. If mismatch → update CLAUDE.md
4. Check README.md references same commands
5. If mismatch → update README.md

**When new features/playbooks added:**
1. Check README.md Playbook Catalog
2. Update to reflect actual state (exists vs planned)

**Verification command:**
```bash
# Count actual commands
ls -1 .claude/commands/*.md | wc -l

# Should match "Commands Available (N total)" in CLAUDE.md
```

### 7. Update Project Documentation (If Registered)

**Project-specific documents to review and update each session:**

<!--
INSTRUCTIONS: When a project establishes docs/, add each document path here.
Remove this comment block and add entries like:

- `docs/ARCHITECTURE.md` - Update when: infrastructure changes
- `docs/API.md` - Update when: endpoints added/modified
-->

_No documents registered yet. Add paths here as project docs are created._

**For each registered document:**
1. Read current content
2. Check if this session's work affects it
3. If yes: update relevant section, add date
4. If no: skip

**When adding new docs to project:**
1. Create the document
2. Add its path to this section with "Update when" trigger
3. Commit this command file with the addition

### 8. Maintain Project-Specific Skills

**Purpose**: Continuously improve project-specific skills based on session experience.

**Scope**: Only project-specific skills — everything in `.claude/commands/` EXCEPT the distributed
defaults, which are named once in § 11.b below. (This list used to be spelled out here too, and went
stale: it said "9 defaults" and named a `refresh-remote.md` that no longer existed while missing
`repo-hygiene.md`. One statement, one place.)

If there are no project-specific skills, skip this step.

**8a. Fix mistakes in skills**

If you made mistakes during this session that a project-specific skill could have prevented or guided better:
- Update that skill with corrective guidance
- Add a note explaining what went wrong and the fix
- This prevents the same mistake in future sessions

**8b. Cross-reference skills**

Ensure each project-specific skill references related skills so Claude knows what's available and when to suggest each one:
```markdown
## Related Skills
- `/composition-editor` - Use when editing product compositions
- `/process-handoff` - Use after completing a batch to hand off
```

**8c. Document skills in project CLAUDE.md**

Ensure the project's `CLAUDE.md` has a section listing all project-specific skills with:
- Skill name
- When to use it
- What it does

Example:
```markdown
## Project Skills
| Skill | When to Use | Purpose |
|-------|------------|---------|
| /composition-editor | Editing product compositions | Guides through composition fields and validation |
| /process-handoff | After completing a processing batch | Documents results and prepares next batch |
```

If skills were added, removed, or renamed this session, update this table.

### 9. Check All Git Repos
```bash
# Orchestration
git status

# Each sub-repo that is present (discovered by glob, not a hardcoded list)
for dir in */; do
  dir="${dir%/}"
  if [ -d "$dir/.git" ]; then
    echo "=== $dir ==="
    git -C "$dir" status --short
  fi
done
```

**The sub-repo list is discovered, never hardcoded** — same rule and same idiom as `/start-session` Steps 0/0.5/8, where the rationale is argued in full. Steps 9 and 10 here used to read `for dir in infrastructure backend frontend testing`, a fixed list that silently matched **nothing** in any project whose sub-repos are named otherwise. Because every iteration is guarded by `[ -d "$dir/.git" ]`, a non-matching name produced **no error and no output**: the step reported success having reviewed, committed and pushed **zero** sub-repos. `progress.json` `git_repos` remains the **declarative registry** this step reports *into*; the filesystem is what it reads *from*. With no subdirectories the glob is a safe no-op.

> **Why this mattered most in Step 10.** A missed *pull* causes staleness and is recoverable — the work still exists on origin. A missed *push* means the work exists on exactly one disk and nowhere else. The hardcoded list was fixed on the pull side (`/start-session`) before the push side; if you are reading this in a project that resolved zero sub-repos before, those repos were never published by session close, while the Step 12 report rendered as though all was well.

### 10. Commit and Push Your Work (every repo you changed this session)

Commit and **FF-push only the work YOU did this session — the repos and files you changed for your task, and nothing else.** This is Axis B (cross-checkout publication): other machines (the box, offline computers) only see your work once it reaches the shared origin, so leaving a repo you changed committed-but-unpushed is exactly the stale-checkout trap that `/start-session` Step 0 then has to skip on the next machine. It is distinct from the same-checkout Multi-Agent Discipline above.

**Two firewalls govern this step:**
1. **Scope to your own work.** Commit by named paths only — never `git add -A` / `git add .` — and only in repos you actually modified for your task. Do not sweep unrelated dirty files, and do not commit or push a repo you did not touch. This is the Multi-Agent Discipline rule "commit only files related to your task," applied across repos. _This rule is now also enforced **mechanically**: a pre-commit guard (`.claude/hooks/pre-commit`, armed by `/start-session` Step 0.5) blocks any commit that newly adds a build artifact or an oversized blob, regardless of how you staged — so `git add -A` cannot silently sweep a build zip into history. The prose here is the intent; the hook is the backstop. If the guard blocks a legitimately-intended large file, allowlist it in `.claude/hooks/artifact-guard.allow` rather than reaching for `--no-verify`._
2. **Push is publish, not deploy** (see the blockquote below).

**Commit the orchestration repo (scoped to its two files, task-ID message):**
```bash
git commit -m "progress: complete task X.Y - [brief description]

Completed:
- Task X.Y: [name]

Next: Task X.Z

🤖 Generated with Claude Code" -- progress.json session_notes.md
```

(The `-m` message comes BEFORE the `--` pathspec — `git commit -- <paths> -m "msg"` fails because
everything after `--` is treated as a pathspec, including `-m`.)

**Commit each sub-repo you changed (scoped by pathspec — never `git add -A`):**
```bash
for dir in */; do
  dir="${dir%/}"
  [ -d "$dir/.git" ] || continue
  [ -n "$(git -C "$dir" status --porcelain)" ] || continue   # skip repos you did not touch
  echo "=== $dir: review, then commit ONLY your task's files ==="
  git -C "$dir" status --short
  # git -C "$dir" commit -m "task X.Y: [what changed in $dir]" -- <your-changed-files>
done
```

**FF-push every repo you committed — fast-forward only; skip + report; never force (same policy as `/start-session` Step 0 and `/distribute-defaults`):**
```bash
push_ff() {  # $1=dir, $2=label; commit BEFORE calling
  git -C "$1" rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1 \
    || { echo "SKIP $2: no upstream (local-only) — committed, NOT pushed"; return; }
  git -C "$1" fetch --quiet 2>/dev/null || { echo "SKIP $2: origin unreachable (offline) — committed locally, push when online"; return; }
  if git -C "$1" push --quiet 2>/dev/null; then
    echo "OK   $2: pushed to origin (commits published; NOT built or deployed)"
  else
    echo "SKIP $2: non-fast-forward — DO NOT force, DO NOT 'git pull'/merge to make it succeed; commit is safe locally; resolve with /syndicate-refresh-remote, then re-push"
  fi
}
push_ff "." orchestration
for dir in */; do
  dir="${dir%/}"
  [ -d "$dir/.git" ] && push_ff "$dir" "$dir"
done
```

Because Step 0 fast-forwarded you to origin-latest at session start and you commit only your task's files, the commits you push are your own. (If a co-agent on this same checkout left an unpushed commit beneath yours, `git push` will publish theirs too — note it in the report; it is committed work, not lost, but it was their publish decision.)

> **CRITICAL — push is PUBLISH, not DEPLOY. Never conflate the two.**
> A successful `git push` means exactly one thing: **your commits now exist on origin.** It does NOT mean a build ran, an artifact was produced, a deployment happened, or any live/running system changed. SOME repos have CI that builds or deploys on push to certain branches; MANY do not — and you cannot reliably tell which. **Treat build and deploy as a SEPARATE step you claim ONLY when you actually ran it and its own verify passed** (the task's `verify`/`verify_result` field is where that evidence lives). In your report and notes, say **"pushed to origin"** — say "built", "deployed", "shipped", or "live" ONLY with independent evidence. If you ran no build/deploy this session, state that plainly.

Mark a repo's `git_repos` status `pushed` only after a confirmed FF-push; a repo skipped for non-FF stays `needs_push` and is surfaced in the Step 12 report. Work is never lost: an unpushable commit stays safe locally and is flagged, never forced and never discarded.

### 11. Extract Session Knowledge

> **SCOPE — read this before anything else in Step 11.** Everything below governs **knowledge
> extractions**: things this session *learned*, headed for the Syndicate expert knowledge base. It
> governs **nothing else**. In particular, the prohibition further down — *"never write the
> extraction into the current repo as a substitute"* — is about **extractions**, and is **not** a
> rule about writing to repos in general. It has already been misread as one, with real cost (see
> § A framework defect is reported, never implemented).

#### 11.a — Two different things travel two different roads. Do not confuse them.

| | **A learning** | **A framework defect** |
|---|---|---|
| What it is | something you now know: a pattern, an anti-pattern, a check | a distributed default is *wrong* |
| Where it goes | the knowledge inbox — this Step 11 | a report to the operator |
| Who consumes it | the Syndicate experts | the engine repo, as an approved task |
| What you do | write the extraction (below) | **report it. Nothing else.** |

#### 11.b — A framework defect is reported, never implemented

If you find a defect in a **distributed default** (`add-work.md`, `check-aws.md`,
`generate-architecture.md`, `generate-phases.md`, `repo-hygiene.md`, `syndicate-refresh-remote.md`,
`setup-workflow-only.md`, `setup.md`, `start-session.md`, `update-progress.md`) — a wrong claim, a
dead path, a rule that misfires — **you report it. You do not fix it.**

**You may not:** edit the engine repo (`syndicate-playbooks-examples`); edit the default in place
here (the next distribution overwrites it, and the edit is *lost*); run `/distribute-defaults`; or
decide that the framework should change. **Every one of those is the operator's call, not yours.**

**Report requirements only** — the problem, the evidence, and what would have to change. Then stop.
The operator carries it to the engine, where agents serving that repo implement it as a tracked,
approved task. That two-step is the long-standing structure and it works: the report is one commit,
the implementation is another, and a human decides in between.

> **This is not hypothetical.** An agent found a real framework defect, hand-patched the engine
> **and** filed its own feedback entry — doing both steps in one act, ticking its own
> `[ ] Reviewed by human` box, and pushing its own conclusions toward every project on the estate.
> Corrected, it then **deleted its own work** on a misreading of the prohibition below, and reported
> `"pushed revert ✓"` for a revert that had not run. Two unilateral acts, the second worse than the
> first. Both were avoidable by stopping at "report".

**Why an extraction is not the channel for this.** An extraction becomes *expert expertise* in the
knowledge base. A framework fix routed there lands as advice attached to an expert — it will never
reach the skill file it was about. Right road, wrong vehicle: **say it to the operator.**

> **The inbox is one instance of a general rule — see `/start-session` Step 2.5.** A repo lives in
> exactly ONE place. `syndicate-playbook` (the inbox) and `mcp-docker-playbook` (the MCP deploy repo)
> live **on the box** and are developed there; `syndicate-playbooks-examples` and `syndicate-remote`
> are **local-only** and must never appear on the box. Any `/home/<user>/<repo>/…` path in a skill is
> a **claim about location that may already be false** — resolve by presence before acting on it, and
> if the repo turned out to be remote, do the work there and say so. Never let a dead path become an
> excuse to improvise locally. The rest of this step applies that rule to the knowledge inbox.

#### 11.0 — ALWAYS FIRST: resolve the inbox, then flush the spool

**Do this on every run of this step, whether or not this session produced any learnings.** A spool
backlog is left by an *earlier* run that hit an outage; it has nothing to do with what *this* session
learned. If the flush were nested under "write extraction file (if candidates found)", a host that
spooled once and then had a run of quiet sessions would never deliver — the spool would silently
become the destination it is explicitly not allowed to be.

**Resolve the delivery route by presence — one method for every host.** The inbox is
`hub440-syndicate/syndicate-playbook` on GitHub, drained onto the box by the `git pull` it already
does. Every host delivers the same way: **POST to the ingest endpoint over HTTPS.** No host uses
inbound SSH, a firewall entry, a static IP, `box.json`, or a PEM — those retired with the `remote`
route (see `syndicate-playbooks-examples/docs/knowledge-ingest-lambda-instruction.md` — that doc lives
in the **engine** repo, which is local-only; it is deliberately NOT distributed, so do not expect a
bare `docs/…` copy of it inside a project). Resolve by **presence**, never by hostname:

```bash
SPOOL="$HOME/.syndicate-knowledge-spool"        # used by 11.0 and by step 3 below
INGEST="$HOME/.syndicate-remote-secrets/ingest.json"
# Trust a config only if it PARSES and carries its required non-empty fields — NEVER by mere
# existence. Measured 2026-07-24: a 0-byte box.json passed an existence check, resolved a "healthy"
# route, then failed every delivery while reporting health. An empty/corrupt ingest.json must
# resolve spool with a DISTINCT warning, not a route.
ingest_ok() { [ -s "$INGEST" ] && python3 -c "import json,sys;d=json.load(open('$INGEST'));sys.exit(0 if d.get('url') and d.get('token') else 1)" 2>/dev/null; }
if [ -d "$HOME/syndicate-playbook/knowledge_extraction" ]; then
  ROUTE=direct         # this host literally holds the inbox (the box) — write straight to it
elif ingest_ok; then
  ROUTE=ingest         # POST the extraction to the ingest endpoint over HTTPS (below)
elif [ -f "$INGEST" ]; then
  ROUTE=spool          # present but EMPTY/INVALID — do NOT trust it into a route
  echo "WARNING: $INGEST exists but is empty or missing url|token — treating as NO route (spool). Re-run syndicate-connect."
else
  ROUTE=spool          # no ingest config on this host yet — spool it, loudly
fi
echo "$ROUTE"
```

`direct` is not a second *method* — it is the same file landing in the same place without a network
hop, on the one host that is already sitting on the inbox. Every other host uses `ingest`.

**If this host resolves `spool`, say the remedy — do not just report the backlog.** An outage clears
on its own; a host that has never been given an ingest config does not. On such a machine both
conditions above stay false forever, every extraction accumulates undelivered, and the flush block
below prints `SPOOL: empty` — which reads as health. Name it as a **setup gap** and give the one
command that closes it (the operator supplies the URL + a per-host token, out of band):

```bash
bash .claude/skills/syndicate-connect/connect.sh --url <ingest url> --token <host token>
```

Per **machine**, once — never per project: the resolver reads `$HOME` and nothing else, so afterwards
every project on the host reports regardless of where it lives on disk (including under `/mnt/c/...`).
The command only writes `ingest.json` (mode 600) after a probe POST returns a non-5xx — a host never
trades `spool` (loud) for `ingest` (confident, and wrong). Whatever is already spooled flushes on the
next run of this step.

Do **not** clone the inbox to make `direct` true instead — it lives in exactly ONE place, and a
second live copy accumulates untracked extraction files that git never reconciles.

**Then flush the spool.** If `ROUTE` is `direct` or `ingest` and `$SPOOL` is non-empty, deliver the
backlog by that route now, and **remove only the files that confirmably arrive** (a `200` from the
endpoint, or a completed `direct` write). A file that fails to deliver stays spooled — never deleted,
never assumed delivered:

```bash
# SELF-CONTAINED ON PURPOSE — re-derives SPOOL and ROUTE instead of inheriting them.
# Each fenced block runs as its OWN shell: variables set in the block above do NOT survive.
# This block used to rely on $SPOOL from that block; it arrived empty, `[ -d "" ]` was false,
# and the flush was skipped SILENTLY with exit 0 — a spooled extraction was never delivered and
# never reported. The one thing the spool exists for is to fail LOUDLY; that bug made it fail
# exactly like the silent repo-scatter it replaces. Keep every variable this block needs local.
SPOOL="$HOME/.syndicate-knowledge-spool"
INGEST="$HOME/.syndicate-remote-secrets/ingest.json"
ingest_ok() { [ -s "$INGEST" ] && python3 -c "import json,sys;d=json.load(open('$INGEST'));sys.exit(0 if d.get('url') and d.get('token') else 1)" 2>/dev/null; }
if [ -d "$HOME/syndicate-playbook/knowledge_extraction" ]; then ROUTE=direct
elif ingest_ok; then ROUTE=ingest
else ROUTE=spool; fi

if [ -d "$SPOOL" ] && [ -n "$(ls -A "$SPOOL" 2>/dev/null)" ]; then
  echo "SPOOL: $(ls -1 "$SPOOL" | wc -l) extraction(s) awaiting delivery — route=$ROUTE"
  # deliver each via $ROUTE (direct: mv into the inbox; ingest: POST — see step 3),
  # and rm ONLY on confirmed success. If ROUTE=spool, deliver nothing and report the backlog.
else
  echo "SPOOL: empty (route=$ROUTE) — nothing awaiting delivery"
fi
```

**Report the outcome in Step 12 even if this session extracted nothing** — `N flushed, M still
spooled`. A backlog that nobody reports is a backlog nobody clears.

#### 11.1 — Extract this session's knowledge

**Purpose**: Capture learnings from this session for future use.

**When to extract** (at least one must apply):
- Fix commits made this session
- User corrections during session
- Non-obvious solutions discovered
- Patterns that apply beyond this project

**Extraction process**:

1. **Identify candidates** from this session:
   - Git commits with `fix:` prefix
   - Commits that correct previous work
   - User corrections noted in conversation
   - Solutions to non-trivial problems

2. **Filter by quality criteria** (must pass ALL):
   - **Actionable**: Clear recommendation, not just observation
   - **Generalizable**: Applies beyond this specific project
   - **Verified**: Actually worked (commit succeeded, test passed)

3. **Write extraction file** (if candidates found):

   **Naming convention**: `{project}-{YYYY-MM-DD}-{topic}-recommended.md`

   Write it via the `$ROUTE` already resolved in **11.0** — do not re-resolve, and never invent a
   third destination:

   - **direct** — write `$HOME/syndicate-playbook/knowledge_extraction/{project}-{YYYY-MM-DD}-{topic}-recommended.md`
     with the Write tool (the box, sitting on the inbox).

   - **ingest** — write the file to a temp path (`TMPFILE=$(mktemp)`, then Write into it), and POST it
     to the endpoint. The endpoint authenticates the token, derives the filename server-side, and
     commits it into the inbox repo; the box drains it by pulling. Uses outbound HTTPS only — no SSH,
     no port 22, nothing opened inbound anywhere:

     ```bash
     CFG=~/.syndicate-remote-secrets/ingest.json
     URL=$(python3 -c "import json;print(json.load(open('$CFG'))['url'])")
     TOK=$(python3 -c "import json;print(json.load(open('$CFG'))['token'])")
     code=$(curl -sS -X POST -H "Authorization: Bearer $TOK" --data-binary @"$TMPFILE" \
       -o /tmp/ingest.out -w '%{http_code}' \
       "$URL?project={project}&topic={topic}&date={YYYY-MM-DD}")
     # 200 = committed to the inbox repo (see /tmp/ingest.out for the path). Any other code:
     # DO NOT drop it — fall through to spool with the code + body as the reason.
     [ "$code" = 200 ] || echo "ingest returned $code: $(cat /tmp/ingest.out)"
     ```

   - **spool** — **also the fallback whenever `direct` fails or the `ingest` POST returns non-200**
     (endpoint down, token rejected, offline). Never drop the extraction, and never substitute a local
     repo path:

     ```bash
     mkdir -p "$SPOOL" && chmod 700 "$SPOOL"
     mv "$TMPFILE" "$SPOOL/{project}-{YYYY-MM-DD}-{topic}-recommended.md"
     ```

     Then **report it loudly** in the Step 12 summary — spooled, not delivered, with the reason verbatim.
     The spool is a **waiting room, not a destination**: it is drained by **11.0** on the next run that
     resolves an inbox, and by `/syndicate-refresh-remote` Step 6a.

   > **Never write the extraction into the current repo as a substitute.** A local write looks like
   > success and silently removes the knowledge from the curation path — that is worse than an outage,
   > because an outage is visible. If the inbox cannot be reached, **spool and say so**. The spool
   > fails *loudly*; the repo-scatter fails *silently*, and the silent one is the failure class this
   > step exists to prevent.
   >
   > **What this rule covers, exactly:** writing **an extraction** somewhere other than the inbox.
   > "The current repo" means **the project you are working in** — the one whose task you are
   > closing. That is the whole scope.
   >
   > **What it does NOT cover** — it has been read as governing all three, and does not:
   > it is not a rule about writing to repos in general; it says nothing about the engine repo
   > (`syndicate-playbooks-examples`), which is not "the current repo" from any project session; and
   > **a change to a canonical skill is not an extraction**, so this sentence neither permits nor
   > forbids it — § 11.b does, and the answer there is *report, never implement*.
   >
   > A rule read past its scope does damage in the direction the rule never intended. This one was
   > read as a ban on legitimate work, and the agent's response was to **delete** it. If you are
   > about to remove content because of this sentence: **stop.** This sentence has never once asked
   > anyone to delete anything.

   The file body, in every case:
   ```markdown
   # {Topic} Knowledge Extraction

   **Project**: {project name}
   **Date**: YYYY-MM-DD
   **Source**: {session description or task range}

   ---

   ## hamilton (Planning)

   ### {Title of learning}
   **Type**: pattern | anti_pattern | check
   **Description**: {Clear, actionable description of the learning}
   **Learned from**: {What happened that taught this lesson}
   **Provenance**: {project:commit_sha or session reference}

   ---

   ## ritchie (Systems/Infrastructure)

   ### {Title}
   **Type**: pattern | anti_pattern | check
   **Description**: {Description}
   **Learned from**: {Context}
   **Provenance**: {Reference}

   ---

   ## dijkstra (Correctness/Testing)

   ### {Title}
   **Type**: pattern | anti_pattern | check
   **Description**: {Description}
   **Learned from**: {Context}
   **Provenance**: {Reference}

   ---

   ## codd (Data/Schema)

   ### {Title}
   **Type**: pattern | anti_pattern | check
   **Description**: {Description}
   **Learned from**: {Context}
   **Provenance**: {Reference}

   ---

   ## wiener (Oversight/Ethics)

   ### {Title}
   **Type**: pattern | anti_pattern | check
   **Description**: {Description}
   **Learned from**: {Context}
   **Provenance**: {Reference}

   ---

   ## Summary

   | Expert | Patterns | Anti-patterns | Checks | Total |
   |--------|----------|---------------|--------|-------|
   | hamilton | X | X | X | X |
   | ritchie | X | X | X | X |
   | dijkstra | X | X | X | X |
   | codd | X | X | X | X |
   | wiener | X | X | X | X |
   | **Total** | **X** | **X** | **X** | **X** |

   ---

   ## Approval Status

   - [ ] Reviewed by human
   - [ ] Approved for loading
   - [ ] Loaded to database
   ```

   **Note**: Only include expert sections that have learnings. Omit empty sections.

   **On leibniz — deliberately absent, and not a gap to fix.** The project declares six experts;
   this template names five. That is **intended**: leibniz is a **meta-expert** and correctly holds
   no extracted expertise, which is why the live knowledge base shows a profile and zero expertise
   items across hundreds of extractions. Do **not** add a leibniz section, do not route learnings
   there, and do not report the absence as a defect — it has been re-discovered and re-raised more
   than once. If that ever changes, it changes here first, by the operator.

4. **Expert assignment**:
   | Domain | Expert |
   |--------|--------|
   | cdk, lambda, iam, aws, infrastructure | ritchie |
   | schema, api, data, dynamodb, contract | codd |
   | test, error, validation, bug, edge case | dijkstra |
   | plan, phase, task, progress, sequence | hamilton |
   | oversight, human review, automation | wiener |

5. **Skip extraction if**:
   - Only trivial changes (typos, formatting)
   - All changes project-specific (config values, paths)
   - No corrections or learnings this session

### 12. Report Summary

```
## Progress Summary

### Completed This Session
- Task 2.3: Add API endpoint (backend) ✓
  - Verify: PASSED
  - Artifacts: [list]

### Tasks Added This Session
- Task 2.3a: Handle edge case (pending)

### Knowledge Extracted (delivery state — say which route, never just "written")
- File: {project}-2025-12-22-api-error-handling-recommended.md
- Items: 2 patterns, 1 anti-pattern
- Delivered: ingest → HTTPS POST, committed to the inbox repo (path from the 200 response)
  (or "direct → $HOME/syndicate-playbook/knowledge_extraction/" on the box; or "SPOOLED → ~/.syndicate-knowledge-spool/ — NOT delivered: <reason verbatim>")
(or "None - no generalizable learnings this session")

### Knowledge Spool (ALWAYS report — never omit, even when nothing was extracted)
- Route resolved: ingest (or direct on the box / spool — no ingest config on this host)
- Flushed this run: 0
- Still spooled: 0
(A backlog is independent of whether this session learned anything. "Nothing extracted" must never
hide "3 extractions still undelivered" — that is how a waiting room quietly becomes a destination.)

### Open Work (rendered mechanically — run it, do not compose it)

{{OPEN_WORK_TABLES}}

[Produced by:  python3 .claude/skills/open-work/open_work.py   — run from the project root,
 output pasted verbatim, every <FILL: …> token replaced. Same three tables and same rules as
 /start-session § 4.0/4.0a, which is where they are explained; this is the same renderer, not a
 second copy of the spec. Exit 2 = progress.json unreadable: report that verbatim rather than
 omitting the tables. Skill absent = render by hand to the same shape and say the skill is
 missing.

 The operator is closing this session and opening another project. They do not carry this
 project's task numbers in their head, and a task that renders as an ID alone has not been
 reported. Do not summarise the tables into prose, and do not drop rows for brevity — a stuck
 or deferred row surviving session after session with no decision is itself the finding, and it
 belongs in Step 3a's dispositions rather than in another silent listing.]


### Overall Progress
Phase 2: 3/5 tasks complete
Total: 8/20 tasks complete (40%)

### Repository Status (publish state only — NOT build/deploy state)
| Repo | Pushed to origin? | Notes |
|------|-------------------|-------|
| orchestration | yes (FF) | commits published; not built/deployed |
| backend | SKIPPED (non-FF) | diverged — committed locally, resolve via /syndicate-refresh-remote then re-push |

"Pushed to origin" means the commits reached the shared origin and other machines can now FF-pull them. The pushes above updated origin only — no CI ran, nothing was built, and no live system changed. A build/deploy is a SEPARATE step, claimed only if you ran it and verified it (state it explicitly, or say "no build/deploy was run").

### Next Task
- Task 2.4: [name] (repo: [repo])

### Action Required (only if something could not be published, or a deploy is expected)
- Diverged repos: resolve with /syndicate-refresh-remote, then re-push. (Your commit is safe locally.)
- Offline / local-only repos: re-push when origin is reachable / after adding an origin.
- Deploy expected but not run: run the deploy command and verify it separately — pushing did not perform it.
- Spooled extractions: the inbox was unreachable; files are safe in `~/.syndicate-knowledge-spool/` and will flush on the next session that reaches it, or run `/syndicate-refresh-remote`. Nothing is lost — but nothing is curated either until they land.
- Spooled **because this host has no route at all** (`route=spool`, no `ingest.json`, no local inbox): that is a **setup gap, not an outage** — it will not clear by waiting, and every future session adds to the pile. Say so, and give the fix: `bash .claude/skills/syndicate-connect/connect.sh --url <ingest url> --token <host token>` (per machine, once; the operator supplies the URL + a per-host token).
- (If every repo shows pushed / nothing-to-push, the spool is empty, and no deploy is pending: no action required.)
```

---

## Notes
- ALWAYS update progress.json BEFORE committing
- ALWAYS verify completed tasks
- NEVER remove or reorder tasks
- Add new tasks with sub-IDs (2.3a, 2.3b)
- Document everything in session_notes.md
- Knowledge extraction is best-effort (skip if no learnings)
