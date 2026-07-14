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
```json
// Add with sub-ID to maintain logical order
{"id": "2.3a", "name": "New task found during 2.3", "status": "pending", "added_reason": "Discovered during implementation of 2.3"}
```

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
   operational claims, verify each against the implementation, fix in place, record
   claim / reality / fix in session_notes.
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

**Scope**: Only project-specific skills — everything in `.claude/commands/` EXCEPT the 10 defaults:
`add-work.md, check-aws.md, generate-architecture.md, generate-phases.md, repo-hygiene.md, syndicate-refresh-remote.md, setup-workflow-only.md, setup.md, start-session.md, update-progress.md`

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

**Resolve the inbox — `syndicate-playbook` is remote-only.** The one inbox is
`<workspace>/syndicate-playbook/knowledge_extraction/`. Resolve it by **presence**, never by hostname
or `$USER`: the same file ships to every host, it works while a local copy still exists, and it needs
no edit on the day the local copy is retired.

```bash
SPOOL="$HOME/.syndicate-knowledge-spool"        # used by 11.0 and by step 3 below
if [ -d "$HOME/syndicate-playbook/knowledge_extraction" ]; then
  ROUTE=direct         # this host holds the inbox — write straight to that path
elif [ -f "$HOME/.syndicate-remote-secrets/box.json" ]; then
  ROUTE=remote         # inbox is on the box — scp it in
else
  ROUTE=spool          # inbox not resolvable from this host — spool it
fi
echo "$ROUTE"
```

**Then flush the spool.** If `ROUTE` is `direct` or `remote` and `$SPOOL` is non-empty, deliver the
backlog by that route now, and **remove only the files that confirmably arrive**. A file that fails to
deliver stays spooled — never deleted, never assumed delivered:

```bash
if [ -d "$SPOOL" ] && [ -n "$(ls -A "$SPOOL" 2>/dev/null)" ]; then
  echo "SPOOL: $(ls -1 "$SPOOL" | wc -l) extraction(s) awaiting delivery — flushing via $ROUTE"
  # deliver each via the resolved route (direct: mv into the inbox; remote: scp — see step 3),
  # and rm ONLY on confirmed success. If ROUTE=spool, deliver nothing and report the backlog.
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
     with the Write tool.

   - **remote** — write the file to a temp path (`TMPFILE=$(mktemp)`, then Write into it), and copy it
     in. This uses only services that already exist on the box; it creates and changes nothing there:

     ```bash
     CFG=~/.syndicate-remote-secrets/box.json
     HOST=$(python3 -c "import json;print(json.load(open('$CFG'))['host'])")
     BUSER=$(python3 -c "import json;print(json.load(open('$CFG'))['user'])")
     WS=$(python3 -c "import json;print(json.load(open('$CFG'))['workspace'])")
     KEY=$(python3 -c "import json;print(json.load(open('$CFG'))['ssh_key'])")
     scp -i "$KEY" -o ConnectTimeout=15 "$TMPFILE" \
       "$BUSER@$HOST:$WS/syndicate-playbook/knowledge_extraction/{project}-{YYYY-MM-DD}-{topic}-recommended.md"
     ```

   - **spool** — **also the fallback whenever `direct` fails or the `remote` `scp` fails** (box rebooting,
     SSH unreachable, key rejected). Never drop the extraction, and never substitute a local repo path:

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
- Delivered: direct → $HOME/syndicate-playbook/knowledge_extraction/
  (or "remote → box inbox via scp"; or "SPOOLED → ~/.syndicate-knowledge-spool/ — NOT delivered: <reason verbatim>")
(or "None - no generalizable learnings this session")

### Knowledge Spool (ALWAYS report — never omit, even when nothing was extracted)
- Route resolved: direct (or remote / spool — inbox unreachable)
- Flushed this run: 0
- Still spooled: 0
(A backlog is independent of whether this session learned anything. "Nothing extracted" must never
hide "3 extractions still undelivered" — that is how a waiting room quietly becomes a destination.)

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
