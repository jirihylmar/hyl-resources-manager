# HYL Resources Manager

Infrastructure and resource management across AWS, GitHub, and Google services.

## Repository Structure

```
aws/                     # AWS account management
  README.md              # Organizations, cross-account roles, MCP tools
  amplify.md             # Amplify apps inventory across accounts
  dynamodb-optimization.md
  copy_workspaces.sh

github/                  # GitHub repository management
  README-git-repos.md    # Scripts and workflow documentation
  generate-clone-list.sh # Auto-generate repo lists from GitHub API
  workspace-repos.json   # Repo-to-URL mapping
  check-workspaces.sh    # Validate workspace integrity
  git-clone-commands*.sh # Clone/update scripts

google/                  # Google services (pending setup)
  README.md              # Known integrations, planned scope

CLAUDE.md                # Project rules and workflow
progress.json            # Task tracking (single source of truth)
session_notes.md         # Session handoff notes
```

## Services Overview

| Service | Accounts | Access Method | Details |
|---------|----------|---------------|---------|
| **AWS** | 6 accounts, 3 orgs | MCP tools (IAM users) | [aws/README.md](aws/README.md) |
| **GitHub** | 5 orgs, 153 repos | PAT via ~/.git-credentials | [github/README-git-repos.md](github/README-git-repos.md) |
| **Google** | TBD | TBD | [google/README.md](google/README.md) |

## AWS Quick Reference

| Account | ID | Org | MCP Tool |
|---------|-----|-----|----------|
| HylmarJ | 182059100462 | VSB (master) | `mcp__aws-hylmar__call_aws` |
| JiHy__vsb__565 | 565393049593 | VSB | `mcp__aws-vsb-565__call_aws` |
| JiHy__vsb__299 | 299025166536 | Hylmar | `mcp__aws-vsb-299__call_aws` |
| JiHy__d4m__975 | 975050190402 | BrainMarket | `mcp__aws-d4m-975__call_aws` |
| JiHy__vsb__030 | 030062527147 | VSB | `mcp__aws-vsb-030__call_aws` |
| JiHy__brm__734 | 734468801561 | BrainMarket | `mcp__aws-brm-734__call_aws` |

See [aws/README.md](aws/README.md) for full organization structure, cross-account roles, and access methods.

## GitHub Organizations

| Organization | Repos |
|-------------|-------|
| Danse4mobility | 87 |
| jirihylmar (personal) | 40 |
| DigitalHorizonCz | 16 |
| BM-Nutritech | 6 |
| MasterIT-technologies-a-s | 4 |

## Workflow

This project uses playbook session discipline. See [CLAUDE.md](CLAUDE.md).

```
/start-session      # Begin work
/update-progress    # Save progress
/add-work           # Add tasks
/check-aws          # Verify AWS resources
```

---

*Last updated: 2026-03-27*
