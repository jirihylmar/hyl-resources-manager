---
name: syndicate-connect
description: Give this machine a working route to the knowledge inbox from two inputs — the ingest URL and a per-host token — so every project on it can deliver knowledge extractions by HTTPS, regardless of where the project lives on disk. Proves the token against the endpoint, then records ~/.syndicate-remote-secrets/ingest.json. Invoke when a host reports NO ROUTE or spool, or when setting up a new or foreign machine.
---

# syndicate-connect

One command, two inputs: the ingest URL and a per-host token. Run once per **machine**, never per
project. Delivery is by HTTPS POST to the ingest endpoint — no ssh key, no `box.json`, no firewall.

## The property this guarantees

> **Where a project lives on disk is irrelevant to whether it can report.**

`/update-progress` § 11.0 resolves the route from `$HOME` alone. A project under `/mnt/c/Users/...`,
one under `~/work/...`, and one on a network path all use the same machine-level `ingest.json`.

## Procedure

The operator hands over the **URL** and a **per-host token** (out of band, as the PEM used to be):

```bash
bash .claude/skills/syndicate-connect/connect.sh --url <ingest url> --token <host token>
```

Or paste the token on stdin (omit `--token`, paste, `Ctrl-D`). That is all — outbound HTTPS is the
only requirement, so it works behind any firewall.

## What it does, in order

1. **Refuses `$HOME` on a Windows mount** (`/mnt/...`) — the token file would be world-readable there.
2. **Refuses sudo/root** — `ingest.json` would land in `/root`, where the session resolver never looks.
3. **Proves the token before writing anything.** It POSTs an *empty body*: the endpoint checks auth
   first, so `401` means the token is bad and `400` (empty body refused) means the token is **good** —
   this validates the credential without delivering a file. `000`/`5xx` means the endpoint is
   unreachable. On any failure it writes nothing and the host stays on `spool` (loud), never `ingest`
   (confident, and wrong).
4. **Writes** `~/.syndicate-remote-secrets/ingest.json` = `{url, token}`, mode 600.
5. **Resolves the route** as § 11.0 does and prints it. Must be `ingest`.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | route proven and recorded |
| `1` | usage error, or an environment that cannot work (`$HOME` on a Windows mount, sudo, no `curl`, no/`http` URL) |
| `3` | token rejected, or endpoint unreachable — **nothing written** |

## If you are an independent / third-party remote

You are one if this machine **cloned the examples itself** and is not the operator's workstation or
the box. Two facts follow, and an agent here should act on them without waiting for chat:

1. **`/distribute-defaults` never reaches you** — updates do not arrive on their own. If your command
   or skill files look older than the operator's, that is expected, not broken.
2. **You refresh yourself** by running the engine locally from your examples clone (same engine the
   operator uses, just run by you):
   ```bash
   cd ~/syndicate-playbooks-examples && git pull
   bash ~/syndicate-playbooks-examples/scripts/distribute-defaults.sh --apply --commit
   ```
   This updates every project under `$HOME` (overlay-aware, scoped commits). Re-running
   `/setup-workflow-only` does **not** refresh commands — this engine run does. Full lifecycle:
   README § *Running on an independent / third-party remote*.

If this host is stuck on a stale delivery route (e.g. it still tries `scp`/`box.json` and spools),
the fix is that refresh — it pulls in the current `/update-progress` that knows the `ingest` route —
followed by the `connect.sh` command above.

## What retired with the SSH model

`box.json`, the PEM, the ssh key install, the security-group `/32` allowlisting, and the `/mnt/c`
key-permission trap are all gone — there is no key to place. The token is a *delivery* credential to
*one* endpoint that only appends a review-pending file to the inbox; it grants no shell.

## Related

- `/update-progress` § 11.0 — the resolver this satisfies (`direct` / `ingest` / `spool`).
- `docs/knowledge-ingest-lambda-instruction.md` — the endpoint's architecture and security posture.
