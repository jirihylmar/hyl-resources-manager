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

<!--
  Centrally distributed by /distribute-defaults from syndicate-playbooks-examples.
  Project-specific additions go in .claude/local-overlays/<this-filename> as
  splice fragments (see /distribute-defaults for the overlay format).
  Direct edits to this file will be flagged on the next distribution.
-->

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
3. **MCP Tool**: Which AWS MCP tool? Read it from the LIVE tool inventory — the handle is
   mcp__aws-<server>__call_aws, and which <server> names exist depends on this host's AWS
   service model (per-account servers, or one central server that needs --profile on every
   call). Detect, never assume — see /check-aws.
4. **Project Prefix**: the ONE name every part of this project shares (e.g. myproject).
   Repos, local folders, and AWS resources all derive from it — see Naming Convention below.
5. **GitHub Org**: (optional)
```

Write to `input/environment.md`.

### 2b. Naming Convention (binding from birth — collect the prefix once, derive everything)

**One prefix drives every name. A name is never invented per-part, and a folder is never named
differently from its repo.**

| Thing | Name | Rule |
|---|---|---|
| Orchestration repo | `<prefix>-orchestration` | **The principal manager.** It governs every other part of this project — sub-repos, resources, workflows all answer to it, and its name must say so unmistakably. |
| Each sub-repo | `<prefix>-<part>` (e.g. `<prefix>-infrastructure`, `<prefix>-backend`) | The part name says what it is; the prefix says what it belongs to. Never a bare `backend`/`infrastructure` — a generic name carries no ownership. |
| Local folder of ANY repo | **identical to the repo name** | Folder = repo = origin name, always. A folder named differently from its origin is drift you cannot grep for. |
| AWS resources | `<prefix>-{service}-{env}` (projects may extend, e.g. with component/account segments) | Holds **whether the resource is provisioned via CDK or created individually** — the convention is about the name, not the tool that made it. |
| `input/`, `docs/`, `exports/`, `imports/`, … | plain directories **inside the orchestration repo** | Orchestration-repo CONTENT, never repos of their own. The orchestration repo both manages the parts and carries the project's working material. |

**Why folder = repo = origin is a rule and not taste:** this framework's own bootstrap used to run
`mkdir {repo_name}` but `gh repo create {org}/{project}-{repo_name}` — quietly creating a folder
named `infrastructure` whose origin was `myproject-infrastructure`. Measured on the estate this
convention was written against: two projects whose orchestration folder and origin name disagree
outright, two projects with prefix-less `backend`/`infrastructure` subs, one project mixing three
naming styles, and a `hub400`/`hub440` typo frozen into two repo names. Names that disagree at
birth never converge later.

### 3. Copy from Playbook Template

```bash
# Copy the playbook's reference files — playbooks vary in what they ship
# (e.g. playbook-mcp-mono-repo has only CLAUDE.md/README.md/progress.json),
# so copy each file only if the selected playbook actually provides it.
for f in IMPLEMENTATION_PLAN.md progress.json session_notes.md; do
  [ -f "syndicate-playbooks-examples/{selected-playbook}/$f" ] \
    && cp "syndicate-playbooks-examples/{selected-playbook}/$f" ./
done
[ -d "syndicate-playbooks-examples/{selected-playbook}/tasks" ] \
  && cp -r "syndicate-playbooks-examples/{selected-playbook}/tasks/" ./

# Copy commands
mkdir -p .claude/commands
cp syndicate-playbooks-examples/_project-template/.claude/commands/*.md .claude/commands/

# Copy CLAUDE.md template
cp syndicate-playbooks-examples/_project-template/CLAUDE.md.template ./CLAUDE.md

# Install the commit guard (mechanical protection against `git add -A` sweeping
# build artifacts) + the baseline .gitignore, and arm it for this clone.
mkdir -p .claude/hooks
cp syndicate-playbooks-examples/_project-template/.claude/hooks/pre-commit .claude/hooks/
cp -n syndicate-playbooks-examples/_project-template/.claude/hooks/artifact-guard.allow .claude/hooks/ 2>/dev/null || true
chmod +x .claude/hooks/pre-commit          # BEFORE git add → the index records mode 100755
cp syndicate-playbooks-examples/_project-template/.gitignore ./.gitignore
git config core.hooksPath .claude/hooks    # repo-local config — arms the guard for this clone
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

### 5b. Verify This Host Can Report Knowledge (the syndicate inbox)

`/update-progress` § 11 writes every session's knowledge extraction to the **one** inbox,
`<workspace>/syndicate-playbook/knowledge_extraction/`, resolving the route by **presence**:

```bash
if   [ -d "$HOME/syndicate-playbook/knowledge_extraction" ]; then echo "direct — this host holds the inbox"
elif [ -f "$HOME/.syndicate-remote-secrets/box.json" ];      then echo "remote — reaches the inbox over ssh"
else echo "NO ROUTE — this host cannot deliver; extractions would spool forever"; fi
```

**`NO ROUTE` is a setup gap, not a runtime condition — resolve it here, before any work starts.**
A host that resolves neither has no way to reach the inbox and will never gain one on its own:
each extraction it writes lands in `~/.syndicate-knowledge-spool/` and stays there, because the
spool is drained only by a run that *does* resolve an inbox. That failure is invisible until the
knowledge already exists — which is exactly too late.

**The fix is one ssh key.** Ask the operator for a key with access to the box, then make `remote`
resolvable:

```bash
mkdir -p ~/.syndicate-remote-secrets && chmod 700 ~/.syndicate-remote-secrets
cat > ~/.syndicate-remote-secrets/box.json <<'JSON'
{"host":"<box host or ip>","user":"<box user>","workspace":"/home/<box user>","ssh_key":"<absolute path to the key>"}
JSON
chmod 600 ~/.syndicate-remote-secrets/box.json
ssh -i <absolute path to the key> -o ConnectTimeout=15 <box user>@<box host> true && echo reachable
```

Re-run the resolver above; it must now print `remote`. `box.json` is per-machine, mode 600, and
lives **outside every git repo** — never commit it, and never put the key inside a repo either.

> **Do not clone the inbox to make `direct` true instead.** `syndicate-playbook` lives in exactly
> ONE place; a second live copy accumulates untracked extraction files that git never reconciles
> (`docs/syndicate-playbook-remote-only-instruction.md`). The key is the whole answer.

### 6. Verify AWS Access

```
{mcp_tool} aws sts get-caller-identity
```

Must match environment config.

### 7. Create Sub-Repositories

For each repo in progress.json `git_repos`, the folder, the repo, and the origin all carry the
SAME name: `<prefix>-<part>` (Naming Convention, Step 2b — the old `mkdir {repo_name}` +
`gh repo create {project}-{repo_name}` pair created a folder whose origin had a different name,
manufacturing drift at birth):

```bash
mkdir -p {prefix}-{part}
cd {prefix}-{part}
git init
# Create initial files based on type
git add .
git commit -m "Initial commit"
gh repo create {github_org}/{prefix}-{part} --private --source=. --push
```

**Then verify the invariant mechanically — folder name = origin repo name, every repo, including
the orchestration repo itself** (same check `/start-session` Step 8 runs every session):

```bash
check_name() {  # $1=dir ('.' for orchestration)
  local o n
  o=$(git -C "$1" remote get-url origin 2>/dev/null | sed 's#.*/##; s/\.git$//')
  n=$(basename "$(cd "$1" && pwd)")
  [ -z "$o" ] && { echo "NOTE $n: no origin yet — name check deferred until origin exists"; return; }
  [ "$o" = "$n" ] && echo "OK   $n: folder = origin name" \
                  || echo "NAMING MISMATCH: folder '$n' vs origin '$o' — fix BEFORE first push"
}
check_name "."
for dir in */; do
  dir="${dir%/}"
  [ -d "$dir/.git" ] && check_name "$dir"
done
```

A mismatch at this point costs a `git remote set-url` or a folder rename; a mismatch discovered a
year in costs a coordinated rename across every checkout and host.

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
# Scoped add by named paths — NEVER `git add -A` (that is the exact pattern that
# once swept a 36MB build zip into history). List only the framework paths that
# exist; drop any that don't.
git add -- CLAUDE.md progress.json IMPLEMENTATION_PLAN.md session_notes.md .gitignore .claude/ tasks/ input/
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
mkdir -p .claude/commands .claude/hooks
cp syndicate-playbooks-examples/_project-template/.claude/commands/*.md .claude/commands/

# Commit guard (mechanical protection against `git add -A` sweeping build artifacts)
cp syndicate-playbooks-examples/_project-template/.claude/hooks/pre-commit .claude/hooks/
cp -n syndicate-playbooks-examples/_project-template/.claude/hooks/artifact-guard.allow .claude/hooks/ 2>/dev/null || true
chmod +x .claude/hooks/pre-commit          # BEFORE git add → the index records mode 100755
cp -n syndicate-playbooks-examples/_project-template/.gitignore ./.gitignore 2>/dev/null || true   # seed only if absent (don't clobber an existing one)
git config core.hooksPath .claude/hooks
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
git add -- .claude/ progress.json CLAUDE.md .gitignore
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

- Playbooks vary in what they ship (see Scenario A step 3) — copy what exists. Some carry a spec/phases/tasks; some carry only CLAUDE.md/README.md/progress.json.
- If the selected playbook ships a complete spec + tasks, `/setup` copies and customizes them — no need to generate phases. If it does not, follow the Phase 0 flow (draft the spec, then `/generate-phases`).
- For additions mid-project, use `/add-work`
- Commands in `_project-template/.claude/commands/` are the source of truth
