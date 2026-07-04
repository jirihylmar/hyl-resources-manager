---
description: Initialize context for a new Claude Code session (project)
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - AskUserQuestion
  - mcp__aws-*__call_aws
---

<!--
  Centrally distributed by /distribute-defaults from syndicate-playbooks-examples.
  Project-specific additions go in .claude/local-overlays/<this-filename> as
  splice fragments (see /distribute-defaults for the overlay format).
  Direct edits to this file will be flagged on the next distribution.
-->

# Start Session

Initialize context and verify previous work before starting new tasks.

---

## Multi-Agent Discipline

When multiple agents work in the same repo simultaneously, each agent is assigned a specific task by the user/orchestrator. Follow these rules to avoid conflicts.

### Task Assignment

- **Your task comes from the user, not from `current_task` in progress.json** — in multi-agent setups, `current_task` may belong to another agent
- If the user specifies a task (e.g., "work on 2.3"), that is YOUR task for this session
- If no task is specified and you are the only agent, use `current_task` as normal

### Reading Shared State

- **Re-read `progress.json` before presenting session handoff** — another agent may have updated it since the file was last cached
- **Do not modify `current_task` or `current_phase`** — in multi-agent setups, the orchestrator manages these fields
- **Check for in-progress tasks by other agents** — if another task shows `in_progress`, note it but don't interfere

### Commit Discipline

- **Include your task ID in all commit messages** — e.g., `progress: complete task 2.3 - [description]`
- **Commit only files related to your task** — don't stage changes from another agent's work

---

## Steps

### 0. Sync to Latest (FF-pull, before any work begins)

**Run this FIRST — before reading orchestration files, before the capability inventory, before AWS verify (Step 5), and before pre-work verify (Step 6).** Those steps all read code or `progress.json`, and a pull can change them; syncing first means every downstream step operates on origin-latest, not a stale tree.

**Why this is a different axis from Multi-Agent Discipline above.** That section governs many agents sharing ONE checkout. This step governs the SAME repo checked out in multiple LOCATIONS — local WSL, the remote dev box (synced via `/syndicate-refresh-remote`, configured by `box.json`), and occasionally-online offline machines — all sharing ONE origin. A commit pushed from any location lands in origin; a checkout that has not pulled is now stale. Surgical Edits cannot save you if the whole file you are editing is three commits behind origin.

**Policy — identical to `/distribute-defaults`: fast-forward only, skip + report, never force.** Never merge, never rebase, never reset, never `--force`. Any repo that cannot fast-forward (dirty tree, diverged, detached HEAD, no upstream, or origin unreachable/offline) is left untouched and reported; resolve divergence with `/syndicate-refresh-remote`. If the repo carrying your task cannot fast-forward, STOP and surface it in the Step 9 report before doing the task — working a stale/diverged checkout risks an unpushable divergence.

For the orchestration repo and each present sub-repo, fetch then fast-forward only:

```bash
sync_ff() {  # $1=dir ('.' for orchestration), $2=label
  git -C "$1" fetch --quiet 2>/dev/null || { echo "SKIP $2: origin unreachable (offline?) — proceeding on current checkout"; return; }
  git -C "$1" rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1 \
    || { echo "SKIP $2: no upstream (local-only) — nothing to pull"; return; }
  [ -z "$(git -C "$1" status --porcelain)" ] \
    || { echo "SKIP $2: working tree dirty — commit/stash or use /syndicate-refresh-remote first"; return; }
  if git -C "$1" merge-base --is-ancestor HEAD @{u} 2>/dev/null; then
    git -C "$1" merge --ff-only @{u} && echo "OK   $2: fast-forwarded to origin-latest"
  else
    echo "SKIP $2: diverged / non-fast-forward — DO NOT force; resolve with /syndicate-refresh-remote"
  fi
}
sync_ff "." orchestration
for dir in infrastructure backend frontend testing; do
  [ -d "$dir/.git" ] && sync_ff "$dir" "$dir"
done
```

A brand-new Phase-0 project whose orchestration repo has no upstream yet is local-only — that is normal; `no upstream` means nothing to pull, so proceed. Carry each repo's sync result into the Step 9 "Session Ready" report. (`infrastructure backend frontend testing` matches the existing Step 8 list; the long-term source of truth is `progress.json` `git_repos`.)

### 0.5. Ensure the Commit Guard Is Armed (idempotent; never creates files)

A mechanical pre-commit guard (`.claude/hooks/pre-commit`) blocks `git add -A` from sweeping build artifacts / oversized blobs into history — enforced by git on **every** commit, so it holds even when an agent forgets the scoped-commit rule. But it only fires once `core.hooksPath` is set, which is **repo-local config that does NOT travel with a clone**. Re-affirm it every session, right after Step 0 and **before any commit this session makes** (e.g. the Step 2 CLAUDE.md self-heal).

This step only ARMS an already-delivered guard — it never creates or commits the hook file (delivery is `/distribute-defaults`'s job). For the orchestration repo and each present sub-repo:

```bash
arm_guard() {  # $1=dir
  local hp="$1/.claude/hooks/pre-commit"
  if [ -f "$hp" ]; then
    chmod +x "$hp" 2>/dev/null
    [ "$(git -C "$1" config --get core.hooksPath 2>/dev/null)" = ".claude/hooks" ] \
      || git -C "$1" config core.hooksPath .claude/hooks
    echo "OK   $1: commit guard armed (core.hooksPath=.claude/hooks)"
  else
    echo "WARN $1: no .claude/hooks/pre-commit — run /distribute-defaults to deliver it (not creating it here)"
  fi
}
arm_guard "."
for dir in infrastructure backend frontend testing; do
  [ -d "$dir/.git" ] && arm_guard "$dir"
done
```

Report each repo's armed/absent result in the Step 9 "Session Ready" block. (Re-running this is a no-op once `core.hooksPath` is set.)

### 1. Read Orchestration Files

- Read `CLAUDE.md` for project context, rules, and conventions
- Read `progress.json` to identify current state and context hints
- Read last entry in `session_notes.md` for recent context

### 2. Build Capability Inventory (before you build anything)

**Why this step exists — the "reinventing the wheel" failure:** agents hand-rebuild functionality that already ships as a project command, because they trust a command list written in `CLAUDE.md` prose. Hand-maintained lists drift the moment a command is renamed, added, or is project-specific. The ONLY source of truth is the live filesystem: `.claude/commands/*.md`. Derive your toolset from the directory every session — never from memory or from prose.

**Enumerate the live inventory (always safe; never hardcode a list):**

```bash
for f in .claude/commands/*.md; do
  [ -e "$f" ] || continue
  name=$(basename "$f" .md)
  desc=$(sed -n 's/^description:[[:space:]]*//p' "$f" | head -1)
  printf '/%s\t%s\n' "$name" "${desc:-(no description)}"
done
```

This answers **"does a command for this already exist / am I aware of it?"** — including project-specific commands the stale prose may omit. It does NOT answer **"is this command the latest canonical version?"** — version reconciliation against central is `/distribute-defaults`'s job, not yours. Do not edit command file contents here. (Output is display-only; descriptions may contain `—`/tabs, so don't re-parse it.)

**Bind yourself to these rules:**

- **Prefer-existing rule.** Before building, scripting, or hand-rolling ANY capability, scan the inventory for a command whose name/description covers the need. If one matches, invoke it instead of doing the work ad-hoc — reinventing an existing command is a defect, not initiative.
- **Open before you reject.** If a command's name plausibly fits but its one-line description is terse, READ that command file before concluding "mine is different." This closes the most common reinvention loophole.
- **Re-derive, don't recall.** Consult the live directory each session; never act on a remembered list or `CLAUDE.md` prose.

**Reconcile `CLAUDE.md` only if it has DRIFTED to a hardcoded list (authorized, scoped, idempotent):**

The correct shape of the `CLAUDE.md` commands section is a **list-free prose pointer** to `.claude/commands/` — NOT an enumerated list (a hand-maintained list is the disease this step cures). Detect the section by a heading matching `^##[[:space:]]+Commands` (tolerant of `## Commands`, `## Commands (N total)`, `## Commands Available (N total)`), spanning to the next `## ` heading or `---`.

- **If that section is already list-free prose → change NOTHING and do NOT commit.** This is the normal case; the step is a no-op.
- **If — and only if — it contains a hardcoded command list** (e.g. a fenced block of `/cmd # …` lines), it has drifted. Self-heal by **replacing the enumerated list with the prose pointer** (no command names — heal toward the directory, never regenerate a list). Touch ONLY that section; touch no other part of `CLAUDE.md` and no other file.
- **Concurrency guard.** Other agents may be editing `CLAUDE.md` concurrently. Only heal when `CLAUDE.md` has no other unstaged changes (`git diff --name-only` does not list it before your edit), and commit by pathspec so you never sweep another agent's pre-staged files:

```bash
git commit CLAUDE.md -m "<task-id>: replace stale hardcoded command list with live-inventory pointer"
```

Never `git add -A` / `git add .` (see Multi-Agent Discipline → "Commit only files related to your task"). If the concurrency guard fails, skip the heal and report the drift in the Session Ready block instead.

**Carry the inventory forward:** include the enumerated list in the Step 9 "Session Ready" report so the prefer-existing reflex stays in working context past session start.

### 2.7. Repo Hygiene Gate (triggered consolidation — /repo-hygiene)

**Why:** one-off documentation audits decay — weeks after a big cleanup, docs drift from the code,
skills reference moved tools, indexes go stale, progress.json balloons. And the rot is not just
index-level: operational claims inside skills/docs (CLI flags, resource names, payload shapes)
decay against the implementation while every index check passes — `/repo-hygiene` grounds a
rotating content slice for exactly this. It is the standing consolidation pass; THIS gate is what
makes it actually run.

Run the quick clock check (read-only, cheap):

```bash
python3 - <<'PY'
import json, time
from pathlib import Path
p = Path(".claude/hygiene-state.json")
if not p.exists():
    print("HYGIENE: never recorded — run /repo-hygiene to establish the baseline")
else:
    st = json.loads(p.read_text())
    age = (time.time() - time.mktime(time.strptime(st.get("last_pass","1970-01-01"), "%Y-%m-%d"))) / 86400
    if age > 60:   print(f"HYGIENE: OVERDUE x2 ({age:.0f}d since {st['last_pass']}) — MUST run /repo-hygiene before new work")
    elif age > 30: print(f"HYGIENE: due ({age:.0f}d since {st['last_pass']}) — schedule /repo-hygiene this session or next")
    elif "grounded" not in st: print("HYGIENE: content baseline missing — run /repo-hygiene once to baseline grounding + terminology (then /update-progress Step 2b rotates per session)")
    else:          print(f"HYGIENE: ok (last pass {st['last_pass']}, {age:.0f}d ago)")
PY
```

- `ok` → proceed; omit from the handoff.
- `due` → surface a "⚠ Repo hygiene due" line in the Session Handoff (informational).
- `content baseline missing` → surface it in the handoff: the clock is fine but the per-session
  content-consolidation rotation (`/update-progress` Step 2b) has no baseline yet — recommend a
  one-time manual `/repo-hygiene` run this session or next.
- `OVERDUE x2` or `never recorded` → surface it PROMINENTLY in the handoff and treat
  `/repo-hygiene` as the recommended first task — the operator can override, but the default
  next action is the hygiene pass, not new work on a drifting tree.
- If the project ships its own richer checker (e.g. a docs-currency tool wired via a local
  overlay), its findings feed the same banner.

### 3. Detect Project State

#### If no `progress.json` exists:
```
## Project Not Initialized

No progress.json found. This project needs setup.

Run `/setup` to:
- Choose a playbook template
- Copy project structure (spec, phases, tasks)
- Configure environment
- Create repositories
```

Direct user to run `/setup`.

#### If no tasks exist in progress.json:
```
## Setup Incomplete

Project has progress.json but no tasks defined.

This can happen if:
- Setup was interrupted
- Commands were injected to existing project without tasks

Would you like me to:
1. **Run /setup** - Complete the setup process
2. **Use /add-work** - Define tasks manually
```

Use AskUserQuestion.

#### If tasks exist:
Proceed to session handoff (Step 4).

### 4. Present Session Handoff

```
## Session Handoff

### Previous Session Summary
[Summarize from session_notes.md last entry:]
- What was accomplished
- Key decisions made
- Any issues encountered

### Upcoming Work
- **Current Task**: X.Y - [Task Name]
- **Phase**: X - [Phase Name]
- **Repo**: [which repository]
- **Description**: [what this task involves]

### Open Items
- [Any pending user decisions from last session]
- [Any blockers noted]

### ⚠ Repo hygiene  (omit if Step 2.7 reported ok)
[due / OVERDUE x2 / never recorded — recommend /repo-hygiene accordingly]

---
**What would you like to do?**
1. **Continue** - proceed with Task X.Y
2. **Redirect** - work on different task
3. **Discuss** - talk about something first (may lead to new tasks)
```

**Use AskUserQuestion tool.**

**If user chooses Discuss:**
- Have the discussion
- If work is identified, ask: "Should I add this as tracked tasks?"
- If yes, follow `/add-work` workflow
- If no, just note in session_notes.md for later

### 5. Verify AWS Account (CRITICAL)

**Only if user chose Continue**

```
{mcp_tool} aws sts get-caller-identity
```

- **STOP if account ID does not match** `context_hints.aws_account`
- Confirm region matches `context_hints.aws_region`

### 6. Pre-Work Verification (MANDATORY)

Before starting NEW work, verify last completed task still works.

Find the last `complete` task in progress.json:
```json
{"id": "X.Y", "name": "...", "status": "complete", "verify": "..."}
```

Run its verification step:
- If `verify` field exists → run that check
- If AWS resources → verify they exist
- If code → verify it builds/runs

**If verification FAILS:**
- Do NOT proceed to new task
- Fix the regression first
- Document in session_notes.md

**If verification PASSES:**
- Proceed to current task

### 7. Check Context Budget

Run `/context` to check usage:
- **<40%**: Start any task
- **40-60%**: Small/medium tasks only
- **60-80%**: Finish current, then wrap up
- **>80%**: Only update progress.json, end session

### 8. Check Git Repo Status

Same sub-repo set as Steps 0/0.5 (long-term source of truth: `progress.json` `git_repos`):

```bash
git status
for dir in infrastructure backend frontend testing; do
  [ -d "$dir/.git" ] && { echo "=== $dir ==="; git -C "$dir" status --short; }
done
```

Update `git_repos` status in progress.json:
- `pushed` - clean and in sync with remote
- `needs_push` - local commits not pushed
- `local_only` - no remote configured

### 9. Report Ready Status

```
## Session Ready

### AWS Account Verified
- Account: {AWS_ACCOUNT_ID} ✓
- Region: {AWS_REGION} ✓
- MCP Tool: {mcp_tool}

### Pre-Work Verification
- Last completed: Task X.Y - [name]
- Verification: [PASSED/FAILED]

### Context Budget
- Current usage: XX%
- Recommended scope: [small/medium/wrap-up]

### Current Task
- Phase: X - [Phase Name]
- Task: X.Y - [Task Name]
- Repo: [repo name]
- Size: [small/medium]

### Repos Status
| Repo | Sync (Step 0) | Status |
|------|---------------|--------|
| orchestration | FF-pulled / up-to-date / DIVERGED / offline / local-only | pushed/needs_push |
| infrastructure | ... | ... |

(If any repo shows DIVERGED, resolve it with /syndicate-refresh-remote before starting the task; if it shows offline, note the stale-checkout risk and re-sync when online.)

### Ready to proceed with Task X.Y
```

---

## Context Management (CRITICAL)

You MUST monitor context:

1. **Check `/context`** to verify current usage
2. **If context is low** (>60%), immediately:
   - Run `/update-progress`
   - Update `session_notes.md` with full context
   - Commit and push all repos
   - Tell user: "Context limit approaching. Progress saved."

---

## CRITICAL: Authorization Boundaries

### What This Session Authorizes
Work on **existing tasks** in progress.json.

### What Requires SEPARATE Approval

| Action | Command | Requires |
|--------|---------|----------|
| Add phases/tasks | `/add-work` | User approval |
| Major scope changes | Discuss first | User approval |
| Modifying IMPLEMENTATION_PLAN.md | Discuss first | User approval |

### Discussion ≠ Authorization

**When user discusses problems or future work:**
- "This needs fixing" → NOT authorization to create tasks
- "We should do X" → NOT authorization to do X

**Only explicit statements authorize:**
- "Add this to the tasks"
- "Yes, do it"

**When uncertain:** ASK: "Should I add this as tracked tasks, or just note it?"

---

## If Claude's Plan Mode Was Used

If you (Claude) used `EnterPlanMode` during a session:

1. That temporary plan lives only in the session
2. Run `/add-work` to transfer to progress.json
3. Don't lose that planning work!

---

## Critical Reminders

- **NEVER** export AWS profiles to environment
- **ALWAYS** use MCP tools for AWS operations
- **ALWAYS** verify account before any AWS operation
- **ALWAYS** verify last task before starting new work
- **NEVER** assume discussion equals authorization
- **BEFORE** writing any script, loop, or multi-step procedure, STOP and check the live `.claude/commands/` inventory for an existing command — prefer it over ad-hoc work
