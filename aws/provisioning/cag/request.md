# CAG Account Provisioning — Request

**Date:** 2026-06-22
**Source:** user request via `/add-work` (Phase 7)

## Ask

Establish a nested member account under the Hylmar organization.

| Field | Value |
|-------|-------|
| Org (management acct) | `287773673380` (`hylmar_OA`), org `o-8i3fdvbxq7`, root `r-om7t` |
| Account name | **CAG** |
| Default region | **eu-central-1** |
| Admin users | `JiHy__hylmar__{first3}`, `MiHy__hylmar__{first3}` |
| Contact alias email | `aws-{first free digits}@hylmar.eu` (Google Workspace) |
| Spend control | 20 EUR / month |

## Resolved decisions

- **Mgmt access:** direct AWS CLI via local profile `JiHy__hylmar__287` (org admin, verified). No MCP bootstrap required.
- **Spend control:** alert-only AWS Budget (no enforced cap).
- **Admin users:** AdministratorAccess, console login (force password reset), access keys, no MFA enforcement.
- **OU placement:** org root (no OUs exist).
- **Root email (two-step):** the alias convention is `aws-{first 3 digits of account id}@hylmar.eu` (existing member 299 → `aws-299@hylmar.eu`). Because the id is unknown until creation, the account was created with the temporary, already-deliverable plus-address **`info+cag@hylmar.eu`**. After creation the id is `126697143436` → first 3 = **126** → target alias **`aws-126@hylmar.eu`**.

## Outcome

Account created: **`126697143436`** (first 3 = `126`).

- Users: `JiHy__hylmar__126`, `MiHy__hylmar__126`
- Target final root email: `aws-126@hylmar.eu`

## Owner follow-ups (out-of-band)

1. Create Google Workspace alias **`aws-126@hylmar.eu`** (deliverable to a monitored mailbox).
2. Change the CAG account **root email** from `info+cag@hylmar.eu` to `aws-126@hylmar.eu`
   (requires root sign-in: password reset to current root email → Account settings → update email → verify new address).
3. Register the **`aws-cag`** MCP connector in Claude config using key `mcp-126697143436` (Secrets Manager `cag/mcp/mcp-126697143436`), then restart.
4. (Optional) To make the budget exactly **20 EUR**: set the account's billing currency to EUR via root, then recreate the budget with `Unit=EUR` (currently 20 USD because EUR is not a supported budget unit for a USD-billed account).
