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
| Root email | `info+cag@hylmar.eu` (temporary) → target `aws-126@hylmar.eu` (owner to switch) |
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
- ACTUAL email alerts at **50% / 80% / 100%** → `info+cag@hylmar.eu`.
- To make it exactly 20 EUR: owner sets billing currency to EUR (root), then recreate with `Unit=EUR`.

## MCP connector (CAG)

- IAM user `mcp-126697143436` + managed policy `MCP-Service-Access` (athena/glue/dynamodb/s3/logs/metrics/lambda-read/sts), access key in Secrets Manager `cag/mcp/mcp-126697143436`.
- **Pending (owner/harness):** register the `aws-cag` connector in Claude config and restart, then verify `sts get-caller-identity` = 126697143436.

## Open owner follow-ups

1. Create Workspace alias `aws-126@hylmar.eu`.
2. Switch CAG root email to `aws-126@hylmar.eu` (root sign-in required).
3. Register `aws-cag` MCP connector + restart.
4. (Optional) EUR billing currency → recreate 20 EUR budget.
