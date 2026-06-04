# Phase 6: Google Cloud + Play External Provisioning (reusable)

**Source:** `input/external-google-cloud-and-play-setup.md` (prepared by the Audory backend/infra agent, 2026-06-04)
**Owner Google account:** `info@hylmar.eu` (Chrome Profile 6) — greenfield, no GCP projects/credentials at start
**Executor:** gcloud CLI auth under info@hylmar.eu
**Goal:** Provision Google Cloud OAuth (Part A) + Google Play Console (Part B) for product **Audory**, built as a **reusable capability** so future external Google setup requests need minimal readjustment.

## Reusable convention

```
google/provisioning/
  schema.md                      # input-request + output-deliverables schema (6.2)
  _template.deliverables.json    # blank deliverables template (6.2)
  <product>/                     # one folder per request, e.g. audory/
    oauth.json                   # Part A deliverables (6.4)
    play.json                    # Part B deliverables (6.5)
    decisions.json               # owner decisions D1-D4 (6.6)
    deliverables.md              # filled hand-back doc (6.7)
```

## Fixed Audory facts (copy exactly — from input doc)

| Item | Value |
|------|-------|
| Product / brand | Audory |
| Cognito Hosted UI domain (dev) | `https://audory-dev-030062527147.auth.eu-west-1.amazoncognito.com` |
| Google → Cognito redirect URI (dev) | `.../oauth2/idpresponse` |
| Cognito User Pool (dev) | `eu-west-1_RJzbzo83A` (eu-west-1) |
| OAuth scopes | `openid`, `email`, `profile` |
| Android package (applicationId) | `cz.audory.app` (⚠ D1 conflict with `com.audory.app://`) |
| Owner contact | projekt1@hub440.cz |
| Consumes (downstream) | `android-auto-orchestrator` task **9.0b** (AWS account vsb-030 / 030062527147) |

## Tasks

### Task 6.1: Install & configure gcloud CLI; auth info@hylmar.eu
- **Size**: small
- **Verify**: `gcloud auth list` shows info@hylmar.eu ACTIVE; `gcloud config get-value account` == info@hylmar.eu
- **Deliverable**: gcloud installed; `gcloud auth login` + `gcloud auth application-default login` done; auth pattern documented (generic for any owner account)

### Task 6.2: Define reusable provisioning schema
- **Size**: small
- **Verify**: `google/provisioning/schema.md` + `google/provisioning/_template.deliverables.json` exist
- **Deliverable**: parameterized input-request + output-deliverables schema

### Task 6.3: Create `audory` GCP project + enable APIs
- **Size**: small
- **Verify**: `gcloud projects describe <audory-project-id>` → ACTIVE; info@hylmar.eu `gcp_projects` updated in `google/accounts.json`
- **Deliverable**: project created; recorded in `gcp-projects.json` + `accounts.json`

### Task 6.4: Part A — OAuth consent screen + Web OAuth client
- **Size**: medium
- **Verify**: `google/provisioning/audory/oauth.json` has client_id + idpresponse redirect URI + consent status
- **Deliverable**: consent screen (External; openid/email/profile; test user projekt1@hub440.cz; authorized domain amazoncognito.com); Web client `audory-cognito-dev`
- **Note**: client SECRET out-of-band only (AWS Secrets Manager) — never commit

### Task 6.5: Part B — Play Console app + signing + internal track
- **Size**: medium
- **Verify**: `google/provisioning/audory/play.json` populated or `pending_verification`
- **Deliverable**: dev account; app `cz.audory.app` (per D1); Play App Signing SHA-1/256; internal-testing track
- **Note**: needs $25 account + identity verification (days); depends on D1

### Task 6.6: Resolve owner decisions D1–D4
- **Size**: small
- **Verify**: `google/provisioning/audory/decisions.json` has D1–D4 answered
- **Deliverable**: D1 canonical package name, D2 languages, D3 pipeline, D4 account type
- **Note**: D1 must precede 6.5 (immutable package name)

### Task 6.7: Filled "Deliverables to return" hand-back doc
- **Size**: small
- **Verify**: `google/provisioning/audory/deliverables.md` complete (no secrets in git)
- **Deliverable**: filled Part A + Part B + decisions tables to hand back to the Audory agent (unblocks 9.0b)
