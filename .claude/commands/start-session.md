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

**Which machine you are running on is not knowable from this file.** Every default command ships
unchanged to two environments — the local workstation and the remote dev box — and they differ in
ways that matter:

| | Local workstation | Remote dev box |
|---|---|---|
| `HOME` | `/home/<user>` | `/home/ubuntu` |
| AWS **service model** | one server **per account**, each carrying its own profile | **one central** server, bound to no account |
| A bare call (no `--profile`) | returns that server's bound account | returns nothing — name the account per call |
| `box.json` | present (it is the local pointer *to* the box) | absent, and that is correct |
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
- A missing `box.json` yields an empty list, not a failure, so everything downstream reads as
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

**Why this is a different axis from Multi-Agent Discipline above.** That section governs many agents sharing ONE checkout. This step governs the SAME repo checked out in multiple LOCATIONS — local WSL, the remote dev box (synced via `/syndicate-refresh-remote`, configured by `box.json`), and occasionally-online offline machines — all sharing ONE origin. A commit pushed from any location lands in origin; a checkout that has not pulled is now stale. Surgical Edits cannot save you if the whole file you are editing is three commits behind origin.

**Policy — identical to `/distribute-defaults`: fast-forward only, skip + report, never force.** Never merge, never rebase, never reset, never `--force`. Any repo that cannot fast-forward (dirty tree, diverged, detached HEAD, no upstream, or origin unreachable/offline) is left untouched and reported; resolve divergence with `/syndicate-refresh-remote`. If the repo carrying your task cannot fast-forward, STOP and surface it in the Step 9 report before doing the task — working a stale/diverged checkout risks an unpushable divergence.

For the orchestration repo and each present sub-repo, fetch then fast-forward only:

```bash
sync_ff() {  # $1=dir ('.' for orchestration), $2=label
  git -C "$1" fetch --quiet 2>/dev/null || { echo "SKIP $2: origin unreachable (offline?) — proceeding on current checkout"; return; }
  git -C "$1" rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1 \
    || { echo "SKIP $2: no upstream (local-only) — nothing to pull"; return; }
  [ -z "$(git -C "$1" status --porcelain)" ] \
    || { echo "SKIP $2: working tree dirty — commit/stash or use /syndicate-refresh-remote first"; return; }
  if git -C "$1" merge-base --is-ancestor HEAD @{u} 2>/dev/null; then
    git -C "$1" merge --ff-only @{u} && echo "OK   $2: fast-forwarded to origin-latest"
  else
    echo "SKIP $2: diverged / non-fast-forward — DO NOT force; resolve with /syndicate-refresh-remote"
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
```

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
CFG="$HOME/.syndicate-remote-secrets/box.json"
SELF="$(basename "$PWD")"

# Repos that are local-only BY POLICY. This is not a nickname and not a location claim: it is a
# host-independent fact, equally true on both machines, so it belongs in a file that ships to both.
# Their absence from the box is the INTENT, never a fault. Stated once, here.
POLICY_LOCAL="syndicate-playbooks-examples syndicate-remote"

# Discover which OTHER repos this project's skills point at — live grep, never a hardcoded list.
REFS=$(grep -rhoE '(/home/[A-Za-z0-9._-]+|\$HOME|~)/[A-Za-z0-9._-]+' .claude/commands/*.md 2>/dev/null \
       | sed -E 's#^(/home/[A-Za-z0-9._-]+|\$HOME|~)/##; s/[.,:;)]+$//' \
       | grep -vE '^\.?$|^\.' | sort -u)

# Probe the box's repo list. CRITICAL: "I could not ask" is NOT "the box does not have it".
# box.json is a LOCAL WORKSTATION artifact — it is this machine's pointer TO the box. Run this step
# ON the box and it is correctly absent. Collapsing that into an empty list is what made a correct
# state report as a blocker.
BOXLIST=""; BOXPROBE="unavailable — no box.json (this may BE the box, or a host with no box configured)"
if [ -f "$CFG" ]; then
  H=$(python3 -c "import json;print(json.load(open('$CFG'))['host'])")
  U=$(python3 -c "import json;print(json.load(open('$CFG'))['user'])")
  K=$(python3 -c "import json;print(json.load(open('$CFG'))['ssh_key'])")
  if BOXLIST=$(ssh -n -i "$K" -o ConnectTimeout=15 -o BatchMode=yes "$U@$H" \
               'for d in ~/*/; do [ -d "$d/.git" ] && basename "$d"; done' 2>/dev/null); then
    BOXPROBE="ok"
  else
    BOXPROBE="unreachable — box did not answer (offline? maintenance?)"
  fi
fi
echo "BOX PROBE: $BOXPROBE"

for r in $REFS; do
  [ "$r" = "$SELF" ] && continue
  case " $POLICY_LOCAL " in *" $r "*) POLICY=yes ;; *) POLICY=no ;; esac
  if [ -d "$HOME/$r/.git" ]; then
    printf 'REPO %-34s local\n' "$r"
  elif [ "$POLICY" = yes ]; then
    printf 'REPO %-34s local-only by policy, absent here — EXPECTED, not a blocker\n' "$r"
  elif [ "$BOXPROBE" = "ok" ] && printf '%s\n' "$BOXLIST" | grep -qx "$r"; then
    printf 'REPO %-34s REMOTE (box) — local paths to it are DEAD\n' "$r"
  elif [ "$BOXPROBE" = "ok" ]; then
    printf 'REPO %-34s UNRESOLVABLE — not local, and the box answered that it is not there either\n' "$r"
  else
    printf 'REPO %-34s UNKNOWN — not local; could not ask the box. Do NOT conclude it is missing.\n' "$r"
  fi
done
```

**Act on the result:**

| Verdict | What it means | What you do |
|---|---|---|
| `local` | The repo is here. | Use it directly. Normal case; say nothing. |
| `local-only by policy` | It is one of the repos policy keeps off the box, and you are not on the machine that holds it. **Its absence is the intent.** | **Nothing.** This is a correct state, not a finding — do not surface it, do not "fix" it, and above all do not clone it here. If your task genuinely needs it, that task belongs on the workstation, and *that* is what you say. |
| `REMOTE (box)` | It lives on the box and is **developed there**. Every `/home/<user>/<repo>/…` path in this project's skills is **dead**. | **Surface it in the handoff.** Work touching that repo must run **on the box** (`ssh`, or a session started there) — reading its files, running its scripts, and committing in it all happen there. Do **not** clone it locally to "fix" the path: that creates a second copy, and the box copy is the real one. |
| `UNRESOLVABLE` | Not local, **and the box answered that it does not have it either.** Genuinely nowhere. | **Report it and stop** before doing work that depends on it. Do not invent a path, do not recreate the tree, do not substitute the current repo. |
| `UNKNOWN` | Not local, and **you could not ask the box** — no `box.json`, or it did not answer. | **Report it; do not conclude anything.** You have no evidence about the box, and no evidence is not evidence of absence. Say "could not resolve" and why. Never upgrade this to `UNRESOLVABLE`. |

> **Why `UNKNOWN` exists at all.** This step used to treat "the probe returned nothing" and "the probe
> could not run" as the same answer. `box.json` is a **local workstation artifact** — this machine's
> pointer *to* the box — so running this step **on the box** finds it correctly absent, produced an
> empty box list, and routed **every** referenced repo to `UNRESOLVABLE → stop`. The two repos it hit
> hardest were the two the paragraph above declares local-only by policy: their absence was the
> intent, reported as a blocker. An empty answer and an unasked question are different facts, and a
> step that conflates them manufactures blockers out of correct states.

> **The one thing you must never do:** treat a dead absolute path as an invitation to improvise. A
> skill that says `/home/<user>/<repo>/…` for a repo that now lives on the box is **stale
> documentation, not an instruction** — resolve where the repo actually is, and if that is the box,
> say so plainly rather than quietly doing the work somewhere else.

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
```

- `ok` → proceed; omit from the handoff.
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

**Open Work — ALWAYS render this table. It is the default, not an extra.** The operator runs
several projects and does not carry this one's task numbers in their head. See § Writing for the
Operator: an ID alone is not a description.

 Scope: ALL open work, in three distinct buckets — current, stuck, deferred. Every open task
 and every backlog item appears in exactly one of them; nothing tracked is ever invisible at
 session start.
 "Stuck"    = in_progress or blocked in a phase that is not the current one — started (or
              obstructed) and then abandoned; precisely the ones that go stale unnoticed.
 "Deferred" = pending in a phase that is not the current one, plus every progress.json
              `backlog` item. Deferred is BY DESIGN — rendering it as "stuck" miscasts
              planned work as neglect, and not rendering it at all is how a 5-item backlog
              sat structurally invisible for months until the operator asked where it was.

 "In plain words" is not the task's name repeated. It is what it MEANS, in language that
 needs no other document open. If you cannot write it, you do not understand the task yet.]

**Phase X — [phase name in plain words]** (N open)

| Task | In plain words | State |
|------|----------------|-------|
| X.Y | [what it actually is — no jargon, no invented labels] | working on it now |
| X.Z | [...] | not started |

**Stuck elsewhere** (omit this block entirely if there is nothing)

| Task | In plain words | Stuck since | Why it's still here |
|------|----------------|-------------|---------------------|
| A.B | [...] | YYYY-MM-DD | [blocked on what, or: abandoned mid-flight] |

[If a stuck task has been pending long enough that its context is likely stale, say so —
 that is a candidate for the disposition rules in /update-progress Step 3a, not a task to
 quietly keep carrying.]

**Deferred work** (omit ONLY if there are no non-current-phase pending tasks AND the backlog
is empty — an empty section is noise, but a silently omitted non-empty one is invisible work)

| Where | In plain words | Open |
|-------|----------------|------|
| Phase A — [phase name in plain words] | [what the phase is for, one line] | N tasks |
| Backlog | [each backlog item, in plain words — these have no task IDs and no other surface] | — |

[Phases summarize to one line each; backlog items are listed individually — the backlog has no
 phase file, no task IDs, and no other rendering surface, so this table is the only place the
 operator ever sees it.]

### ⚠ Remote-resident repos  (omit ONLY if Step 2.5 found none needing action)
[repo → REMOTE (box): this project's skills reference it by a local path that is DEAD.
 Work touching it must run on the box. Name every one — an agent that does not know this
 will improvise into the current repo and report success.]
[repo → UNRESOLVABLE: not local, and the box answered that it is not there. Do not start
 work that depends on it.]
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
1. **Continue** - proceed with Task X.Y
2. **Redirect** - work on different task
3. **Discuss** - talk about something first (may lead to new tasks)
```

**Use AskUserQuestion tool.**

**If user chooses Discuss:**
- Have the discussion
- If work is identified, ask: "Should I add this as tracked tasks?"
- If yes, follow `/add-work` workflow
- If no, just note in session_notes.md for later

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
