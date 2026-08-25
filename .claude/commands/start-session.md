---
description: Initialize context for a new Claude Code session (project)
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - AskUserQuestion
  - mcp__aws-*__call_aws
---

<!--
  Centrally distributed by /distribute-defaults from syndicate-playbooks-examples.
  Project-specific additions go in .claude/local-overlays/<this-filename> as
  splice fragments (see /distribute-defaults for the overlay format).
  Direct edits to this file will be flagged on the next distribution.
-->

# Start Session

Initialize context and verify previous work before starting new tasks.

---

## Multi-Agent Discipline

When multiple agents work in the same repo simultaneously, each agent is assigned a specific task by the user/orchestrator. Follow these rules to avoid conflicts.

### Task Assignment

- **Your task comes from the user, not from `current_task` in progress.json** — in multi-agent setups, `current_task` may belong to another agent
- If the user specifies a task (e.g., "work on 2.3"), that is YOUR task for this session
- If no task is specified and you are the only agent, use `current_task` as normal

### Reading Shared State

- **Re-read `progress.json` before presenting session handoff** — another agent may have updated it since the file was last cached
- **Do not modify `current_task` or `current_phase`** — in multi-agent setups, the orchestrator manages these fields
- **Check for in-progress tasks by other agents** — if another task shows `in_progress`, note it but don't interfere

### Commit Discipline

- **Include your task ID in all commit messages** — e.g., `progress: complete task 2.3 - [description]`
- **Commit only files related to your task** — don't stage changes from another agent's work

---

## Writing for the Operator (binds this whole session, not just the report)

**The operator is running several projects at once and has none of this project's internals in
working memory.** Not the task numbers, not the plan you made twenty minutes ago, not the labels you
invented while making it. Assume that every session, from scratch. It is not a failure of theirs to
be fixed by explaining more later — it is the normal condition, and it is what you write for.

**The three rules:**

1. **Never present a task by its ID alone.** `999.c.i` is not a description of anything. An ID is an
   index into a document the reader does not have open. Always: the ID **and** what it means in plain
   words — *"4.2 — stop agents writing in shorthand the operator can't follow"*.
2. **Expand every abbreviation on first use, every session.** If you use it, you explain it. An
   unexplained abbreviation carries no information; it only makes the reader ask, which costs them
   more than spelling it out would have cost you.
3. **Never use a label you invented.** *"I'm working on a and g"* means nothing to someone who did
   not watch you write the list `a`…`g`. Your plan's internal names are yours alone. Say the thing.

**This binds mid-session, not only at the handoff.** Every progress line, every question you ask,
every proposal — the operator has to be able to follow it *as it happens*, without reconstructing
your reasoning first. A report they have to decode is a report that has not been delivered.

> **The test, before you send anything:** could someone who has not read this project's
> `progress.json` today act on this sentence? If not, rewrite it. Information the reader cannot use
> is, as the operator put it, *"good for nothing"*.

---

## Two Environments (this file ships to both — nothing in it may assume one)

> **A third environment: the independent remote.** If this machine cloned the examples itself and is
> not the operator's workstation or the box, it is **not in the distribution topology** —
> `/distribute-defaults` never reaches it, so its defaults are current only as often as it refreshes
> *itself* (`git pull` the examples clone, then run `scripts/distribute-defaults.sh --apply --commit`
> locally). Stale defaults here are expected, not a fault. Full lifecycle: README § *Running on an
> independent / third-party remote*, and the `syndicate-connect` skill. Reporting knowledge from such
> a host is the `ingest` route (§ that skill), never inbound SSH.

**Which machine you are running on is not knowable from this file.** Every default command ships
unchanged to two environments — the local workstation and the remote dev box — and they differ in
ways that matter:

| | Local workstation | Remote dev box |
|---|---|---|
| `HOME` | `/home/<user>` | `/home/ubuntu` |
| AWS **service model** | one server **per account**, each carrying its own profile | **one central** server, bound to no account |
| A bare call (no `--profile`) | returns that server's bound account | returns nothing — name the account per call |
| A host config in `~/.syndicate-remote-secrets/` | present (it is the local pointer *to* the box) | absent, and that is correct |
| Which repos exist | some live only here, by policy | some live only there, and are developed there |

> **The AWS row is a deliberate design difference, not drift — and the box is AHEAD, not broken.**
> Every configured AWS MCP server spawns **its own process per session** (~120 MB). Twelve
> per-account servers across six live sessions needs ~8.8 GB for AWS tooling alone — more RAM than
> the box has, so it burst; one central server cut that ~12×. **Never "fix" a central-server host by
> restoring per-account servers.** The per-account model is a large-RAM luxury, and hosts move
> *toward* central as sessions multiply — the workstation is expected to follow. `/check-aws` detects
> the model rather than assuming it; do the same anywhere else you reach AWS.

> **`--profile` is honoured on both machines, and it silently OVERRIDES the binding.** Passing a
> profile that exists returns **that** profile's account, with a `200 OK` and no warning — even on a
> connection bound to a different account. Measured: the connection bound to account `030…`, given a
> profile belonging to account `299…`, returned **`299…`** and success. Passing a profile that does
> *not* exist on this machine is the only case that errors (`The config profile could not be found`).
>
> So the failure mode is not "the call breaks" — it is **"the call succeeds against the wrong
> account and nothing tells you."** This is exactly why the rule below says *verify identity*: the
> account number is the only thing that can catch it. An earlier draft of this table claimed naming
> an account "fails" locally; that was inferred from a single probe using a profile name that only
> exists on the *other* machine — the probe artifact, not the behaviour. It is recorded here because
> the mistake is instructive: it is the same error the rule exists to prevent.

> **DECIDED 2026-07-30 — a central server carries NO default account, and that is a safety property,
> not an omission.** The recurring question is whether the unbound central server should be given a
> default profile so a bare call "just works". The answer is **no**, and the reason is the paragraph
> directly above: `--profile` silently overrides, returning `200 OK` for whatever account it names.
> With no default, a call that forgets to name its account **returns nothing** — the failure is
> immediate, local, and obvious. With a default, the same forgetful call **succeeds against the
> default account**, and you find out when you read a resource list from the wrong place, or write to
> it. A default profile does not remove the wrong-account hazard; it makes the hazard quiet. Naming
> the account per call is the cost of having the mistake be loud. Revisit only with a measured case
> where naming it cost more than a silent wrong-account write would.

> **A session should cost memory only for the AWS access it actually needs.** Servers belong in the
> projects that use them, not in a global block every project inherits. Measured on the workstation
> 2026-07-30: seven servers were declared globally, so **every session spawned all seven** — about
> 590 MB — including sessions in projects that touch no AWS at all. Scoping each server to the
> projects that declare its account took the per-session average from 7.00 servers to 0.62, and 15 of
> 34 projects now spawn none. If you are configuring a host, declare a server where it is used.
> **Assign by account number, never by server name** — a name is exactly the thing that can lie, and
> `sts get-caller-identity` is what settles it.

**The rule — and it is one rule, not four:**

> **Verify identity. Resolve location. Never declare a nickname.**
>
> - **Verify identity** — prove you reached the thing you meant to reach (the account number, the
>   repo) *before* acting on it. Reaching *something* is not reaching the *right* thing.
> - **Resolve location** — ask the filesystem, the live tool list, a probe. Presence is ground truth;
>   a declaration drifts the moment anything moves.
> - **Never declare a nickname** — a name that is true on only one machine must never be written into
>   a file that travels to both. `progress.json` travels. So does this one.

**A nickname is any name true on only one machine:** an MCP server name, an AWS profile name, an
absolute path, a hostname, `$USER`. An AWS **account number** is not a nickname — it is the same on
both machines, which is precisely why it is the thing you verify against. Same shape elsewhere: a
repo's *identity* is its name; where it *lives* is a per-machine fact you resolve.

**Why a rule and not just care — this failure class is silent by construction.** It does not error;
it succeeds wrongly, and the report reads as though all was well:

- The sub-repo loop once hardcoded `infrastructure backend frontend testing`. In any project whose
  sub-repos are named otherwise it matched **nothing** and printed **no error** — reporting success
  having synced zero repos, while drift accumulated unseen.
- A `/home/<user>/<repo>/…` path to a repo that moved to the box resolves to nothing, and the agent
  does not stop. It improvises — writes into the current repo, "recreates" the missing tree — and
  reports success.
- A missing host config yields an empty list, not a failure, so everything downstream reads as
  "nothing is on the box."

**You find out by resolving, or you do not find out.**

**Where this rule already applies in this file** — each is an *instance*, not a separate rule; they
point here rather than restate it: Step 0 (sub-repo discovery by glob), Step 2 (live command
inventory), Step 2.5 (cross-host repo resolution), Step 5 (AWS identity). Same rule, four surfaces.
When you meet a fifth, it is still this rule.

---

## Steps

### 0. Sync to Latest (FF-pull, before any work begins)

**Run this FIRST — before reading orchestration files, before the capability inventory, before AWS verify (Step 5), and before pre-work verify (Step 6).** Those steps all read code or `progress.json`, and a pull can change them; syncing first means every downstream step operates on origin-latest, not a stale tree.

**Why this is a different axis from Multi-Agent Discipline above.** That section governs many agents sharing ONE checkout. This step governs the SAME repo checked out in multiple LOCATIONS — local WSL, the remote dev box (synced via `/syndicate-refresh-remote`, configured by a per-machine host config in `~/.syndicate-remote-secrets/`), and occasionally-online offline machines — all sharing ONE origin. A commit pushed from any location lands in origin; a checkout that has not pulled is now stale. Surgical Edits cannot save you if the whole file you are editing is three commits behind origin.

**Policy — identical to `/distribute-defaults`: fast-forward only, skip + report, never force.** Never merge, never reset, never `--force` **in this step**. Any repo that cannot fast-forward (dirty tree, diverged, detached HEAD, no upstream, or origin unreachable/offline) is left untouched and reported; resolve divergence per **§ 0a below**, which runs on any host. If the repo carrying your task cannot fast-forward, STOP and surface it in the Step 9 report before doing the task — working a stale/diverged checkout risks an unpushable divergence.

For the orchestration repo and each present sub-repo, fetch then fast-forward only:

```bash
sync_ff() {  # $1=dir ('.' for orchestration), $2=label
  git -C "$1" fetch --quiet 2>/dev/null || { echo "SKIP $2: origin unreachable (offline?) — proceeding on current checkout"; return; }
  git -C "$1" rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1 \
    || { echo "SKIP $2: no upstream (local-only) — nothing to pull"; return; }
  [ -z "$(git -C "$1" status --porcelain)" ] \
    || { echo "SKIP $2: working tree dirty — commit it, or leave it and skip this repo (see § 0a)"; return; }
  if git -C "$1" merge-base --is-ancestor HEAD @{u} 2>/dev/null; then
    git -C "$1" merge --ff-only @{u} && echo "OK   $2: fast-forwarded to origin-latest"
  else
    echo "SKIP $2: diverged / non-fast-forward — DO NOT force; resolve per § 0a below (runs on ANY host)"
  fi
}
sync_ff "." orchestration
for dir in */; do
  dir="${dir%/}"
  [ -d "$dir/.git" ] && sync_ff "$dir" "$dir"
done
```

A brand-new Phase-0 project whose orchestration repo has no upstream yet is local-only — that is normal; `no upstream` means nothing to pull, so proceed. Carry each repo's sync result into the Step 9 "Session Ready" report.

**Why the sub-repo list is discovered, not hardcoded.** This loop used to read `for dir in infrastructure backend frontend testing` — a fixed list that silently matched **nothing** in any project whose sub-repos are named otherwise (`mcp-docker-playbook`'s are `mcp-infrastructure`, `mcp-connectors`, `mcp-solutions`, `mcp-audit`). Because each iteration is guarded by `[ -d "$dir/.git" ]`, a non-matching name produced **no error and no output** — the step reported success having synced zero sub-repos, and multi-location drift accumulated unseen. Discovery by glob is ground truth for the thing this loop actually asks ("which sub-repos are *present*?"), needs no parser, and cannot drift. `progress.json` `git_repos` remains the **declarative registry** (Step 8 reports status into it); a future refinement could cross-check the two and warn on a declared-but-absent repo. With no subdirectories the glob is a safe no-op.

### 0a. Resolving a divergence — this procedure runs on EVERY host

Both this file and `/update-progress` used to answer a non-fast-forward with one remedy:
*"resolve with `/syndicate-refresh-remote`"*. **That command is local-only by policy** — it is the
workstation's tool for syncing *to* the box — so on the box, the framework's only stated remedy
resolved to nothing, while forbidding the two moves that would have worked. And the box is the
machine that diverges **most**: concurrent sessions, a continuous stream of incoming commits on the
same branch. Found by being hit (2026-08-05: a box session at ahead 2 / behind 2 with **zero file
overlap** — no conflict of any kind — and no legal move).

```bash
git fetch --quiet
U=$(git rev-parse --abbrev-ref --symbolic-full-name @{u}) || echo "no upstream — local-only repo"
git rev-list --left-right --count "$U"...HEAD    # -> "<behind>  <ahead>"
```

> **`@{u}`, never `origin/HEAD`.** `origin/HEAD` is a convenience ref that many clones simply do
> not have — measured on a real project in this estate, where `git rev-parse origin/HEAD` fails and
> every command built on it fails with it. The tracked upstream is the branch this checkout is
> actually measured against, and it exists wherever a push has ever been possible.

| State | Move |
|---|---|
| behind only | fast-forward: `git merge --ff-only "$U"` |
| ahead only | `git push` |
| **diverged** | test for overlap first — the next block |

```bash
# Do the two sides touch any of the same files? Nothing else decides whether a rebase is safe.
comm -12 <(git diff --name-only HEAD..."$U" | sort) \
         <(git diff --name-only "$U"...HEAD | sort)
```

- **No output — the sides are disjoint.** A rebase cannot conflict, because there is no file for it
  to conflict over. `git pull --rebase` then `git push`. This is the common case on a shared box and
  it is not "improvising": it is the one move whose safety you have just *measured*.
- **Any output — the sides overlap.** STOP. Do not rebase, do not merge, do not force. Name the
  overlapping files in the report and leave the commit where it is; it is safe locally and nothing
  is lost. Resolving it is a content decision, and content decisions are the operator's.

**Never resolve a divergence in a checkout holding someone else's uncommitted work.** If
`git status --porcelain` shows changes you did not make this session, leave the repo alone entirely
and report it — a rebase would stash or refuse, and a stash of another agent's work is a deletion
with extra steps.

> On the authority host, `/syndicate-refresh-remote` remains available as an interactive helper for
> the same job. It is a convenience there, **not** the remedy, and it is not available anywhere else.

### 0.5. Ensure the Commit Guard Is Armed (idempotent; never creates files)

A mechanical pre-commit guard (`.claude/hooks/pre-commit`) blocks `git add -A` from sweeping build artifacts / oversized blobs into history — enforced by git on **every** commit, so it holds even when an agent forgets the scoped-commit rule. But it only fires once `core.hooksPath` is set, which is **repo-local config that does NOT travel with a clone**. Re-affirm it every session, right after Step 0 and **before any commit this session makes** (e.g. the Step 2 CLAUDE.md self-heal).

This step only ARMS an already-delivered guard — it never creates or commits the hook file (delivery is `/distribute-defaults`'s job). For the orchestration repo and each present sub-repo:

```bash
arm_guard() {  # $1=dir
  local hp="$1/.claude/hooks/pre-commit"
  if [ -f "$hp" ]; then
    chmod +x "$hp" 2>/dev/null
    [ "$(git -C "$1" config --get core.hooksPath 2>/dev/null)" = ".claude/hooks" ] \
      || git -C "$1" config core.hooksPath .claude/hooks
    echo "OK   $1: commit guard armed (core.hooksPath=.claude/hooks)"
  else
    echo "WARN $1: no .claude/hooks/pre-commit — run /distribute-defaults to deliver it (not creating it here)"
  fi
}
arm_guard "."
for dir in */; do
  dir="${dir%/}"
  [ -d "$dir/.git" ] && arm_guard "$dir"
done
```

Report each repo's armed/absent result in the Step 9 "Session Ready" block. (Re-running this is a no-op once `core.hooksPath` is set.)

### 0.7. Delivered-Defaults Drift Check (vs the distribution manifest; any host, no network)

**Why this step exists — 17 projects ran hand-edited defaults indefinitely while every check said
clean.** Delivery to remote hosts goes via origin (push, then FF-pull), so the delivering engine
never sees a remote working tree — and an FF-pull leaves a locally-modified file alone whenever
upstream did not touch it. A hand-edit to a delivered default therefore survives every sync,
silently, on the host that made it. The one artifact that can see this from ANYWHERE is
`.claude/distribution-manifest.json`: the engine writes it beside every delivery and it records the
sha256 of the exact bytes delivered (post-overlay bake), travelling with the files on every route.

Run the comparison every session start (read-only, no network, correct on any host):

```bash
python3 - <<'PY'
import json, hashlib
from pathlib import Path
m = Path(".claude/distribution-manifest.json")
if not m.exists():
    print("DEFAULTS DRIFT: n/a — no distribution manifest (not a distributed project, or never delivered by the engine)")
    raise SystemExit
man = json.loads(m.read_text())
drifted, missing, checked = [], [], 0
for rel, meta in sorted(man.get("files", {}).items()):
    checked += 1
    p = Path(rel)
    if not p.exists():
        missing.append(rel); continue
    if hashlib.sha256(p.read_bytes()).hexdigest() != meta.get("sha256"):
        drifted.append(rel)
if not drifted and not missing:
    print(f"DEFAULTS DRIFT: ok — all {checked} manifest-listed files carry their delivered bytes "
          f"(delivered {man.get('written_at','?')}, canonical {str(man.get('canonical_commit','?'))[:12]})")
else:
    for f in drifted: print(f"DEFAULTS DRIFT: DRIFTED  {f} — bytes differ from what the engine delivered")
    for f in missing: print(f"DEFAULTS DRIFT: MISSING  {f} — manifest says delivered; file is absent")
PY
DRIFT_RC=$?
[ "$DRIFT_RC" -eq 0 ] || echo "DEFAULTS DRIFT: DID-NOT-RUN (interpreter exit $DRIFT_RC) — drift is UNKNOWN for this project, which is NOT ok"
```

> **The exit status is tested, and it is the same rule this file applies to every other verdict:
> a check that could not run must say so.** Every verdict above is *printed by the interpreter*,
> so an interpreter that dies prints nothing — and nothing is exactly what a clean project prints.
> Reported upstream 2026-08-05 as framework defect 4, which named only Step 2.5; Steps 0.7 and 2.7
> carry the same shape and were found by looking for it rather than by being told.

**Why this cannot cry wolf on legitimate variance:** the manifest records *delivered* bytes, so a
file customized via `.claude/local-overlays/` hash-matches (its baked result IS what was delivered),
and a file forked via `.skip` — or ever classified divergent — is *absent from the manifest by
design* and is not checked at all. What remains is exactly one thing: **a file the engine delivered
whose bytes have since changed on this host.**

**Act on the result:**

- `ok` / `n/a` → proceed; omit from the handoff.
- `DRIFTED` / `MISSING` → **surface every named file in the Session Handoff (⚠ section) — and do
  NOT silently revert it.** The edit may encode true local knowledge the canonical file lacks
  (measured case: hand-edits on a remote host were the only written record of that host's AWS
  service model). The honest moves are: report it as a framework defect per `/update-progress`
  § 11.b if canonical is wrong; propose a `.claude/local-overlays/` entry if the variance is
  legitimately local; or restore delivered bytes if it was an accident — the operator picks.
  A stale manifest is not among the explanations: the engine rewrites it on every apply.

### 1. Read Orchestration Files

- Read `CLAUDE.md` for project context, rules, and conventions
- Read `progress.json` to identify current state and context hints
- Read last entry in `session_notes.md` for recent context

### 2. Build Capability Inventory (before you build anything)

**Why this step exists — the "reinventing the wheel" failure:** agents hand-rebuild functionality that already ships as a project command, because they trust a command list written in `CLAUDE.md` prose. Hand-maintained lists drift the moment a command is renamed, added, or is project-specific. The ONLY source of truth is the live filesystem: `.claude/commands/*.md`. Derive your toolset from the directory every session — never from memory or from prose.

**Enumerate the live inventory (always safe; never hardcode a list):**

```bash
for f in .claude/commands/*.md; do
  [ -e "$f" ] || continue
  name=$(basename "$f" .md)
  desc=$(sed -n 's/^description:[[:space:]]*//p' "$f" | head -1)
  printf '/%s\t%s\n' "$name" "${desc:-(no description)}"
done
```

This answers **"does a command for this already exist / am I aware of it?"** — including project-specific commands the stale prose may omit. It does NOT answer **"is this command the latest canonical version?"** — version reconciliation against central is `/distribute-defaults`'s job, not yours. Do not edit command file contents here. (Output is display-only; descriptions may contain `—`/tabs, so don't re-parse it.)

**Bind yourself to these rules:**

- **Prefer-existing rule.** Before building, scripting, or hand-rolling ANY capability, scan the inventory for a command whose name/description covers the need. If one matches, invoke it instead of doing the work ad-hoc — reinventing an existing command is a defect, not initiative.
- **Open before you reject.** If a command's name plausibly fits but its one-line description is terse, READ that command file before concluding "mine is different." This closes the most common reinvention loophole.
- **Re-derive, don't recall.** Consult the live directory each session; never act on a remembered list or `CLAUDE.md` prose.

**Reconcile `CLAUDE.md` only if it has DRIFTED to a hardcoded list (authorized, scoped, idempotent):**

The correct shape of the `CLAUDE.md` commands section is a **list-free prose pointer** to `.claude/commands/` — NOT an enumerated list (a hand-maintained list is the disease this step cures). Detect the section by a heading matching `^##[[:space:]]+Commands` (tolerant of `## Commands`, `## Commands (N total)`, `## Commands Available (N total)`), spanning to the next `## ` heading or `---`.

- **If that section is already list-free prose → change NOTHING and do NOT commit.** This is the normal case; the step is a no-op.
- **If — and only if — it contains a hardcoded command list** (e.g. a fenced block of `/cmd # …` lines), it has drifted. Self-heal by **replacing the enumerated list with the prose pointer** (no command names — heal toward the directory, never regenerate a list). Touch ONLY that section; touch no other part of `CLAUDE.md` and no other file.
- **Concurrency guard.** Other agents may be editing `CLAUDE.md` concurrently. Only heal when `CLAUDE.md` has no other unstaged changes (`git diff --name-only` does not list it before your edit), and commit by pathspec so you never sweep another agent's pre-staged files:

```bash
git commit CLAUDE.md -m "<task-id>: replace stale hardcoded command list with live-inventory pointer"
```

Never `git add -A` / `git add .` (see Multi-Agent Discipline → "Commit only files related to your task"). If the concurrency guard fails, skip the heal and report the drift in the Session Ready block instead.

**Carry the inventory forward:** include the enumerated list in the Step 9 "Session Ready" report so the prefer-existing reflex stays in working context past session start.

### 2.5. Cross-Host Repo Resolution (where does each repo you reach into actually LIVE?)

**A repo lives in exactly ONE place.** If a repo is on the remote box, it is **developed there** — a
local directory of the same name would be a stale backup or leftover, not the truth. The inverse also
holds: some repos are **local-only by policy** and must never appear on the box
(`syndicate-playbooks-examples`, `syndicate-remote`).

**Why this step exists — the hardcoded-path failure.** Project skills reach into *other* repos by
absolute path (`/home/<user>/<repo>/…`). The moment that repo moves to the box, every such path
resolves to **nothing** — and the agent does not error. It improvises: writes into the current repo,
"recreates" the missing tree, or reports success having done neither. This is the same failure class
as a knowledge extraction scattering into the local repo, and it is worse than an outage because it
looks like success. Measured on this estate: one designer skill carried **11** references to a deploy
repo that had moved to the box; all 11 pointed at an empty path.

**This step is one instance of the rule in § Two Environments above — *resolve location* applied to
repos.** Resolve by presence; never by hostname, `$USER`, or a hardcoded list. The rule is stated
there and not restated here; if this step and that section ever disagree, that section wins.

```bash
SECRETS="$HOME/.syndicate-remote-secrets"
SELF="$(basename "$PWD")"

# Repos that are local-only BY POLICY. This is not a nickname and not a location claim: it is a
# host-independent fact, equally true on both machines, so it belongs in a file that ships to both.
# Their absence from the box is the INTENT, never a fault. Stated once, here.
POLICY_LOCAL="syndicate-playbooks-examples syndicate-remote"

# Discover which OTHER repos this project's skills point at — live grep, never a hardcoded list.
REFS=$(grep -rhoE '(/home/[A-Za-z0-9._-]+|\$HOME|~)/[A-Za-z0-9._-]+' .claude/commands/*.md 2>/dev/null \
       | sed -E 's#^(/home/[A-Za-z0-9._-]+|\$HOME|~)/##; s/[.,:;)]+$//' \
       | grep -vE '^\.?$|^\.' | sort -u)

# Discover the configured host(s) BY SHAPE, never by filename. A host config is any *.json in the
# secrets dir carrying non-empty host + user + workspace + ssh_key. This probe does not itself need
# `workspace` (it enumerates ~/*/ on the far side), but it requires it anyway so that ONE predicate
# decides what a host is: a file that is a host here and "broken" to the estate tools — or the
# reverse — is a split-brain, and split-brains are what this whole discovery change removes.
# The file that used to be read by name was
# `box.json`, named for one machine that no longer exists; naming its successor would just move the
# problem. Emits "user host" per line — nothing else in this block knows a filename.
#
# CRITICAL: "I could not ask" is NOT "the host does not have it". These configs are a LOCAL
# WORKSTATION artifact — this machine's pointer TO a host. Run this step ON that host and they are
# correctly absent. Collapsing that into an empty list is what made a correct state report a blocker.
#
# Trust a config only if it PARSES and carries the three fields — never by mere existence. An
# empty/corrupt file (measured: a 0-byte config, 2026-07-24) must read as "no host configured", NOT
# as a false "unreachable", which invites chasing a network fault that is really a bad file.
HOSTS=""; BAD=0; PARSER_RC=0
if [ -d "$SECRETS" ]; then
  # THE EXIT STATUS IS CAPTURED, and that is not defensive habit — it is the difference between
  # two opposite answers. With `2>/dev/null` and no rc check, a python3 that exists but FAILS
  # (a broken install, a partial upgrade, an interpreter killed by the OOM killer) empties HOSTS
  # exactly as a machine with no host config does, and this step then prints the all-clear for a
  # correct state while the configured hosts were never asked. lib/estate-reach.sh:211-216 makes
  # this same argument for the same reason and propagates rc; the defaults did not.
  HOSTS=$(python3 - "$SECRETS" <<'PY' 2>/tmp/secrets-parse.err
import json, os, sys
d = sys.argv[1]; bad = 0; seen = set()
for n in sorted(os.listdir(d)):
    if not n.endswith(".json"): continue
    try:
        with open(os.path.join(d, n)) as fh: data = json.load(fh)
    except Exception:
        bad += 1; continue
    for o in (data if isinstance(data, list) else [data]):
        if not isinstance(o, dict): continue
        got = [k for k in ("host","user","workspace","ssh_key") if o.get(k)]
        if not got: continue                       # not a host config at all — silent, by design
        if len(got) < 4: bad += 1; continue        # host-shaped and unusable — say so, do not ignore
        if o["host"] in seen: continue             # one machine described twice is still one machine
        seen.add(o["host"])
        print("%s\t%s\t%s" % (o["user"], o["host"], os.path.expanduser(o["ssh_key"])))
print("BAD\t%d\t-" % bad)
PY
)
  PARSER_RC=$?
  BAD=$(printf '%s\n' "$HOSTS" | awk -F'\t' '$1=="BAD"{print $2}')
  HOSTS=$(printf '%s\n' "$HOSTS" | awk -F'\t' '$1!="BAD"')
  if [ "$PARSER_RC" -ne 0 ]; then
    # NOT "no host configured". We could not look, so every configured host is UNKNOWN — the same
    # distinction Step 0.7 and the estate runners make, and the one this step was missing.
    echo "HOST CONFIGS UNREAD: the parser exited $PARSER_RC — the hosts in $SECRETS were NOT asked."
    echo "  cause: $(head -c 300 /tmp/secrets-parse.err 2>/dev/null || echo '(no stderr captured)')"
    HOSTS=""
  fi
fi

# Ask EVERY configured host. ASKED counts the ones that answered, TOTAL the ones we meant to ask —
# their difference is the whole reason UNKNOWN exists below.
REMOTELIST=""; TOTAL=0; ASKED=0
while IFS=$'\t' read -r U H K; do
  [ -z "${H:-}" ] && continue
  TOTAL=$((TOTAL+1))
  # -n is mandatory: without it the first ssh consumes the remaining host rows as its own stdin.
  #
  # THE TRAILING `; :` IS LOad-BEARING, NOT TIDINESS. A `for` loop exits with the status of its
  # LAST iteration, and the body `[ -d "$d/.git" ] && basename "$d"` is FALSE for any directory
  # that is not a git repo. So a perfectly healthy host whose home directory happens to end with
  # `venv/`, `tmp/`, `snap/` — anything sorting last without a .git — returned rc 1, and this
  # probe reported "did not answer" for a host that had just answered in full. `; :` makes the
  # remote program's status mean "the program ran", which is the only question ssh's rc should
  # be answering; a genuine connection failure still surfaces as ssh's own 255.
  #
  # ServerAlive* bounds the connection AFTER the handshake. ConnectTimeout does not: a host that
  # authenticates and then stalls (memory pressure, full disk) would hang this block, and this
  # block runs at the start of EVERY session in every project. 5s x 3 = a ~15s ceiling per host.
  if L=$(ssh -n -i "$K" -o ConnectTimeout=15 -o ServerAliveInterval=5 -o ServerAliveCountMax=3 \
             -o BatchMode=yes "$U@$H" \
         'for d in ~/*/; do [ -d "$d/.git" ] && basename "$d"; done; :' 2>/dev/null); then
    ASKED=$((ASKED+1)); REMOTELIST="$REMOTELIST
$L"
  else
    echo "HOST $H did not answer (offline? maintenance?) — its repos are NOT in this probe."
  fi
done <<< "$HOSTS"

# A BROKEN CONFIG IS AN UNASKED HOST, whether or not some OTHER host answered. This used to be
# reported only when TOTAL was 0, so one good config beside one unusable one printed
# "ok — asked 1 of 1" — true of the hosts it managed to parse, false as a statement about the
# machine — and then sent every unfound repo to UNRESOLVABLE, whose whole meaning is "every
# configured host was asked and said no". A host we could not even read was never asked.
if [ "${BAD:-0}" -gt 0 ]; then
  echo "HOST CONFIG UNUSABLE: $BAD file(s) in \$HOME/.syndicate-remote-secrets are host-shaped but empty, unparseable, or missing host|user|workspace|ssh_key. Those hosts were NOT asked; fix or remove them."
fi

if   [ "${BAD:-0}" -gt 0 ] && [ "$TOTAL" = 0 ]; then
  PROBE="unavailable — $BAD host config(s) present but unusable (treat as no host configured; fix or remove them)"
elif [ "$TOTAL" = 0 ]; then
  PROBE="unavailable — no host configured (this may BE the host, or a machine that syncs with none)"
elif [ "${BAD:-0}" -gt 0 ]; then
  PROBE="partial — asked $ASKED of $TOTAL readable host(s), and $BAD further config(s) are unusable so those hosts were never asked"
elif [ "$ASKED" = "$TOTAL" ]; then
  PROBE="ok — asked $ASKED of $TOTAL configured host(s)"
elif [ "$ASKED" = 0 ]; then
  PROBE="unreachable — none of $TOTAL configured host(s) answered"
else
  PROBE="partial — asked $ASKED of $TOTAL; anything not found may live on the host that did not answer"
fi
echo "HOST PROBE: $PROBE"

for r in $REFS; do
  [ "$r" = "$SELF" ] && continue
  case " $POLICY_LOCAL " in *" $r "*) POLICY=yes ;; *) POLICY=no ;; esac
  if [ -d "$HOME/$r/.git" ]; then
    printf 'REPO %-34s local\n' "$r"
  elif [ "$POLICY" = yes ]; then
    printf 'REPO %-34s local-only by policy, absent here — EXPECTED, not a blocker\n' "$r"
  elif printf '%s\n' "$REMOTELIST" | grep -qx "$r"; then
    printf 'REPO %-34s REMOTE (host) — local paths to it are DEAD\n' "$r"
  elif [ "$TOTAL" -gt 0 ] && [ "$ASKED" = "$TOTAL" ] && [ "${BAD:-0}" = 0 ]; then
    printf 'REPO %-34s UNRESOLVABLE — not local, and every configured host answered that it is not there either\n' "$r"
  else
    printf 'REPO %-34s UNKNOWN — not local; at least one host could not be asked. Do NOT conclude it is missing.\n' "$r"
  fi
done
```

**Act on the result:**

| Verdict | What it means | What you do |
|---|---|---|
| `local` | The repo is here. | Use it directly. Normal case; say nothing. |
| `local-only by policy` | It is one of the repos policy keeps off the remote host, and you are not on the machine that holds it. **Its absence is the intent.** | **Nothing.** This is a correct state, not a finding — do not surface it, do not "fix" it, and above all do not clone it here. If your task genuinely needs it, that task belongs on the workstation, and *that* is what you say. |
| `REMOTE (host)` | It lives on a configured host and is **developed there**. Every `/home/<user>/<repo>/…` path in this project's skills is **dead**. | **Surface it in the handoff.** Work touching that repo must run **on that host** (`ssh`, or a session started there) — reading its files, running its scripts, and committing in it all happen there. Do **not** clone it locally to "fix" the path: that creates a second copy, and the remote copy is the real one. |
| `UNRESOLVABLE` | Not local, **and every configured host answered that it does not have it either.** Genuinely nowhere. | **Report it and stop** before doing work that depends on it. Do not invent a path, do not recreate the tree, do not substitute the current repo. |
| `UNKNOWN` | Not local, and **at least one host could not be asked** — none is configured, or one did not answer. | **Report it; do not conclude anything.** You have no evidence about that host, and no evidence is not evidence of absence. Say "could not resolve" and why. Never upgrade this to `UNRESOLVABLE`. |

> **Why `UNKNOWN` exists at all.** This step used to treat "the probe returned nothing" and "the probe
> could not run" as the same answer. A host config is a **local workstation artifact** — this machine's
> pointer *to* a host — so running this step **on that host** finds it correctly absent, produced an
> empty repo list, and routed **every** referenced repo to `UNRESOLVABLE → stop`. The two repos it hit
> hardest were the two the paragraph above declares local-only by policy: their absence was the
> intent, reported as a blocker. An empty answer and an unasked question are different facts, and a
> step that conflates them manufactures blockers out of correct states.
>
> **With more than one host configured there is a fourth state, and it is not cosmetic.** `partial`
> means some hosts answered and some did not: a repo found on none of them might still live on the
> one that stayed silent, so it is `UNKNOWN`, never `UNRESOLVABLE`. `UNRESOLVABLE` requires that
> **every** configured host was asked and every one said no.

> **The one thing you must never do:** treat a dead absolute path as an invitation to improvise. A
> skill that says `/home/<user>/<repo>/…` for a repo that now lives on another host is **stale
> documentation, not an instruction** — resolve where the repo actually is, and if that is a remote
> host, say so plainly rather than quietly doing the work somewhere else.

**Cross-host work is a real constraint, not a detail.** A skill whose *source* repo is local and whose
*target* repo is remote cannot run wholly on either host. When you hit one, surface the split to the
operator rather than half-executing it — half of a two-sided sync is a partial-sync defect.

### 2.7. Repo Hygiene Gate (triggered consolidation — /repo-hygiene)

**Why:** one-off documentation audits decay — weeks after a big cleanup, docs drift from the code,
skills reference moved tools, indexes go stale, progress.json balloons. And the rot is not just
index-level: operational claims inside skills/docs (CLI flags, resource names, payload shapes)
decay against the implementation while every index check passes — `/repo-hygiene` grounds a
rotating content slice for exactly this. It is the standing consolidation pass; THIS gate is what
makes it actually run.

Run the quick clock check (read-only, cheap):

```bash
python3 - <<'PY'
import json, time
from pathlib import Path
p = Path(".claude/hygiene-state.json")
if not p.exists():
    print("HYGIENE: never recorded — run /repo-hygiene to establish the baseline")
else:
    st = json.loads(p.read_text())
    lp = st.get("last_pass")   # may be absent OR explicitly null — treat both as "no full pass yet"
    if not lp:
        if "grounded" in st:
            print("HYGIENE: content baseline missing — grounded map exists but no full pass; run /repo-hygiene once to set the clock (then /update-progress Step 2b rotates per session)")
        else:
            print("HYGIENE: never recorded — run /repo-hygiene to establish the baseline")
    else:
        age = (time.time() - time.mktime(time.strptime(lp, "%Y-%m-%d"))) / 86400
        if age > 60:   print(f"HYGIENE: OVERDUE x2 ({age:.0f}d since {lp}) — MUST run /repo-hygiene before new work")
        elif age > 30: print(f"HYGIENE: due ({age:.0f}d since {lp}) — schedule /repo-hygiene this session or next")
        else:          print(f"HYGIENE: ok (last pass {lp}, {age:.0f}d ago)")
PY
HYG_RC=$?
[ "$HYG_RC" -eq 0 ] || echo "HYGIENE: DID-NOT-RUN (interpreter exit $HYG_RC) — the clock is UNKNOWN, which is NOT ok"
```

- `ok` → proceed; omit from the handoff.
- **`DID-NOT-RUN`** → surface it in the handoff. An unknown clock is not a healthy clock; treat it
  as `never recorded` until a run succeeds (framework defect 4's shape, at its second site).
- `due` → surface a "⚠ Repo hygiene due" line in the Session Handoff (informational).
- `content baseline missing` → surface it in the handoff: the clock is fine but the per-session
  content-consolidation rotation (`/update-progress` Step 2b) has no baseline yet — recommend a
  one-time manual `/repo-hygiene` run this session or next.
- `OVERDUE x2` or `never recorded` → surface it PROMINENTLY in the handoff and treat
  `/repo-hygiene` as the recommended first task — the operator can override, but the default
  next action is the hygiene pass, not new work on a drifting tree.
- If the project ships its own richer checker (e.g. a docs-currency tool wired via a local
  overlay), its findings feed the same banner.

### 3. Detect Project State

#### If no `progress.json` exists:
```
## Project Not Initialized

No progress.json found. This project needs setup.

Run `/setup` to:
- Choose a playbook template
- Copy project structure (spec, phases, tasks)
- Configure environment
- Create repositories
```

Direct user to run `/setup`.

#### If no tasks exist in progress.json:
```
## Setup Incomplete

Project has progress.json but no tasks defined.

This can happen if:
- Setup was interrupted
- Commands were injected to existing project without tasks

Would you like me to:
1. **Run /setup** - Complete the setup process
2. **Use /add-work** - Define tasks manually
```

Use AskUserQuestion.

#### If tasks exist:
Proceed to session handoff (Step 4).

### 4. Present Session Handoff

#### 4.0 — Render the open-work tables FIRST, mechanically. This is a step, not a suggestion.

**Run this before you write a word of the handoff:**

```bash
python3 .claude/skills/open-work/open_work.py     # from the project root
```

Paste its output verbatim where the template below says `{{OPEN_WORK_TABLES}}`, then replace
**every** `<FILL: …>` token with what that task MEANS — language needing no other document open.
`"In plain words"` is never the task's name repeated; if you cannot write it, you do not yet
understand the task. Exit code `2` means `progress.json` is missing, unreadable, or has no
recognisable phases: **report that verbatim to the operator** — it is a real defect, not a reason
to skip the tables. If the skill is not installed in this project, render the three tables by hand
to the same shape (`§ 4.0a`) and report the missing skill.

**Why this is mechanical.** These tables were once specified in prose inside the template block
below, and sessions rendered them as prose instead — an 11-task phase collapsed to one sentence,
deferred phases printed as bare numbers (`Phase 66 (1)`), which is exactly the *"an ID alone is not
a description"* failure the tables exist to prevent. The hosts had the correct file; one had zero
drift. **A row a script emits cannot be dropped for brevity.**

#### 4.0a — What the three tables are (the shape the renderer emits)

Scope: **ALL open work, in three buckets — current, stuck, deferred.** Open work is tasks and
phases: every open task appears in exactly one bucket, so nothing tracked is ever invisible at
session start. A record that is not a task is not open work and has no row here — an untriaged
note with no owner and no authorization was never open work, it only looked like it while it sat
in `progress.json` (`/add-work` § *The Four Destinations*).

| Bucket | Contains |
|---|---|
| **Current phase** | every task in the current phase that is not complete/superseded, one row each |
| **Stuck elsewhere** | `in_progress` or `blocked` in a phase that is *not* current — started or obstructed, then abandoned; precisely the ones that go stale unnoticed |
| **Deferred work** | `pending` in a non-current phase, one row per phase with its open count |

Deferred is **by design**: rendering it as "stuck" miscasts planned work as neglect, and not
rendering it at all is how work that nothing else points at goes structurally invisible for months
until the operator asks where it went — measured on the untyped `backlog` array this table used to
render, removed on 2026-08-25 because nothing in it could be acted on. The lesson outlived the
channel: a phase nobody is currently working on is exactly the thing that goes quiet, so it is
counted here every session. A stuck task old enough that its context has gone stale is a candidate
for the disposition rules in `/update-progress` Step 3a — say so rather than carrying it silently.

The renderer also emits a **pointer check** when `current_task`/`current_phase` is stale, absent,
or not an id. Report those lines; do not quietly fix `progress.json` here.

#### 4.1 — Present the handoff

```
## Session Handoff

### Previous Session Summary
[Summarize from session_notes.md last entry:]
- What was accomplished
- Key decisions made
- Any issues encountered

### Upcoming Work

<!-- HEADING NAMES IN THIS FILE ARE A PUBLIC API — DO NOT RENAME THIS ONE.
     Projects splice overlay content onto exact heading text (`<!-- splice-before: "### Upcoming
     Work" -->`). Renaming a heading orphans every anchor pointing at it: the bake fails
     (apply-overlay.py exit 2 = broken-overlay), the engine's blocker gate fires, and
     /distribute-defaults exits 3 having written NOTHING to ANY project on that host.
     This is not hypothetical — this exact heading was renamed to "### Open Work" during
     development and broke 4 anchors in a live project, which would have halted distribution
     estate-wide. Add sections; never rename one. -->

{{OPEN_WORK_TABLES}}

[Replace the line above with the verbatim output of § 4.0's renderer, every <FILL: …> token
 filled in. Three tables: current phase, "Stuck elsewhere" (omit if empty), "Deferred work"
 (omit ONLY if there are no non-current-phase pending tasks). Do not summarise them into prose,
 and do not drop rows.]

### ⚠ Remote-resident repos  (omit ONLY if Step 2.5 found none needing action)
[repo → REMOTE (host): this project's skills reference it by a local path that is DEAD.
 Work touching it must run on that host. Name every one — an agent that does not know this
 will improvise into the current repo and report success.]
[repo → UNRESOLVABLE: not local, and every configured host answered that it is not there.
 Do not start work that depends on it.]
[repo → UNKNOWN: not local, and the box could not be asked. Say so and say why. Do NOT
 present this as missing — you have no evidence either way.]
[repo → local-only by policy: OMIT ENTIRELY. Its absence is the intent, not a finding.
 Mentioning it trains the operator to ignore this section.]

### ⚠ Repo hygiene  (omit if Step 2.7 reported ok)
[due / OVERDUE x2 / never recorded — recommend /repo-hygiene accordingly]

### ⚠ Delivered-defaults drift  (omit if Step 0.7 reported ok or n/a)
[Name every DRIFTED / MISSING file verbatim from the Step 0.7 output. Do not revert anything
 here — the edit may encode true local knowledge; the operator picks the remedy (report per
 /update-progress § 11.b / local-overlay / restore). A drift line that appears session after
 session with no decision is itself a finding — say so.]

---
**What would you like to do?**
1. **Continue** — [what Task X.Y actually is, in plain words] (Task X.Y)
2. **Redirect** — work on a different task
3. **Discuss** — talk about something first (may lead to new tasks)
```

**Use AskUserQuestion tool.**

> **Option 1 must say what the task IS — the bare ID is not an option, it is a lookup.** This is the
> one line the operator has to act on, and they are running several projects with none of this one's
> numbers in working memory. `Continue — proceed with Task 6.7` asks them to go and find out what
> they are agreeing to before they can agree to it; `Continue — stop every session loading all seven
> AWS servers (Task 6.7)` can be answered on sight. Keep the ID — it is how they refer back to it —
> but never let it stand alone. Same rule for the option *descriptions*: state the consequence of
> choosing, not a restatement of the label. (This prompt violated the rule that § Writing for the
> Operator states in this very file, for as long as both have shipped together — a rule and its
> counter-example in one document. If you find another, treat it the same way.)

**If user chooses Discuss:**
- Have the discussion
- If work is identified, ask: "Should I add this as tracked tasks?"
- If yes, follow `/add-work` workflow
- If no, it is an untracked observation: `session_notes.md` only, never `progress.json` under any
  key (`/add-work` § *The Four Destinations*)

### 5. Verify AWS Account (CRITICAL)

**Only if user chose Continue**

```
{mcp_tool} aws sts get-caller-identity
```

- If `context_hints` has no `aws_account` (a Phase 0 project, or one without AWS), skip this step and record "AWS verify: n/a (no aws_account in context_hints)" in the Step 9 report.
- **STOP if account ID does not match** `context_hints.aws_account`
- Confirm region matches `context_hints.aws_region`

### 6. Pre-Work Verification (MANDATORY)

Before starting NEW work, verify last completed task still works.

Find the last `complete` task in progress.json:
```json
{"id": "X.Y", "name": "...", "status": "complete", "verify": "..."}
```

Run its verification step:
- If `verify` field exists → run that check
- If AWS resources → verify they exist
- If code → verify it builds/runs

**If verification FAILS:**
- Do NOT proceed to new task
- Fix the regression first
- Document in session_notes.md

**If verification PASSES:**
- Proceed to current task

### 7. Check Context Budget

Run `/context` to check usage:
- **<40%**: Start any task
- **40-60%**: Small/medium tasks only
- **60-80%**: Finish current, then wrap up
- **>80%**: Only update progress.json, end session

### 8. Check Git Repo Status

Same discovered sub-repo set as Steps 0/0.5 (`progress.json` `git_repos` is the declarative registry this step reports *into*):

```bash
git status
for dir in */; do
  dir="${dir%/}"
  [ -d "$dir/.git" ] && { echo "=== $dir ==="; git -C "$dir" status --short; }
done
```

**Also check the naming invariant — folder name = origin repo name, orchestration repo included**
(the convention `/setup` § Naming Convention binds at birth; this is its standing session-time
check. The framework's own bootstrap once created folders whose origin carried a different name,
and two live projects still disagree folder-vs-origin — drift you cannot grep for):

```bash
check_name() {  # $1=dir ('.' for orchestration)
  local o n
  o=$(git -C "$1" remote get-url origin 2>/dev/null | sed 's#.*/##; s/\.git$//')
  n=$(basename "$(cd "$1" && pwd)")
  [ -n "$o" ] && [ "$o" != "$n" ] && echo "NAMING MISMATCH: folder '$n' vs origin '$o'"
}
check_name "."
for dir in */; do
  dir="${dir%/}"
  [ -d "$dir/.git" ] && check_name "$dir"
done
```

A repo with no origin is silent (nothing to disagree with yet). Any `NAMING MISMATCH` line goes
into the Step 9 repos table — report it, do not rename anything: a rename touches every checkout
on every host and is the operator's call.

Update `git_repos` status in progress.json:
- `pushed` - clean and in sync with remote
- `needs_push` - local commits not pushed
- `local_only` - no remote configured

### 9. Report Ready Status

```
## Session Ready

### AWS Account Verified
- Account: {AWS_ACCOUNT_ID} ✓
- Region: {AWS_REGION} ✓
- MCP Tool: {mcp_tool}

### Pre-Work Verification
- Last completed: Task X.Y - [name]
- Verification: [PASSED/FAILED]

### Context Budget
- Current usage: XX%
- Recommended scope: [small/medium/wrap-up]

### Current Task
- Phase: X - [Phase Name]
- Task: X.Y - [Task Name]
- Repo: [repo name]
- Size: [small/medium]

### Repos Status
| Repo | Sync (Step 0) | Status |
|------|---------------|--------|
| orchestration | FF-pulled / up-to-date / DIVERGED / offline / local-only | pushed/needs_push |
| infrastructure | ... | ... |

(If any repo shows DIVERGED, resolve it with /syndicate-refresh-remote before starting the task; if it shows offline, note the stale-checkout risk and re-sync when online.)

### Ready to proceed with Task X.Y
```

---

## Context Management (CRITICAL)

You MUST monitor context:

1. **Check `/context`** to verify current usage
2. **If context is low** (>60%), immediately:
   - Run `/update-progress`
   - Update `session_notes.md` with full context
   - Commit and push all repos
   - Tell user: "Context limit approaching. Progress saved."

---

## CRITICAL: Authorization Boundaries

### What This Session Authorizes
Work on **existing tasks** in progress.json.

### What Requires SEPARATE Approval

| Action | Command | Requires |
|--------|---------|----------|
| Add phases/tasks | `/add-work` | User approval |
| Major scope changes | Discuss first | User approval |
| Modifying IMPLEMENTATION_PLAN.md | Discuss first | User approval |

### Discussion ≠ Authorization

**When user discusses problems or future work:**
- "This needs fixing" → NOT authorization to create tasks
- "We should do X" → NOT authorization to do X

**Only explicit statements authorize:**
- "Add this to the tasks"
- "Yes, do it"

**When uncertain:** ASK: "Should I add this as tracked tasks, or just note it?"

---

## If Claude's Plan Mode Was Used

If you (Claude) used `EnterPlanMode` during a session:

1. That temporary plan lives only in the session
2. Run `/add-work` to transfer to progress.json
3. Don't lose that planning work!

---

## Critical Reminders

- **NEVER** export AWS profiles to environment
- **ALWAYS** use MCP tools for AWS operations
- **ALWAYS** verify account before any AWS operation
- **ALWAYS** verify last task before starting new work
- **NEVER** assume discussion equals authorization
- **BEFORE** writing any script, loop, or multi-step procedure, STOP and check the live `.claude/commands/` inventory for an existing command — prefer it over ad-hoc work
