# Phase 7: CAG Account Provisioning (Hylmar org `o-8i3fdvbxq7`)

Establish a new nested member account **CAG** under the Hylmar management account
**287773673380** (`hylmar_OA`), default region **eu-central-1**, with two admin users,
a Google Workspace contact-alias root email, and a 20 EUR/month spend control.

## Context & Access

- **Management account:** `287773673380` (`hylmar_OA`), org `o-8i3fdvbxq7` (FeatureSet ALL, SCP enabled).
- **Executor:** direct AWS CLI via local profile **`JiHy__hylmar__287`**
  (verified `arn:aws:iam::287773673380:user/JiHy__hylmar__287`, org admin). No MCP bootstrap needed.
- **Cross-account:** assume `OrganizationAccountAccessRole` into the new CAG account for IAM/budget work.
- **Secrets rule:** passwords / access keys staged in Secrets Manager or handed off out-of-band — **never** committed to git.

## Decisions (captured at /add-work)

| Key | Decision |
|-----|----------|
| Mgmt access | Direct CLI with `--profile JiHy__hylmar__287` |
| Spend control | Alert-only AWS Budget, 20 EUR/month, alerts at 50/80/100% (no enforced cap) |
| Alias email | `aws-{first free digits}@hylmar.eu`, owner-created in Google Workspace; gates 7.2 |
| Admin users | `JiHy__hylmar__{XXX}` / `MiHy__hylmar__{XXX}` (XXX = first 3 digits of new acct id); AdministratorAccess, console pw force-reset, access keys, no MFA enforcement |
| OU placement | Org root (default; change if owner specifies an OU) |
| Currency | EUR budget unit needs account billing currency = EUR (default USD) — confirm in 7.4 |

## Tasks

### Task 7.1: Google Workspace alias root email
- **Size**: small
- **Verify**: `aws/provisioning/cag/request.md` records the exact alias and confirms uniqueness
- **Deliverable**: `aws/provisioning/cag/request.md`
- Owner picks the first free digits per the `aws-NNN@hylmar.eu` scheme and creates the alias/group in Workspace. Gates 7.2.

### Task 7.2: Create CAG member account
- **Size**: small
- **Verify**: `aws --profile JiHy__hylmar__287 organizations describe-create-account-status` = `SUCCEEDED`; account id captured
- Run `organizations create-account --account-name CAG --email <alias> --role-name OrganizationAccountAccessRole` from the mgmt profile. Default OU = root. Capture `AccountId` (→ `{XXX}`).

### Task 7.3: Admin IAM users
- **Size**: medium
- **Verify**: `iam list-users` in CAG shows both users with AdministratorAccess + login profile + access key; secrets out-of-band
- Assume `arn:aws:iam::{CAG}:role/OrganizationAccountAccessRole`. Create `JiHy__hylmar__{XXX}` and `MiHy__hylmar__{XXX}`: attach `AdministratorAccess`, create login profile (`--password-reset-required`), one access key each. Stage credentials in Secrets Manager / hand off.

### Task 7.4: Spend control budget
- **Size**: small
- **Verify**: `budgets describe-budget` returns 20 EUR monthly budget with 3 notifications to the alias
- Alert-only. Confirm billing currency for EUR unit. Mirrors `vsb-299` budget (task 5.2).

### Task 7.5: MCP connector for CAG
- **Size**: medium
- **Verify**: after owner loads connector + restart, the new MCP tool returns `sts get-caller-identity` = CAG id
- Create `mcp-{CAG-id}` IAM user + `MCP-Service-Access` policy + access keys via assumed role. Owner registers connector in Claude config and restarts (harness-side).

### Task 7.6: Document & hand back
- **Size**: small
- **Verify**: `aws/accounts.json` has CAG entry under `o-8i3fdvbxq7`; `deliverables.md` complete; no secrets in git
- **Deliverables**: `aws/accounts.json`, `CLAUDE.md` (account table), `aws/provisioning/cag/deliverables.md`
- Record console_login, profiles (`JiHy__hylmar__{XXX}`, `MiHy__hylmar__{XXX}`), mcp_connector, default_region eu-central-1, costcenter hylmar.

## Dependency order

```
7.1 ──> 7.2 ──┬──> 7.3 ──┐
              ├──> 7.4 ──┼──> 7.6
              └──> 7.5 ──┘
```
