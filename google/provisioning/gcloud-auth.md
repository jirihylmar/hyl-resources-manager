# gcloud CLI — install & auth pattern (reusable)

Reusable setup for executing Google Cloud provisioning (Phase 6 and future external
Google requests) from this WSL2 environment. Parameterized by **owner Google account** —
swap `info@hylmar.eu` for whichever account owns the target project.

## Environment

- Host: WSL2, Ubuntu 24.04, x86_64
- `sudo` is **not** passwordless here → system package install (`apt`) is not used.
- gcloud installed via the **no-root tarball** into `~/google-cloud-sdk`.

## Install (no root)

```bash
curl -fsSL -o /tmp/gcloud-cli.tar.gz \
  "https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz"
cd ~ && tar -xzf /tmp/gcloud-cli.tar.gz
./google-cloud-sdk/install.sh --quiet --usage-reporting=false --path-update=true --command-completion=true
```

- Binary: `~/google-cloud-sdk/bin/gcloud` (version 571.0.0 at install).
- `install.sh` appends PATH to `~/.bashrc` (backed up to `~/.bashrc.backup`). A **new**
  shell picks it up; in a non-login shell, prepend manually:

```bash
export PATH="$HOME/google-cloud-sdk/bin:$PATH"
```

## Authenticate an owner account

Login is **interactive** — the agent's non-interactive shell cannot complete it. Run it in a
real terminal (in Claude Code, prefix with `!`):

```bash
~/google-cloud-sdk/bin/gcloud auth login <owner@account> --no-launch-browser --update-adc
```

1. Prints an `accounts.google.com/o/oauth2/auth?...` URL.
2. Open it in the **Chrome profile signed in as that account** (info@hylmar.eu = Profile 6),
   choose the matching account on the consent screen.
3. Copy the verification code Google shows, paste at `Enter authorization code:`.

`--update-adc` sets **both** user credentials (for `gcloud` commands) and
**Application Default Credentials** (for SDK/API calls) in one login.

## Verify

```bash
gcloud auth list                       # owner account shown ACTIVE (*)
gcloud config get-value account        # == owner@account
gcloud auth application-default print-access-token >/dev/null && echo "ADC OK"
gcloud projects list                   # current projects (empty = greenfield)
```

## Credential locations

| Item | Path |
|------|------|
| User credentials | `~/.config/gcloud/` (legacy creds db) |
| Application Default Credentials | `~/.config/gcloud/application_default_credentials.json` (mode 600) |

> **Do not commit** anything under `~/.config/gcloud/`. These are live credentials.

## Switching accounts later

```bash
gcloud auth login <other@account> --no-launch-browser --update-adc
gcloud config set account <other@account>
```

## State recorded for this project (2026-06-04)

- Owner account authenticated: **info@hylmar.eu** (ACTIVE), ADC present and working.
- `gcloud projects list` → **0 projects** (greenfield, as expected before Task 6.3).
