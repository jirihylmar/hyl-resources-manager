---
description: Verify AWS resources for this project (project)
allowed-tools:
  - Read
  - mcp__aws-*__call_aws
---

<!--
  Centrally distributed by /distribute-defaults from syndicate-playbooks-examples.
  Project-specific additions go in .claude/local-overlays/<this-filename> as
  splice fragments (see /distribute-defaults for the overlay format).
  Direct edits to this file will be flagged on the next distribution.
-->

# Check AWS Resources

Verify all project AWS resources are properly configured.

## Prerequisites

Before running AWS checks, environment config must exist.

**Read environment from:**
1. `input/environment.md` or `input/env.md`
2. `CLAUDE.md` Quick Reference section
3. `progress.json` context_hints

**Required — and there is only one:**
- **AWS Account ID** (`context_hints.aws_account`). It is the same twelve digits on every machine,
  which is exactly why it is the thing you verify against.
- Also useful: AWS Region, project prefix (naming convention).

**A hint, never a requirement — `context_hints.mcp_tool`.** It names an AWS connection, and a
connection name is a **nickname**: true on the machine it was written on, quite possibly false on
this one. `progress.json` is committed and travels to both machines, so a nickname stored there can
only ever be correct on one of them. Treat `mcp_tool` as the first candidate to try, never as the
answer — **a wrong, retired, or missing `mcp_tool` is not an error and needs no migration.** Step 2
resolves it either way. (The rule and the reasoning: `/start-session` § Two Environments.)

**If the account ID is missing:** STOP and direct user to `/setup` (its environment-collection step
gathers account/region/MCP/naming), or to add the values to `CLAUDE.md` / `input/environment.md`.

---

## Steps

### 1. Read Environment Config
```
Read environment from standard locations.
Extract: aws_account (REQUIRED), aws_region, project_prefix
Also read mcp_tool if present — as a hint for Step 2, not as an instruction.
```

**Check that `aws_account` is actually an account number — twelve digits, nothing else.** A nickname
has been found sitting in this field (e.g. `d4m-975` instead of `975050190402`), and it fails in the
worst way: no candidate in Step 2 can ever match it, so the honest-looking report becomes *"account
unreachable from this machine"* when the truth is *"this project's account number is not an account
number."* If it is not twelve digits, STOP and say exactly that:

```
context_hints.aws_account is "{value}", which is not an account number (expected 12 digits).
This is a nickname in the one field that must hold the real identity. Fix it in progress.json —
the account number is visible in the Arn of any successful `aws sts get-caller-identity`.
```

### 2. Resolve the AWS handle, and prove it reached your account

> **This step is one instance of the rule in `/start-session` § Two Environments — *verify identity,
> resolve location, never declare a nickname*. The rule is stated there and not restated here.**

**There are two AWS service models. Both are correct. Detect which one this host runs — never assume.**

| Model | How it is set up | How you call it |
|---|---|---|
| **Per-account servers** | one MCP server per account, each carrying its own `AWS_PROFILE` | pick the right server, pass **nothing** |
| **One central server** | a single MCP server bound to **no** account | name the account with `--profile` on every call |

> **Why two models exist — memory, and this is not negotiable.** Every configured AWS MCP server
> spawns **its own process per session** (~120 MB each). A host with 12 per-account servers and 6
> live sessions needs ~8.8 GB **for AWS tooling alone** — which is more RAM than the dev box has, so
> it burst. Moving that host to one central server cut it roughly 12×. **Do not "fix" a central-server
> host by re-adding per-account servers**: you will re-create the outage, and it will look like you
> improved the config. The per-account model is a large-RAM luxury; the central model is what a host
> adopts when sessions multiply. Expect hosts to move **toward** central, never back.

> **`--profile` silently OVERRIDES a binding — it does not fail.** Passing a profile that exists
> returns *that* profile's account with `200 OK`, even on a server bound to a different one
> (measured: a server bound to `030…`, given a profile for `299…`, returned `299…`). Only a profile
> that does not exist on this host errors. **So a wrong profile does not break the run — it quietly
> checks the wrong account.** Two consequences, both load-bearing: never pass `--profile` to a server
> that already answered bare, and never trust "the call worked" — *only the returned account number
> tells you where you landed.*

**Candidates, in this order:** `context_hints.mcp_tool` if present, then every other
`mcp__aws-*__call_aws` tool available in THIS session. Read your own live tool inventory — **never a
list written down anywhere, including this file.** The set differs per machine and grows over time.

**Probe each candidate bare:**

```
{candidate} aws sts get-caller-identity
```

| What comes back | Which model | What you do |
|---|---|---|
| Identity, `Account` **==** `aws_account` | per-account | **Resolved.** Use this candidate **bare** everywhere below. Adding `--profile` here can only move you off a correct binding. |
| Identity, `Account` **!=** `aws_account` | per-account, wrong one | Say which account it hit. Next candidate. |
| Error: no credentials / no default account | **central** | Not broken — this is the central model. Find the profile that reaches your account (below). |
| Error: unknown tool | not on this host | Next candidate. |

**Central server — match a profile by account number, never by name:**

First, list the profiles this host actually has. **Read BOTH `$HOME/.aws/config` and
`$HOME/.aws/credentials`** (with the Read tool — `Read` is in this command's `allowed-tools` for
exactly this). Take the names from `config`'s `[profile <name>]` headers **and** from `credentials`'
`[<name>]` section headers, and use the union.

> **Both files, or you will report a reachable account as unreachable.** A profile whose keys live in
> `credentials` with no matching `config` stanza is completely valid and works — `config` carries
> region and settings, not existence. Measured on one workstation: `config` had **5** profile headers,
> `credentials` had **29**, so **24** profiles were invisible to a config-only listing — including the
> organization-management credential that had demonstrably run `organizations create-account` from
> that machine. Two profiles backing *working* MCP servers were among the 24.
>
> Do not "fix" this by writing the missing stanzas. Profiles arrive by many routes — the console, SSO,
> another machine, a provisioning script, by hand — so no single writer can be corrected into
> covering them all. **Enumerate both files here**, which is correct however the profile was born.
> **Never read a key, a secret, or a token value out of either file** — you want section *names*.

> **Read it, never write it.** You are reading a list of *names* to find which one reaches your
> account. `/check-aws` never modifies AWS configuration, never adds a profile, and never edits
> `~/.aws/*`. If the profile you need does not exist on this host, that is a host-configuration gap —
> **report it** (§ below); creating it is the operator's call, not yours.
>
> **Why the file, and not a command:** profile names are per-host and unguessable — the same account
> is `vsb-182` on one machine and `HylmarJ` on another, with no rule connecting them — so the name
> cannot live in `progress.json` (which travels to every host). And you cannot ask AWS: the MCP
> server validates commands against the AWS service model and rejects `aws configure` outright
> (`ServiceNotAllowedError: The given service name is not allowed: configure`). The names live in a
> config file, so the file is where you read them.

> **Do NOT ask the AWS connection to list profiles.** `aws configure list-profiles` is **rejected
> before it runs** — the MCP server validates every command against the AWS service model and
> `configure` is not a service: `ServiceNotAllowedError: The given service name is not allowed:
> configure`. Verified on multiple connections. An earlier draft of this step prescribed exactly
> that command, which dead-ended the *only* resolution path the remote box can use and would have
> produced a false *"account not reachable"* report there. Profiles live in a **config file**, so
> read the file.

Then, for each profile until one matches:

```
{candidate} aws sts get-caller-identity --profile {profile}
```

The profile whose `Account` equals `aws_account` is your handle; append `--profile {that}` to every
command below. **Profile names are nicknames too.** The same account is named differently on each
machine — one may name it after a person, another after the account number — and *you cannot compute
one from the other*. There is no convention to infer. Match by account number and nothing else.

**Below, `{handle}` means:** the resolved candidate, plus `--profile {profile}` appended to the `aws`
command if and only if Step 2 resolved through a profile.

**If no candidate reaches `aws_account`, report and stop. Say which model this host runs — that is
what makes the report actionable:**

```
This project's AWS account {aws_account} is not reachable from this host.

  Host model:  per-account servers  (or: one central server)
  Tried:       {each candidate/profile and what it returned}
  Gap:         no server is bound to {aws_account}
               (central model: no profile in ~/.aws/config OR ~/.aws/credentials reaches it)

This is a host-configuration matter, not something to work around. Either the account
belongs on another host — run /check-aws where it lives — or this host is missing the
server/profile, which is the operator's call to add.
```

Same answer the framework gives for a repo that lives on the other machine: **do the work where the
thing actually is.** Do not invent a profile, do not guess a name from a pattern, do not add a
server, and do not report on resources you could not see. **Never present an unreachable account as a
resource finding** — *zero found* and *could not look* are different facts.

**Record nothing.** Never write the resolved handle into `progress.json` — it travels to both
machines, where it would be a nickname true on only one. Resolving costs one call; a stale nickname
costs a silent wrong answer.

**Expected-resource lists come from THIS project** — derive them from `IMPLEMENTATION_PLAN.md`
(and `resource_inventory` in progress.json if it exists), never from this template's examples.

### 3. Check S3 Buckets
```
{handle} aws s3 ls
```
Filter for project buckets (matching project_prefix), e.g. `{project}-artifacts-*`.

### 4. Check DynamoDB Tables
```
{handle} aws dynamodb list-tables
```
Filter for project tables (matching project_prefix).

### 5. Check SQS Queues
```
{handle} aws sqs list-queues
```
Filter for project queues (matching project_prefix), including any `*-dlq` dead-letter pairs.

### 6. Check SNS Topics
```
{handle} aws sns list-topics
```
Filter for project topics (matching project_prefix).

### 7. Check Lambda Functions
```
{handle} aws lambda list-functions
```
Filter for project functions (matching project_prefix).

### 8. Check CloudFormation Stacks
```
{handle} aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE
```
Filter for project stacks.

### 9. Check IAM Roles
```
{handle} aws iam list-roles
```
Filter for project roles (matching project_prefix).

---

## Output

```
## AWS Resource Check

### Environment
- Account: {aws_account} ✓
- Region: {aws_region} ✓
- Project: {project_prefix}

### Handle Resolved (this machine only — recorded nowhere)
- Connection: {the candidate that worked}
- How it was called: no profile needed — this connection is tied to one account
  (or: named the account explicitly with `--profile {profile}`, because this connection serves many)
- Identity verified: {actual_account} — matches {aws_account} {✓ or ✗ STOP}
- (If context_hints.mcp_tool was present and did not resolve, say so plainly AND say it is
  harmless: it is a nickname from the other machine, not a defect to fix.)

### Resources Found

| Type | Expected | Found | Status |
|------|----------|-------|--------|
| S3 Buckets | 2 | 2 | ✓ |
| DynamoDB Tables | 1 | 1 | ✓ |
| SQS Queues | 2 | 0 | ✗ Missing |
| SNS Topics | 1 | 0 | ✗ Missing |
| Lambda Functions | 7 | 0 | ✗ Not deployed |
| CloudFormation Stacks | 2 | 0 | ✗ Not deployed |

### Missing Resources
- {resource} — created by {task/phase ref from progress.json}
- ...

### Next Steps
- {deploy/create step for the missing resources, from progress.json}
- Or continue with current phase task
```

**If the account was unreachable from this machine**, the report is the Step 2 block and nothing
else. Do not render an empty resource table — *zero found* and *could not look* are different facts,
and printing the first when the second is true is a false report.

---

## Notes

- Always read environment config first
- **Verify the account number before reading any resource** — reaching *an* account is not reaching
  the *right* one
- Use MCP tools, never raw aws CLI
- Compare against expected resources from IMPLEMENTATION_PLAN.md
- Add project-specific resource types via `.claude/local-overlays/check-aws.md` (splice fragment), not by hand-editing this distributed default
- Use resource_inventory in progress.json as reference if it exists
