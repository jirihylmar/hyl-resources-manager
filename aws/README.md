# AWS Account Management

## Overview

6 AWS accounts across 3 AWS Organizations, connected via MCP tools for CLI access.

---

## Organizations

### Org 1: o-j8lu4vyjwi (VSB/Academic)

| Account ID | Name | Email | Region | MCP Tool | Role |
|------------|------|-------|--------|----------|------|
| **182059100462** | vsb_bh6_dat_dev | miroslav.voznak@vsb.cz | eu-west-1 | `mcp__aws-hylmar__call_aws` | **MASTER** |
| 565393049593 | dev_zoneiot | dev@zoneiot.cz | eu-central-1 | `mcp__aws-vsb-565__call_aws` | Member |
| 030062527147 | projekt1_hub440 | projekt1@hub440.cz | eu-west-1 | `mcp__aws-vsb-030__call_aws` | Member |
| 313426237404 | open_qkd_dev | open_qkd@d4m.tech | - | *No MCP* | Member |
| 919765081653 | D4M_npl_dat_tes | admin@d4m.tech | - | *No MCP* | Member |
| 235542510807 | voip_dev_001 | voip@d4m.tech | - | *No MCP* | Member |

### Org 2: o-8i3fdvbxq7 (Hylmar)

| Account ID | Name | Email | Region | MCP Tool | Role |
|------------|------|-------|--------|----------|------|
| **287773673380** | *(master)* | info@hylmar.eu | - | *No MCP* | **MASTER** |
| 299025166536 | *(member)* | - | eu-central-1 | `mcp__aws-vsb-299__call_aws` | Member |

### Org 3: o-o4t4kfs7th (BrainMarket/D4M)

| Account ID | Name | Email | Region | MCP Tool | Role |
|------------|------|-------|--------|----------|------|
| **471112898889** | *(master)* | tomicek@brainmarket.cz | - | *No MCP* | **MASTER** |
| 975050190402 | *(member)* | - | eu-central-1 | `mcp__aws-d4m-975__call_aws` | Member |
| 734468801561 | *(member)* | - | eu-central-1 | `mcp__aws-brm-734__call_aws` | Member |

---

## Connected IAM Users

| Account | IAM User | User ARN |
|---------|----------|----------|
| 182059100462 | HylmarJ | `arn:aws:iam::182059100462:user/HylmarJ` |
| 565393049593 | JiHy__vsb__565 | `arn:aws:iam::565393049593:user/JiHy__vsb__565` |
| 299025166536 | JiHy__vsb__299 | `arn:aws:iam::299025166536:user/JiHy__vsb__299` |
| 975050190402 | JiHy__d4m__975 | `arn:aws:iam::975050190402:user/JiHy__d4m__975` |
| 030062527147 | JiHy__vsb__030 | `arn:aws:iam::030062527147:user/JiHy__vsb__030` |
| 734468801561 | JiHy__brm__734 | `arn:aws:iam::734468801561:user/JiHy__brm__734` |

---

## Cross-Account Access Methods

### 1. OrganizationAccountAccessRole

Standard AWS Organizations role created in each member account. Allows the org master to assume full admin access.

| Account | Role | Trusted Principal (Master) |
|---------|------|---------------------------|
| 565393049593 | `OrganizationAccountAccessRole` | `arn:aws:iam::182059100462:root` |
| 030062527147 | `OrganizationAccountAccessRole` | `arn:aws:iam::182059100462:root` |
| 975050190402 | `OrganizationAccountAccessRole` | `arn:aws:iam::715123384340:root` |
| 734468801561 | `OrganizationAccountAccessRole` | `arn:aws:iam::471112898889:root` |

**Usage from master (182059100462):**
```bash
mcp__aws-hylmar__call_aws aws sts assume-role \
  --role-arn arn:aws:iam::565393049593:role/OrganizationAccountAccessRole \
  --role-session-name cross-account-session
```

**Note:** Account 975050190402's OrganizationAccountAccessRole trusts `715123384340` (not the current org master `471112898889`). This may be a legacy configuration from a previous organization membership.

### 2. AWS SSO (IAM Identity Center)

All 6 connected accounts have SSO configured via `AWSReservedSSO_AdministratorAccess_*` roles. SSO is managed from the org master accounts.

| Account | SSO Region | SSO Role |
|---------|-----------|----------|
| 182059100462 | eu-west-1 | `AWSReservedSSO_AdministratorAccess_2581556ffa3260cf` |
| 565393049593 | eu-west-1 | `AWSReservedSSO_AdministratorAccess_f52b855f568c6454` |
| 030062527147 | eu-west-1 | `AWSReservedSSO_AdministratorAccess_7644c13dac5eabc6` |
| 975050190402 | eu-central-1 | `AWSReservedSSO_AdministratorAccess_802d80ec6d0c950d` |
| 734468801561 | eu-central-1 | `AWSReservedSSO_AdministratorAccess_ba35237e4d63c7b7` |

### 3. Cross-Account Service Roles (BMPSS Pipeline)

Active cross-account integration between accounts 975 and 565 for the BMPSS (BrainMarket Product Specification) pipeline:

| Role (in account) | Trusted Principal | Purpose |
|-------------------|-------------------|---------|
| `bmpss-cross-account-pdf-trigger-role` (565) | `975:bmpss-stepfunctions-execution-role`, `975:bmpss-api-proxy-execution-role` | Account 975 triggers PDF generation in 565 |
| `bmpss-cross-account-s3-read-role` (565) | `975:bmpss-lambda-execution-role` | Account 975 reads S3 assistant results from 565 |
| `assistants-cross-account-crawler-role` (975) | `565:assistants-stepfunctions-execution-role` | Account 565 starts Glue crawlers in 975 |

### 4. Cross-Account Data Access Roles

| Role (in account) | Trusted Principal | Purpose |
|-------------------|-------------------|---------|
| `mcp-athena-cross-account-role` (975) | `565:JiHy__vsb__565`, `565:mcp-ec2-role`, `030:mcp-docker-task-role`, `030:JiHy__vsb__030` | MCP/Athena queries from 565 and 030 into 975 |
| `source_299025166536_for_target_97505019040_Role` (975) | `299:root` | Account 299 cross-account access to 975 |
| `AWSGlueServiceRole-AWSGlueServiceRole` (975) | `299:root`, `glue`, `quicksight` | Glue/QuickSight from 299 into 975 |
| `CRM` (182) | `010366900445:root` | External CRM system access |

### 5. Cross-Organization CDK Deploy (182 -> 975)

Account 182059100462 (Org 1 master) can deploy CDK stacks into 975050190402 (Org 3 member) in eu-central-1:

| CDK Role (in 975) | Also Trusts |
|-------------------|-------------|
| `cdk-hnb659fds-deploy-role-975050190402-eu-central-1` | `182059100462:root` |
| `cdk-hnb659fds-file-publishing-role-975050190402-eu-central-1` | `182059100462:root` |
| `cdk-hnb659fds-image-publishing-role-975050190402-eu-central-1` | `182059100462:root` |
| `cdk-hnb659fds-lookup-role-975050190402-eu-central-1` | `182059100462:root` |

### 6. ConsoleAccessServiceRole

Self-assume roles for console access via IAM users:

| Account | Trusted User |
|---------|-------------|
| 182059100462 | `HylmarJ` |
| 975050190402 | `JiHy__d4m__975` |

---

## Cross-Account Relationship Map

```
Org 1 (VSB)                    Org 2 (Hylmar)         Org 3 (BrainMarket)
o-j8lu4vyjwi                   o-8i3fdvbxq7           o-o4t4kfs7th

182059100462 [MASTER]          287773673380 [MASTER]   471112898889 [MASTER]
  |  HylmarJ                    |  (no MCP)             |  (no MCP)
  |                              |                       |
  +-- 565393049593               +-- 299025166536        +-- 975050190402
  |     dev_zoneiot                   JiHy__vsb__299     |     JiHy__d4m__975
  |     <----BMPSS pipeline---->                         |     <----BMPSS pipeline---->
  |                                   |                  |
  +-- 030062527147                    +--Glue/QS-------->+
  |     projekt1_hub440                                  |
  |     -----MCP/Athena------------->                    +-- 734468801561
  |                                                           JiHy__brm__734
  +-- 313426237404 (no MCP)                                   (nutritech)
  +-- 919765081653 (no MCP)
  +-- 235542510807 (no MCP)

Cross-org links:
  182 --CDK deploy--> 975 (eu-central-1)
  565 <--BMPSS------> 975
  030 --Athena------> 975
  299 --Glue/data---> 975
```

---

## Access via MCP Tools

Each MCP connector authenticates as a dedicated IAM user with access keys. These are the primary method for programmatic access from this workstation.

```bash
# Verify identity
mcp__aws-hylmar__call_aws aws sts get-caller-identity

# List org accounts (from master only)
mcp__aws-hylmar__call_aws aws organizations list-accounts

# Cross-account assume role
mcp__aws-hylmar__call_aws aws sts assume-role \
  --role-arn arn:aws:iam::565393049593:role/OrganizationAccountAccessRole \
  --role-session-name admin-session
```

---

## Gaps and Notes

- **No MCP for org masters 287773673380 and 471112898889** - cannot manage these orgs directly
- **No MCP for member accounts 313426237404, 919765081653, 235542510807** - 3 accounts in Org 1 without CLI access
- **Account 975 OrganizationAccountAccessRole** trusts `715123384340` instead of current org master `471112898889` - possible legacy config
- **External trust: CRM role in 182** trusts unknown account `010366900445`

---

*Last updated: 2026-03-27*
