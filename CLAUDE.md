# HYL Resources Manager

Infrastructure and resource management for AWS accounts and services - managing Amplify apps, domains, DNS, and DynamoDB across multiple AWS accounts.

---

## Quick Reference

| Item | Value |
|------|-------|
| GitHub Repo | `jirihylmar/hyl-resources-manager` |
| Primary Domain | `hub440.cz` |

### AWS Accounts & MCP Tools

| Account | ID | Region | MCP Tool |
|---------|-----|--------|----------|
| HylmarJ | `182059100462` | eu-west-1 | `mcp__aws-hylmar__call_aws` |
| JiHy__vsb__565 | `565393049593` | eu-central-1 | `mcp__aws-vsb-565__call_aws` |
| JiHy__vsb__299 | `299025166536` | eu-central-1 | `mcp__aws-vsb-299__call_aws` |
| JiHy__d4m__975 | `975050190402` | eu-central-1 | `mcp__aws-d4m-975__call_aws` |
| JiHy__vsb__030 | - | - | `mcp__aws-vsb-030__call_aws` |
| JiHy__brm__734 | - | - | none — `aws-brm-734` was retired estate-wide (engine 6.7); use the CLI profile |
| CAG (JiHy__hylmar__126) | `126697143436` | eu-central-1 | `mcp__aws-cag__call_aws` _(active after Claude restart)_ |

> CAG is a member of the Hylmar org (`o-8i3fdvbxq7`, master `287773673380`). The `aws-cag` connector is registered in `~/.claude.json` and authenticates as IAM user `JiHy__hylmar__126` (profile of the same name). It becomes available as `mcp__aws-cag__call_aws` after restarting Claude Code. Fallback: assume `OrganizationAccountAccessRole` from profile `JiHy__hylmar__287`.

## Commands
```
/start-session           # Begin work session with verification
/update-progress         # Save progress at end of session
/generate-phases         # Create progress.json from approved plan
/generate-architecture   # Generate architecture diagram
/add-work                # Add phases or tasks mid-project
/check-aws               # Verify AWS resources
/provision-account       # Provision a new nested AWS member account end-to-end
```

### Project Skills

| Skill | When to Use | Purpose |
|-------|-------------|---------|
| `/provision-account` | Creating a new nested AWS member account in an org | End-to-end: create-account → admin users → budget → SSO assignment → MCP connector → root-email finalization → docs. Generalized from the CAG/Phase 7 run; includes the known gotchas. |

## Key Files
| File | Purpose | Updates |
|------|---------|---------|
| `progress.json` | Task state - **SINGLE SOURCE OF TRUTH** | Every session |
| `session_notes.md` | Session history log | Every session |
| `amplify.md` | Amplify apps inventory | When apps change |
| `dynamodb-optimization.md` | DynamoDB cost notes | As needed |

---

## Session Workflow

### Before Starting
1. Run `/start-session`
2. Verify AWS accounts match
3. Check last completed task still works
4. Review context budget

### During Session
- Complete **AT LEAST ONE** task perfectly
- Leave codebase in **deployable state**
- Don't start tasks you can't finish

### Context Budget
Check with `/context`:
- **<40%**: Start any task
- **40-60%**: Small/medium tasks only
- **60-80%**: Finish current, then wrap up
- **>80%**: Update progress.json and end session

---

## Progress Rules

**progress.json is append-only for tasks.**

### ALLOWED:
- Change task `status`
- Add timestamps, artifacts, notes
- Add NEW tasks with sub-IDs (1.3a, 1.3b)

### NEVER:
- Remove tasks (mark `superseded` instead)
- Reorder or rename tasks
- Change task IDs

---

## Git Discipline

**Commits**: After completing each task.

**Pushes**: At meaningful boundaries, not after every commit.
- After completing a phase
- Before ending a session
- When sharing/debugging

---

## Task Sizing

Before adding task to progress.json:
- [ ] Single deliverable (one sentence)?
- [ ] Verifiable (one command/action)?
- [ ] <=3 files touched?
- [ ] Deployable state after completion?

**If any NO -> break it down further**

---

## Critical Rules

### 1. AWS Account Verification
**ALWAYS verify before any AWS operation.**

Use the correct MCP tool for each account:
```
mcp__aws-hylmar__call_aws     -> HylmarJ (182059100462)
mcp__aws-vsb-565__call_aws    -> JiHy__vsb__565 (565393049593)
mcp__aws-vsb-299__call_aws    -> JiHy__vsb__299 (299025166536)
mcp__aws-d4m-975__call_aws    -> JiHy__d4m__975 (975050190402)
```

### 2. Use MCP Tools
```bash
# BEST - Use MCP for the correct account
mcp__aws-hylmar__call_aws aws amplify list-apps --region eu-west-1

# WRONG - Never do
export AWS_PROFILE=...
```

### 3. Pre-Work Verification
Before starting NEW work:
1. Find last `complete` task in progress.json
2. Run its `verify` step
3. If FAILS -> fix before proceeding

### 4. Context Management
Check `/context` before significant work. If low:
1. Run `/update-progress`
2. Update `session_notes.md`
3. Commit all changes
4. End session

---

## Playbook Workflow

This project uses playbook session discipline for task tracking.

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

---

## Tool Preferences

| Task | Use | Not |
|------|-----|-----|
| Read files | `Read` | `cat` |
| Edit files | `Edit` | `sed` |
| Search files | `Glob`/`Grep` | `find`/`grep` |
| AWS operations | MCP tools | bash aws |
