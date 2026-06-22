---
description: Provision a new nested AWS member account end-to-end (account, admin users, budget, SSO, MCP connector, root email) (project)
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash
  - AskUserQuestion
  - mcp__aws-*__call_aws
---

<!--
  Project-local skill (NOT centrally distributed). Captures the repeatable
  new-account provisioning flow first executed for account "CAG" (Phase 7).
  See aws/provisioning/<account>/ for per-run request + deliverables.
-->

# Provision AWS Account

Create a new nested member account under an existing AWS Organization and fully wire it:
account → admin users → spend budget → Identity Center (SSO) → MCP connector →
final root email → documentation.

**Reference run:** account `CAG` / `126697143436` (progress.json Phase 7).

---

## Inputs (collect first; ask only what's missing)

| Input | Example | Notes |
|-------|---------|-------|
| Org management access | profile `JiHy__hylmar__287` **or** an `mcp__aws-*` tool | Must be admin in the org **management** account. Verify before anything. |
| Account name | `CAG` | `--account-name` |
| Default region | `eu-central-1` | Convention only (recorded + used in connector env; AWS regions are per-call) |
| Admin user convention | `JiHy__hylmar__{first3}`, `MiHy__hylmar__{first3}` | `{first3}` = first 3 digits of the NEW account id (known only after creation) |
| Root email convention | `aws-{first3}@<domain>` (Workspace) | Domain mail is owner-managed (e.g. Google Workspace) |
| Budget | `20` + currency | AWS Budgets only supports the account's **billing currency** (default **USD**) |
| OU placement | org root (default) | |

## Decisions to confirm (AskUserQuestion if not given)

1. **Mgmt access** — direct CLI profile vs MCP tool vs owner-runs.
2. **Spend control** — alert-only budget (default) vs enforced budget action.
3. **Admin user access** — console + keys + MFA / console-only + MFA / console + keys, no MFA.
4. **MCP connector identity** — least-priv `mcp-{id}` (read/query) vs an admin user (full; matches existing connectors).

---

## Procedure

> Run privileged ops from the **management account** (CLI: `aws --profile <MGMT> …`).
> Cross-account ops use the auto-created `OrganizationAccountAccessRole` in the new account.
> **Secrets** (passwords, access keys) go to Secrets Manager — **never** git or chat (except deliberate hand-off).

### 0. Verify access & survey the org
```bash
aws --profile <MGMT> sts get-caller-identity
aws --profile <MGMT> organizations describe-organization
aws --profile <MGMT> organizations list-accounts \
  --query "Accounts[].{Id:Id,Name:Name,Email:Email}" --output table
aws --profile <MGMT> organizations list-roots --query "Roots[].Id" --output text
```
Confirm the email convention from an existing member (e.g. `aws-299@…`). Confirm the account name isn't taken.

### 1. Create the account
`create-account` needs a **unique, deliverable** email **up front**, but the id (→ `{first3}`) is only known **after**. Resolve with a temporary **plus-address** of a real mailbox, then fix the root email in step 7.
```bash
aws --profile <MGMT> organizations create-account \
  --account-name "<NAME>" --email "info+<name>@<domain>" \
  --role-name OrganizationAccountAccessRole --iam-user-access-to-billing ALLOW
# poll until SUCCEEDED, capture AccountId:
aws --profile <MGMT> organizations describe-create-account-status \
  --create-account-request-id <car-id> --query "CreateAccountStatus.[State,AccountId]" --output text
```
Record `ACCT=<id>`, `F3=<first 3 digits>`.

### 2. Admin users (assume into the new account)
Create `JiHy__hylmar__$F3` and `MiHy__hylmar__$F3`: `AdministratorAccess`, console login
(`--password-reset-required`), one access key each. Store each user's
`{password, access_key_id, secret_access_key, console_login}` in Secrets Manager
`<name>/admin/<user>` (region = default). Never echo secrets.
(See the reference run for the exact assume-role + loop snippet.)

### 3. Spend budget (alert-only)
```bash
# via assumed role into $ACCT; EUR will fail on a USD-billed account -> fall back to USD
aws budgets create-budget --account-id $ACCT \
  --budget '{"BudgetName":"monthly-cost-alerts","BudgetLimit":{"Amount":"<N>","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST"}' \
  --notifications-with-subscribers '<3x ACTUAL 50/80/100% -> alias email>'
```
**Currency gotcha:** for an exact EUR budget, the account's billing currency must first be set to EUR (root/billing console), then recreate with `Unit=EUR`.

### 4. Identity Center (SSO) — only if the org owns an instance
New accounts get **no** assignments automatically. Find the instance, mirror an existing account's principal+permission set, then assign:
```bash
aws --profile <MGMT> --region <sso-region> sso-admin list-instances
aws --profile <MGMT> --region <sso-region> sso-admin create-account-assignment \
  --instance-arn <inst> --target-id $ACCT --target-type AWS_ACCOUNT \
  --permission-set-arn <ps> --principal-type USER --principal-id <user-id>
```
(The Hylmar org instance `ssoins-68043e6b5b6e0104` / portal `d-9367ab04ac` lives in **eu-west-1**.)

### 5. MCP connector
- (Optional least-priv) create `mcp-$ACCT` + an `MCP-Service-Access` policy + key.
- Put the chosen identity's key into `~/.aws/credentials` as a profile (pull from Secrets Manager; don't print the secret).
- Register the connector — concise name `aws-<name>`:
```bash
claude mcp add aws-<name> --scope user \
  --env AWS_PROFILE=<profile> --env AWS_REGION=<region> -- awslabs.aws-api-mcp-server
```
  (or add the `aws-<name>` block to `~/.claude.json` `mcpServers`). **Restart Claude** to load `mcp__aws-<name>__call_aws`.

### 6. Finalize the root email (replace the temp plus-address)
Use the **Account Management API** (works from the management account — *not* console-only):
```bash
aws --profile <MGMT> account start-primary-email-update \
  --account-id $ACCT --primary-email "aws-$F3@<domain>"   # OTP -> new address
# owner reads OTP from aws-$F3@<domain>:
aws --profile <MGMT> account accept-primary-email-update \
  --account-id $ACCT --otp <code> --primary-email "aws-$F3@<domain>"
# verify:
aws --profile <MGMT> account get-primary-email --account-id $ACCT
```
Requires the target alias to be created in Workspace first (owner) and able to receive external mail.

### 7. Document
- Add the account to `aws/accounts.json` (org, default_region, costcenter, console_login, profiles, mcp_connector, root_email, sso_access, budget, secret ARNs).
- Add a row to the `CLAUDE.md` account table.
- Write `aws/provisioning/<name>/request.md` + `deliverables.md` (no secrets — ARNs only).
- Update `progress.json` (`/update-progress`).

---

## Gotchas (learned the hard way)

- **Root email IS API-changeable** (`start`/`accept-primary-email-update`) — earlier belief that it needs root console sign-in was wrong.
- **create-account email** must be unique + deliverable at creation; use a plus-address, fix later (step 6).
- **Budgets** only accept the account billing currency (USD by default) — EUR errors out.
- **SSO** assignments are never automatic for new accounts.
- **IAM users live only in the new account** — view them in *that* account's console (wrong-account console shows "user not found"/empty keys).
- Console **"API keys"** (service-scoped, e.g. Bedrock) ≠ IAM **access keys** (`AKIA…`) used by CLI/MCP. Don't confuse them.
- MCP connectors authenticate via `AWS_PROFILE` in `~/.aws/credentials` — **no keys in the Claude config**.
- Back up `~/.claude.json` and `~/.aws/credentials` before editing.

## Output

```
## Account Provisioned: <NAME> (<ACCT>)
- Org / OU: <org> / root
- Admin users: JiHy__hylmar__<F3>, MiHy__hylmar__<F3> (creds in Secrets Manager)
- Budget: <N> USD, alerts 50/80/100% -> aws-<F3>@<domain>
- SSO: AdministratorAccess -> <user>
- MCP connector: aws-<name> (restart to load)
- Root email: aws-<F3>@<domain>
- Docs: accounts.json, CLAUDE.md, aws/provisioning/<name>/
- Pending: <restart / billing-currency / etc.>
```

---

## Related Skills

- `/add-work` — track this provisioning as a phase/tasks in `progress.json` before executing.
- `/update-progress` — mark tasks complete, sync docs, commit + push when done.
- `/check-aws` — verify the new account's resources afterward.
- `/start-session` — confirm correct account/access at session start.
