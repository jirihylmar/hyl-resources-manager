---
description: Inject playbook workflow into existing project without full setup (project)
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# Setup Workflow Only

Inject the playbook workflow system into an existing project that wasn't created with `/setup`.

Use this when:
- Project already exists with code/structure
- Want to add session discipline and progress tracking
- Don't need full template setup

---

## Step 1: Verify This Is an Existing Project

Check current state:

```bash
ls -la
```

**Expected**: Project has existing code, configs, or structure.

**If empty directory**: Recommend using `/setup` instead for full template setup.

---

## Step 2: Check What Already Exists

```bash
# Check for existing playbook files
ls CLAUDE.md progress.json .claude/commands/ 2>/dev/null || echo "none"
```

If any exist, ask:
```
## Existing Files Detected

Found: [list files]

Options:
1. **Merge** - Keep existing, add missing pieces
2. **Replace** - Overwrite with fresh workflow files
3. **Cancel** - Stop and review manually
```

Use AskUserQuestion.

---

## Step 3: Locate Examples Repository

```bash
# Check common locations
ls -d syndicate-playbooks-examples 2>/dev/null || \
ls -d ../syndicate-playbooks-examples 2>/dev/null || \
echo "NOT_FOUND"
```

**If NOT_FOUND**:
```
## Examples Repository Not Found

The examples repo is needed to copy workflow files.

Options:
1. Clone it: `git clone https://github.com/hub440-syndicate/syndicate-playbooks-examples.git`
2. Specify path if it's elsewhere

Where is the examples repository?
```

Use AskUserQuestion.

Set `$EXAMPLES_PATH` to the found/specified path.

---

## Step 4: Copy Workflow Files

### 4.1 Commands (verify present)

Commands should already be copied (per README instructions). Verify and copy if missing:

```bash
if [ ! -d ".claude/commands" ] || [ -z "$(ls .claude/commands/ 2>/dev/null)" ]; then
  mkdir -p .claude/commands
  cp $EXAMPLES_PATH/_project-template/.claude/commands/*.md .claude/commands/
  echo "Commands copied"
else
  echo "Commands already present"
fi
```

### 4.2 Session Notes (if missing)

```bash
if [ ! -f session_notes.md ]; then
  cp $EXAMPLES_PATH/_project-template/session_notes.md ./
fi
```

### 4.3 CLAUDE.md (merge or create)

**If CLAUDE.md exists:**

Read the existing file and append workflow sections. Do NOT overwrite existing content.

```markdown
# Append to existing CLAUDE.md:

---

## Playbook Workflow

This project uses playbook session discipline for task tracking.

### Commands
- `/start-session` - Begin work session
- `/update-progress` - Save progress, end session
- `/add-work` - Add phases or tasks
- `/generate-phases` - Generate tasks from spec
- `/check-aws` - Verify AWS resources

### Session Discipline
- Start each session with `/start-session`
- End each session with `/update-progress`
- Track tasks in `progress.json`
- Document handoffs in `session_notes.md`

### Working Style
Work autonomously within tasks. Checkpoints only at:
- Session start (after `/start-session`)
- Task completion
- Major decisions requiring user input
```

Use Edit tool to append, preserving all existing content.

**If CLAUDE.md does not exist:**

Copy template and customize:
```bash
cp $EXAMPLES_PATH/_project-template/CLAUDE.md.template ./CLAUDE.md
```

Ask user for:
- Project name
- AWS account/region (if applicable)
- MCP tool name (if applicable)
- Any project-specific rules

---

## Step 5: Create progress.json

This is the key file for workflow tracking.

### 5.1 Gather Project Info

```
## Project Information

1. **Project name**:
2. **Brief description**:
3. **Uses AWS?**: Yes/No
   - If yes: Account ID, Region, MCP tool
4. **Git remotes**: (I'll detect these)
```

Use AskUserQuestion.

### 5.2 Detect Git Repos

```bash
# Main repo
git remote -v 2>/dev/null | head -2

# Check for sub-repos
for dir in */ ; do
  if [ -d "$dir/.git" ]; then
    echo "$dir: $(cd $dir && git remote get-url origin 2>/dev/null || echo 'local only')"
  fi
done
```

### 5.3 Ask About Existing Work

```
## Define Current Work

What phase is this project in?

1. **Planning** - Still defining what to build
2. **Early development** - Initial implementation
3. **Mid-project** - Significant work done
4. **Maintenance** - Core features complete

What are you currently working on? (This becomes your first task)
```

Use AskUserQuestion.

### 5.4 Generate progress.json

Create based on gathered info:

```json
{
  "version": "2.0",
  "project": "{project_name}",
  "description": "{description}",
  "created_at": "{today}",
  "last_updated": "{today}",
  "last_session_summary": "Workflow injected into existing project",

  "context_hints": {
    "aws_account": "{if applicable}",
    "aws_region": "{if applicable}",
    "mcp_tool": "{if applicable}"
  },

  "phases": {
    "phase_1_current": {
      "name": "{phase name based on project state}",
      "status": "in_progress",
      "started_at": "{today}",
      "tasks": [
        {
          "id": "1.1",
          "name": "{current work description}",
          "status": "pending",
          "size": "medium"
        }
      ]
    }
  },

  "current_task": "1.1",
  "current_phase": "phase_1_current",

  "git_repos": {
    "{detected repos}"
  },

  "blockers": [],
  "backlog": []
}
```

Write to `progress.json`.

---

## Step 6: Offer to Define More Tasks

```
## Additional Tasks

Would you like to define more tasks now?

1. **Yes** - Add tasks for current phase
2. **Later** - Use `/add-work` when needed
3. **Generate** - Let me analyze codebase and suggest tasks
```

If "Generate":
- Scan codebase for TODOs, FIXMEs
- Check for incomplete features
- Look at open issues if GitHub repo
- Propose tasks based on findings

---

## Step 7: Update .gitignore (if needed)

Check if workflow files should be tracked:

```bash
# Add examples repo to gitignore if cloned locally
if [ -d "syndicate-playbooks-examples" ]; then
  grep -q "syndicate-playbooks-examples" .gitignore 2>/dev/null || \
    echo "syndicate-playbooks-examples/" >> .gitignore
fi
```

---

## Step 8: Remove Examples Repository

The examples repo is no longer needed — all workflow files have been copied.

```bash
rm -rf syndicate-playbooks-examples/
```

Remove the gitignore entry too (nothing to ignore anymore):

```bash
# Remove the syndicate-playbooks-examples/ line from .gitignore
```

Use Edit tool to remove the `syndicate-playbooks-examples/` line from `.gitignore`.

---

## Step 9: Commit Workflow Files

```bash
git add .claude/ progress.json session_notes.md CLAUDE.md .gitignore
git commit -m "workflow: Add playbook session discipline

Added:
- .claude/commands/ (8 commands)
- progress.json (task tracking)
- session_notes.md (session handoff)

Updated:
- CLAUDE.md (workflow rules merged)

Removed:
- syndicate-playbooks-examples/ (no longer needed)

🤖 Generated with Claude Code"
```

---

## Output

```
## Workflow Injection Complete

### Files Added/Updated
| File | Action | Purpose |
|------|--------|---------|
| `.claude/commands/*.md` | Added | 7 slash commands |
| `progress.json` | Created | Task and phase tracking |
| `session_notes.md` | Created | Session handoff notes |
| `CLAUDE.md` | Merged/Created | Workflow rules appended |

### Commands Available
- `/start-session` - Begin work session
- `/update-progress` - Save progress, end session
- `/add-work` - Add phases or tasks
- `/generate-phases` - Generate tasks from spec
- `/check-aws` - Verify AWS resources
- `/setup` - Full project setup (not needed now)

### Current State
- Phase: {phase_name}
- Task: 1.1 - {task_name}
- Status: Ready

### Cleanup
- Examples repo removed (no longer needed)

### Next Steps
1. Review `CLAUDE.md` and adjust rules if needed
2. Run `/start-session` to begin tracked work
3. Use `/add-work` to define more tasks as needed

---
**Ready to start.** Run `/start-session` to begin.
```

---

## Notes

- This command injects workflow without restructuring the project
- Existing code, configs, and structure are preserved
- Use `/add-work` to expand tasks as project evolves
- Session discipline starts immediately after injection
