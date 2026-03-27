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

<!-- Sessions are prepended above this line -->
