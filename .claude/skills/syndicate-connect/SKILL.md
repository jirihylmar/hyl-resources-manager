---
name: syndicate-connect
description: Give this machine a working route to the syndicate box from a single input — the private key — so every project on it can deliver knowledge extractions, regardless of where the project lives on disk. Installs the key with correct permissions, proves the connection, then records ~/.syndicate-remote-secrets/box.json. Invoke when a host reports NO ROUTE or spool, when setting up a new or foreign machine, or when the box address changed.
---

# syndicate-connect

One command, one input: the PEM. Run once per **machine**, never per project.

## The property this guarantees

> **Where a project lives on disk is irrelevant to whether it can report.**

`/update-progress` § 11.0 resolves the knowledge route from `$HOME` alone. So a project under
`/mnt/c/Users/...`, one under `~/work/...`, and one on a network path all use the same machine-level
config. Setting it up per project would be wrong; there is nothing per project to set up.

## Procedure

The operator hands over two things separately: **this command** (which carries the box address) and
**the PEM**. On the target machine, inside WSL or any Linux shell:

```bash
bash .claude/skills/syndicate-connect/connect.sh --host <box-address>
# paste the whole -----BEGIN ... END----- block, then press Ctrl-D
```

Or from a file:

```bash
bash .claude/skills/syndicate-connect/connect.sh --host <box-address> --pem ~/Downloads/box-key.pem
```

| Option | Default | When to change it |
|---|---|---|
| `--host` | none — **required** | always: the box's public address changes when it is stopped and started |
| `--pem` | read from stdin | you already have the key in a file |
| `--user` | `ubuntu` | a box with a different login |
| `--workspace` | `/home/<user>` | a box whose repos live elsewhere |
| `--key-name` | `syndicate-box` | keeping several box keys side by side |

**Why the address is not baked in.** It is volatile — one stop/start reassigns it — and a stale
value shipped to every project would fail on every machine at once while looking like a key problem.
Canonical carries no name that is true on only one machine or one moment; that is the same rule that
keeps hostnames, profile names and absolute paths out of these files.

## What it does, in order

1. **Refuses to run if `$HOME` is on a Windows mount** (`/mnt/...`). Such a mount reports `0777` for
   every file and `chmod` is a no-op there, so ssh would reject the key whatever the script did.
2. **Reads the key**, strips `\r`. A key pasted through a Windows clipboard arrives CRLF-terminated
   and ssh rejects it as *"invalid format"* — an error that names the format and never the line
   endings, which is exactly why this is done for you.
3. **Installs it** at `~/.ssh/<key-name>.pem`, mode 600, backing up any different key already there.
4. **Proves the connection** — `ssh … true`, batch mode, 15s timeout.
5. **Only then writes** `~/.syndicate-remote-secrets/box.json`, mode 600.
6. **Verifies the inbox** exists and is writable — the thing the config is actually for.
7. **Resolves the route** exactly as § 11.0 does and prints it. Must be `remote`.

**Step 4 before step 5 is the whole design.** A config recording an unproven route flips this host
from `spool` (loud, recoverable, nothing lost) to `remote` (confident, and wrong at the moment it
matters). On any failure, nothing is recorded and the host keeps failing loudly.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | route works and is recorded |
| `1` | usage error, or an environment that cannot work (`$HOME` on a Windows mount, no `ssh`, no `--host`) |
| `2` | what was pasted is not a private key — a `.pub` or a certificate will not do |
| `3` | box unreachable with this key: stopped, address changed, wrong key, or wrong `--user`. **Nothing written.** |
| `4` | key and box fine, but the inbox is missing or read-only — box.json is correct; the box needs attention |

## Afterwards

Nothing else to do. `/update-progress` § 11 finds `box.json` on its own and delivers by `scp`; any
extractions already sitting in `~/.syndicate-knowledge-spool/` flush on the next run. Re-run this
script with the new `--host` whenever the box is stopped and started.

## Related

- `/update-progress` § 11.0 — the resolver this satisfies (`direct` / `remote` / `spool`).
- `/setup` § 5b, `/setup-workflow-only` § 4.4 — the prerequisite check that sends you here.
