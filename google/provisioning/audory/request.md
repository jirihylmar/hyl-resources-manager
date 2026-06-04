# External Setup Instructions — Google Cloud (federated login) + Google Play (Android publishing)

**Audience:** the external agent preparing Google Cloud / Google Play on the owner's behalf.
**Prepared by:** backend/infra agent for **android-auto-orchestrator** (project "Audory").
**Date:** 2026-06-04.

This document has two independent deliverables:

- **Part A — Google Cloud OAuth 2.0 app** so users can choose "Sign in with Google" on our
  Cognito Hosted UI. This unblocks our task **9.0b**.
- **Part B — Google Play Console setup** so we can publish the Android Auto app.

You do **not** need AWS access. Everything below is done in the **Google Cloud Console**
(console.cloud.google.com) and the **Google Play Console** (play.google.com/console).
When you finish, fill in the **"Deliverables to return"** section at the bottom and we will
wire it into our infrastructure.

---

## Fixed facts about our system (do not change — copy values exactly)

| Item | Value |
|------|-------|
| Product / brand name | **Audory** |
| AWS Cognito Hosted UI domain (dev) | `https://audory-dev-030062527147.auth.eu-west-1.amazoncognito.com` |
| **Google → Cognito redirect URI** (dev) | `https://audory-dev-030062527147.auth.eu-west-1.amazoncognito.com/oauth2/idpresponse` |
| Cognito User Pool (dev) | `eu-west-1_RJzbzo83A` (region `eu-west-1`) |
| OAuth scopes we request | `openid`, `email`, `profile` |
| Android app package name (applicationId) | **`cz.audory.app`** — see ⚠️ decision D1 below |
| Owner contact email | projekt1@hub440.cz |

> There will later be **prod** (and possibly **staging**) Cognito domains with the same
> `.../oauth2/idpresponse` shape but a different prefix. Build the OAuth client so we can
> **add more redirect URIs later** — you don't need them now.

---

## Part A — Google Cloud OAuth 2.0 (Sign in with Google via Cognito)

Goal: a **Web application** OAuth 2.0 Client ID that AWS Cognito uses as a federated identity
provider. The user clicks "Sign in with Google" on our Hosted UI → Google authenticates →
Google redirects back to the Cognito `idpresponse` URL above. The Android app and web app
themselves never talk to Google directly, so **a "Web application" client type is correct**
(not "Android", not "iOS").

### A1. Create / choose a Google Cloud project
- Create a project named **`audory`** (or reuse an existing owner project). Note the **Project ID**.

### A2. Configure the OAuth consent screen
- **User type:** External.
- **App name:** Audory
- **User support email:** projekt1@hub440.cz
- **App logo:** optional for now (we can supply later; see Part B branding).
- **Authorized domains:** add **`amazoncognito.com`** (this is required — it's where the
  redirect URI lives).
- **Scopes:** add the non-sensitive scopes **`openid`**, **`email`**, **`profile`**
  (`.../auth/userinfo.email`, `.../auth/userinfo.profile`, and `openid`). No sensitive or
  restricted scopes are needed, so **no Google verification/review is required** to go live.
- **Test users:** while the consent screen is in "Testing" status, add at least
  `projekt1@hub440.cz` so we can verify before publishing the consent screen.

### A3. Create the OAuth 2.0 Client ID
- **APIs & Services → Credentials → Create credentials → OAuth client ID.**
- **Application type:** **Web application**.
- **Name:** `audory-cognito-dev` (so we can tell environments apart later).
- **Authorized JavaScript origins:**
  - `https://audory-dev-030062527147.auth.eu-west-1.amazoncognito.com`
- **Authorized redirect URIs:**
  - `https://audory-dev-030062527147.auth.eu-west-1.amazoncognito.com/oauth2/idpresponse`
- Create it. Google shows a **Client ID** and a **Client secret** — both are needed (see
  deliverables). The Client secret is **confidential**.

### A4. (Leave to us) What we do with your output
We will store the Client ID + secret in AWS Secrets Manager and add a
`UserPoolIdentityProviderGoogle` to Cognito with attribute mapping
(`email`, `name`, `picture`) via our CDK. **You do not configure anything on the AWS side.**

---

## Part B — Google Play Console (Android publishing)

Goal: a Play Console app entry ready for an **internal-testing** release, so we can upload a
signed app bundle and invite testers. Production rollout comes later.

### B1. Developer account
- Ensure the owner has a **Google Play Console developer account** (one-time \$25 registration;
  organization account preferred over personal if this ships commercially). Identity
  verification can take a few days — start this first.

### B2. Create the app
- **App name:** Audory
- **Default language:** decide (likely Czech `cs-CZ` with English as additional) — see D2.
- **App or game:** App. **Free or paid:** Free (entitlement is org-based inside the app).
- **Package name:** **`cz.audory.app`** — ⚠️ see decision **D1**. This is **immutable once the
  app is created**, so confirm it before creating.

### B3. App signing (Play App Signing)
- Use **Play App Signing** (Google holds the app signing key; we hold an upload key). We will
  generate and hold the **upload keystore** on our side and build the signed `.aab`.
- From Play Console, capture and return to us: the **app signing certificate SHA-1 and SHA-256**
  fingerprints (under *Setup → App integrity → App signing*). We need these on record in case we
  later add native Google Sign-In / Credential Manager or other Google SDKs that key off the
  signing cert. (Our current login flow is browser-based via Cognito Hosted UI and does **not**
  require them, but capture them anyway.)

### B4. Android Auto compliance (important — this is a car/media app)
- This app drives **Android Auto** (media app, Media3/`MediaLibraryService`). Play reviews media +
  Android Auto apps against the **Android Auto app quality** and **media app** guidelines, and an
  Auto app must be opted into the **"Cars"** distribution / declared as an Auto-enabled app.
- Action: in the Play Console app content, plan for the **Android Auto declaration** and be ready
  for the media-app review. Flag to us anything the review checklist needs from the build side
  (e.g., specific manifest declarations) — we own the app code.

### B5. Store listing + policy content (owner-provided content)
Prepare placeholders / gather from owner:
- Short description, full description (Czech + English).
- App icon (512×512), feature graphic (1024×500), phone + Android Auto screenshots.
  - Note: branding/adaptive-icon asset is still pending from the owner (tracked on our side).
- **Privacy policy URL** (required — the app handles accounts/email; Data safety form depends on it).
- **Data safety** form: we collect email + account identifiers (auth) and playback/resume state.
  We do **not** sell data. Coordinate the exact disclosures with us before submitting.
- **Content rating** questionnaire, **target audience**, **ads** declaration (no ads).

### B6. First release track
- Set up an **Internal testing** track and add `projekt1@hub440.cz` (+ any owner testers).
- We will provide the signed `.aab` to upload (or, if CI/CD with the Play Developer API is
  preferred later, see D3).

---

## Decisions we need from the owner / you (please answer in the returned doc)

- **D1 — Package name mismatch (must resolve before B2).** The Android build's `applicationId`
  is **`cz.audory.app`**, but our OAuth/AppAuth redirect scheme is **`com.audory.app://`**
  (and Cognito's `consumer-app` client callback is `com.audory.app://oauth/callback`). These
  are inconsistent. **The Play package name is permanent**, so we must pick the canonical
  identifier now. Recommendation: standardize on **`cz.audory.app`** everywhere (we'll update the
  redirect scheme + Cognito callback to match). **Please confirm the canonical package name.**
- **D2 — Store languages:** primary listing language (Czech vs English) and which additional
  languages to include.
- **D3 — Publishing pipeline:** do you want us to wire CI/CD to publish via the **Google Play
  Developer API** (needs a Play Console service account we'd grant), or will you upload the
  `.aab` manually for now? (Manual is fine to start.)
- **D4 — Account type:** organization vs individual Play developer account (affects branding +
  data-safety attribution).

---

## ⚠️ Secret handling (read before returning anything)

- The **Google OAuth client *secret*** (Part A) and any **keystore / service-account JSON**
  (Part B) are **confidential — do NOT commit them to git** and do not paste them into this
  file in the repo.
- Return the **Client ID** in the deliverables table below (it's not secret).
- Send the **Client secret** to us via a secure channel (the owner's password manager share,
  encrypted message, or a one-time secret link) — **not** in the repo. We will put it straight
  into AWS Secrets Manager.

---

## Deliverables to return (fill this in, then notify us)

### Part A — Google OAuth (for task 9.0b)
| Field | Value |
|-------|-------|
| Google Cloud Project ID | `__________` |
| OAuth consent screen status | Testing / In production |
| OAuth Client ID (Web application) | `__________` |
| OAuth Client secret | **delivered out-of-band (do NOT write here)** ☐ |
| Redirect URI registered exactly? | `.../oauth2/idpresponse` confirmed ☐ |

### Part B — Google Play
| Field | Value |
|-------|-------|
| Play developer account active | yes / pending verification |
| App created, package name | `__________` (per D1) |
| App signing cert SHA-1 | `__________` |
| App signing cert SHA-256 | `__________` |
| Internal testing track created | ☐ |

### Decisions
| ID | Answer |
|----|--------|
| D1 canonical package name | `__________` |
| D2 store languages | `__________` |
| D3 publishing pipeline | manual / Play Developer API |
| D4 account type | organization / individual |

---

When this is filled in and pushed back, we will: (9.0b) store the secret in Secrets Manager and
add the Google IdP to Cognito via CDK, verify the "Sign in with Google" button end-to-end; and
(publishing) reconcile the package name, generate the upload keystore, and produce a signed
`.aab` for the internal track.
