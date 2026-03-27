# Google Services Management

## Skill Outputs

| Skill | Output | Description |
|-------|--------|-------------|
| `google-check-accounts` | `accounts.json` | 7 Google accounts with org, purpose, Chrome profile mapping |
| `google-check-gcp-projects` | `gcp-projects.json` | 7 GCP projects with 4 SAs + 4 OAuth clients (all verified) |
| `google-check-integrations` | `integrations.json` | 6 Google↔AWS integration points |

## Summary

- **7 Google accounts** across 5 orgs (Hylmar, D4M, VSB, Goldsport, BrainMarket + Personal)
- **7 GCP projects** with active credentials
- **4 Service Accounts** (d4m-goo-master ×2, vsb-bh6-gdr, goldsport-default-project)
- **4 OAuth Clients** (macro-griffin, red-formula, default-project-hub440, quickstart)
- **All 8 credential files verified present** on local filesystem

## Integration Status

| Integration | Google API | AWS Account | Status |
|-------------|-----------|-------------|--------|
| goldsport-booking-to-sheets | Sheets | vsb-565 | active |
| goldsport-video-feedback | Drive | vsb-565 | needs investigation |
| bmpss-batch-filler-sheets | Sheets | vsb-565 | needs investigation |
| d4m-gdrive-automation | Drive | d4m-975 | active |
| vsb-gdrive-access | Drive | vsb-565 | active |
| hub440-bills-processing | Drive/Gmail | hylmar | active |

---

*Last updated: 2026-03-27*
