# Part A — Google OAuth for Audory: Console steps (info@hylmar.eu)

**Why console:** the IAP OAuth Admin APIs (only programmatic path) were permanently shut down
2026-03-19, and `android-auto-audory` is a new project — so the consent screen + Web client must
be created in the Console. ~5 minutes.

**Sign in as `info@hylmar.eu` (Chrome Profile 6). Confirm the project picker shows
`android-auto-audory` (number 360321714436) before each step.**

Copy values **exactly** — they must match AWS Cognito.

---

## Step 1 — OAuth consent screen / "Google Auth Platform" → Branding + Audience

Open: https://console.cloud.google.com/auth/branding?project=android-auto-audory
(older UI: **APIs & Services → OAuth consent screen**)

- **Audience / User type:** **External**
- **App name:** `Audory`
- **User support email:** `projekt1@hub440.cz`
- **App logo:** skip for now (optional)
- **Authorized domains:** add `amazoncognito.com`
  *(optional: also add `hylmar.eu`)*
- **Developer contact email:** `projekt1@hub440.cz`
- **Save.** Leave publishing status as **Testing** (fine for Cognito; no verification needed).

### Scopes
Open **Data Access** (or **Scopes** in older UI) and add the three non-sensitive scopes:
- `openid`
- `.../auth/userinfo.email`
- `.../auth/userinfo.profile`

Save. (No sensitive/restricted scopes → **no Google verification required**.)

### Test users
Open **Audience** (or **Test users**) → **Add users** → `projekt1@hub440.cz` → Save.

---

## Step 2 — Create the OAuth Web client

Open: https://console.cloud.google.com/auth/clients?project=android-auto-audory
(older UI: **APIs & Services → Credentials → Create credentials → OAuth client ID**)

- **Create client / Create credentials → OAuth client ID**
- **Application type:** **Web application**
- **Name:** `android-auto-cognito-dev`
- **Authorized JavaScript origins → Add URI:**
  ```
  https://audory-dev-030062527147.auth.eu-west-1.amazoncognito.com
  ```
- **Authorized redirect URIs → Add URI:**
  ```
  https://audory-dev-030062527147.auth.eu-west-1.amazoncognito.com/oauth2/idpresponse
  ```
- **Create.**

Google shows a **Client ID** and a **Client secret**.

---

## Step 3 — Return the values

- **Client ID** (NOT secret) → paste it back here in chat; I'll write it into `oauth.json`.
- **Client secret** → **confidential. Do NOT paste into chat or any repo file.** Keep it for the
  backend agent to put into AWS Secrets Manager (vsb-030) during Audory task 9.0b. Deliver via
  password-manager share / encrypted message only.

> Reminder: the secret never goes in git. `oauth.json` records the Client ID only.

---

## Notes
- Adding **staging/prod** later = edit this same client and append more
  `.../oauth2/idpresponse` redirect URIs + origins. No new client needed.
- D1 (package name) does **not** affect this client — that redirect is the HTTPS `idpresponse`
  URL, unrelated to the Android custom scheme.
