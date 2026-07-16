---
description: Add new work to project - phases or tasks (requires approval) (project)
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
---

<!--
  Centrally distributed by /distribute-defaults from syndicate-playbooks-examples.
  Project-specific additions go in .claude/local-overlays/<this-filename> as
  splice fragments (see /distribute-defaults for the overlay format).
  Direct edits to this file will be flagged on the next distribution.
-->

# Add Work

Add new work to the project - either a new phase or tasks within an existing phase.

**Consolidates:** Adds phases AND tasks in one command based on what's needed.

---

## When to Use

Use this command when:
- Claude used `EnterPlanMode` and created temporary tasks that need tracking
- Discussion revealed work that should become formal tasks
- New feature set needs a new phase
- Mid-implementation discoveries need to be tracked

---

## CRITICAL: Authorization Boundaries

### Discussion ≠ Authorization

**When user discusses problems or future work:**
- Acknowledging issues → NOT authorization
- "We should do X" → NOT authorization
- "That needs fixing" → NOT authorization

**Only explicit statements authorize:**
- "Add this to the tasks"
- "Create a phase for this"
- "Yes, track this"
- "Add it"

**When uncertain:** ASK first.

---

## Procedure

### 1. Determine Work Type

Use AskUserQuestion:

```
## Adding Work

What type of work should I add?

A) **New tasks** - Add to existing Phase X (current phase)
B) **New phase** - Create a new phase for this feature set
C) **Just noting** - Record for later, don't create tasks yet

Which applies?
```

Wait for explicit answer.

### 2. Collect Work Details

**For tasks (A):**
- What needs to be done?
- What's the expected deliverable?
- How to verify it's done?

**For phase (B):**
- What's the objective?
- What are the major task groups?
- Dependencies on other phases?

### 3. Apply Task Sizing Rules

Every task MUST be:
- **Single deliverable** - one file, one endpoint, one component
- **Session-sized** - completable in <30 min
- **Verifiable** - has concrete verification
- **Deployable state** - code works after task

**If too big → break down further**

### 4. Generate Task IDs

**Before choosing any number, apply the goal test: does this work serve the goal of the phase you
would be putting it in?** The first digit carries **one goal** — that is what lets a phase finish.
Work that does not serve it does not belong in it, however it was discovered.

| The work… | ID | Why |
|---|---|---|
| is needed to finish task 3.4 itself | `3.4a`, `3.4b` | It *is* the current work. |
| serves phase 3's goal, own deliverable | `3.5`, `3.6` | Same goal, new task. |
| **does NOT serve phase 3's goal** | **new phase `4.1`, `4.2`** | Different work. Filing it under 3 is what makes phase 3 uncloseable. |

**"I found it while doing 3.4" is not a reason to number it 3.x.** Where work was *discovered* says
nothing about which goal it *serves* — conflating the two is exactly how a phase becomes a drawer
that never closes and never forces a decision on anything in it.

**Symptom you can check for right now:** if the phase you are about to extend has a name like
*"Ongoing Improvements"* or *"Misc"*, or holds tasks that plainly serve different goals, it has
already lost its finish line. Do not deepen it — start the new phase and say why.

**For tasks in current phase (A):**
```
Current task: 3.4
New tasks: 3.4a, 3.4b, 3.4c  (sub-tasks — only if they serve phase 3's goal)
   OR: 3.5, 3.6, 3.7  (after current phase tasks — same test applies)
```

**For new phase (B):**
```
Last phase: 3
New phase: 4
Tasks: 4.1, 4.2, 4.3...
```

**A task in a new phase must be written to stand alone.** The session that found it is gone by the
time anyone reads it. State what is wrong, where, and how you know — never `"the thing we discussed"`.
If you cannot restate it for a cold reader, that is evidence it should not be tracked at all.

### 5. Present Summary

```
## Proposed Work

**Type**: [Tasks in Phase X / New Phase X]
**Count**: N items
**Source**: [EnterPlanMode / Discussion / Discovery]

| ID | Name | Size | Verify |
|----|------|------|--------|
| X.Y | [description] | small | [check] |
| ... | ... | ... | ... |

---

Add these to progress.json?
```

**Wait for explicit approval.**

### 6. Update Files

**Read current progress.json** first.

**For tasks:**
```json
// Add to existing phase's tasks array
{
  "id": "3.4a",
  "name": "Task description",
  "status": "pending",
  "size": "small",
  "verify": "verification step",
  "added_reason": "From [source] - [context]"
}
```

**For new phase:**
```json
// Add new phase to phases object
"phase_4_featurename": {
  "name": "Feature Name",
  "status": "pending",
  "tasks": [
    {"id": "4.1", "name": "...", "status": "pending", ...},
    {"id": "4.2", "name": "...", "status": "pending", ...}
  ]
}
```

**If the project keeps per-phase task files** (a `tasks/` directory exists), create/update the
phase's existing `tasks/phase_X_<name>.md` (the file `/generate-phases` created) — projects that
track work in progress.json only skip this:
```markdown
# Phase X: [Name]

## Tasks

### Task X.Y: [Name]
- **Size**: small
- **Verify**: [command]
- **Deliverable**: [file]

[Implementation notes]
```

### 7. Update session_notes.md

```markdown
### Work Added
- [list of new tasks/phase]
- Source: [EnterPlanMode / Discussion]
- Reason: [why added]
```

### 8. Commit

Scoped to the files this command changed (include `tasks/` only if the project keeps task files
and you updated them):

```bash
git add progress.json session_notes.md   # + tasks/phase_X_<name>.md if updated
git commit -m "work: add [N] tasks to Phase X

Added:
- X.Ya: [name]
- X.Yb: [name]

Source: [source]

🤖 Generated with Claude Code"
```

### 9. Report

```
## Work Added

**Phase**: X - [Name]
**Items**: N tasks added
**IDs**: X.Ya, X.Yb, ...

| ID | Name | Size | Status |
|----|------|------|--------|
| X.Ya | [name] | small | pending |
| ... | ... | ... | ... |

Ready to continue with current task or start new work.
```

---

## Handling EnterPlanMode Output

When Claude used `EnterPlanMode` during coding:

1. The plan is temporary (lives in session only)
2. Run `/add-work` to capture it
3. Select option A (tasks) or B (phase) based on scope
4. Tasks are now tracked in progress.json

**Example conversion:**

EnterPlanMode output:
```
1. Extract validation to middleware
2. Add refresh logic
3. Update routes
4. Add tests
```

After `/add-work`:
```json
{"id": "2.3a", "name": "Extract validation to middleware", ...},
{"id": "2.3b", "name": "Add token refresh logic", ...},
{"id": "2.3c", "name": "Update routes to use middleware", ...},
{"id": "2.3d", "name": "Add middleware tests", ...}
```

---

## Rules

### ALLOWED:
- Add tasks with sub-IDs (X.Ya)
- Add tasks at phase end (X.N+1)
- Create new phases with user approval
- Maximum 7 tasks per invocation

### NEVER:
- Remove existing tasks
- Change existing task IDs
- Reorder existing tasks
- Add work without user approval
- Create "large" tasks (break them down)

---

## Notes

- This command consolidates `/add-phase` and `/add-tasks`
- Always apply task sizing rules
- Always get explicit approval
- Always capture EnterPlanMode output before session ends
