# Google Cloud + Play provisioning — request & deliverables schema

Reusable contract for "provision Google Cloud OAuth (+ optionally Google Play) for product X
under owner account Y". The first instance is **Audory** (`audory/`). Future requests add a new
`<product>/` folder and reuse this schema unchanged.

## Folder convention

```
google/provisioning/
  gcloud-auth.md                 # install + auth pattern (owner-account agnostic)
  schema.md                      # this file
  _template.deliverables.json    # blank deliverables to copy per product
  <product>/
    request.md                   # the incoming request (copy of input/*.md)
    oauth.json                   # Part A deliverables (filled as work proceeds)
    play.json                    # Part B deliverables
    decisions.json               # owner decisions D1..Dn
    deliverables.md              # human-readable hand-back doc returned to requester
```

A request may be **Part A only** (OAuth) or **Part A + Part B** (OAuth + Play). Part B fields
are optional/`null` when not requested.

## Input request — required fields

A request must supply (or the doc must let us derive):

| Field | Meaning | Example (Audory) |
|-------|---------|------------------|
| `product` | brand / app name | `Audory` |
| `owner_google_account` | Google account that owns the GCP project / Play account | `info@hylmar.eu` |
| `gcp_project.name` | desired project name | `audory` |
| `environments[]` | one per Cognito env; each needs the redirect URI | see below |
| `oauth.scopes[]` | requested scopes (non-sensitive avoids Google review) | `openid`, `email`, `profile` |
| `consent.user_type` | `external` / `internal` | `external` |
| `consent.support_email` | shown on consent screen | `projekt1@hub440.cz` |
| `consent.authorized_domains[]` | domains in redirect URIs | `amazoncognito.com` |
| `android.package_name` | Play applicationId (immutable once created) | `cz.audory.app` |

### environments[] (per Cognito environment)

```json
{
  "env": "dev",
  "cognito_hosted_ui_domain": "https://audory-dev-030062527147.auth.eu-west-1.amazoncognito.com",
  "redirect_uri": "https://audory-dev-030062527147.auth.eu-west-1.amazoncognito.com/oauth2/idpresponse",
  "user_pool_id": "eu-west-1_RJzbzo83A",
  "aws_account_id": "030062527147",
  "region": "eu-west-1"
}
```

The OAuth Web client's **Authorized redirect URIs** = every `environments[].redirect_uri`;
**Authorized JavaScript origins** = every `environments[].cognito_hosted_ui_domain`. Build the
client so more environments can be appended later without recreating it.

## Output — `oauth.json` (Part A deliverables)

```json
{
  "product": "string",
  "owner_google_account": "string",
  "gcp_project_id": "string|null",
  "consent_screen": {
    "user_type": "external|internal",
    "status": "testing|in_production|null",
    "app_name": "string",
    "support_email": "string",
    "authorized_domains": ["string"],
    "scopes": ["openid","email","profile"],
    "test_users": ["string"]
  },
  "web_client": {
    "name": "string",
    "client_id": "string|null",
    "client_secret": "OUT_OF_BAND — never stored in git",
    "secret_destination": "AWS Secrets Manager (account/region/name) | password-manager-share",
    "javascript_origins": ["string"],
    "redirect_uris": ["string"]
  },
  "status": "pending|in_progress|delivered",
  "notes": "string"
}
```

## Output — `play.json` (Part B deliverables, optional)

```json
{
  "product": "string",
  "developer_account": "active|pending_verification|none",
  "account_type": "organization|individual|null",
  "app": {
    "name": "string",
    "package_name": "string|null",
    "default_language": "string|null",
    "additional_languages": ["string"],
    "free_or_paid": "free|paid"
  },
  "app_signing": {
    "play_app_signing": true,
    "sha1": "string|null",
    "sha256": "string|null"
  },
  "android_auto": { "declared": false, "notes": "media app review requirements" },
  "tracks": { "internal_testing": false, "testers": ["string"] },
  "data_safety": { "collects": ["email","account_id","playback_state"], "sells_data": false },
  "status": "pending|in_progress|pending_verification|delivered",
  "notes": "string"
}
```

## Output — `decisions.json` (owner decisions)

```json
{
  "decisions": [
    { "id": "D1", "question": "string", "answer": "string|null", "answered": false }
  ]
}
```

## Secret handling (hard rule)

- OAuth **client secret** and any **keystore / service-account JSON** are confidential.
- **Never** write secrets into any file under this repo. `oauth.json` records `client_id` only;
  the secret field is a literal placeholder pointing at the out-of-band destination.
- Deliver secrets via the owner's password manager share / encrypted message; the consuming
  side stores them in AWS Secrets Manager.

## Execution capability notes (from Task 6.1 reality check)

- `gcloud` reliably handles: project create, billing link, **API enablement**, service accounts.
- Creating a **general "Web application" OAuth client** + the **OAuth consent screen** is largely
  **console-only** (gcloud/IAP APIs cover IAP-specific clients, not generic web clients). Plan for
  console steps under the owner Chrome profile; record the resulting `client_id` here.
- **Google Play Console** has **no CLI** for account/app setup; the Play Developer API only covers
  release management *after* the account + app exist. Part B is manual; this repo tracks deliverables.
