---
description: Interactively sync git repos between local WSL and a configured remote dev box. Asks which repos + how to resolve conflicts on the fly. Handles nested sub-repos, .env files. Local-only.
---

<!--
  Centrally distributed by /distribute-defaults from syndicate-playbooks-examples.
  Project-specific additions go in .claude/local-overlays/<this-filename> as
  splice fragments (see /distribute-defaults for the overlay format).
  Direct edits to this file will be flagged on the next distribution.
-->

# /refresh-remote

Bidirectional git-based sync between your local repos and a single configured remote box (the **syndicate-remote box** by default). **Interactive by design** — invoke `/refresh-remote` with no arguments and the skill asks you what to do.

**Run from:** local WSL only. The skill refuses if invoked on the box itself.

---

## How this skill is wired (canonical home + companion runtime)

This skill is a **playbook default** distributed by `/distribute-defaults` from `~/syndicate-playbooks-examples/_project-template/.claude/commands/refresh-remote.md` to every playbook project (i.e. any directory with both `progress.json` and `.claude/commands/`). Edits to the skill happen in the `_project-template/` canonical and then `/distribute-defaults` propagates them.

The skill itself is markdown-only. The deterministic backend is a CLI binary `syndicate-refresh-remote`, installed from `~/syndicate-remote/scripts/refresh-remote.sh` via `~/syndicate-remote/scripts/install.sh` (one install per machine; binary lands in `~/.local/bin/`). The binary is configured per-machine by `~/.syndicate-remote-secrets/box.json` (host, user, workspace, ssh_key).

So:
- **`syndicate-playbooks-examples`** owns the skill `.md` (the conversational front-end). Distributed to all projects.
- **`syndicate-remote`** owns the binary source + installer (the runtime). Installed per-machine.
- **`~/.syndicate-remote-secrets/box.json`** owns the per-machine config.

If you ever read this skill markdown in any project and the binary isn't installed, run `~/syndicate-remote/scripts/install.sh` once. If the binary IS installed but `box.json` is missing/empty, the binary will surface the exact stub to fill in.

---

## Invocation patterns

| You type | What happens |
|---|---|
| `/refresh-remote` | Skill asks: which repos? (offers a multi-select of all top-level repos under `~/`); then asks about env-file sync + conflict policy + dry-run. |
| `/refresh-remote syndicate-remote` | Uses that one repo; still asks about options if relevant. |
| `/refresh-remote broadcasting-orchestration aps-brm-products-playbook` | Uses both repos. Skips the "which repos" prompt. |
| `/refresh-remote all` | Sync **every** top-level repo under `~/` (confirms count first — typically ~60–70 repos). |
| `/refresh-remote hyl-*` | Glob match; lists candidates and asks to confirm. |

When user input is ambiguous or incomplete, the skill **asks** rather than assumes.

---

## Step-by-step the skill follows

### Step 1 — Pre-flight (always run, never skipped)

1. **Hostname check.** If `hostname -s` matches the box's pattern (typically `ip-172-31-*` for AWS-launched boxes), abort with "this is the box; refresh-remote is local-only". The box-side hostname is one of the few things hardcoded.
2. **Binary check.** `command -v syndicate-refresh-remote` must succeed. If not, surface:
   > "syndicate-refresh-remote not installed. Run `~/syndicate-remote/scripts/install.sh` once on this machine, then retry."
3. **Config check.** `~/.syndicate-remote-secrets/box.json` must exist and have non-empty `host`, `user`, `workspace`, `ssh_key`. If missing fields, surface:
   > "box.json missing fields X, Y. Resolve current values and update the file; the binary's first `--help` invocation prints the schema."
4. **SSH probe.** The binary's first pre-flight step does this. If it fails, ask the user what likely changed: box IP / SG / box stopped / key file missing — and offer the matching remediation.

### Step 2 — Gather the repo list (if not provided as args)

Use `AskUserQuestion` (multi-select) populated by:
```bash
find ~ -maxdepth 1 -type d -name '.git' \! -path "${HOME}/.*" -prune -o -maxdepth 1 -type d -print \
  | xargs -I {} sh -c 'test -d "{}/.git" && basename "{}"' \
  | sort
```
Highlight "main" repos first (anything matching `*orchestration*`, `*playbook*`, `syndicate-*`, `*hub440*`, plus any repo already present on the box at `<workspace>/`).

If user picks "all", confirm with a count first: "N repos, this will take ~5–10 min. Continue?".

### Step 3 — Gather options (if not provided as args)

Use `AskUserQuestion`:

| Question | Options |
|---|---|
| Sync `.env*` files too? | Yes (default) / No |
| If repos diverge between local and box, what to do? | Ask me per repo (default) / Keep local everywhere / Keep box everywhere / Abort the run |
| Dry-run? | No, do it for real (default) / Yes, dry-run |

### Step 4 — Invoke the binary

```bash
syndicate-refresh-remote \
  [--dry-run] \
  [--skip-env] \
  [--keep-side local|box] \
  <repo>...
```

Stream stdout to the user so they see live progress.

### Step 5 — Handle interactive conflicts

If the binary exits 2 (HALT — conflict) and `--keep-side` wasn't pre-set:

1. Parse the output for the offending repo + divergence info.
2. `AskUserQuestion`:
   - **Keep local** — `git reset --hard origin/<branch>` on the box (loses box-only commits).
   - **Keep box** — push box-only commits to origin; then local pulls.
   - **Manual** — print the SSH command + diff and stop; user resolves themselves.
   - **Skip this repo** — leave it diverged, move on.
3. Re-invoke the binary for just that repo with the resolved flag (or skip).

### Step 6 — Per-repo + final summary

After all repos process, the binary prints:

```
=== refresh-remote summary ===
repos:   N total, M synced cleanly, K had conflicts (resolved: ..., skipped: ...)
env:     E files transferred
host:    <ip> (saved to ~/.syndicate-remote-secrets/box.json)
```

Then ask: "Anything else to sync?" (no / yes — back to step 2).

---

## Inputs the skill should be robust to

- **No arguments at all** → step 2 multi-select.
- **One repo by name** (`syndicate-remote`) → use it directly.
- **Multiple repo names** → use them all.
- **`all`** → all top-level repos under `~/` (confirm count first).
- **A subdir-name that's actually a nested repo** (e.g. `broadcast-infrastructure` inside `broadcasting-orchestration`) → resolve to the parent and tell user.
- **A glob pattern** (`hyl-*`) → expand, list matches, confirm.
- **A typo / non-existent repo** → list close matches, ask which one they meant.

Always confirm before executing if interpretation is non-obvious.

---

## What the skill never does

- **Run on the box.** First step verifies hostname.
- **Force-push.** "Keep box" pushes box-only commits the normal way — not `--force`.
- **Delete files.** Even if a file is locally removed, the skill doesn't touch the same path on the box unless `git rm` was committed.
- **Touch AWS** beyond a single read-only call to find the box IP when prompted. No mutations.
- **Transfer secrets through git.** Only `.env*` files via scp (mode 600 on receiver).
- **Cross branches.** Only syncs the currently-checked-out branch on each side. If branches differ, it surfaces and asks.

---

## Companion runtime — `syndicate-refresh-remote` binary

Lives in `~/.local/bin/syndicate-refresh-remote` after running `~/syndicate-remote/scripts/install.sh` once per machine. Source: `~/syndicate-remote/scripts/refresh-remote.sh`. Implements the per-repo loop (pre-flight, push, clone-or-pull, env-file scp, summary).

The skill above is the conversational front-end that:

1. Gathers inputs interactively when they're missing.
2. Invokes the binary with the right flags.
3. Handles conflict-resolution prompts when the binary halts.

**To update the binary:** edit `~/syndicate-remote/scripts/refresh-remote.sh`, commit there, re-run `~/syndicate-remote/scripts/install.sh` (idempotent — just re-installs the latest).

**To update this skill markdown:** edit the canonical at `~/syndicate-playbooks-examples/_project-template/.claude/commands/refresh-remote.md`, commit, then run `/distribute-defaults` from `syndicate-playbooks-examples`.

---

## Failure modes & rescue

| Symptom | Likely cause | Fix |
|---|---|---|
| `syndicate-refresh-remote: command not found` | Binary not installed on this machine | `~/syndicate-remote/scripts/install.sh` |
| `no remote configured at ~/.syndicate-remote-secrets/box.json` | First-time setup not done | Run install.sh; it creates a stub. Fill in `host` (and other fields if defaults don't match). |
| `ssh: connect to host … port 22: Operation timed out` | Box public IP changed (stop/start) | Update `host` in `~/.syndicate-remote-secrets/box.json` with the new IP. |
| `Connection refused` | Your home IP changed; SG blocks you | `aws ec2 authorize-security-group-ingress --group-id sg-... --protocol tcp --port 22 --cidr <new-ip>/32` (use the admin profile for the deployment account). |
| `Permission denied (publickey)` | `.pem` not in `~/.ssh/` or wrong mode | Verify `ssh_key` value in `box.json` and the file's mode (must be 0400 or 0600). |
| `fatal: not a git repository` on box | Repo never cloned on box | Binary auto-clones; if it fails, check `gh auth status` on the box. |
| `! [rejected] main -> main (non-fast-forward)` | Local and box diverged | Skill's conflict-resolution dialog handles this. |
| Repo has no `origin` remote | Local-only repo never pushed | Binary reports + skips. Add an origin first. |

---

## Cross-references

- **Skill canonical:** `~/syndicate-playbooks-examples/_project-template/.claude/commands/refresh-remote.md`
- **Distribution:** `~/syndicate-playbooks-examples/.claude/commands/distribute-defaults.md` (run `/distribute-defaults` to propagate)
- **Binary source:** `~/syndicate-remote/scripts/refresh-remote.sh`
- **Binary installer:** `~/syndicate-remote/scripts/install.sh`
- **Binary installed at:** `~/.local/bin/syndicate-refresh-remote`
- **Per-machine config:** `~/.syndicate-remote-secrets/box.json` (mode 0600, never in any git repo)
- **Box-deployment project:** `~/syndicate-remote/` (`README.md` is the maintainers' entry point; provisions the EC2 box that this skill targets)
