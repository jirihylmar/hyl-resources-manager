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

<!--
  Centrally distributed by /distribute-defaults from syndicate-playbooks-examples.
  Project-specific additions go in .claude/local-overlays/<this-filename> as
  splice fragments (see /distribute-defaults for the overlay format).
  Direct edits to this file will be flagged on the next distribution.
-->

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
ls CLAUDE.md AGENTS.md progress.json .claude/commands/ .agents/skills/ 2>/dev/null || echo "none"
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

> **This copies commands only when they are ABSENT — it is not a refresh.** Re-running
> `/setup-workflow-only` on a project that already has commands leaves them as they are. To *update*
> an existing project's defaults on a host that distribution does not reach (an independent remote),
> run the engine locally: `bash ~/syndicate-playbooks-examples/scripts/distribute-defaults.sh --apply
> --commit` (README § *Running on an independent / third-party remote*). The skills copy below is
> unconditional precisely because a missing skill silently breaks § 4.4 and the open-work render.

```bash
if [ ! -d ".claude/commands" ] || [ -z "$(ls .claude/commands/ 2>/dev/null)" ]; then
  mkdir -p .claude/commands
  cp $EXAMPLES_PATH/_project-template/.claude/commands/*.md .claude/commands/
  echo "Commands copied"
else
  echo "Commands already present (to UPDATE, run the distribute engine locally — see note above)"
fi

# Skills (each a directory: SKILL.md + its files). Without these, § 4.4's
# syndicate-connect, /start-session § 4.0 and /update-progress § 12 (open_work.py) reference
# files that do not exist until the next /distribute-defaults.
mkdir -p .claude/skills
cp -r $EXAMPLES_PATH/_project-template/.claude/skills/* .claude/skills/
echo "Skills copied ($(ls -1d .claude/skills/*/ | wc -l) present)"

# Codex adapters are additive and inert for Claude-only projects.
mkdir -p .agents/skills
cp -r $EXAMPLES_PATH/_project-template/.agents/skills/* .agents/skills/
echo "Codex skills copied ($(ls -1d .agents/skills/*/ | wc -l) present)"
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
The live inventory is `.claude/commands/` — one file per command; `/start-session` enumerates
it every session (do not maintain a hardcoded list here). Core workflow: `/start-session` →
work → `/update-progress`.

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

### 4.3b AGENTS.md (merge or create)

Do not duplicate the project-owned prose from `CLAUDE.md`. If `AGENTS.md` is absent, copy the thin
Codex entry and fill its project placeholders:

```bash
cp $EXAMPLES_PATH/_project-template/AGENTS.md.template ./AGENTS.md
```

If `AGENTS.md` already exists, it is project-owned: preserve it and add only a short pointer to
`CLAUDE.md` plus the `.agents/skills/` entry convention when those facts are not already present.

### 4.4 Verify This Host Can Report Knowledge (the syndicate inbox)

An existing project being put on the workflow is usually on a host that has never run one — so
check the knowledge path here, at injection, not months later. `/update-progress` § 11 delivers every
extraction to the **one** inbox by HTTPS POST to the ingest endpoint, resolving the route by
**presence**:

```bash
if   [ -d "$HOME/syndicate-playbook/knowledge_extraction" ]; then echo "direct — this host holds the inbox (the box)"
elif [ -f "$HOME/.syndicate-remote-secrets/ingest.json" ];   then echo "ingest — POSTs to the endpoint over HTTPS"
else echo "NO ROUTE — this host cannot deliver; extractions would spool forever"; fi
```

**`NO ROUTE` is a setup gap, not a runtime condition.** Neither becomes true on its own: extractions
land in `~/.syndicate-knowledge-spool/` and stay there, because the spool is drained only by a run
that *does* resolve a route.

**The fix is one command with two inputs — the ingest URL and a per-host token.** Ask the operator
for both, then:

```bash
bash .claude/skills/syndicate-connect/connect.sh --url <ingest url> --token <host token>
```

It proves the token against the endpoint (empty-body probe: `400` = good, `401` = bad; no file
delivered) and writes `ingest.json` only after the proof. Re-run the resolver; it must print
`ingest`. (No skill? `mkdir -p ~/.syndicate-remote-secrets && chmod 700` it, write
`{"url":"...","token":"..."}` to `~/.syndicate-remote-secrets/ingest.json`, `chmod 600`.)

**Where the project lives is irrelevant** — the resolver reads `$HOME` only, so this is machine-level
setup done once, and a project under `/mnt/c/Users/...` reports exactly like one under `~`. Delivery
is outbound HTTPS — no ssh key, no `box.json`, no firewall entry. `ingest.json` is per-machine, mode
600, outside every git repo — never commit it. Keep `$HOME` off `/mnt/c` (a Windows mount can't hold
0600, so the token would be world-readable). Do **not** clone the inbox to make `direct` true — it
lives in exactly ONE place.

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
    "{repo name}": {"local": "{path}", "remote": "{origin url}", "status": "clean"}
  },

  "blockers": []
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
git add .claude/ .agents/ progress.json session_notes.md CLAUDE.md AGENTS.md
[ -f .gitignore ] && git add .gitignore   # only if present — new projects may not have one yet
git commit -m "workflow: Add playbook session discipline

Added:
- .claude/commands/ (distributed default commands)
- .agents/skills/ (Codex workflow adapters)
- progress.json (task tracking)
- session_notes.md (session handoff)

Updated:
- CLAUDE.md (workflow rules merged)
- AGENTS.md (Codex entry merged/created)

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
| `.claude/commands/*.md` | Added | Distributed default commands (count = files in the directory) |
| `progress.json` | Created | Task and phase tracking |
| `session_notes.md` | Created | Session handoff notes |
| `CLAUDE.md` | Merged/Created | Workflow rules appended |
| `AGENTS.md` | Merged/Created | Thin Codex entry; detailed rules remain in CLAUDE.md |

### Commands Available
Enumerate the live directory rather than trusting a list (counts drift; the directory is truth):
```bash
for f in .claude/commands/*.md; do basename "$f" .md; done
```
Core workflow: `/start-session` → work → `/update-progress`; `/add-work` to add tracked tasks.

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
