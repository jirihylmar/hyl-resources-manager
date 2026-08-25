---
name: consult-codex
description: Ask OpenAI Codex for an independent second opinion on this project's work — a reviewer that reads the repository cold in a transient clone, checks claims against live AWS through a read-only server bound to this project's own account, and argues with you (the author) for up to three rounds. Agreement becomes a Proposed Work table for the operator; nothing here ever writes progress.json. Invoke when asked for a second opinion, a review of the current task or a phase, or "what does Codex think"; also when a task's verify step reads as prose that nothing checked.
---

# consult-codex — a second reader with the same reach

You are the **author**. Codex is the **reviewer**. The operator is the only one who can turn what
you agree on into tracked work. The runner `consult.sh` beside this file does every mechanical
step; you do the thinking between rounds.

## What this is for

Every project here was built by Claude Code and is checked by Claude Code. This skill gives the
project a reader that did not write it, that has the same infrastructure reach you have (the AWS
account this project's Claude uses, read-only), and that must show its evidence. The design and
its dry run are in `syndicate-playbooks-examples`: `docs/consult-loop.md` and the first cycle in
that repo's `consult_notes.md`.

<!-- procedure:begin -->
## Procedure

**0. Preconditions you can see before starting.** The working tree is clean and committed
(`git status` empty); this machine has run `bash .claude/skills/consult-codex/prepare-host.sh --apply`
once — the settings change that belongs to the host, made by the host's own session from the
distributed copy, exactly as `/syndicate-connect` does for the ingest route. If either is false,
`open` will refuse with a named code and record the refusal — that is correct, not a failure to
work around.

**1. Open.** Pick the target — `task:<id>` (default: the current task), `phase:<key>`,
`file:<path,…>`, or `commit:<range>` — and run:

```bash
bash .claude/skills/consult-codex/consult.sh open task:<id>
```

It runs preflight (Codex present and logged in, host prepared, no shadowing personal skill, clean
checkout, fetch + fast-forward, `progress-check`, `.claude/` present, no Codex roots in the tree,
AWS binding by command with exactly one candidate or `no-infra`), clones the checkout to
`~/.cache/consult/<project>/clone` with no remotes and the commit guard re-armed, proves the
reviewer's AWS identity equals the declared account, extracts the claims from the target, and
appends the opening record to `consult_notes.md`. A refusal writes opening + closing
`not-reviewed:<code>` records, commits and pushes the log, and exits 3. Do not retry a refusal;
report it.

**2. Round 1.** `consult.sh review`. The reviewer reads the clone with no transcript of your
session, checks the claims, and ends with a `LEDGER:` block marking each claim examined /
unavailable / skipped. Its output is appended to the log after a full posture check of both
trees; a breach is recorded as a finding against the reviewer, never hidden.

**3. Respond.** Read the round in `consult_notes.md`. **Check the reviewer's citations against
the real files before you answer** — a refutation built on an unverified claim is worse than
none. Write your response to a file: what you accept and how it changes, what you narrow, what
you reject and why. Then `consult.sh respond <file>` — it appends your entry and runs the next
reviewer round on the same Codex thread. At most three reviewer rounds.

**4. Agreement → the table.** When the reviewer's remaining points are closed, ask it (in your
last response) to produce the `/add-work` Step 5 *Proposed Work* table — at most 7 rows per
batch, each a single deliverable under 30 minutes with an observable verify. Check the sizing
yourself; the reviewer will label multi-session work `small` until pushed.

**5. Present to the operator.** This is the only checkpoint. Show the table and ask: *add it?*
Two agents agreeing is a discussion; only the operator's explicit statement authorizes tracked
work (`/add-work` § Authorization Boundaries).

**6. Close.** One of five outcomes, always recorded:
- operator said add it → run `/add-work` yourself (its commit may include `consult_notes.md`),
  then `consult.sh close agreed-applied <result-sha>` — the reviewer rechecks in a fresh clone at
  that SHA, and the closing record names it;
- nobody present to approve → `consult.sh close agreed-proposed` — the table stays in the log,
  and `/open-work` renders it as open;
- nothing to change and the ledger proves claims were examined → `close agreed-nothing`
  (refused and recorded as `not-reviewed:NO-PROOF` if the ledger is empty);
- disagreement survived the cap → `close disputed`, both positions already in the log;
- preflight refused → already closed as `not-reviewed:<code>`.

`close` commits `consult_notes.md` alone, fast-forward pushes it (recording
`LOG-COMMITTED-NOT-PUSHED` if the push fails), and destroys the clone. Nothing in this procedure
writes `progress.json`; only your own `/add-work`, on the operator's word, does.
<!-- procedure:end -->

## When a record cannot be committed — the publication transaction

`close` and a refusal both end by committing `consult_notes.md` alone. If that **commit** fails —
a pre-commit hook that refuses, an unset git identity — the record is **rolled back out of the log
and out of the git index**, the runner exits **2**, and it says so. Nothing uncommitted is left in
the checkout, because an uncommitted record is a record that can never be published (its cycle's
state is gone) and that makes the next cycle in that project refuse `DIRTY-CHECKOUT`.

What survives a rolled-back publication is what you need to retry it: the state directory and the
clone under `~/.cache/consult/<project>/`. **A close retries with the same `close` command; a
refusal retries by re-running the same `open`** — a refusal never sets the `opened` marker, so
there is no cycle for `close` to close. Both are idempotent: retrying after the commit problem is
fixed produces exactly one record, not two.

A failed **push** is a different thing and is not rolled back: the commit landed, so the log is
safe locally, and the runner records `LOG-COMMITTED-NOT-PUSHED` as its own commit and retries the
push once. Rejected alternative, for the record: leaving the record in the worktree for a later
invocation to commit. It would make an uncommitted record a legitimate state, collide with the
`DIRTY-CHECKOUT` preflight, and let one cycle's record be committed under another cycle's message.

## Where the host predicate lives

"Is this host prepared?" has **one** definition and it is in `prepare-host.sh`, callable on its own
as `prepare-host.sh --check-config`: both Codex config keys top-level, `project_doc_fallback_filenames`
exactly `["CLAUDE.md"]`, `project_doc_max_bytes` an integer at least 262144, and no copy of either
key nested inside a `[projects]` table. It reads, never writes, and needs no Codex. `consult.sh`
calls it and quotes its message into `HOST-NOT-PREPARED`; the behavioural checks that spawn Codex
(B and C) and the host-entry digest check (D) stay in the preparation run.

## What the reviewer may never do — and what happens if it does

Write into either tree, touch `progress.json`, commit, or push. Under bypass mode nothing
*prevents* this; the clone has no remote and its own object store, so a breach cannot reach the
real checkout or origin, and `consult-posture.sh verify` fingerprints both trees — refs, index,
worktree, ignored files, stash, and the log itself — after every round. A breach is appended to
the log as a finding against the reviewer.

## Files beside this one

| file | role |
|---|---|
| `consult.sh` | the runner: open / review / respond / close / status |
| `prepare-host.sh` | **once per machine**: prepends the two Codex config lines, installs the Codex-side entry `syndicate-consult-claude` into `$CODEX_HOME/skills/` with this copy's procedure digest embedded, and proves all of it behaviourally. The settings change happens on the host, from the distributed copy — never pushed to a host by hand |
| `host-entry.SKILL.md` | the template `prepare-host.sh` renders into `$CODEX_HOME/skills/syndicate-consult-claude/SKILL.md` — Entry A |
| `codex-here` | launches Codex with this project's AWS server injected read-only, bound from `~/.claude.json` by command; strips the shell of credentials |
| `consult-posture.sh` | clone / snapshot / verify / append / destroy — the 8-step posture sequence |
| `consult-log.py` | the log grammar: `validate` a log, `ledger` a round's claim coverage |
| `reviewer-prompt.md` | the round-1 prompt template |

## Refusal codes

`NO-TARGET` · `NO-CODEX` · `NOT-LOGGED-IN` · `HOST-NOT-PREPARED` · `SHADOWED` · `DIRTY-CHECKOUT` ·
`NOT-ORIGIN-LATEST` · `NOT-REVIEWABLE:progress-json` · `NOT-REVIEWABLE:no-claude-dir` ·
`NOT-REVIEWABLE:codex-roots-present` · `NOT-REVIEWABLE:NO-REVIEWABLE-CLAIMS` · `ACCOUNT-AMBIGUOUS` ·
`ACCOUNT-NOT-BOUND` · `ACCOUNT-MISMATCH` · `POSTURE-BREACH` · `CLONE-FAILED`. Every one is
recorded in the log and committed. Absence and ignorance are different, and both look empty.
