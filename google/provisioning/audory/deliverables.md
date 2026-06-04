# Audory — Google Cloud + Play provisioning: deliverables (hand-back)

**From:** hyl-resources-manager (Phase 6), executed under **info@hylmar.eu**
**To:** Audory coordinating/backend agent (android-auto-orchestrator)
**Date:** 2026-06-04
**Re:** `input/external-google-cloud-and-play-setup.md`

> **TL;DR — Part A (Google OAuth) is DONE and the secret is pre-staged in your AWS
> Secrets Manager.** You can proceed with task **9.0b**. Part B (Google Play) is deferred
> pending decisions D2–D4 and a $25 developer account (see below). It does **not** block auth.

---

## Part A — Google OAuth (for task 9.0b) ✅ DELIVERED

| Field | Value |
|-------|-------|
| Google Cloud Project ID | `android-auto-audory` |
| Google Cloud Project number | `360321714436` |
| Owner Google account / org | `info@hylmar.eu` / Workspace org `hylmar.eu` (259828723728) |
| OAuth consent screen | **External**, scopes `openid` `email` `profile` (non-sensitive → no Google review) |
| OAuth consent screen status | ⚠️ **Testing** — owner publishing to Production (confirm before relying on non-test-user logins) |
| OAuth Client ID (Web application) | `360321714436-mcpgco121lh857lcmo38jiveeoure945.apps.googleusercontent.com` |
| OAuth client label | `android-auto-cognito-dev` |
| OAuth Client secret | **In AWS Secrets Manager (see below)** — not written here |
| Redirect URI registered exactly? | ✅ `https://audory-dev-030062527147.auth.eu-west-1.amazoncognito.com/oauth2/idpresponse` |
| JavaScript origin registered | ✅ `https://audory-dev-030062527147.auth.eu-west-1.amazoncognito.com` |
| Verification | Live `GET accounts.google.com/o/oauth2/v2/auth` → HTTP 302 sign-in flow, no `invalid_client` / `redirect_uri_mismatch` (2026-06-04) |

### 🔑 Client secret — pre-staged in YOUR Secrets Manager
We stored `client_id` + `client_secret` in your account so you don't handle the raw secret:

| Field | Value |
|-------|-------|
| Account | `030062527147` (vsb-030) |
| Region | `eu-west-1` |
| Secret name | `audory/dev/google-oauth` |
| Secret ARN | `arn:aws:secretsmanager:eu-west-1:030062527147:secret:audory/dev/google-oauth-pisEJK` |
| Payload shape | `{ "client_id": "...", "client_secret": "..." }` |
| Tags | `Project=audory` `Env=dev` `ManagedBy=hyl-resources-manager` `Purpose=google-oauth-idp` |

Read in CDK, e.g. `Secret.fromSecretNameV2(this, 'GoogleOAuth', 'audory/dev/google-oauth')`
and pull `client_id` / `client_secret` fields.

### What 9.0b still needs to do (your side — Cognito half)
1. Add `UserPoolIdentityProviderGoogle` to pool `eu-west-1_RJzbzo83A` using the secret above.
2. Attribute mapping: `email` → email, `name` → name, `picture` → picture.
3. Enable **Google** as a supported IdP on the Hosted UI app client; ensure callback/scopes set.
4. Test "Sign in with Google" on the Hosted UI end-to-end.
   - ⚠️ If the **consent screen is still in Testing**, only consent-screen *test users* can
     complete sign-in (others get `access_denied`). Owner is publishing to Production to remove
     this limit; confirm status at
     https://console.cloud.google.com/auth/audience?project=android-auto-audory

---

## Decisions

| ID | Question | Answer |
|----|----------|--------|
| **D1** | Canonical Android package name | ✅ **`eu.hylmar.audory.app`** (reverse-DNS of owner-controlled `audory.hylmar.eu`) |
| D1b | Native app OAuth callback | **`eu.hylmar.audory.app://oauth/callback`** (custom scheme; App Links upgrade possible later) |
| D2 | Store listing languages | ⛔ pending |
| D3 | Publishing pipeline (manual vs Play Developer API) | ⛔ pending |
| D4 | Play account type (org vs individual) | ⛔ pending |

### D1 reconciliation — change surface YOU own (app/backend)
The app code is entirely `cz.audory.*`; only the OAuth redirect carried `com.audory.*`. On
AGP 8.4.2 `applicationId` is decoupled from `namespace`, so set the Play identity without renaming
the source tree:

| File / resource | Change |
|-----------------|--------|
| `android-auto-app app/build.gradle.kts:12` | `applicationId = "eu.hylmar.audory.app"` |
| `android-auto-app app/build.gradle.kts:18` | `appAuthRedirectScheme = "eu.hylmar.audory.app"` |
| `android-auto-app AuthManager.kt:103` | `REDIRECT_URI = "eu.hylmar.audory.app://oauth/callback"` |
| `android-auto-app AndroidManifest.xml:25-27` | update comment to new scheme |
| Cognito **consumer-app** client `7lt16dfjsgejceu60s5nqtqrrg` (vsb-030) | whitelist `eu.hylmar.audory.app://oauth/callback` (replace `com.audory.app://oauth/callback`) |
| `cz.audory.*` namespaces / source tree | **no change** |

> Note: D1 is about the **native app PKCE callback** (consumer-app client). It is **independent**
> of the Google federation client above (whose redirect is the HTTPS `idpresponse` URL).

---

## Part B — Google Play ⛔ DEFERRED (not started)

Not begun — needs a one-time **$25 developer account + identity verification (can take days)** and
decisions D2–D4. Package name is settled (D1 = `eu.hylmar.audory.app`). Part B does **not** block
the auth flow. When ready, resume Phase 6 task 6.5:

| Field | Value |
|-------|-------|
| Play developer account active | ⛔ not created |
| App created, package name | ⛔ pending (will be `eu.hylmar.audory.app`) |
| App signing cert SHA-1 / SHA-256 | ⛔ pending (from Play App Signing) |
| Internal testing track | ⛔ pending |

⚠️ Also: `gcloud billing accounts list` shows **0 billing accounts** visible to info@hylmar.eu —
sort out Cloud Billing before any paid API / Play Developer API (D3) work.

---

## Status summary

| Item | Status |
|------|--------|
| GCP project `android-auto-audory` | ✅ created (under hylmar.eu org) |
| OAuth consent screen | ✅ configured · ⚠️ publish to Production pending owner confirm |
| OAuth Web client + redirect URI | ✅ created & verified live |
| Client secret → Secrets Manager (vsb-030) | ✅ staged (`audory/dev/google-oauth`) |
| D1 package name | ✅ resolved (`eu.hylmar.audory.app`) |
| D2 / D3 / D4 | ⛔ pending |
| Part B — Google Play | ⛔ deferred |
