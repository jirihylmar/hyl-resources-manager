# HYL Resources Manager

Resource management across AWS, GitHub, and Google services. Organized by **skills** - each skill produces structured output.

## Skills

| Skill | Service | Output | Status |
|-------|---------|--------|--------|
| `aws-check-accounts` | AWS | [`aws/accounts.json`](aws/accounts.json) | done |
| `aws-check-amplify` | AWS | [`aws/amplify-inventory.md`](aws/amplify-inventory.md) | stale |
| `aws-optimize-dynamodb` | AWS | [`aws/dynamodb-optimization.md`](aws/dynamodb-optimization.md) | stale |
| `github-check-repos` | GitHub | [`github/workspace-repos.json`](github/workspace-repos.json) | done |
| `google-check-services` | Google | [`google/README.md`](google/README.md) | pending |

## Services

| Service | Accounts | Access | Structured Output |
|---------|----------|--------|-------------------|
| **AWS** | 23 accounts (6 active MCP, 3 orgs) | MCP tools, CLI profiles | `aws/accounts.json` |
| **GitHub** | 5 orgs, 153 repos | PAT via `~/.git-credentials` | `github/workspace-repos.json` |
| **Google** | TBD | TBD | - |

## Repository Structure

```
aws/
  accounts.json              # aws-check-accounts output (source of truth)
  amplify-inventory.md       # aws-check-amplify output (stale)
  dynamodb-optimization.md   # aws-optimize-dynamodb output (stale)
  README.md                  # index

github/
  workspace-repos.json       # github-check-repos output
  generate-clone-list.sh     # generates workspace-repos.json
  git-clone-commands*.sh     # clone/update scripts
  check-workspaces.sh        # validate workspace integrity
  copy_workspaces.sh         # workspace copy utility
  README-git-repos.md        # scripts documentation

google/
  README.md                  # known integrations, pending setup

CLAUDE.md                    # project rules and workflow
progress.json                # task tracking (single source of truth)
session_notes.md             # session handoff notes
```

## Workflow

```
/start-session       # begin work
/update-progress     # save progress
/add-work            # add tasks
/check-aws           # verify AWS resources
/provision-account   # provision a new nested AWS member account end-to-end
```

---

*Last updated: 2026-06-22*
