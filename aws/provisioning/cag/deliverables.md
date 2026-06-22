# CAG Account Provisioning — Deliverables

**Date:** 2026-06-22 · **Phase 7** · executed via profile `JiHy__hylmar__287`

## Account

| Field | Value |
|-------|-------|
| Account name | CAG |
| Account ID | **126697143436** |
| Organization | `o-8i3fdvbxq7` (Hylmar), master `287773673380`, root `r-om7t`, OU = root |
| Default region (convention) | eu-central-1 |
| Cost center | hylmar |
| Console | https://126697143436.signin.aws.amazon.com/console |
| Root email | **`aws-126@hylmar.eu`** (set 2026-06-22 via Account Mgmt API; temp `info+cag@` removed) |
| Create request | `car-83dc05078abc493f95a34955afb3b988` → SUCCEEDED |
| Cross-account role | `OrganizationAccountAccessRole` (trusts 287773673380) |

## Admin users

| User | Access | Credentials |
|------|--------|-------------|
| `JiHy__hylmar__126` | AdministratorAccess, console (reset required), access key, no MFA | Secrets Manager `cag/admin/JiHy__hylmar__126` (eu-central-1) |
| `MiHy__hylmar__126` | AdministratorAccess, console (reset required), access key, no MFA | Secrets Manager `cag/admin/MiHy__hylmar__126` (eu-central-1) |

> Passwords + access keys are stored only in Secrets Manager — never in git or the transcript.

## Spend control

- AWS Budget **`monthly-cost-alerts`**, COST, MONTHLY, **20 USD** (EUR unit unsupported — account bills USD; 20 USD ≈ 18.4 EUR, a slightly tighter cap).
- ACTUAL email alerts at **50% / 80% / 100%** → **`aws-126@hylmar.eu`** (repointed 2026-06-22 once the alias was established).
- To make it exactly 20 EUR: owner sets billing currency to EUR (root), then recreate with `Unit=EUR`.

## MCP connector (CAG)

- Connector **`aws-cag`** registered in `~/.claude.json` (`type stdio`, `awslabs.aws-api-mcp-server`, env `AWS_PROFILE=JiHy__hylmar__126`, `AWS_REGION=eu-central-1`).
- **Authorized with the created admin user** `JiHy__hylmar__126` (AdministratorAccess) per owner instruction — profile written to `~/.aws/credentials` from Secrets Manager `cag/admin/JiHy__hylmar__126`. Verified: profile authenticates as `user/JiHy__hylmar__126`.
- Least-priv `mcp-126697143436` + `MCP-Service-Access` (key in `cag/mcp/...`) still exist but are **not** used by the connector.
- **Activates as `mcp__aws-cag__call_aws` after a Claude Code restart.** Config backups: `~/.claude.json.bak-cag`, `~/.aws/credentials.bak-cag`.

## Open owner follow-ups

1. ~~Create Workspace alias `aws-126@hylmar.eu`~~ ✅ done 2026-06-22; budget alerts repointed to it.
2. ~~Switch CAG **root sign-in email** to `aws-126@hylmar.eu`~~ ✅ done 2026-06-22 via Account Mgmt API (`start`/`accept-primary-email-update`); verified; `info+cag@hylmar.eu` removed.
3. ~~Register `aws-cag` MCP connector~~ ✅ done — registered in `~/.claude.json` (profile `JiHy__hylmar__126`). **Restart Claude Code** to load `mcp__aws-cag__call_aws`.
4. (Optional) EUR billing currency → recreate 20 EUR budget.

## SSO access (added)

IAM Identity Center `d-9367ab04ac` (instance `ssoins-68043e6b5b6e0104`, eu-west-1, owned by mgmt 287) — **`AdministratorAccess` assigned to `jiri-hylmar`** on CAG. Appears at https://d-9367ab04ac.awsapps.com/start/ (new accounts need this assignment; it is not automatic).
