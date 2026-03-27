# AWS Account Management

**Source of truth**: [`accounts.json`](accounts.json)

## Summary

- **23 accounts** with CLI profiles in `~/.aws/credentials`
- **3 AWS Organizations** (VSB, Hylmar, BrainMarket)
- **6 MCP connectors** for Claude Code access
- **20 profiles** without MCP (CLI-only via `aws --profile`)

## MCP Connectors (Claude Code)

| Connector | Profile | Account | Region |
|-----------|---------|---------|--------|
| `aws-hylmar` | `HylmarJ` | 182059100462 | eu-west-1 |
| `aws-vsb-565` | `JiHy__vsb__565` | 565393049593 | eu-central-1 |
| `aws-vsb-299` | `JiHy__vsb__299` | 299025166536 | eu-central-1 |
| `aws-d4m-975` | `JiHy__d4m__975` | 975050190402 | eu-central-1 |
| `aws-vsb-030` | `JiHy__vsb__030` | 030062527147 | eu-west-1 |
| `aws-brm-734` | `JiHy__brm__734` | 734468801561 | eu-central-1 |

All use `awslabs.aws-api-mcp-server` with `AWS_PROFILE` env var pointing to `~/.aws/credentials`.

## Cross-Account Access

See `accounts.json` `cross_account_roles` for full structured data.

**Key relationships:**
- `182059100462` (HylmarJ) is Org 1 master, can assume `OrganizationAccountAccessRole` in 565 and 030
- `182059100462` can CDK deploy into `975050190402` (cross-org)
- `565393049593` <-> `975050190402` bidirectional BMPSS pipeline
- `299025166536` and `030062527147` have data access roles into `975050190402`

## Profiles Without MCP

20 CLI profiles have credentials but no MCP connector. See `accounts.json` `profiles_without_mcp` for the full list. Key ones:

| Profile | Account | Note |
|---------|---------|------|
| `JiHy__hylmar__287` | 287773673380 | Org 2 master |
| `JiHy_d4m_nnn_nnn_pri` | 715123384340 | D4M governance, old org master |
| `DigitalHorizon_root_299` | 299025166536 | Root user for Digital Horizon |

## File Index

| File | Contents |
|------|----------|
| `accounts.json` | Structured inventory: accounts, orgs, MCP connectors, cross-account roles, profiles |
| `amplify.md` | Amplify apps inventory across accounts |
| `dynamodb-optimization.md` | DynamoDB cost optimization notes |
| `copy_workspaces.sh` | Workspace copy script |

---

*Last updated: 2026-03-27*
