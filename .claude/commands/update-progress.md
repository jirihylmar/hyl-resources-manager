---
description: Mark tasks complete with ultra-conservative update rules (project)
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash
  - mcp__aws-*__call_aws
---

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

**Append** new session entry:

```markdown
---

## Session X - YYYY-MM-DD

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

### 8. Check All Git Repos
```bash
# Orchestration
git status

# Each code repo
for dir in infrastructure backend frontend testing; do
  if [ -d "$dir/.git" ]; then
    echo "=== $dir ==="
    git -C "$dir" status --short
  fi
done
```

### 9. Commit Orchestration Changes
```bash
git add progress.json session_notes.md
git commit -m "progress: complete task X.Y - [brief description]

Completed:
- Task X.Y: [name]

Next: Task X.Z

🤖 Generated with Claude Code"
git push
```

### 10. Extract Session Knowledge

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

   Create `/home/hylmarj/syndicate-playbook/knowledge_extraction/{project}-{YYYY-MM-DD}-{topic}-recommended.md`:
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

### 11. Report Summary

```
## Progress Summary

### Completed This Session
- Task 2.3: Add API endpoint (backend) ✓
  - Verify: PASSED
  - Artifacts: [list]

### Tasks Added This Session
- Task 2.3a: Handle edge case (pending)

### Knowledge Extracted
- File: knowledge_extraction/2025-12-22-api-error-handling.md
- Items: 2 patterns, 1 anti-pattern
(or "None - no generalizable learnings this session")

### Overall Progress
Phase 2: 3/5 tasks complete
Total: 8/20 tasks complete (40%)

### Repository Status
| Repo | Status | Notes |
|------|--------|-------|
| orchestration | pushed | ✓ |
| backend | needs_push | 2 files changed |

### Next Task
- Task 2.4: [name] (repo: [repo])

### Action Required
- Push backend repo: `cd backend && git push`
```

---

## Notes
- ALWAYS update progress.json BEFORE committing
- ALWAYS verify completed tasks
- NEVER remove or reorder tasks
- Add new tasks with sub-IDs (2.3a, 2.3b)
- Document everything in session_notes.md
- Knowledge extraction is best-effort (skip if no learnings)
