---
description: Initialize project from playbook template or inject commands into existing project (project)
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - AskUserQuestion
  - mcp__aws-*__call_aws
---

# Setup

Initialize a new project from a playbook template, or inject commands into an existing project.

---

## Detect Scenario

### Scenario A: New Project (no IMPLEMENTATION_PLAN.md)

Full setup from playbook template:
1. Choose playbook template
2. Copy template files (spec, phases, tasks, progress)
3. Customize for this project
4. Create sub-repositories

### Scenario B: Existing Project (has IMPLEMENTATION_PLAN.md)

Inject playbook commands into existing project:
1. Copy commands only
2. Create progress.json if missing
3. Verify environment

---

## Scenario A: New Project Setup

### 1. List Available Playbooks

```bash
ls -d syndicate-playbooks-examples/playbook-*/
```

Present options:
```
## Available Playbook Templates

| Template | Description |
|----------|-------------|
| playbook-aws-serverless-multirepo | AWS Lambda + API GW + CDK, multi-repo |
| [others...] | ... |

Which template matches your project?
```

Use AskUserQuestion to select.

### 2. Collect Environment Info

```
## Environment Configuration

1. **AWS Account ID**:
2. **AWS Region**: (e.g., eu-west-1)
3. **MCP Tool**: Which AWS MCP tool? (e.g., mcp__aws-hylmar__call_aws)
4. **Naming Pattern**: Resource prefix? (e.g., myproject-{service}-{env})
5. **GitHub Org**: (optional)
```

Write to `input/environment.md`.

### 3. Copy from Playbook Template

```bash
# Copy all template files
cp syndicate-playbooks-examples/{selected-playbook}/IMPLEMENTATION_PLAN.md ./
cp syndicate-playbooks-examples/{selected-playbook}/progress.json ./
cp syndicate-playbooks-examples/{selected-playbook}/session_notes.md ./
cp -r syndicate-playbooks-examples/{selected-playbook}/tasks/ ./

# Copy commands
mkdir -p .claude/commands
cp syndicate-playbooks-examples/_project-template/.claude/commands/*.md .claude/commands/

# Copy CLAUDE.md template
cp syndicate-playbooks-examples/_project-template/CLAUDE.md.template ./CLAUDE.md
```

### 4. Customize for This Project

**Update IMPLEMENTATION_PLAN.md:**
- Replace template project name with actual project name
- Update AWS resource names with actual naming pattern
- Adjust phases if project scope differs

**Update progress.json:**
- Update `context_hints` with environment values
- Update resource names in verify steps
- Reset task statuses if needed

**Update CLAUDE.md:**
- Fill in all `{{PLACEHOLDER}}` values from environment

### 5. Verify Prerequisites

```bash
node --version    # >= 18
npm --version
aws --version     # >= 2
cdk --version     # >= 2
gh --version
```

### 6. Verify AWS Access

```
{mcp_tool} aws sts get-caller-identity
```

Must match environment config.

### 7. Create Sub-Repositories

For each repo in progress.json `git_repos`:

```bash
mkdir -p {repo_name}
cd {repo_name}
git init
# Create initial files based on type
git add .
git commit -m "Initial commit"
gh repo create {github_org}/{project}-{repo_name} --private --source=. --push
```

### 8. CDK Bootstrap (if using CDK)

```
{mcp_tool} aws cloudformation describe-stacks --stack-name CDKToolkit
```

If not bootstrapped:
```bash
cd infrastructure
cdk bootstrap aws://{account}/{region}
```

### 9. Commit Orchestration Repo

```bash
git add -A
git commit -m "setup: Initialize from {playbook} template

Template: {playbook}
Environment:
- Account: {account}
- Region: {region}
- Naming: {pattern}

🤖 Generated with Claude Code"
```

---

## Scenario B: Inject Commands to Existing Project

### 1. Verify Project State

Check what exists:
- `IMPLEMENTATION_PLAN.md` - should exist
- `progress.json` - may or may not exist
- `.claude/commands/` - probably missing

### 2. Copy Commands

```bash
mkdir -p .claude/commands
cp syndicate-playbooks-examples/_project-template/.claude/commands/*.md .claude/commands/
```

### 3. Create progress.json (if missing)

If no `progress.json`, create from existing spec:

```json
{
  "project": "{project_name}",
  "last_updated": "{now}",
  "current_task": "1.1",
  "context_hints": {
    "aws_account": "{from environment}",
    "aws_region": "{from environment}",
    "mcp_tool": "{mcp tool name}"
  },
  "phases": {
    "phase_1": {
      "name": "{from spec}",
      "status": "in_progress",
      "tasks": []
    }
  }
}
```

Ask user to define tasks or read from existing task documentation.

### 4. Create CLAUDE.md (if missing)

Copy template and fill in values.

### 5. Commit Changes

```bash
git add .claude/ progress.json CLAUDE.md
git commit -m "setup: Add playbook commands to existing project

🤖 Generated with Claude Code"
```

---

## Output

```
## Setup Complete

### Mode
[New project from template / Commands injected to existing project]

### Template
[playbook name if new project]

### Environment
- Account: {account} ✓
- Region: {region} ✓
- MCP Tool: {tool} ✓
- Naming: {pattern}

### Files Created/Updated
- IMPLEMENTATION_PLAN.md [created/existed]
- progress.json [created/existed]
- CLAUDE.md [created/updated]
- .claude/commands/ [created]
- tasks/ [created/existed]

### Repositories
| Repo | Status |
|------|--------|
| orchestration | pushed |
| infrastructure | created |
| ... | ... |

### Ready
Run `/start-session` to begin work.
```

---

## Notes

- Playbook templates contain complete specs, phases, and tasks
- `/setup` copies and customizes - no need to generate phases
- For additions mid-project, use `/add-work`
- Commands in `_project-template/.claude/commands/` are the source of truth
