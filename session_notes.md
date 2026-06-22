# Session Notes

This file tracks session history for context continuity between Claude Code sessions.

---

## Template Entry

### Session: YYYY-MM-DD HH:MM

**Context**:
- Phase: X - [Phase Name]
- Task: X.Y - [Task Name]
- Context used: XX%

**Completed**:
- [What was accomplished]

**Artifacts Created**:
- [Files, resources, etc.]

**Next Session**:
- Continue with: [next task or action]
- Blockers: [if any]

---

### Session: 2026-03-27

**Context**:
- Phase: 2 - Service Organization & Cross-Account Documentation
- Completed: All of Phase 2 (2.1-2.7) + repo philosophy shift
- Context used: ~50%

**Completed**:
- Phase 2 (7 tasks): repo structure, AWS account docs, skill-based reorganization
- Skill `aws-check-accounts` produced `aws/accounts.json` (23 accounts, 3 orgs, 6 MCP)
- Discovered mcp-{account_id} IAM users + MCP-Service-Access policy on all 6 accounts
- Repo philosophy: skill-based outputs, not static documentation
- Phase 3 added: refresh stale skill outputs (amplify, dynamodb, github, google)

**Artifacts Created**:
- `aws/accounts.json` - 23 accounts, sorted (6 active MCP first), tags, status, cross-account roles
- `aws/README.md` - skill output index
- `google/README.md` - placeholder with known AWS integrations
- `README.md` - central index organized by skills

**Key Decisions**:
- Repo organized by skills (verb), not by static docs (noun)
- Each skill produces structured output (JSON preferred over markdown)
- `accounts.json` is array (not object) for sorting: mcp-connected first
- Tags: mcp-connected, org-master, governance, org-member, legacy
- Status: active/passive

**Pending Cleanup**:
- hub440/ and aws-mcp-claude-code/ deletions not yet committed (in backlog)

**Next Session**:
- Phase 3: refresh stale outputs (3.1 aws-check-amplify, 3.2 aws-check-dynamodb)
- Commit pending deletions

---

### Session: 2026-03-27 (Session 2)

**Context**:
- Redirected from Phase 3 to Google services
- Added Phase 4: Google Services Inventory

**Work Added**:
- Phase 4 with 4 tasks (4.1-4.4): accounts, GCP projects, credentials, integrations
- Task 3.4 superseded by Phase 4
- Backlog cleaned (hub440 deletion was already committed in ee32983)

**User-Provided Context**:
- 7 Google accounts (Chrome profiles): admin@hub440.cz, info@hylmar.eu, service@d4m.tech, master@goldsport.cz, jiri.hylmar@gmail.com, jiri.hylmar@g.vsb.cz, hylmar@brainmarket.cz
- 4 Service Accounts: d4m-goo-master (2 SAs), vsb-bh6-gdr (1 SA), goldsport-default-project (1 SA)
- 4 OAuth Clients: macro-griffin-441215-v4, red-formula-306011, default-project-hub440, quickstart-1583930073537
- Credential paths provided for all 8 credentials

**Completed**:
- Phase 4 (6 tasks, 4.1-4.6): all complete
- 4.1: `google/accounts.json` — 7 Google accounts
- 4.2: `google/gcp-projects.json` — 7 GCP projects, 4 SAs, 4 OAuth clients
- 4.3: Verified all 8 credential files exist at listed paths
- 4.4: `google/integrations.json` — 6 Google↔AWS integration points
- 4.5: Added Chrome profile dir mapping (`Default`, `Profile 2`..`7`), gaia_name, gaia_id to accounts.json
- 4.6: `google/chrome-profiles.json` — 7 profiles with available data types (Bookmarks/Preferences as JSON, History/WebData as SQLite)
- Removed misleading `aws_association` from accounts.json per user feedback

**Key Decisions**:
- Google accounts are the core resource — 7 accounts, each is a Chrome profile
- Chrome data accessible via `/mnt/c/Users/jirih/AppData/Local/Google/Chrome/User Data/`
- Bookmarks and Preferences always readable (JSON), History/SQLite when Chrome closed
- Don't put speculative cross-references (aws_association was wrong)

**Artifacts Created**:
- `google/accounts.json` — 7 accounts with chrome_profile_dir, gaia_id
- `google/gcp-projects.json` — 7 projects, 8 credentials (all verified)
- `google/integrations.json` — 6 integration points
- `google/chrome-profiles.json` — profile data access inventory
- `google/README.md` — updated skill output index

**Phase 3 Completed** (same session, continued):
- 3.1: `aws/amplify-inventory.json` — 37 apps across 6 accounts (2 FAILED branches flagged)
- 3.2: `aws/dynamodb-inventory.json` — 59 tables across 6 accounts
- 3.3: `github/workspace-repos.json` — 191 repos (was 152), reorganized by 6 orgs

**Infrastructure Changes**:
- Changed `vouchers-gsp` (vsb-299) from PROVISIONED to PAY_PER_REQUEST — now 59/59 on-demand
- Removed obsolete `github/.claude/settings.local.json`

**Chrome Discovery**:
- Chrome profiles accessible at `/mnt/c/Users/jirih/AppData/Local/Google/Chrome/User Data/`
- Can launch Chrome with specific profile: `chrome.exe --profile-directory="Profile 4"`
- Can read bookmarks, preferences, extensions from all 7 profiles

**User Corrections**:
- Don't put speculative aws_association on Google accounts — misleading
- Don't say "can't do it" about Chrome — WSL2 can access Windows-side Chrome data via /mnt/c/
- Accounts are the core resource regardless of whether they have GCP projects

**Next Session**:
- All phases (2, 3, 4) complete
- No pending tasks — ready for new work

---

### Session: 2026-05-25 / 2026-05-26 (Session 3)

**Context**:
- All prior phases complete; reactive session triggered by AWS Health notification
- Account: vsb-299 (299025166536), region eu-central-1

**Trigger**:
- AWS Health event `a01ks3h6ekfjgzyjqq1vvm2dskr` — Lambda recursive loop detected and stopped

**Completed**:
- Phase 5 (2 tasks) added retroactively:
  - 5.1: Diagnosed `amplify-d2thadu8jkg00-mai-recordingsenricherlambda-7hdomPr9REk9` recursive loop, wrote incident report, verified external team's fix
  - 5.2: Created monthly cost budget on vsb-299 ($100/mo, alerts at $20/$50/$100 ACTUAL + $100 FORECASTED → info@hylmar.eu)

**Incident Timeline**:
- 2026-05-20 09:24 UTC — recordings bucket reference parameter created
- 2026-05-20 17:00–18:00 UTC — ~898k invocations charged (loop active)
- 2026-05-20 19:00 UTC — Lambda guard tripped, loop neutralised
- 2026-05-21 10:01 UTC — initial post-incident redeploy
- 2026-05-25 20:22 UTC — external team's fix deployed (verified)
- 2026-05-26 — budget created, $20 email alert confirmed received

**Root Cause**:
- S3 bucket notification on `amplify-d2thadu8jkg00-mai-recordingsbucket304ae6cd-wec5ccmzzyi2` triggered Lambda on any PutObject
- Lambda wrote 4 sidecar objects back to the same bucket → unbounded self-recursion

**External Fix Verified**:
- No resource-based trigger (no S3 notification, no EventBridge rule, no Lambda policy)
- Invocation is now via direct `lambda:Invoke` from an orchestrator (AppSync resolver or upstream Lambda) — structurally cannot self-loop
- New env var `METADATA_REPOSITORY_TABLE_NAME=digital-horizon-metadata-repository`
- Timeout increased 60s → 180s
- Idempotent: rerun logs "notes already exist … preserving operator edits"
- `RecursiveInvocationsDropped` = 0 since 2026-05-21; healthy 1-4 invocations/hr

**Cost Controls Added (vsb-299)**:
| Threshold | Type | State |
|---|---|---|
| $20 (20%) | ACTUAL | ALARM (already past, email confirmed) |
| $50 (50%) | ACTUAL | OK |
| $100 (100%) | ACTUAL | OK |
| $100 (100%) | FORECASTED | OK (forecast $46.73) |

**Artifacts Created**:
- `aws/incidents/2026-05-20-vsb-299-recordings-enricher-recursive-loop.md` — incident handoff for external team
- `arn:aws:budgets::299025166536:budget/monthly-cost-alerts`

**Key Decisions**:
- Created new `aws/incidents/` directory for incident handoff documents
- Scope of budget: vsb-299 only (per user choice) — other 5 MCP accounts not covered yet
- Notification posture: AWS-managed Health configurations are sufficient for "you got told", but added Budgets for cost-specific early warning
- Did NOT add notification hub or CloudWatch Lambda runaway alarm (user deemed measures sufficient)

**Outstanding (not actioned)**:
- Owner needs to acknowledge AWS Health event in console for 299025166536
- Other 5 MCP accounts have no cost budgets configured
- No CloudWatch alarm on `RecursiveInvocationsDropped` (could catch future loops faster than Health)

**Next Session**:
- No pending tasks; project back to maintenance state

---

### Session: 2026-06-04 (Session 4 — Part A delivered)

**Context**:
- Phase 6 Google provisioning for product **Audory** under **info@hylmar.eu**
- Goal: deliver Part A (Google OAuth for Cognito federation) so the Audory coordinating agent can run task 9.0b

**Completed this session**:
- 6.1 gcloud installed (~/google-cloud-sdk, no-root) + info@hylmar.eu authed (user creds + ADC)
- 6.2 reusable schema (google/provisioning/schema.md + _template.deliverables.json)
- 6.3 GCP project **android-auto-audory** (number 360321714436) under hylmar.eu org (259828723728)
- 6.4 OAuth Web client **android-auto-cognito-dev** (client_id 360321714436-mcpgco121lh857lcmo38jiveeoure945) — verified live (authorize endpoint → HTTP 302, no errors)
- 6.7 hand-back doc (google/provisioning/audory/deliverables.md)
- D1 resolved → **eu.hylmar.audory.app** (decisions.json + research)

**Secret handling**:
- Client secret pre-staged in **vsb-030 Secrets Manager**: `audory/dev/google-oauth`
  ARN `arn:aws:secretsmanager:eu-west-1:030062527147:secret:audory/dev/google-oauth-pisEJK`, eu-west-1, payload {client_id,client_secret}, tagged
- Added `.gitignore` (client_secret*.json, keystores). Downloaded secret file gitignored; now redundant (in Secrets Manager) — offer to shred.

**Key findings**:
- IAP OAuth Admin APIs permanently shut down 2026-03-19 → OAuth consent/client creation is **console-only**, no CLI path (confirmed via Google docs + live probe). Owner did the console clicks.
- `gcloud projects create` 429s on zero-project accounts (shared CLI quota pool); created project in console, then set ADC quota project → fixed.
- GCP project IDs can't contain 'google'/'ssl'.
- Domains (RDAP): audory.com = third-party GoDaddy since 2014; audory.cz unregistered; **audory.hylmar.eu owned** → chosen.
- AGP 8.4.2 decouples applicationId from namespace → D1 rename is ~3 lines, no source churn.
- ⚠️ gcloud sees 0 billing accounts for info@hylmar.eu (flag for Part B / paid APIs).

**Open / handed to coordinating agent (9.0b)**:
- Add UserPoolIdentityProviderGoogle to pool eu-west-1_RJzbzo83A using the secret ARN; map email/name/picture; enable Google on hosted UI; test login.
- ⚠️ Consent screen still **Testing** — owner to **Publish to Production** (guided) so non-test users can sign in.
- D1 change surface (app/backend): applicationId + appAuthRedirectScheme + AuthManager REDIRECT_URI + Cognito consumer-app callback.

**Deferred**:
- 6.5 Part B (Google Play): needs $25 dev account + ID verification + D2/D3/D4. Does not block auth.

**Next session**:
- Optional: confirm consent screen Published; shred redundant local secret file.
- When ready: Part B (Play) — register developer account, then 6.5 + resolve D2-D4.

---

### Session: 2026-06-04 (Session 4 — start)

**Context**:
- All prior phases (2–5) complete; project was in maintenance state
- User request: provision Google Cloud OAuth + Google Play for product **Audory** under **info@hylmar.eu**

**Inspection (before adding work)**:
- `info@hylmar.eu` (Chrome Profile 6) has **NO GCP projects, NO service accounts, NO OAuth clients, NO stored tokens** — `gcp_projects: []`. User's hunch that access/tokens already existed was incorrect → greenfield.
- No `gcloud` CLI installed, no gcloud auth, no audory/hylmar.eu credential files on disk, no GCP/Play bookmarks in Profile 6.
- Input doc: `input/external-google-cloud-and-play-setup.md` — Part A (Web OAuth client for Cognito federation, unblocks Audory task 9.0b on AWS vsb-030) + Part B (Google Play app `cz.audory.app`, Android Auto) + 4 owner decisions D1–D4.

**Work Added (/add-work, approved)**:
- New **Phase 6: Google Cloud + Play External Provisioning (reusable)** — 7 tasks (6.1–6.7)
- Built broad/reusable per user request: `google/provisioning/<product>/` convention + shared schema so future requests need minimal readjustment
- Executor: gcloud CLI auth under info@hylmar.eu
- Source: user request + input doc

**Reality flags**:
- 6.4: general Web OAuth client creation via gcloud/API is limited → consent screen + Web client likely console under info@hylmar.eu; gcloud does project + API enablement; result recorded
- 6.5: $25 Play dev account + identity verification (days) → may land pending_verification
- 6.6→6.5: D1 (`cz.` vs `com.audory.app`) must be resolved before immutable package name is created

**Next Session**:
- Start Task 6.1 — install + configure gcloud, authenticate info@hylmar.eu
- current_task set to 6.1

---

### Session: 2026-06-22

**Context**:
- Phase: 7 - CAG Account Provisioning (Hylmar org `o-8i3fdvbxq7`)

**Work Added (/add-work, approved)**:
- New **Phase 7: CAG Account Provisioning** — 6 tasks (7.1–7.6)
- Establish nested member account **CAG** under mgmt account **287773673380** (`hylmar_OA`),
  default region **eu-central-1**, 2 admin users, Workspace contact-alias root email, 20 EUR/month budget
- Source: user request

**Access finding (resolved mid-discussion)**:
- `aws/accounts.json` showed `hylmar_OA` (287773673380) with **no MCP connector** → looked like a blocker.
- User confirmed local profile **`JiHy__hylmar__287`** has access. Verified live:
  `arn:aws:iam::287773673380:user/JiHy__hylmar__287`, org `o-8i3fdvbxq7` readable (FeatureSet ALL, SCP enabled).
- → Execution model = direct CLI via `--profile JiHy__hylmar__287`; cross-account via assumed `OrganizationAccountAccessRole`. No MCP bootstrap needed.

**Decisions captured (AskUserQuestion)**:
- Spend control = **alert-only** budget (20 EUR/mo, 50/80/100% email alerts), no enforced cap
- Alias email = `aws-{first free digits}@hylmar.eu`, **owner-created in Google Workspace** (gates account creation)
- Admin users = `JiHy__hylmar__{XXX}` / `MiHy__hylmar__{XXX}` (XXX = first 3 digits of new acct id); AdministratorAccess, console pw force-reset, access keys, no MFA enforcement
- OU placement = org root (default)

**Reality flags**:
- 7.1 owner dependency: Workspace alias must exist + be unique before `create-account`
- 7.4: EUR budget unit needs account billing currency = EUR (new accounts default USD) — confirm
- 7.5: MCP connector registration is harness-side (owner loads config + restart)

**Next Session**:
- Start with 7.1 (await Workspace alias address), then 7.2 create-account
- current_task set to 7.1

---

<!-- Sessions are prepended above this line -->
