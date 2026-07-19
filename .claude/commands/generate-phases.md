---
description: Break down specification into phases with atomic tasks (project)
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

<!--
  Centrally distributed by /distribute-defaults from syndicate-playbooks-examples.
  Project-specific additions go in .claude/local-overlays/<this-filename> as
  splice fragments (see /distribute-defaults for the overlay format).
  Direct edits to this file will be flagged on the next distribution.
-->

# Generate Phases

Break down the approved specification into phases, each containing atomic tasks.

**Run this AFTER specification approval, BEFORE any coding work begins.**

---

## Prerequisites (CRITICAL)

Before generating tasks, verify these conditions are met:

### 1. Environment Configuration Must Exist

Check for environment info in:
- `input/environment.md` or `input/env.md`
- `CLAUDE.md` Quick Reference section
- `progress.json` context_hints

**Minimum required:**
- At least one AWS account/region/MCP tool combination
- Project naming prefix

**Structure is flexible** - may include:
- Multiple accounts (cross-account scenarios)
- Multiple regions
- Multiple MCP tools
- Integration notes

**If missing:** STOP and direct user to run `/setup` (its environment-collection step gathers
account/region/MCP/naming), or to add the values to `CLAUDE.md` / `input/environment.md` directly —
then re-run this command.

### 2. Specification Must Be Approved

Check for approval indicator (the Phase 0 spec-approval task records the approval — it does not
appear on its own):
- `session_notes.md` contains an explicit approval record from the spec-approval task, OR
- `IMPLEMENTATION_PLAN.md` carries a `## Status: Approved` line the approver added

**If not approved:** STOP and inform user:
```
## Cannot Generate Phases

The specification must be reviewed and approved first.

### Next Steps
1. Review IMPLEMENTATION_PLAN.md
2. Provide explicit approval ("approved", "looks good", etc.)
3. Then run `/generate-phases`

Approval is given directly in the conversation — the spec-approval task in Phase 0 presents
IMPLEMENTATION_PLAN.md and blocks until you approve it.
```

### 3. Phases Must Not Already Exist

Check if phases have already been generated:
- Look for `tasks/phase_*.md` files
- Check if `progress.json` has phases with populated task arrays

**If phases already exist:** WARN user:
```
## Phases Already Generated

Phase files already exist. Running /generate-phases again will:
- NOT modify existing phases/tasks
- Only add new phases if specification has changed

To regenerate all phases, manually delete tasks/ folder and phase entries in progress.json first.

To add work to existing phases, use `/add-work` instead.
```

---

## Task Sizing Rules

### Each Task MUST:
1. **Single deliverable** - one file, one endpoint, one component
2. **Verifiable** - has a concrete verification step
3. **Session-sized** - completable in <30 min of Claude time
4. **Deployable state** - code works after task completes
5. **No implicit continuation** - doesn't require "then do X"

### Sizing Checklist (for each task):
- [ ] Can I describe the deliverable in one sentence?
- [ ] Can I verify it with one command/action?
- [ ] Does it touch ≤3 files?
- [ ] If I stop after this task, is code deployable?

**If any answer is NO → break it down further**

---

## Steps

### 1. Verify Prerequisites
Run the checks from the Prerequisites section above:
```
Checking prerequisites...
✓ Environment: Found in CLAUDE.md (AWS: {account}, Region: {region})
✓ Plan: IMPLEMENTATION_PLAN.md approved
✓ Tasks: Not yet generated

Ready to generate tasks.
```

If any check fails, stop and report what's needed.

### 2. Read Specification
Read `IMPLEMENTATION_PLAN.md` thoroughly.

Identify:
- Major phases/milestones
- Features to implement
- AWS resources needed
- Backend/frontend components
- Dependencies between features

**Also read environment config** to use correct:
- Naming conventions in verify steps
- AWS region in resource ARNs
- MCP tool references

### 3. Create Phase Structure
For each major phase, create a task file:

```bash
tasks/
├── phase_1_foundation.md
├── phase_2_backend.md
├── phase_3_seeding.md
└── ...
```

### 4. Decompose Each Feature into Atomic Tasks

**BAD (too big):**
```json
{"id": "2.1", "name": "Implement user authentication"}
```

**GOOD (atomic):**
```json
{"id": "2.1", "name": "Create Cognito User Pool via CDK", "verify": "aws cognito-idp list-user-pools --max-results 10 shows pool", "size": "small"},
{"id": "2.2", "name": "Add signup Lambda function", "verify": "Lambda exists in console", "size": "small"},
{"id": "2.3", "name": "Add login Lambda function", "verify": "Lambda exists", "size": "small"},
{"id": "2.4", "name": "Create API Gateway auth endpoints", "verify": "POST /auth/signup returns 200", "size": "medium"},
{"id": "2.5", "name": "Add JWT validation middleware", "verify": "Protected endpoint returns 401 without token", "size": "small"}
```

### 5. Add Required Fields to Each Task

```json
{
  "id": "2.3",
  "name": "Add login Lambda function",
  "status": "pending",
  "repo": "infrastructure",
  "size": "small",
  "verify": "aws lambda get-function --function-name X returns config",
  "deliverable": "infrastructure/lambda/auth/login.py",
  "depends_on": ["2.1"]
}
```

**Required fields:**
- `id` - Unique identifier (phase.task format)
- `name` - One sentence description
- `status` - Always starts as "pending"
- `repo` - Which repo this task works in

**Recommended fields:**
- `size` - small/medium (no large tasks!)
- `verify` - How to confirm it works (use correct naming convention!)
- `deliverable` - Primary file(s) created/modified
- `depends_on` - Task IDs that must complete first

### 6. Use Environment Values in Verify Steps

**IMPORTANT:** Use actual environment values from config:

```json
// BAD - the generated task still carries an unresolved placeholder
{"verify": "aws dynamodb describe-table --table-name {TABLE_NAME}"}

// GOOD - the generated task carries values RESOLVED from THIS project's environment.
// Illustration for a project whose naming pattern is myproject-{service}-{env}:
{"verify": "mcp__aws-<server>__call_aws aws dynamodb describe-table --table-name myproject-experts-dev"}
```

Resolve both halves at generation time, from the project you are generating for:
- **The MCP handle**: read it from the LIVE tool inventory — never copy a server name from this
  file or from another project. Which `<server>` names exist depends on the host's AWS service
  model (per-account servers, or one central server); on a central-server host the command must
  also carry `--profile <account>`. Detect, never assume — see /check-aws.
- **The resource name**: construct it from the project's own naming convention in
  `input/environment.md`. A real resource name belonging to some other project is wrong even if
  the command would run.

### 7. Write Phase Task Files

For each phase, write `tasks/phase_X_name.md`:

```markdown
# Phase X: [Name]

## Overview
[Brief description of what this phase accomplishes]

## Prerequisites
- Phase X-1 complete
- [Other requirements]

## Environment
- AWS Account: [from env]
- Region: [from env]
- Naming: [from env]

## Tasks

### Task X.1: [Name]
- **Repo**: infrastructure
- **Size**: small
- **Deliverable**: infrastructure/lib/stacks/auth-stack.ts
- **Verify**: `cdk synth` succeeds

**Details:**
[Implementation notes, code patterns to follow, etc.]

### Task X.2: [Name]
...
```

### 8. Update progress.json

Add all generated tasks to progress.json:

```json
{
  "phases": {
    "phase_0_planning": {
      "name": "Planning & Setup",
      "status": "complete",
      "tasks": [...]
    },
    "phase_1_foundation": {
      "name": "Foundation",
      "status": "pending",
      "tasks": [
        {"id": "1.1", "name": "...", "status": "pending", "repo": "...", "size": "small", "verify": "..."},
        {"id": "1.2", "name": "...", "status": "pending", "repo": "...", "size": "small", "verify": "..."}
      ]
    },
    "phase_2_backend": {
      "name": "Backend",
      "status": "pending",
      "tasks": [...]
    }
  },
  "current_task": "1.1"
}
```

### 9. Verify Task Count and Coverage

Check:
- [ ] Every feature from IMPLEMENTATION_PLAN.md has tasks
- [ ] No task is larger than "medium"
- [ ] Every task has a verify step with actual resource names
- [ ] Dependencies are correctly specified
- [ ] Task order is logical
- [ ] Naming conventions match environment config

### 10. Commit Phase Definitions

```bash
git add tasks/ progress.json
git commit -m "phases: generate from specification

Phases: X
Total tasks: Y
Average per phase: Z

Environment:
- Account: {account}
- Region: {region}
- Naming: {pattern}

🤖 Generated with Claude Code"
```

---

## Output

After running this command:

```
## Phase Generation Complete

### Prerequisites Verified
- Environment: ✓ (Account: 123456789012, Region: eu-west-1)
- Specification: ✓ (IMPLEMENTATION_PLAN.md approved)
- Existing phases: ✓ (None found, generating fresh)

### Phases Created
| Phase | Name | Tasks |
|-------|------|-------|
| 1 | Foundation | 5 |
| 2 | Backend | 8 |
| 3 | Seeding | 12 |

### Task Summary
- Total tasks: 25
- Small tasks: 20 (80%)
- Medium tasks: 5 (20%)
- Large tasks: 0 (0%) ✓

### Files Created
- tasks/phase_1_foundation.md
- tasks/phase_2_backend.md
- tasks/phase_3_seeding.md
- progress.json (created)

### Ready to Start
- Run `/start-session` to begin Phase 1
- First task: 1.1 - [name]
```

---

## Notes

- Run this ONCE after specification approval, before starting implementation
- DO NOT code during this session - only generate phases
- Commit phase files and end session
- Coding starts in next session with `/start-session`
- If tasks need adjustment later, use `/add-work` to add tasks with sub-IDs
- Always use actual environment values, not placeholders
