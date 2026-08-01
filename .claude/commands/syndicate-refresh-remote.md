---
description: Interactively sync git repos between local WSL and a configured remote dev box. Asks which repos + how to resolve conflicts on the fly. Handles nested sub-repos, .env files. Local-only.
---

<!--
  Centrally distributed by /distribute-defaults from syndicate-playbooks-examples.
  Project-specific additions go in .claude/local-overlays/<this-filename> as
  splice fragments (see /distribute-defaults for the overlay format).
  Direct edits to this file will be flagged on the next distribution.
-->

# /syndicate-refresh-remote

Bidirectional git-based sync between your local repos and a single configured remote box (the **syndicate-remote box** by default). **Interactive by design** — invoke `/syndicate-refresh-remote` with no arguments and the skill asks you what to do.

**Run from:** local WSL only. The skill refuses if invoked on the box itself.

---

## How this skill is wired (canonical home + companion runtime)

This skill is a **playbook default** distributed by `/distribute-defaults` from `~/syndicate-playbooks-examples/_project-template/.claude/commands/syndicate-refresh-remote.md` to every playbook project (i.e. any directory with both `progress.json` and `.claude/commands/`). Edits to the skill happen in the `_project-template/` canonical and then `/distribute-defaults` propagates them.

The skill itself is markdown-only. The deterministic backend is a CLI binary `syndicate-refresh-remote`, installed from `~/syndicate-remote/scripts/syndicate-refresh-remote.sh` via `~/syndicate-remote/scripts/install.sh` (one install per machine; binary lands in `~/.local/bin/`). It is configured per-machine from `~/.syndicate-remote-secrets/` (host, user, workspace, ssh_key).

So:
- **`syndicate-playbooks-examples`** owns the skill `.md` (the conversational front-end). Distributed to all projects.
- **`syndicate-remote`** owns the binary source + installer (the runtime). Installed per-machine.
- **`~/.syndicate-remote-secrets/`** owns the per-machine config. Never in any git repo.

> ### ⚠ Which file you edit, and which one you must not
>
> The host is described by a **device-named** file — `~/.syndicate-remote-secrets/<device>.json`
> (e.g. one named for the laptop or box it describes). **That is the file you edit.**
>
> `box.json` still exists on machines that were set up earlier, and the **binary still reads it by
> name**, but it is a **generated shim**: `~/syndicate-remote/scripts/install.sh` rewrites it from the
> device-named file. So:
>
> | | |
> |---|---|
> | **Edit** | `~/.syndicate-remote-secrets/<device>.json` — then run `~/syndicate-remote/scripts/install.sh` to regenerate the shim |
> | **Never edit** | `box.json` — the next install silently overwrites your change, and you will debug a config that is not being read |
>
> Why it is named after a **device** and not a role: `box.json` was named for one EC2 instance that no
> longer exists, and this estate has more than one host. A filename that names a machine has to be
> chased every time the machine changes; a file named for the device it describes does not.
>
> **This division is not cosmetic.** The skill `.md` you are reading is owned by
> `syndicate-playbooks-examples`; the binary that reads the shim is owned by `syndicate-remote`. If
> the two ever disagree about which file is authoritative, the **binary** decides what actually
> happens — so regenerate rather than hand-edit.

If you ever read this skill markdown in any project and the binary isn't installed, run `~/syndicate-remote/scripts/install.sh` once. If the binary IS installed but no config resolves, the binary will surface the exact stub to fill in.

---

## Invocation patterns

| You type | What happens |
|---|---|
| `/syndicate-refresh-remote` | Skill asks: which repos? (offers a multi-select of all top-level repos under `~/`); then asks about env-file sync + conflict policy + dry-run. |
| `/syndicate-refresh-remote syndicate-remote` | Uses that one repo; still asks about options if relevant. |
| `/syndicate-refresh-remote broadcasting-orchestration aps-brm-products-playbook` | Uses both repos. Skips the "which repos" prompt. |
| `/syndicate-refresh-remote all` | Sync **every** top-level repo under `~/` (confirms count first — typically ~60–70 repos). |
| `/syndicate-refresh-remote hyl-*` | Glob match; lists candidates and asks to confirm. |
| `/syndicate-refresh-remote --status` | **Drift dashboard mode** — informational only, never mutates. Surveys every **top-level** repo under `~/` on local and the box, prints a table showing per-repo LOCAL/BOX/DRIFT state. Project-agnostic: the answer is the same regardless of which playbook you invoke from. ⚠ **Depth-1 only — see below.** |
| `/syndicate-refresh-remote --status --json` | Same survey, JSON output on stdout (chatter goes to stderr). For tooling/agents that want to consume drift state. ⚠ Same depth-1 blindness. |
| `/syndicate-refresh-remote --status syndicate-remote app-foo` | Status of only the named repos. ⚠ Same depth-1 blindness. |

> **⚠ `--status` does NOT see nested sub-repos.** Both the local and box surveys glob one level
> (`<base>/*/`) and never recurse, so for a nested project the dashboard prints the **parent** as a
> single row — and an `in sync` parent tells you **nothing** about its children. A sub-repo can be 40
> commits diverged behind a green parent row.
>
> This is the one place the skill's own "handles nested sub-repos" claim does not hold: **only the sync
> path is nesting-aware** (it walks the tree with `find`); the dashboard is not. For a nested project,
> **do not trust `--status`** — verify via the sync path (a real or `--dry-run` run), or check each
> sub-repo manually.

When user input is ambiguous or incomplete, the skill **asks** rather than assumes.

---

## Step-by-step the skill follows

### Step 1 — Pre-flight (always run, never skipped)

1. **Am I the host?** This tool is local-only: run it *on* the machine it syncs *to* and it is
   meaningless. **Resolve by presence, not by a hostname pattern.** If `~/.syndicate-remote-secrets/`
   holds no host config, or the one it holds names this machine's own `workspace` as its target,
   abort with "this looks like the host itself; syndicate-refresh-remote is local-only".
   > An earlier version matched `hostname -s` against `ip-172-31-*`, the pattern AWS gives instances
   > it launches. On any host that is not an AWS instance that pattern matches **nothing**, so the
   > guard stops guarding without ever saying so. A check that silently becomes a no-op is worse than
   > no check, because the report still reads as though it ran.
2. **Binary check.** `command -v syndicate-refresh-remote` must succeed. If not, surface:
   > "syndicate-refresh-remote not installed. Run `~/syndicate-remote/scripts/install.sh` once on this machine, then retry."
3. **Config check.** A host config must resolve with non-empty `host`, `user`, `workspace`, `ssh_key`. If fields are missing, surface:
   > "Host config missing fields X, Y. Fix them in `~/.syndicate-remote-secrets/<device>.json` — the device-named file, **not** the generated `box.json` shim — then run `~/syndicate-remote/scripts/install.sh` to regenerate. If no config exists at all, running `syndicate-refresh-remote` prints the exact seed command with the full schema."
4. **SSH probe.** The binary's first pre-flight step does this. If it fails, ask the user what likely changed: the host is down, the network path is down, or the key file is missing — and offer the matching remediation from *Failure modes* below.

### Step 2 — Gather the repo list (if not provided as args)

Use `AskUserQuestion` (multi-select) populated by:
```bash
find ~ -mindepth 1 -maxdepth 1 -type d -not -name '.*' \
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
| If repos diverge between local and box, what to do? | Ask me per repo (default) / Keep local everywhere ⚠ auto-stashes / Keep box everywhere ⚠ auto-stashes / Abort the run |
| Dry-run? | No, do it for real (default) / Yes, dry-run |

> **⚠ Both "everywhere" options set `--keep-side`, which auto-stashes and never restores.** Do not
> present them as a plain divergence policy — they are also a **dirty-tree** policy. When the tree is
> dirty and `--keep-side` is set, the binary runs `git stash push -u` (uncommitted **and untracked**
> work) and **never pops it**. The work leaves the tree; it is recoverable only via `git stash list`.
> Worse, the stash fires **per sub-repo, before any divergence is even detected** — so one run over a
> nested project with N dirty repos leaves N separate orphaned stashes, one in each repo, and the
> final Summary never mentions them.
>
> **State this to the user before they choose.** If the tree is dirty, the correct remedy is
> **commit first**. With no `--keep-side`, the binary **refuses to touch the dirty repo**
> (`HALT_LOCAL_DIRTY`) and stops the run — **that halt is the safe default and the good path**, not an
> obstacle to route around. Prefer "Ask me per repo" and resolve dirt by committing.
>
> **But the halt is not a rewind.** The dirty check runs *per repo, inside the loop*, so every repo
> processed **before** the dirty one has already been fully synced — pushed to origin, cloned or
> fast-forwarded on the box, and its `.env*` files copied over. The binary says so itself:
> `halted after N ok`. So a halt means "stopped here", **not** "nothing happened". On a nested
> project the parent is processed first, so a dirty **child** halts a run in which the parent is
> already synced. Read the Summary to see what did land before reporting the run as a no-op.

### Step 4 — Invoke the binary

```bash
syndicate-refresh-remote \
  [--dry-run] \
  [--skip-env] \
  [--keep-side local|box] \
  <repo>...
```

> **⚠ `--keep-side` takes a value and must never be the final argument.** Always place it **before**
> the repo list, exactly as shown. Trailing it (`syndicate-refresh-remote repo --keep-side`) makes the
> binary's argument parser **hang forever** — it `shift 2`s on a single remaining argument, the shift
> fails, the argument count never decrements, and the parse loop spins. There is no error and no
> timeout; the command simply never returns.

Stream stdout to the user so they see live progress.

### Step 4a — Exit codes, as the binary **actually** emits them

Trust this table, not the binary's own header comment — the two disagree.

| Code | Emitted when | What it does **not** mean |
|---|---|---|
| `0` | Every repo returned OK — **or was silently skipped**. `SKIP_*` results (including `SKIP_NOT_GIT`, a repo name that is missing or not a git repo) take the empty arm and fall through to `exit 0`. | **Not** "everything synced". A typo'd repo name is a **silent success**: exit 0 with a `SKIP_NOT_GIT` row buried in the Summary. |
| `1` | Pre-flight / setup failure. | — |
| `2` | Any `HALT_*`: a real conflict, `HALT_LOCAL_DIRTY`, **or `HALT_UNKNOWN`** (which is what a no-origin repo produces). | **Not** necessarily a conflict — the skill must not assume divergence and open the Step 5 dialog without reading the actual status. |
| ~~`3`~~ | **Never.** The binary's header documents `3 local repo missing or not a git repo`, but no code path emits it — that condition returns `0`. | Do not test for `3`, and do not tell the user it exists. |

**Therefore: always read the Summary table rows — never conclude from the exit code alone.** Exit 0 with a `SKIP_*` row means that repo was *not* synced. Report skipped repos to the user by name.

### Step 5 — Handle interactive conflicts

If the binary exits 2 (HALT) and `--keep-side` wasn't pre-set — **first read the status: `HALT_CONFLICT` is a divergence, `HALT_LOCAL_DIRTY` means commit first, `HALT_UNKNOWN` usually means no `origin`.** Only a genuine divergence warrants the dialog below:

1. Parse the output for the offending repo + divergence info.
2. `AskUserQuestion`:
   - **Keep local** — `git reset --hard origin/<branch>` on the box. ⚠ **The binary never checks whether the box tree is dirty.** Box-only commits are reflog-recoverable, but **uncommitted and staged changes to tracked files on the box are destroyed — no stash, no reflog, unrecoverable.** Verify the box tree is clean first: `ssh <box> "git -C '<box_path>' status --porcelain"` (must be empty).
   - **Keep box** — push box-only commits to origin; then local pulls.
   - **Manual** — print the SSH command + diff and stop; user resolves themselves.
   - **Skip this repo** — leave it diverged, move on.
3. Re-invoke the binary for just that repo with the resolved flag (or skip).

### Step 6 — Per-repo + final summary

After all repos process, the binary prints:

```
=== Summary ===
repo                                               status               detail
----                                               ------               ------
<repo>                                             <result>             <detail>
...

total conflicts encountered: <N>
box host used: <ip>
box info cached at: /home/<user>/.syndicate-remote-secrets/box.json
```

### Step 6a — Flush the knowledge spool (only after the box is confirmed reachable)

`/update-progress` writes session knowledge to the **one** inbox at
`<workspace>/syndicate-playbook/knowledge_extraction/` on the box. When the box is unreachable it
spools to `~/.syndicate-knowledge-spool/` rather than losing the extraction or scattering it into the
current repo. This run has just proven the box reachable, so it is the natural flush point.

```bash
SPOOL="$HOME/.syndicate-knowledge-spool"
[ -d "$SPOOL" ] && [ -n "$(ls -A "$SPOOL" 2>/dev/null)" ] \
  && echo "SPOOL: $(ls -1 "$SPOOL" | wc -l) extraction(s) awaiting delivery"
```

If non-empty, `scp` each file to the box inbox using the same host-config values the binary just used,
and **remove only the files that arrive**. A file that fails to copy **stays spooled** — never deleted,
never assumed delivered. Report the result: `N flushed, M still spooled`.

Skip this step entirely on a dry-run, and on any run where the box was not reached.

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
- **`git clean`.** The binary never runs it, anywhere. This matters concretely: nested clones are typically **gitignored**, so a `git clean -xdf` would destroy them. It is not in the tool.
- **Touch AWS** beyond a single read-only call to find the box IP when prompted. No mutations.
- **Transfer secrets through git.** Only `.env*` files via scp (mode 600 on receiver).
- **Cross branches.** Only syncs the currently-checked-out branch on each side. If branches differ, it surfaces and asks.

### The exceptions — read this before trusting the list above

**`--keep-side` is not free, and it cuts on both sides.** Everything above is true *by default*; none
of it survives `--keep-side`. There are **two** distinct hazards, and the second is worse:

**1. Local — auto-stash, never restored (recoverable).** On a dirty local tree, `--keep-side` runs
`git stash push -u` (uncommitted **and untracked**) and never pops it — one stash per sub-repo, before
any divergence is detected. The work is **recoverable** via `git stash list`; it is not deleted.

**2. Box — `git reset --hard`, no dirty check at all (UNRECOVERABLE).** On a divergence with
`--keep-side local`, the binary runs `git reset --hard origin/<branch>` **on the box**. There is **no
box-side dirty check anywhere in the tool** — the only `git status --porcelain` it performs is on the
*local* tree. So:
>
> - Box-only **commits** are reflog-recoverable.
> - Box-only **uncommitted or staged changes to tracked files are destroyed** — no stash, no reflog,
>   **no recovery.** (Untracked files on the box survive `reset --hard`.)
>
> This also means the "Delete files" bullet above holds **only** without `--keep-side`: a
> `reset --hard` will discard box-side modifications to tracked paths that were never `git rm`'d.

**Before ever choosing "Keep local" on a diverged repo, check that the box tree is clean** — the tool
will not check for you:

```bash
ssh <box> "git -C '<box_path>' status --porcelain"   # must be empty
```

Read the list above as: *the tool is genuinely safe by default — no force-push, no `git clean`, no
deletions — and `--keep-side` is the single edge you must opt into knowingly, in both directions.*
The safe default is to pass no `--keep-side`, let a dirty repo halt, and **commit first — on whichever
side is dirty.**

---

## Companion runtime — `syndicate-refresh-remote` binary

Lives in `~/.local/bin/syndicate-refresh-remote` after running `~/syndicate-remote/scripts/install.sh` once per machine. Source: `~/syndicate-remote/scripts/syndicate-refresh-remote.sh`. Implements the per-repo loop (pre-flight, push, clone-or-pull, env-file scp, summary).

The skill above is the conversational front-end that:

1. Gathers inputs interactively when they're missing.
2. Invokes the binary with the right flags.
3. Handles conflict-resolution prompts when the binary halts.

**To update the binary:** edit `~/syndicate-remote/scripts/syndicate-refresh-remote.sh`, commit there, re-run `~/syndicate-remote/scripts/install.sh` (idempotent — just re-installs the latest).

**To update this skill markdown:** edit the canonical at `~/syndicate-playbooks-examples/_project-template/.claude/commands/syndicate-refresh-remote.md`, commit, then run `/distribute-defaults` from `syndicate-playbooks-examples`.

---

## Failure modes & rescue

| Symptom | Likely cause | Fix |
|---|---|---|
| `syndicate-refresh-remote: command not found` | Binary not installed on this machine | `~/syndicate-remote/scripts/install.sh` |
| `no remote configured at ~/.syndicate-remote-secrets/box.json` | First-time setup not done | Run install.sh; it creates a stub. Fill in the **device-named** file, then re-run install.sh to regenerate the shim the binary reads. |
| `ssh: connect to host … port 22: Operation timed out` | The host is down, or the network path to it is | Check the host is up. **Do NOT "fix" this by putting an IP in `host`** — see the ⚠ below. |
| `Connection refused` | Something is listening-but-refusing, or a firewall on the host rejects your source address | Check the host's own firewall (e.g. `ufw status`) and that sshd is running. This is a host-side answer, not a config edit. |
| `Permission denied (publickey)` | Key not in `~/.ssh/`, wrong mode, or not authorised on the host | Verify the `ssh_key` value in the **device-named** config and the file's mode (must be 0400 or 0600), and that the matching public key is in the host's `~/.ssh/authorized_keys`. |
| `fatal: not a git repository` on box | Repo never cloned on box | Binary auto-clones; if it fails, check `gh auth status` on the box. |
| `! [rejected] main -> main (non-fast-forward)` | Local and box diverged | Skill's conflict-resolution dialog handles this. |
| `unexpected status:  — treating as failure` (blank status), exit 2 | **Repo has no `origin` remote.** The binary does **not** skip it — `git fetch origin` fails, execution continues, and the empty box status falls through to `HALT_UNKNOWN` → **exit 2**, which is the same code as a real conflict. Misleading twice over: it prints `local synced with origin` first, for a repo that has no origin. | Add an origin, then re-run. Do not hunt for a conflict — there isn't one. |
| Work disappeared from the **local** tree after a `--keep-side` run | `git stash push -u` fired on a dirty tree and was never popped (see the ⚠ under Step 3). One stash **per sub-repo**. | `git stash list` in the affected repo (and in **each** sub-repo of a nested project), then `git stash pop`. Nothing is lost — it is stashed, not deleted. |
| Work disappeared from the **box** tree after `--keep-side local` on a diverged repo | `git reset --hard origin/<branch>` ran on the box. **There is no box-side dirty check in the tool at all.** | Box-only **commits**: recover via `git reflog` on the box. Box-only **uncommitted/staged changes to tracked files**: **unrecoverable** — no stash was taken. Untracked files survive. Check `ssh <box> "git -C '<box_path>' status --porcelain"` *before* choosing this, every time. |
| A typo'd or never-cloned repo name reports **success** | `SKIP_NOT_GIT` exits **0**. A no-op is indistinguishable from a sync. | Read the Summary table rows — do not trust the exit code alone. Check the repo name spelling. |
| Command hangs forever, no output, no timeout | `--keep-side` was passed as the **final** argument — the parser spins (see the ⚠ under Step 4). | Ctrl-C. Re-run with `--keep-side` **before** the repo list. |

> ### ⚠ Never put a bare IP in `host` — it is the failure that looks like success
>
> `host` may be an **ssh_config alias**, not an address. When it is, the `Host` block it names carries
> the routing (a `ProxyCommand`, a jump host, a tunnel) that makes the machine reachable from
> anywhere. Replace the alias with the IP and ssh **bypasses that block entirely**: the connection
> falls back to whatever direct path happens to exist, which on a home network is the LAN.
>
> The result is a machine that works where you tested it and **nowhere else** — and it reports
> success the whole time. This is why a connection timeout is diagnosed on the host, not repaired by
> editing `host`. If you genuinely need the direct address (because the routing itself is what is
> broken), the device-named config carries it separately as `host_lan`; use that deliberately, and
> put it back afterwards.

---

## Cross-references

- **Skill canonical:** `~/syndicate-playbooks-examples/_project-template/.claude/commands/syndicate-refresh-remote.md`
- **Distribution:** `~/syndicate-playbooks-examples/.claude/commands/distribute-defaults.md` (run `/distribute-defaults` to propagate)
- **Binary source:** `~/syndicate-remote/scripts/syndicate-refresh-remote.sh`
- **Binary installer:** `~/syndicate-remote/scripts/install.sh`
- **Binary installed at:** `~/.local/bin/syndicate-refresh-remote`
- **Per-machine config:** `~/.syndicate-remote-secrets/<device>.json`, mode 0600, never in any git repo. The binary reads the generated `box.json` shim; `install.sh` rewrites it from the device-named file. **Edit the device-named file.**
- **Host-deployment project:** `~/syndicate-remote/` (`README.md` is the maintainers' entry point; it provisions and maintains the host this skill targets)
