# AWS

**Source of truth**: [`accounts.json`](accounts.json)

## Skill Outputs

| Skill | Output | Description | Status |
|-------|--------|-------------|--------|
| `aws-check-accounts` | `accounts.json` | 23 accounts, 3 orgs, MCP connectors, cross-account roles, IAM users | done |
| `aws-check-amplify` | `amplify-inventory.md` | Amplify apps across accounts with domains | stale |
| `aws-optimize-dynamodb` | `dynamodb-optimization.md` | DynamoDB cost optimization actions | stale |

## Quick Reference (from accounts.json)

6 MCP-connected accounts (active):

| Account ID | Name | Region | MCP Connector | Org | Master |
|------------|------|--------|---------------|-----|--------|
| 182059100462 | vsb_bh6_dat_dev | eu-west-1 | `aws-hylmar` | VSB/Academic | *(is master)* |
| 565393049593 | dev_zoneiot | eu-central-1 | `aws-vsb-565` | VSB/Academic | vsb_bh6_dat_dev |
| 299025166536 | digital_horizon | eu-central-1 | `aws-vsb-299` | Hylmar | hylmar_OA |
| 975050190402 | brainmarket_preprod | eu-central-1 | `aws-d4m-975` | BrainMarket/D4M | brainmarket_master |
| 030062527147 | projekt1_hub440 | eu-west-1 | `aws-vsb-030` | VSB/Academic | vsb_bh6_dat_dev |
| 734468801561 | nutritech | eu-central-1 | `aws-brm-734` | BrainMarket/D4M | brainmarket_master |

+17 passive/legacy accounts with CLI profiles only. See `accounts.json`.

---

*Last updated: 2026-03-27*
