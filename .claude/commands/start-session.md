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

# Start Session

Initialize context and verify previous work before starting new tasks.

---

## Steps

### 1. Read Orchestration Files

- Read `CLAUDE.md` for project context, rules, and conventions
- Read `progress.json` to identify current state and context hints
- Read last entry in `session_notes.md` for recent context

### 2. Detect Project State

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
Proceed to session handoff (Step 3).

### 3. Present Session Handoff

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

### 4. Verify AWS Account (CRITICAL)

**Only if user chose Continue**

```
{mcp_tool} aws sts get-caller-identity
```

- **STOP if account ID does not match** `context_hints.aws_account`
- Confirm region matches `context_hints.aws_region`

### 5. Pre-Work Verification (MANDATORY)

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

### 6. Check Context Budget

Run `/context` to check usage:
- **<40%**: Start any task
- **40-60%**: Small/medium tasks only
- **60-80%**: Finish current, then wrap up
- **>80%**: Only update progress.json, end session

### 7. Check Git Repo Status

```bash
git status
git -C infrastructure status --short 2>/dev/null
git -C backend status --short 2>/dev/null
```

Update `git_repos` status in progress.json:
- `pushed` - clean and in sync with remote
- `needs_push` - local commits not pushed
- `local_only` - no remote configured

### 8. Report Ready Status

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
| Repo | Status |
|------|--------|
| orchestration | pushed/needs_push |
| infrastructure | ... |

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
