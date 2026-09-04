---
name: progress-check
description: Check progress.json for corruption that destroys data, preserve task and phase identity, require authored_by plus assigned_to on new work, and warn when a terminal task's semantic record changes. Invoke before committing progress.json or investigating missing, changed, malformed, stale, or unattributed work.
---

# progress-check

`progress.json` is the single source of truth for a project's state, and until 2026-07-30 nothing
verified it. **Five of 34 live projects were already damaged**, and no check anywhere could see it.

## Run it

```bash
python3 .claude/skills/progress-check/progress_check.py              # working tree
python3 .claude/skills/progress-check/progress_check.py --staged     # the bytes that would be committed
python3 .claude/skills/progress-check/progress_check.py --base none  # skip the append-only comparison
```

Exit `0` ok · `1` **FAIL, do not commit** · `2` could not check (file missing/unreadable).

It also runs at commit time, within three limits worth knowing. `.claude/hooks/pre-commit` invokes
it only when `progress.json` is **staged** for the commit being made (`git diff --cached
--name-only` lists it) — an edit that sits unstaged in the working tree is never checked, and
neither is a commit in which `progress.json` is not among the staged files, whatever else is. And
the hook **fails open**: if `python3` is not on `PATH`, or
`.claude/skills/progress-check/progress_check.py` is not at the repo's top level, it skips the
check silently and the commit goes through. That is deliberate — blocking every commit because an
interpreter is absent would be a worse failure than the one being prevented — but it means a host
without either gets no check and no message saying so. And the hook runs only in a clone whose
`core.hooksPath` is `.claude/hooks` — `/distribute-defaults` sets that per clone (`arm_hookspath`);
a fresh clone has no hook until then. When it matters, run it by hand.

## What it fails on

<!-- No count in this heading, and that is deliberate. It read "three corruptions … plus two
     prospective rules" while the table below listed five failures and the code enforced more
     than either number; nothing would have caught the drift. A hand-maintained total is the rot
     this repo keeps curing. The table is the index; `progress_check.py` is the source of truth. -->

| Failure | Why it matters |
|---|---|
| **Does not parse** | Every reader gets nothing. `Extra data` specifically means content was appended *after* the closing brace — usually a whole phase written outside `phases`. The text is in the file; the document does not contain it. |
| **Duplicate key in one object** | **This is valid JSON.** `json.load` keeps the last and drops the first, silently. A parse check passes and the value is already gone. |
| **Duplicate task id in a phase** | Two records claim to be the same task; which one any tool reads is arbitrary. |
| **A task or phase present in the last commit is absent** | Not necessarily data loss — the previous commit still holds a removed task's text, and an empty phase has none to lose: this is the framework's oldest rule — *never remove a task, mark it superseded* — the **append-only policy**, enforced mechanically instead of by prose. It compares ids only, so it refuses the removal of an **empty** phase exactly as it refuses a full one (`phase 'x' existed in the previous commit and is now GONE (0 task(s) with it)`). Uniform on purpose: the checker cannot judge whether what vanished mattered, so it does not try. — And, since 2026-08-06, an `estate_notice` marker stripped from a task that kept its id, for the same reason: the next central run would append a second copy. |
| **A newly added phase or task lacks `authored_by` or `assigned_to`** | Operator decision 2026-08-29: the record must say who wrote an entry and whose job execution is. This is prospective, detected by comparison with the previous commit; historical work is not rewritten to adopt a new schema. The two values may differ. |
| **Required root metadata still holds an unresolved `{{TOKEN}}`** | `project`, `description` and `created_at` say what this project is; a template token there means the record describes the template it was copied from. Shipped since before this rule was written down. With no committed base — the shipped bootstrap and both example playbooks, which carry the tokens on purpose — it downgrades to a warning, so a freshly bootstrapped project is not blocked before it has substituted anything. |
| **An `unattended` block that describes an operation incompletely** | `PROJECT_CHARTER.md` section 11 makes the difference between a watched operation and an unwatched one a fact about recorded state. A half-described operation reads as supervised and is not. Strict rather than prospective, and deliberately so: the key did not exist before 2026-09-02, so there is no historical vocabulary to tolerate. The required fields and the permitted values live in `progress_check.py` and are not restated here. |
| **A phase that becomes TERMINAL in this commit with no completion date** | Closing a phase is the moment its date is known, and a phase closes rarely — so the rule costs almost nothing and the record keeps saying when the work ended. Prospective: a phase already terminal in the previous commit is left alone. The same rule on *tasks* is a warning, not a failure — see below. |
| **`current_task` written as an object or a list** | Every reader stringifies this field, so a container publishes `[object Object]` as the project's current work and no task id can ever match it. Prospective, and narrowly so: it blocks at the commit where the shape ENTERS history, and warns where the previous commit already carried one (one live project has, since 2026-07-07) or where the previous commit cannot be read. A project this repository must never write may always commit the fix to its own file. |
| **A `relations` block the collector cannot read** | `relations` is how a manager declares what it manages, and it is the *only* place that edge is written — nothing else in the estate records it. A shape the reader rejects discards the whole declaration, or silently drops one member from it, while the repository still reports success. Optional throughout: no block at all is silent, and `"members": []` is a legitimate positive claim. See *The declared relations block*. |

## The project-identity and current-work block

Everything above is about *not losing what is written*. This section is about the handful of root
keys that say what the project **is** and what it is **doing** — the only fields a reader outside
the project can use, and the ones the estate dashboard reads verbatim
(`syndicate-dashboard/collector/src/progress.ts`).

Severity is not uniform here, and the rule that sets it is worth stating once because every row
below is derived from it: **a field's severity may not exceed what the estate is permitted and able
to fix.** A field a project can fill from proof it already holds may block a commit. A field only
the operator can decide is reported, never enforced. A field nobody is permitted to write is not
reported at all — a complaint no one may act on is noise, and noise is how a checker gets switched
off.

| Root key | What a good value is | Who fills it | If it is wrong |
|---|---|---|---|
| `project` | Non-empty single-line string naming this project. Default it to the **repository name** — `/setup` § Naming Convention already makes folder = repo = origin a rule, so the repo name is unique at the hosting provider and inherits that uniqueness for free. | The project itself, once, at setup; afterwards only the operator. No other repository ever writes it. | **FAIL** on an unresolved `{{TOKEN}}` once a committed base exists. Nothing else about the name is enforced — see *What is deliberately not enforced about the name*. |
| `description` | One sentence saying what the project is for. It is the dashboard's only project-level prose. | The operator, at setup, refreshed when the specification is approved. | **FAIL** on an unresolved `{{TOKEN}}` (same rule as `project`). Nothing may compose one: no file on disk proves a project's purpose. |
| `created_at` | ISO-8601 date or timestamp, set once. | Setup. | **FAIL** on an unresolved `{{TOKEN}}` (same rule). |
| `last_updated` | ISO-8601 date or timestamp; the input to the staleness comparison below. | `/update-progress` when it closes a task. | Warning only — see the next section. |
| `current_task` | **`string \| null`.** When a string: the `id` of exactly one task under `phases`. `/open-work` treats anything longer than 40 characters as prose rather than a pointer and says so. | The executor at session start and `/update-progress`; in multi-agent setups, the orchestrator alone. | An object or list **FAILS prospectively** (table above). A string matching no task id is a **warning**, and is suppressed entirely when no task in the file is identifiable — with no ids to compare against, the comparison has nothing to say. `null` or absent is **SILENT**. |
| `current_phase` | `string \| null`; when a string, a key of `phases`. | As `current_task`. | Not checked here at all. `/open-work` reports a stale, absent or non-existent pointer when it renders. |

Per task, the record says: `id` (non-empty, unique within its phase, never changed — enforced
above), `name` (a one-line statement of what it delivers; this is the string the dashboard shows as
the project's current work), `status` from the project's own vocabulary (this checker enforces
none), `authored_by` and `assigned_to` on every new entry (enforced above), and — once the task
reaches a terminal status — the date it closed, as `completed_at` or the older `completed`.

**`null` means PARKED, and parked is a legitimate state.** No task is claimed. `/open-work` says so
in as many words when it renders — *"that is a legitimate state at a clean close; it is reported so
it cannot be mistaken for a lost pointer"* — and `/start-session` forbids modifying `current_task`
or `current_phase` outright. So nobody is permitted to fill it, and a checker that complained about
it would be demanding a fix no reader of the message is allowed to make. Measured 2026-09-02 across
15 local projects: **6 parked (`null`), 1 an object, 8 resolving strings, 0 absent** — the silence
is load-bearing for 6 of 15, and the object is the one shape that is genuinely unreadable.

**A task that becomes terminal with no completion date is a WARNING, not a failure — this phase.**
Measured 2026-09-02: 415 of ~2872 terminal tasks estate-wide (14%) carry no `completed_at` or
`completed`, including 24 of 319 in this repo's own file. A *phase* becomes terminal rarely, so
blocking there costs nothing; a *task* becomes terminal in nearly every `/update-progress` commit,
so blocking here would stop roughly one commit in seven — the "disabled within a day" signature the
design rule at the top of `progress_check.py` was written against. The promotion criterion is
written beside the rule in the code: promote it to a failure once two consecutive full-estate probe
runs show zero new dateless terminal transitions.

**Per-task dates are not what the dashboard reads.** The collector reads root `last_updated` and
the resolved current task's id, name and status — nothing else. The date is required because *this*
checker's freshness comparison reads it, and because a record of closed work that cannot say when it
closed is not a record.

### What a local check can and cannot prove about the name

A project cannot see the estate, so it cannot prove its own name is unique. What it can prove is
that the name is present, substituted and its own — and that is the whole of what is enforced here.

Global identity does not come from the name. `deriveIdentity`
(`syndicate-dashboard/contracts/src/identity.ts`) returns `origin:<normalized origin>` with
`verified: true` **whenever a git origin normalizes**, and falls back to `host:<host>/<display
name>` only where there is none. Every project measured in this estate on 2026-09-02 had a GitHub
origin, so for all of them identity is unique by construction and the display name is a **label**,
not a key. Estate-wide name collision is a separate, weaker signal computed only where every project
is visible at once (`classifyConflicts` in the same file), never by a project about itself.

The live cost of a placeholder or missing name is therefore narrower than it first looks, and worth
stating exactly so nobody argues from the overstatement: the collector nulls the placeholder, records
a `project_name_unavailable` read error, and labels the project's row by its **directory basename**
on whichever machine was scanned. The project appears on the board under a per-machine nickname with
an error attached. That is a real defect and it is why the token blocks — it is not a lost identity.

### What is deliberately not enforced about the name

No length limit, no reserved-word list, no trim rule, no capitalisation policy. The three that were
actually proposed — a maximum length, a list of reserved generic names, and an untrimmed value —
were measured across the whole estate on 2026-09-02 and had **zero** offenders each. This module
does not add a failure that fires on nobody; that is the same standard applied everywhere else here.
Style observations belong in an estate survey, which costs nobody a commit.

```json
{
  "project": "myproject-voucher-portal",
  "description": "Issue and redeem prepaid vouchers for the myproject storefront.",
  "created_at": "2026-01-14",
  "last_updated": "2026-09-02",
  "current_task": "2.3",
  "current_phase": "phase_2_redemption"
}
```

Pinned by `scripts/test-progress-check-metadata-contract.sh` in the central repo.

## The declared relations block

`relations` is **optional**, and its absence is not a claim. A manager repository uses it to declare
what it manages — downward only, in its own `progress.json`, never the other way round — so exactly
one repository writes each edge and two machines can never disagree about it. The declaration
travels with the clone, so it needs no change to any host's collector configuration.

```json
"relations": {
  "version": 1,
  "members": [
    { "origin": "https://github.com/org/member.git", "relation": "governed", "note": "why" },
    { "path": "backend", "relation": "nested" }
  ]
}
```

`origin` joins across hosts; `path` joins inside this repository, on a host that holds it. At least
one of the two is required — a member naming neither can be joined to nothing. The relation word is
**yours**: `nested`, `governed`, `metadata-governed` and `orchestrated` are in use today and a new
one is legal, so nothing here judges it.

**`"members": []` is a positive claim that this repository manages nothing; omitting the block says
nothing at all.** Those are different facts and the dashboard keeps them apart — it will never
render silence as a claim. So a file with no `relations` key passes in complete silence, and so does
an explicit `null`, which the reader also treats as absence.

| It **fails** on | Why that is a failure |
|---|---|
| `relations` present and not an object; `version` missing or not `1`; `members` missing or not an array | The **whole block** is discarded and the repository publishes as `malformed`. Every edge named inside it goes unpublished, and the operator who wrote them is told nothing. |
| a member that is not an object; a member with no non-empty `relation`; a member naming neither `origin` nor `path` | **That member** is dropped. The declaration survives with a hole in it, which reads on the board as a manager governing fewer repositories than it says it does. |
| a member whose ONLY locator is a `path` that is absolute or contains a `..` segment | A manager may only declare what it **contains**, so the reader discards such a path — and with no `origin` beside it the member then names nothing at all and goes unpublished. |
| an unsubstituted `{{TEMPLATE_TOKEN}}` in a member's `relation`, `origin`, `path` or `note` | The reader treats a bare token as no value, exactly as it does for project metadata, so the member is dropped without a word anywhere. |

| It **warns** about | Why that is only a warning |
|---|---|
| a member repeating another member's `origin` or `path` | Nothing is lost — both entries publish — the member is merely drawn twice. |
| a `note` longer than 200 characters | Only the *published* copy is truncated; the full text stays in this file, so nothing is destroyed. |
| an `origin` that resolves to no host plus repository path | Nothing local can reach a remote to prove an origin wrong, and the vocabulary of git remotes is open. It is reported because such an origin joins to nothing — never blocked. |
| an unusable `path` **beside a usable `origin`** | The reader ignores the path and joins the member by its origin, reporting nothing discarded. The declaration still says something untrue about where the member lives, so it is reported — and never blocked, because blocking a commit the reader accepts is the one mistake this guard may not make. |
| more than 100 members | The reader publishes the first 100. Nothing in this file is lost, but the count on the board becomes a cap rather than a total. |
| an `origin` or `path` that is present but empty, or not a string | The reader treats it as no value. The member survives on its other locator; it is only reported so the operator knows one of the two joins is not working. |

The split is this file's own rule applied again: **a failure has to be unambiguous, and has to cost
the operator something they cannot see.** Both columns are read out of the implementation that
consumes the block — `syndicate-dashboard/collector/src/progress.ts` (`parseRelations`,
`declaredMember`, `declaredPath`) and `contracts/src/schema.ts` (`validateMember`) — rather than
invented here. The dividing line is not "what the reader discards" but **what the reader discards
with nothing left over**: an unusable path beside a good origin loses nothing, so it warns, while
the same path alone loses the member, so it fails.

Strict rather than prospective, on the `unattended` precedent: no `progress.json` in the estate
carried this key before 2026-09-03, so there is no historical vocabulary to tolerate and no project
can be blocked by a shape it has already committed. Measured 2026-09-04 across every reachable
project on both hosts — the ones that declare pass, the ones that do not are passed in silence.

Pinned by `scripts/test-progress-check-relations.sh` in the central repo.

## Plus one thing it warns about: a stale `last_updated`

Since 2026-08-25 the check also compares `last_updated` against the newest completion date it can
find, and **warns** if the file reports itself as older than the work inside it. Found here on
2026-08-21: `last_updated: 2026-08-21` while phase 30's tasks carried `completed_at: 2026-08-25`.
Nothing anywhere compared the two.

It is a **warning, never a failure** — exit stays `0` and commits are not blocked. A stale date
destroys nothing, and this checker is armed as a pre-commit hook across the whole estate; a fifth
failure would stop commits everywhere over a cosmetic field. The remedy is `/update-progress`,
which refreshes `last_updated` when it closes a task.

What it looks at, and what it stays quiet about:

- Both `completed_at` **and** the older `completed`, on tasks **and** on phases. In this repo's own
  file, 158 tasks use the first spelling and 58 use the second, and the two sets are disjoint.
- Dates truncated to `YYYY-MM-DD`, so `2026-08-25` and `2025-12-20T10:00:00Z` compare alike.
- **Absence is not staleness.** No `last_updated`, a `null` placeholder, an unsubstituted
  `{{CREATION_DATE}}` template placeholder, or no completion date anywhere means the check simply
  does not apply and says nothing. (`progress.json.bootstrap` ships `{{CREATION_DATE}}`, so without
  that second carve-out every freshly bootstrapped project would open its life complaining about a
  value the framework itself wrote.)
- A value that is not shaped like an ISO date is reported in a **separate** warning that names the
  offenders (first three, plus a count) and is left out of the comparison. If one of them is a
  compaction sidecar pointer (`archived: docs/_archive/progress-sidecars/…`) the warning says so —
  the date now lives in the sidecar and this file no longer states when the work finished.
- Status is not consulted: a task marked `superseded` that carries a completion date still counts.
  This checker enforces no vocabulary, here as everywhere else.

**You will see it at commit time.** `--quiet` suppresses the all-clear line and nothing else:
warnings go to stderr, and the pre-commit hook prints them under *"progress-check notes; NOT
blocking this commit"*. Until 2026-08-25 `--quiet` swallowed warnings outright, and the hook —
the only automated caller — passes `--quiet`, so a warning was in practice printed to nobody at
the one moment it was written for.

Pinned by `scripts/test-progress-check-freshness.sh` in the central repo (16 cases, including the
shipped bootstrap and both example playbooks staying silent).

## Terminal-task drift warning

Every **non-terminal** task is editable planning state, including work that is planned, ongoing,
blocked or deferred. Findings may refine, combine, divide, reassign, re-scope or relocate it so the
open-work landscape remains coherent and phases can close. The checker deliberately says nothing
when semantic fields change on such work.

Closure is the immutability boundary. When a task was already terminal in the previous commit —
`complete`, `completed`, `superseded`, `done`, `closed`, `dropped`, `cancelled`, `canceled`,
`resolved`, `obsolete` or `abandoned` — the checker **warns** if its `name`, `description`, `verify`,
`verify_result`, `dependencies` or `depends_on` changes. These fields state what the historical
record meant and what evidence closed it. Later work belongs in a non-terminal task that links back.

Candidate-only terminal status does not warn: the same commit may legitimately refine open work and
then close it. The next commit sees it as history. The warning never blocks because Git still holds
the previous bytes and historical projects use varied schemas; it makes the retelling visible at
review instead of pretending it did not happen. Warnings are capped after three full entries.

Pinned by `scripts/test-progress-check-mutability.sh` in the central repo.

## What it deliberately does NOT enforce

No retrospective schema migration, no status vocabulary and no style policing. Measured across 34 real projects: `phases` is a dict in 30 and a
**list** in 2; `tasks` is a list in most and a **dict** in one; some tasks are bare strings; status
values include both `complete` and `completed`. All of that is tolerated.

**A checker that enforced the template's shape would block commits in real projects and be switched
off within a day** — which is worse than no checker. It fails only on things that lose data, plus
the append-only and new-entry identity rules above.

## The three corruptions it was built from

1. **A phase appended outside the document** — found in two projects, committed **2026-03-11** and
   **2026-03-26**, invisible for four months. An agent wrote a phase, committed it, and reported
   success; the phase has never existed as far as any tool is concerned.
2. **A duplicate key from an orphaned field** — an edit spliced one task's tail into its neighbour,
   leaving two `verify` keys in one object. Valid JSON. The real value was silently replaced.
3. **A missing comma** — the cheap one; it does not parse, so it is loud.

Only (3) announces itself. (1) is loud but was never checked. **(2) is invisible even to a parse
check**, which is why the checker parses with `object_pairs_hook` instead of plain `json.load`.

## If it fails

Fix the file and re-stage it. The repair is never blocked — only the damage is. `--no-verify`
exists, but using it commits state you have been told is broken.

An **already-damaged** file does not hold the repo hostage — the guard fires only on a staged
`progress.json` (above), so unrelated work still commits. It stops the next person who writes the file.

## Related

- `/update-progress` — the conservative edit rules this enforces mechanically (append-only, never
  remove, never change ids; a warning when a terminal task's semantic fields
  drifts). Reordering is forbidden there and not detected here.
- `/open-work` — renders the tables from this file; exits 2 when it cannot read it. If `open-work`
  reports it cannot read `progress.json`, run this to find out why.
