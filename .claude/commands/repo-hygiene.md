---
description: Periodic repo consolidation pass — verify every docs + skills file is canonical and current, ground a rotating slice of operational claims against the implementation, enforce naming/terminology discipline, archive stale material, reconcile indexes and knowledge surfaces, compact progress.json. Triggered by the hygiene clock at session start; not a scheduled chore.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion
---
<!--
  Centrally distributed by /distribute-defaults from syndicate-playbooks-examples.
  Project-specific additions go in .claude/local-overlays/<this-filename> as
  splice fragments (see /distribute-defaults for the overlay format).
  Direct edits to this file will be flagged on the next distribution.
-->

# Repo Hygiene — periodic consolidation pass

**Why this exists.** One-off documentation audits decay: within weeks of a big cleanup, working
dirs re-accumulate, docs drift from the code they describe, skills reference tools that moved,
indexes go stale, and progress.json grows without bound. The fix is not a bigger audit — it is a
**standing, triggered pass** that every repo runs when its hygiene clock expires, so the tree never
drifts far enough to need a crusade.

**The standard this pass enforces:**
- `docs/` contains **only canonical, current methods** (plus clearly-separated trail:
  `_archive/`, incidents, audit records). A doc that describes yesterday's system is corrected or archived.
- **Skills** (`.claude/commands/`) are current: every referenced tool/path/procedure exists and
  matches reality; no two skills duplicate one capability.
- **Indexes are true**: whatever index surfaces exist (CLAUDE.md pointers, a skill picker, an
  MCP/advisor knowledge base) reflect the real file set and route correctly.
- **progress.json stays lean**: append-only is sacred, but verbose bodies of long-completed work
  live in committed sidecars, not in the working file.
- **Timeless canon**: durable instructions carry no session/phase/task numbers — process metadata
  lives in progress.json / session_notes / incidents / `_archive` (the trail), never in canonical
  method docs, skills, or externally-served knowledge bases.
- **Content grounded**: the operational claims inside skills and canonical docs — cited file paths,
  CLI flags, deployed-resource names, payload/query shapes, documented commands — are verified
  against the actual implementation, not read-and-nodded. Index-level checks cannot see this rot:
  a repo has passed every clock/ref/index gate while carrying dozens of confirmed grounding defects
  (flags that don't exist, queries against nonexistent table models, procedures invoking retired
  resources, example payloads that half-execute a pipeline).
- **One name per concept**: a ratified terminology registry gives each concept ONE grep-friendly
  canonical name; competing synonyms and bare ambiguous words are flagged. The operating test:
  a human's search and an agent's grep must land on ALL and ONLY the relevant places with one
  keyword — that is how both humans and agents verify anything.

**Cadence**: triggered, not scheduled. `/start-session` Step 2.7 surfaces a banner from the clock
in `.claude/hygiene-state.json` alone (`last_pass` >30 days → due; >60 days or the file absent →
MUST-RUN-before-new-work; a `grounded` map present but no `last_pass` → content-baseline-missing).
The Step 0 quick checks below run inside THIS pass, not at session start. **Content consolidation
does NOT wait for this clock**: `/update-progress` Step 2b grounds one rotating file at every
session close; this pass baselines that rotation (first run — trigger it manually once in an
existing project after receiving these defaults) and catches up whatever the session cadence missed.

---

## Step 0 — Mechanical quick checks (safe, read-only)

```bash
python3 - <<'PY'
import json, os, re, sys, time
from pathlib import Path
root = Path.cwd()
findings = []

# (A) hygiene clock
# `last_pass` may be ABSENT or explicitly NULL — both mean "no full pass yet", and
# /start-session's clock check documents that state as legitimate. Read it the same way here.
# (`st.get("last_pass", "1970-01-01")` returns None for a present-but-null key — the default only
# fires when the KEY is missing — and strptime(None) raises TypeError. Because check A runs first
# and this block is one script, that crash took B/C/D/F/G down with it: the whole quick-check
# reported nothing at all on a state the sibling file calls normal. Do not "simplify" this back.)
state_p = root/".claude/hygiene-state.json"
if state_p.exists():
    st = json.loads(state_p.read_text())
    lp = st.get("last_pass") or None
    if not lp:
        findings.append("A: no full hygiene pass recorded yet (last_pass absent/null) — run /repo-hygiene to set the clock")
    else:
        try:
            age = (time.time() - time.mktime(time.strptime(lp, "%Y-%m-%d"))) / 86400
            if age > 30: findings.append(f"A: hygiene pass overdue ({age:.0f} days since {lp})")
        except (ValueError, TypeError):
            findings.append(f"A: last_pass is not a YYYY-MM-DD date ({lp!r}) — cannot age the clock; fix or clear it")
else:
    findings.append("A: hygiene never recorded (.claude/hygiene-state.json absent)")

# (B) stale working dirs under docs/
for d in sorted((root/"docs").glob("*")) if (root/"docs").exists() else []:
    if d.is_dir() and re.match(r"^(phase-|wip-|tmp-|scratch)", d.name):
        findings.append(f"B: working dir docs/{d.name}/ — extract-then-archive when its work closes")

# (C) broken repo-relative doc refs from live surfaces (docs + commands)
ref_re = re.compile(r"(?<![\w/])(docs/[A-Za-z0-9_\-./]+\.(?:md|tsv|json|py|png|html))")
# The rotation set must be every file a reader takes as current — see
# /update-progress Step 2b. Restricting it to docs/ + .claude/commands/ silently
# excluded README.md, CLAUDE.md, IMPLEMENTATION_PLAN.md and every ops/ runbook,
# which is how one project's README went on describing a deleted host for days.
surfaces = (list((root/"docs").rglob("*.md")) + list((root/".claude/commands").glob("*.md"))
            + list((root/"ops").rglob("*.md"))
            + [root/n for n in ("README.md", "CLAUDE.md", "IMPLEMENTATION_PLAN.md")])
surfaces = [p for p in surfaces if p.exists() and "_archive" not in p.parts]
seen = set()
for f in surfaces:
    if "_archive" in f.parts: continue
    try: text = f.read_text(errors="ignore")
    except OSError: continue
    text = re.sub(r"```.*?```", "", text, flags=re.S)  # skip fenced code — path strings inside examples aren't live refs
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)  # skip HTML comments — instructional example paths aren't live refs
    for m in ref_re.finditer(text):
        ref = m.group(1).rstrip(".,)")
        if ref in seen: continue
        seen.add(ref)
        if not (root/ref).exists() and "..." not in ref:
            findings.append(f"C: {f.relative_to(root)} -> {ref} (missing)")

# (D) progress.json weight
pj = root/"progress.json"
if pj.exists():
    kb = pj.stat().st_size/1024
    if kb > 300: findings.append(f"D: progress.json {kb:.0f}KB (>300KB) — compaction due (Step 4)")

# (F) process metadata leaked into canonical surfaces (sizes the Step 3 de-phase slice)
#
# SCOPE: project-owned surfaces only. `.claude/commands/` is EXCLUDED by construction.
# Those are centrally distributed defaults, and "Phase 1", "task 2.3" etc. inside them are the
# ENGINE'S OWN DOMAIN LANGUAGE in worked examples — correct content, not leakage. The check used to
# include them and fired on exactly that: 16 of 21 hits in one real pass were generic examples inside
# defaults. Worse, it was unactionable BY CONSTRUCTION — it pointed the agent at the one set of files
# the same skill forbids it to hand-edit (fix them centrally, or via an overlay; never in place).
# A check whose only remedy is a forbidden act is noise that trains agents to ignore findings.
meta_re = re.compile(r"\b(?:Phase|Session)\s+\d+\b|\btask\s+\d+\.\d+\b", re.I)
mcount = mfiles = 0
skipped_defaults = 0
for f in surfaces:
    if "_archive" in f.parts: continue
    if ".claude" in f.parts and "commands" in f.parts:
        skipped_defaults += 1; continue
    try: text = f.read_text(errors="ignore")
    except OSError: continue
    n = len(meta_re.findall(text))
    if n: mcount += n; mfiles += 1
if mcount > 20: findings.append(f"F: {mcount} phase/session/task refs across {mfiles} project-owned canonical files — de-phase slice due (Step 3)")
# Report the exclusion rather than hiding it — a silent scope cut reads as "clean" when it is "not looked at".
if skipped_defaults: print(f"   (F: skipped {skipped_defaults} file(s) under .claude/commands/ — distributed defaults; their phase/task vocabulary is the engine's own and is not leakage)")

# (G) terminology registry presence (Step 3a)
if (root/"docs").exists() and not list((root/"docs").rglob("terminology.md")):
    findings.append("G: no terminology registry under docs/ — bootstrap one (Step 3a)")

for f in findings: print(" -", f)
print(f"\nHYGIENE-CHECK findings: {len(findings)}")
PY
```

If the project ships its own richer checker (e.g. a `tools/docs_currency_check.py`), run that too —
project checkers are authoritative over this generic one; this one is the floor every repo gets.

**(E) Overlay discipline — establish provenance BEFORE you classify anything.**

> **Absence of an overlay is not evidence of a hand-edit.** An edited-looking default with no overlay
> is *exactly as consistent with* a `/distribute-defaults` run that has not been committed yet. In
> the working tree those two are **byte-identical** — nothing distinguishes them, and you cannot
> compare against canonical yourself (`syndicate-playbooks-examples` is local-only by policy and is
> not reachable from the box). A real pass inferred "edited + no overlay = hand-edited", classified
> two legitimate central updates `divergent`, and recommended **reverting** them. The operator caught
> it: *"this is not divergent. its simply the centraly managed skills were updated."* Had that been
> followed, real work would have been destroyed.

**Step 1 — read the delivery record.** `/distribute-defaults` writes
`.claude/distribution-manifest.json` recording, per file, the sha256 of the exact bytes it delivered:

```bash
python3 - <<'PY'
import json, hashlib
from pathlib import Path
m = Path(".claude/distribution-manifest.json")
if not m.exists():
    print("E: NO PROVENANCE — no distribution manifest. Report the defaults' state; classify NOTHING.")
else:
    d = json.loads(m.read_text())
    print(f"E: manifest from canonical {d.get('canonical_commit','?')[:8]} written {d.get('written_at','?')}")
    for rel, rec in d.get("files", {}).items():
        p = Path(rel)
        if not p.exists():
            print(f"   {rel}: MISSING — recorded as delivered but not on disk"); continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        if h == rec["sha256"]:
            print(f"   {rel}: delivered ({rec['source']}) — matches the manifest, NOT divergent")
        else:
            print(f"   {rel}: CHANGED SINCE DELIVERY — investigate; do not assume, and do not revert")
PY
```

| What you find | What it means | What you do |
|---|---|---|
| Hash **matches** the manifest | The engine delivered these exact bytes | **Delivered. Not divergent — whatever the git state.** Uncommitted is normal: distribution writes, the project commits later. Say nothing. |
| Hash **differs** from the manifest | The file changed after delivery | A hand-edit is now *plausible*, not proven. Report the file and the difference. **Do not revert it.** Fixing it means folding the intent into the overlay so the next distribution rebakes it. |
| **No manifest at all** | This project predates the record, or has never been distributed to | **No provenance. Report and stop.** Do not classify, do not infer from overlay presence, and above all do not recommend reverting a default. Recommend a `/distribute-defaults` run, which establishes the record. |

**Never recommend reverting a distributed default.** Distribution is the engine's job and the
operator's decision. The worst outcome this check can produce is not a missed hand-edit — it is
destroying a central update that every other repo already has.

**The standing rule when a default genuinely needs project-specific content:** fold it into a splice
fragment in `.claude/local-overlays/<file>`. The next `/distribute-defaults` rebakes canonical+overlay
centrally (via the engine's `scripts/apply-overlay.py`) and redistributes — you never rebake by hand
in the project.

> **`overlay-stale`** — the state a file is in when it *has* an overlay fragment but its content is
> not the current canonical+overlay bake, either because canonical moved on or because someone edited
> the baked result directly. The next distribution **rebakes it from canonical + the overlay
> fragment**, so anything living only in the baked file — and not in the fragment — is gone at that
> moment, with no warning and no error. The term is the engine's; this is what it means for you.
> **The practical consequence:** an edit is durable only if it is in the overlay fragment. Editing
> the delivered file directly, even correctly, is a change with an expiry date.

Project-specific session steps belong in the overlay, period.
(When auditing git history, the engine's own sync commits — message
`chore(playbook): sync default commands` — legitimately rewrite command files without touching
overlays. Note this reads *committed history only*, which is exactly why it could never see the
uncommitted case above; the manifest is what closes that gap.)

## Step 1 — Per-file sweep (the judgment work)

Go through **every file** in `docs/` (excluding `_archive/`) and **every skill** in
`.claude/commands/`. For each, assign one disposition:

> **Before you act on ANY disposition, ask who owns the file.** The distributed defaults — the list
> is named once, in `/update-progress` § 11.b; do not copy it here, this exact list has gone stale
> before — are **read-only to you**. Judge them, ground them, and
> **report** what you find — but never fix, archive, or consolidate one in place. See
> `/update-progress` § 11.b. Every action column below applies to **project-owned files**; for a
> default, the action is always *report it and move on*. An in-place edit is either silently
> overwritten by the next distribution (your fix lost, the defect back everywhere) or it blocks
> distribution for every project on the host.

| Disposition | Meaning | Action (project-owned files; for a default → report instead) |
|---|---|---|
| `current-canonical` | Describes today's system truthfully | none |
| `needs-update` | Right home, stale substance (paths/tools/procedures drifted) | fix in place, verify claims against the live tree |
| `stale-archive` | Superseded or dead | **extract-then-archive**: repoint/extract any live inbound refs FIRST, then move to `docs/_archive/` — never blind-move, never delete |
| `trail-ok` | Record (incident, audit, dated memo with a defer-banner) | leave; ensure the banner/pointer is accurate |
| `duplicate-consolidate` | Same substance stated in ≥2 places | pick ONE canonical home, others become pointers |

Verification discipline: a "current" verdict requires the claims to be **checked against the live
tree** (referenced tool exists, path resolves, procedure matches the code), not read-and-nodded.
For large repos, fan the sweep out (subagents/workflow) — but the dispositions land in one merged
table and every actionable one is executed or explicitly deferred with a named reason.

## Step 1a — Grounding slice: baseline + catch-up (deep content verification, bounded)

The Step 1 sweep judges every file's *disposition*; this step goes one level deeper on a **bounded
subset** and verifies the file's operational claims line by line.

**Division of labor**: the PRIMARY grounding cadence is per-session — `/update-progress` Step 2b
grounds one rotating file at EVERY session close, so the backlog is paid down continuously. This
step is (a) the **baseline**: the first pass in a project establishes the `grounded` map and the
terminology registry that Step 2b then rotates on — in an existing project, run `/repo-hygiene`
**manually once** after receiving these defaults; and (b) the **catch-up backstop**: when the pass
runs, it grounds whatever the per-session rotation has left oldest (sessions get skipped, repos go
dormant — the clock catches what session cadence missed). Both use the SAME `grounded` map, so
nothing is double-verified.

1. **Pick the slice.** From the live skills + canonical docs, take the least-recently-grounded
   files per the `grounded` map in `.claude/hygiene-state.json` (never-grounded first). Bound the
   slice — 3–5 files, or roughly what one pass can verify properly. The bound is the point.
2. **Extract the claims.** For each file in the slice, list every operational claim: cited file
   paths, CLI flags, deployed-resource names, payload/query shapes, commands presented as runnable.
3. **Verify each claim against the implementation**, not against other docs: the path resolves;
   the flag exists in the tool's argument parser; the resource name appears in a **fresh** inventory
   (not a remembered one); the payload/query shape matches the deployed definition; the command is
   shell-runnable as written (multi-line commands actually paste-and-run).
4. **Record per finding**: claim / reality / fix — then act by **ownership**: fix a project-owned
   file in place; for one of the 10 distributed defaults, **report it and never edit it**
   (`/update-progress` § 11.b — grounding them is exactly how engine defects get found, but the
   remedy is a report). At scale (many findings, or subagent fan-out), add an independent refutation
   step before reporting so the worklist stays confirmed-only: a finding that survives an adversarial
   attempt to refute it is a fact, not a maybe.
5. **Advance the cursor.** Update the `grounded` map in Step 5 so the next pass picks the next slice.

Claims that cannot be verified this pass (resource offline, tool unavailable) are deferred with a
named reason — an unverifiable claim is a finding, not a pass.

## Step 2 — Index + knowledge-surface reconciliation

After the sweep, reconcile every index surface to the post-sweep reality:
- CLAUDE.md doc/skill pointers resolve and describe the current set.
- Any skill-picker / occasion→skill index covers ALL skills, no ghosts.
- **If the repo feeds an MCP connector / advisor knowledge base**: the KB's repo-map/skill-catalog
  must cover the post-sweep file set with correct routing. Update the KB **source**; deploy through
  the repo's sanctioned connector-update procedure (never hand-push KB without its verify gates).

## Step 3 — Timeless-canon check (de-phased canonical surfaces)

Grep the **project-owned canonical tree** — docs, project-specific skills, and any externally-served
knowledge base — for process metadata (`Session N`, `Phase N`, dotted task IDs, dated anchors) that
leaked in since the last pass (quick check F sizes this).

> **Scope must match its own gauge.** `.claude/commands/`'s 10 distributed defaults are **excluded**
> — check F skips them by construction, because `Phase N` / `task 2.3` in a default is the engine's
> own vocabulary in a worked example, not leakage. Do not de-phase a default: it is read-only to you
> (§ Step 1), the edit would be overwritten or would block distribution, and F's count — the number
> that sizes this slice — never counted them in the first place. A step that acts on files its own
> gauge declares out of bounds will always look like it has work to do.

Phase/task/session numbering is never load-bearing content
in a canonical surface; phase-scoped working material lives clearly separated (phase dirs /
`_archive/`). Keep durable tokens (schema versions, § refs, regulation numbers, file names) and
allow process metadata where the context is explicitly archival or changelog. Fix in place —
statement stays, process token goes. If leakage is heavy (hundreds of refs), fix a bounded slice
and defer the rest with the count — never let this step become a mass rewrite.

## Step 3a — Terminology / naming discipline

Naming fragments silently: real usage found ~85 distinct referents hiding behind 8 recurring bare
words ("matcher" meaning 9 different things), which defeats both a human's search and an agent's
grep. The countermeasure is a **canonical terminology registry as a first-class artifact** —
a `terminology.md` anywhere under the docs tree — ratified and binding:

- **One grep-friendly canonical name per concept**, each grounded in the code/resource that IS
  the thing; deployed resource names verbatim.
- **A convention that makes grep decisive** (e.g. underscore selects the code symbol, hyphen
  selects the deployed thing).
- **Explicit bans on bare ambiguous words** — the registry names the banned words and what to
  write instead.

This pass:
1. **If no registry exists** (quick check G), bootstrap one from the concepts the Step 1/1a sweep
   actually touched — start small and ratified rather than large and speculative.
2. **Flag competing synonyms** in the files this pass touched: two names for one concept → the
   registry name wins; the other becomes a pointer or is rewritten.
3. **Renames go through the registry first**, then propagate — never as local drift in one file.

New/edited content anywhere in the repo must use registry names (that half is enforced at touch —
see `/update-progress`); this step is the periodic backstop that catches what slipped through.

## Step 4 — progress.json compaction (guarded; append-only preserved)

progress.json is append-only for tasks — compaction **relocates verbose prose, never removes
tasks or fields that identify/verify them**. Bodies move to committed sidecars with full fidelity.

**What moves is decided by a deny-list, and that is the load-bearing choice.** The rule used to
name the three fields it *would* move (`findings`, `verify_result`, `notes`), so a project keeping
its bulk under any other key got no relief. Reported 2026-08-21 by app-brm-manufacturing-products:
a clean run moved 210 bodies from 52 completed phases and took 3,679,053 B to 3,450,961 — 6.2%.
Measured by *running* both rules across 24 local projects: the old one freed **exactly zero bytes
in 15 of them**. Projects invent keys weekly (one carries 556 distinct task keys): what may be
moved is unknowable, what must be **kept** is finite. So the script names the keep-set, and every
other long body in a *finished* task moves. On the same file that takes 3,679,053 B to 2,630,804 —
**28.5%**, against the old rule's 6.2%.

**Three guards exist because widening the field set makes their absence dangerous, not because
they are tidy:** a task still open inside a finished phase keeps its prose (open-work renders it —
`open_work.py` bucket 3); a task carrying `estate_notice` is never touched at all (the probe that
delivered it compares every field, so archiving one re-proposes the notice forever); and a task
whose id is missing or duplicated within its phase is refused rather than merged into a colliding
sidecar slot.

```bash
cat > /tmp/progress-compact.py <<'PY'
import json, re, subprocess, sys, time
from pathlib import Path
APPLY = "--apply" in sys.argv
KEEP_RECENT = 2           # newest N finished phases keep verbose bodies
MIN_LEN = 300             # only bodies longer than this move

# A phase or a task is FINISHED under many spellings. This rule used to recognise exactly one
# ("complete"), so phases spelt superseded/closed/done were never compactable at all. This is the
# SAME tuple the open-work renderer uses (skills/open-work/open_work.py DONE) and it must stay the
# same: open-work renders every task IT considers non-terminal, so a spelling terminal here but open
# there would archive the prose out of a row still being shown. The test compares the two sets.
DONE = ("complete", "completed", "superseded", "done", "closed", "dropped",
        "cancelled", "canceled", "resolved", "obsolete", "abandoned")

# NEVER moved. Two grounds, both checkable: machinery reads it (start-session EXECUTES `verify`;
# open-work renders id/name/status/size and the dependency keys; progress-check compares
# estate_notice; this script's own selection reads the timestamps), or it identifies the task.
# Everything else that is long prose in a FINISHED task moves.
#
# This is a DENY-list, and that IS the fix. The old rule named the three fields it WOULD move
# ("findings", "verify_result", "notes"), so a project keeping its bulk under any other key got no
# relief — and projects invent keys weekly (one estate project's tasks carry 556 distinct keys).
# What must be KEPT is finite and knowable; what may be moved is not.
KEEP_TASK = {"id", "name", "title", "status", "size", "priority", "type", "phase", "owner",
             "repo", "branch", "verify", "estate_notice",
             "depends_on", "depends_on_shipped", "blocked_by", "blocked_on", "blocks",
             "superseded_by", "parent_task", "subtasks", "decomposed_into",
             "added_by", "added_at", "added_on", "started_at", "completed_at", "superseded_at",
             "deferred_at", "verified_at", "filed_at", "approval_gate", "approval_status"}
KEEP_PHASE = {"id", "key", "name", "title", "status", "goal", "description", "objective",
              "tasks", "started_at", "completed_at", "superseded_at", "depends_on"}
SIDE_PHASE_KEY = "__phase__"          # sidecar slot for the phase's own bodies
DATE_FIELDS = ("completed_at", "closed_at", "superseded_at", "finished_at")
PTR = re.compile(r"^archived: docs/_archive/progress-sidecars/(.+)\.json#(.+)$")

root = Path.cwd(); pj = root/"progress.json"
raw_before = pj.read_bytes()
size_before = len(raw_before)
trailing_nl = raw_before.endswith(b"\n")

def no_dupes(pairs):
    out = {}
    for k, v in pairs:
        if k in out: raise ValueError("duplicate key %r" % k)
        out[k] = v
    return out
try:
    text = raw_before.decode("utf-8")
except UnicodeDecodeError as e:
    sys.exit("NOT EXAMINED: progress.json is not valid UTF-8 (%s). Nothing was read." % e)
try:
    data = json.loads(text, object_pairs_hook=no_dupes)
except json.JSONDecodeError as e:
    sys.exit("NOT EXAMINED: progress.json does not parse (%s). Compaction cannot run on a file it "
             "cannot read — repair it first (docs/progress-json-repair-instruction.md)." % e)
except ValueError as e:
    sys.exit("REFUSING: progress.json has a %s. Rewriting the file would silently drop one of the "
             "two values — the exact corruption the progress-check skill is armed to catch, and it "
             "would be laundered before the commit hook ever sees it. Repair it first." % e)

phases = data.get("phases", {})
# `phases` is a DICT in some projects ({"phase_2": {...}}) and a LIST in others ([{...}, ...]).
# This block used to call phases.items() unconditionally, so on a list-shaped progress.json the
# whole compaction died with AttributeError the first time it was due — and because the weight gate
# (D) fires only above 300KB it could sit latent for a repo's whole life and fail exactly when it
# was finally needed. Same failure class as the last_pass-is-null crash in check A. Do not simplify.
#
# The two branches derive the sidecar name DIFFERENTLY and must keep doing so: projects already hold
# sidecars written under the old scheme (a raw dict key; a lowercased slug for a list), and changing
# either would split a phase's archive across two filenames.
if isinstance(phases, dict):
    items = [(str(k), v) for k, v in phases.items()]
elif isinstance(phases, list):
    items = [(re.sub(r"[^a-z0-9._-]+", "-", str(p.get("id") or p.get("name") or "phase_%d" % i).lower()).strip("-")
              or "phase_%d" % i, p)
             for i, p in enumerate(phases) if isinstance(p, dict)]
else:
    items = []
if not items:
    sys.exit("NOT EXAMINED: progress.json carries no readable `phases` (found %s). That is not the "
             "same as a file with nothing to compact, and it is not reported as one."
             % type(phases).__name__)

# ONE safety sanitiser over both shapes — IDENTITY for an ordinary key, so existing sidecars keep
# their names — then a uniqueness pass. The dict branch used to pass the raw key straight into a
# filename: a key containing `/` or `..` wrote the archived body outside docs/_archive/ entirely,
# where "commit the sidecars" would never stage it. And any two keys that sanitise alike shared ONE
# sidecar, each overwriting the other's bodies. The counter here must advance on the BASE, not on
# the name it just produced — the obvious version of this loop collapses N collisions onto 2 names.
stems, used = {}, set()
for idx, (key, ph) in enumerate(items):
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", key).strip("-.") or "phase"
    stem, n = base, 1
    while stem in used:
        stem = "%s-%d" % (base, n); n += 1
    used.add(stem); stems[idx] = stem
assert len(used) == len(items), "sidecar stems are not unique"

def tasks_of(ph):
    t = ph.get("tasks")
    return t if isinstance(t, list) else list(t.values()) if isinstance(t, dict) else []
def term(o):  return str((o or {}).get("status") or "").strip().lower() in DONE
def blob(v):  return len(json.dumps(v, ensure_ascii=False))
def ident(v):
    # current_task / current_phase is a bare string in most projects and an OBJECT in some. Reading
    # it with str() turned the object into "{'id': '5.2', ...}", which matches no task id, so the
    # guard that protects live work was silently inert exactly where the pointer was richest.
    if isinstance(v, dict):
        for f in ("id", "key", "task", "name"):
            if isinstance(v.get(f), (str, int, float)): return str(v[f])
        return ""
    return str(v) if isinstance(v, (str, int, float)) else ""
def eff_date(ph, ts):
    for f in DATE_FIELDS:
        v = ph.get(f)
        if isinstance(v, str) and v.strip(): return v.strip()
    # A phase whose own stamp was never written is still dateable from its tasks: 19 phases in one
    # estate project were marked complete with NO completed_at and were exempt FOREVER under the old
    # selection — the single largest bucket it could not see. A phase with no date ANYWHERE sorts
    # first and is therefore compacted on the first run: it cannot be shown to be recent.
    ds = [t[f] for t in ts if isinstance(t, dict) for f in DATE_FIELDS
          if isinstance(t.get(f), str) and t[f].strip()]
    return max(ds) if ds else ""

cur_phase = ident(data.get("current_phase"))
cur_task  = ident(data.get("current_task"))

finished, skipped = [], []           # skipped carries a REASON and bytes — never silently
for idx, (key, ph) in enumerate(items):
    if not isinstance(ph, dict): skipped.append((key, "not a dict", 0)); continue
    ts = tasks_of(ph)
    ids = {str(t.get("id")) for t in ts if isinstance(t, dict) and t.get("id") is not None}
    if not term(ph):
        skipped.append((key, "status=%r — not finished" % ph.get("status"), blob(ph))); continue
    if cur_phase and cur_phase in (key, str(ph.get("id")), str(ph.get("name"))) or (cur_task and cur_task in ids):
        skipped.append((key, "holds current_phase/current_task", blob(ph))); continue
    finished.append((eff_date(ph, ts), idx, key, ph))
finished.sort(key=lambda r: r[0])
targets = finished[:-KEEP_RECENT] if len(finished) > KEEP_RECENT else []
for d, i, k, ph in (finished[-KEEP_RECENT:] if len(finished) > KEEP_RECENT else finished):
    skipped.append((k, "newest %d finished (KEEP_RECENT)" % KEEP_RECENT, blob(ph)))

side_dir = root/"docs/_archive/progress-sidecars"
def ignored(p):
    try:
        return subprocess.run(["git", "check-ignore", "-q", p], capture_output=True).returncode == 0
    except FileNotFoundError:
        return False        # no git here; the gitignore question cannot be answered, not "no"
if APPLY and (ignored("docs/_archive/progress-sidecars")
              or ignored("docs/_archive/progress-sidecars/probe.json")):
    sys.exit("REFUSING: docs/_archive/progress-sidecars (or the .json files in it) is gitignored. "
             "The sidecars would not be committed and every pointer left behind would dangle. "
             "Un-ignore it first.")

moved = 0
declined = {"non-string body": [0, 0], "task carries an estate_notice": [0, 0],
            "task has no id": [0, 0], "duplicate task id": [0, 0],
            "task still open inside a finished phase": [0, 0], "protected field": [0, 0],
            "sidecar unreadable — phase skipped": [0, 0],
            "sidecar slot already holds a different body": [0, 0]}
def decline(kind, n, b): declined[kind][0] += n; declined[kind][1] += b
per_phase, wrote, side_cache = [], [], {}

for _d, idx, key, ph in targets:
    stem = stems[idx]
    side_p = side_dir/("%s.json" % stem)
    if side_dir.resolve() not in side_p.resolve().parents:
        print("!! %s: sidecar path would escape the archive directory — phase skipped" % key); continue
    try:
        side = json.loads(side_p.read_text()) if side_p.exists() else {}
        if not isinstance(side, dict) or any(not isinstance(v, dict) for v in side.values()):
            raise ValueError("not a mapping of task id -> {field: body}")
    except Exception as e:
        # One interrupted run used to leave a half-written sidecar that aborted EVERY future run
        # with a bare traceback. Name it, skip that phase, carry on.
        print("!! %s: existing sidecar %s is unusable (%s) — phase skipped" % (key, side_p.name, e))
        decline("sidecar unreadable — phase skipped", 1, blob(ph)); continue
    side_cache[stem] = (side_p, side)
    ts = tasks_of(ph)
    seen, dup = set(), set()
    for t in ts:
        if isinstance(t, dict) and t.get("id") is not None:
            i = str(t["id"]); dup.add(i) if i in seen else seen.add(i)
    ph_moved = ph_freed = 0
    def relocate(holder, fld, val, side_key, keepset):
        global moved, ph_moved, ph_freed
        if fld in keepset or fld == "tasks": return
        if not isinstance(val, str):
            if blob(val) > MIN_LEN: decline("non-string body", 1, blob(val))
            return
        if len(val) <= MIN_LEN or val.startswith("archived:"): return
        ptr = "archived: docs/_archive/progress-sidecars/%s.json#%s" % (stem, side_key)
        if len(val) <= len(ptr) + 50: return          # a pointer that costs more than it saves
        prior = side.get(side_key, {}).get(fld)
        if prior is not None and prior != val:
            # The slot already holds a DIFFERENT body — from an earlier run, or from another phase
            # that shares this stem. Writing would destroy it, and the pointer would then name text
            # that was never here. Refuse, and say which slot.
            print("!! %s#%s[%s]: sidecar slot already holds different text — left in place" % (stem, side_key, fld))
            decline("sidecar slot already holds a different body", 1, len(val)); return
        side.setdefault(side_key, {})[fld] = val
        holder[fld] = ptr                      # mutate always; only the WRITE is gated on --apply
        wrote.append((stem, side_key, fld, val, ptr))
        moved += 1; ph_moved += 1; ph_freed += len(val) - len(ptr)
    for t in ts:
        if not isinstance(t, dict): continue
        if t.get("estate_notice") is not None:
            # A central notice is compared FIELD BY FIELD by the probe that delivered it
            # (scripts/probes/notify-mcp-transport.probe). Archiving its `detail` would make the
            # delivered notice differ from the one the survey would send, so the estate would
            # re-propose it forever. Notices are never compacted, whatever their status.
            decline("task carries an estate_notice", 1, blob(t)); continue
        if t.get("id") is None:
            decline("task has no id", 1, blob(t)); continue      # no pointer could resolve to it
        tid = str(t["id"])
        if tid in dup:
            # Two tasks sharing an id used to funnel into one sidecar slot: the first body was
            # overwritten and BOTH pointers named the survivor. Silent, unrecoverable, and it got
            # worse with every field added to the old list. Refuse, and say so.
            decline("duplicate task id", 1, blob(t)); continue
        if tid == SIDE_PHASE_KEY:
            decline("duplicate task id", 1, blob(t)); continue    # would collide with the phase slot
        if not term(t) or tid == cur_task:
            # open-work renders EVERY non-terminal task, including ones inside a phase marked
            # complete (open_work.py bucket 3 — itself a fix for 28 invisible rows across 7
            # projects). Archiving their prose empties rows the operator is still being shown.
            decline("task still open inside a finished phase", 1, blob(t)); continue
        for fld, val in list(t.items()):
            if fld in KEEP_TASK and isinstance(val, str) and len(val) > MIN_LEN:
                decline("protected field", 1, len(val))
            relocate(t, fld, val, tid, KEEP_TASK)
    for fld, val in list(ph.items()):
        if fld in KEEP_PHASE and isinstance(val, str) and len(val) > MIN_LEN:
            decline("protected field", 1, len(val))
        relocate(ph, fld, val, SIDE_PHASE_KEY, KEEP_PHASE)
    if ph_moved: per_phase.append((key, ph_moved, ph_freed))

# The mutation above always happens, so the predicted size is the REAL size — the old dry-run
# subtracted body lengths and ignored re-serialisation, and a re-serialise at indent=2 GROWS nine
# of the estate's files. A predicted shrink that is really a growth is the one number the operator
# uses to decide whether to apply.
out = json.dumps(data, indent=2, ensure_ascii=False) + ("\n" if trailing_nl else "")
size_after = len(out.encode("utf-8"))

def account():
    head = ("APPLIED" if moved else "NOTHING TO MOVE") if APPLY else "DRY-RUN"
    print("%s: %d bodies from %d of %d phases %s sidecars, %s -> %s bytes" % (
          head, moved, len(targets), len(items),
          "->" if (APPLY and moved) else "would move ->", format(size_before, ","),
          format(size_after if moved else size_before, ",")))
    for k, n, b in sorted(per_phase, key=lambda r: -r[2])[:10]:
        print("   %4d bodies  ~%9s B  %s" % (n, format(b, ","), k))
    print("NOT moved — this is the rest of the file, and none of it is dropped silently:")
    for kind, (n, b) in sorted(declined.items(), key=lambda kv: -kv[1][1]):
        if n: print("   %5d x %-42s ~%10s B" % (n, kind, format(b, ",")))
    agg = {}
    for k, r, b in skipped:
        a = agg.setdefault(r, [0, 0]); a[0] += 1; a[1] += b
    for r, (n, b) in sorted(agg.items(), key=lambda kv: -kv[1][1]):
        print("   %5d phases %-42s ~%10s B" % (n, r, format(b, ",")))

if not APPLY:
    account()
    # Pointers already in the file, from earlier runs: are they still resolvable? Nothing else in
    # the estate ever checks, so a sidecar deleted or renamed away leaves progress.json pointing at
    # text that is gone, and every run before this one reported clean.
    dangling = []
    def scan(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str):
                    m = PTR.match(v)
                    if m and not any(w[4] == v and w[2] == k for w in wrote):
                        try:
                            json.loads((side_dir/(m.group(1)+".json")).read_text())[m.group(2)][k]
                        except Exception: dangling.append(v)
                else: scan(v)
        elif isinstance(o, list):
            for v in o: scan(v)
    scan(data)
    if dangling:
        print("!! %d pointer(s) already in this file do NOT resolve — the archived text is gone or "
              "the sidecar was renamed. First: %s" % (len(dangling), dangling[0]))
    raise SystemExit(0)

if not moved:
    account()
    print("Nothing to move — progress.json was not rewritten. (A run that moves nothing must not "
          "reformat the file: that is a diff with no compaction in it.)")
    raise SystemExit(0)

# --- APPLY --------------------------------------------------------------------------------------
# The pre-state: git holds it whenever progress.json is tracked and unmodified, which is the normal
# case at a hygiene pass. A file copy is taken ONLY when git cannot recover it — the old rule copied
# every time, into the very directory the instructions tell the operator to commit, so compaction
# added far more tracked bytes than it removed and the ignore rule to prevent that existed in one
# repo only. Rollback below never depends on the copy: the original bytes are held in memory.
def git_has_prestate():
    try:
        t = subprocess.run(["git", "ls-files", "--error-unmatch", "progress.json"], capture_output=True)
        if t.returncode != 0: return None
        d = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "progress.json"], capture_output=True)
        if d.returncode != 0: return None
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
        return r.stdout.strip() or None
    except FileNotFoundError:
        return None
ref = git_has_prestate()
bak = None
if ref is None:
    # Never overwrite an existing copy. A date-only name let a second run the same day replace the
    # true pre-state with an already-compacted one; a stamp to the second still collides when two
    # runs land in the same second, which is exactly what a scripted apply-after-dry-run does.
    stamp = time.strftime("%Y%m%dT%H%M%S")
    bak = side_dir/("progress.json.pre-compact.%s" % stamp); n = 1
    while bak.exists():
        bak = side_dir/("progress.json.pre-compact.%s-%d" % (stamp, n)); n += 1
    bak.parent.mkdir(parents=True, exist_ok=True)
    bak.write_bytes(raw_before)

for stem, (side_p, side) in side_cache.items():
    if not side: continue
    side_dir.mkdir(parents=True, exist_ok=True)
    tmp = side_p.with_name(side_p.name + ".tmp")       # atomic: an interrupted write used to poison
    tmp.write_text(json.dumps(side, indent=1, ensure_ascii=False))   # every later run
    tmp.replace(side_p)

def restore(why):
    pj.write_bytes(raw_before)
    sys.exit("ROLLED BACK — %s. progress.json restored byte for byte%s; the sidecars written this "
             "run are still on disk and safe to inspect. Nothing was lost."
             % (why, "" if bak is None else " (a copy is also at %s)" % bak.name))
try:
    tmp = pj.with_name("progress.json.tmp")           # atomic: write_text truncates in place, so an
    tmp.write_text(out)                               # ENOSPC/OOM mid-write left the file that holds
    tmp.replace(pj)                                   # the project's whole state truncated
except Exception as e:
    restore("writing progress.json failed (%s)" % e)

# THE GATE. The old one re-parsed the bytes json.dumps had just produced — it could only fail if the
# JSON library were broken. This one re-reads FROM DISK and checks the three things that actually
# went wrong: a task lost, a pointer that is not the one intended, and a pointer that resolves to
# something other than the body that was taken.
def census(pairs):
    out = []
    for k, ph in pairs:
        if not isinstance(ph, dict): continue
        for t in tasks_of(ph):
            if isinstance(t, dict): out.append((k, str(t.get("id"))))
    return sorted(out)
census_before = census([(k, json.loads(raw_before.decode())["phases"][k]) for k, _ in items]) \
                if isinstance(phases, dict) else None
try:
    back = json.loads(pj.read_text(), object_pairs_hook=no_dupes)
except Exception as e:
    restore("the rewritten progress.json does not read back (%s)" % e)
bp = back.get("phases", {})
bi = [(str(k), v) for k, v in bp.items()] if isinstance(bp, dict) else \
     [(str(i), p) for i, p in enumerate(bp) if isinstance(p, dict)]
oi = [(str(k), v) for k, v in phases.items()] if isinstance(phases, dict) else \
     [(str(i), p) for i, p in enumerate(json.loads(raw_before.decode()).get("phases", [])) if isinstance(p, dict)]
if census(bi) != census(oi):
    lost = sorted(set(census(oi)) - set(census(bi)))
    restore("task ids changed: %d lost, first %s" % (len(lost), lost[:3]))
found = set()
def collect(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str):
                m = PTR.match(v)
                if m: found.add((m.group(1), m.group(2), k, v))
            else: collect(v)
    elif isinstance(o, list):
        for v in o: collect(v)
collect(back)
for stem, side_key, fld, original, ptr in wrote:
    if (stem, side_key, fld, ptr) not in found:
        restore("the pointer for %s#%s[%s] is not in the written file" % (stem, side_key, fld))
    try:
        body = json.loads((side_dir/("%s.json" % stem)).read_text())[side_key][fld]
    except Exception:
        restore("pointer %s.json#%s[%s] does not resolve" % (stem, side_key, fld))
    if body != original:
        restore("pointer %s.json#%s[%s] resolves to text that is not the body it replaced — a "
                "sidecar slot was overwritten" % (stem, side_key, fld))

account()
if bak is None:
    print("PRE-STATE: progress.json was tracked and clean, so git holds it — recover with "
          "`git show %s:progress.json`. No copy was written; committed pre-compact copies cost the "
          "repo more than compaction saves it." % ref)
else:
    print("PRE-STATE: git could not recover it (untracked or already modified), so a copy is at "
          "docs/_archive/progress-sidecars/%s. It is a LOCAL rollback, not part of the trail — "
          "delete it once this compaction is committed." % bak.name)
PY
python3 /tmp/progress-compact.py            # dry-run: reads, writes nothing, prints the account
```

**Read the account, not the headline** — and it is a separate fence for that reason: pasting one
block must not apply anything. The run prints what it moved *and* what it did not, with bytes and a
named reason for each bucket: protected fields, non-string bodies, open tasks, notices, phases that
are not finished, phases the newest-`KEEP_RECENT` window protects. A shrink that disappoints is
usually not a narrow field list — in the reporting project 983,214 B (28% of the phases blob) sat in
phases that were still open, which compaction must never touch, and another 799,421 B in finished
phases the old selection could not recognise. Both read straight off the account; their absence is
what produced the first, wrong diagnosis. The dry-run's predicted size is the real serialised size,
not an estimate, because a re-serialisation alone changes nine of the estate's files. Then, and only
then:

```bash
python3 /tmp/progress-compact.py --apply
```

**Rules.** Tasks, ids, status, names, `verify`, `estate_notice`, the dependency keys and the
timestamps never change. Only *finished* phases outside the newest `KEEP_RECENT` are touched —
"finished" being the same terminal-status set the open-work renderer uses, not the single spelling
`complete`; a phase whose own `completed_at` was never written is dated from its tasks, and one with
no date anywhere sorts oldest and is compacted on the first run, because nothing about it can be
shown to be recent. The phase holding `current_phase`/`current_task` is skipped whatever its status
says, including when that pointer is an object rather than a string. The sidecars are committed
together with the shrunk progress.json.

**Resolving an archived body.** The pointer names a task slot, not a field, so this prints every
body archived for that task and you read the one you want:
`python3 -c "import json,sys;p=sys.argv[1].split('#');d=json.load(open(p[0].split(' ',1)[1]))[p[1]];[print('---',k,'---',v,sep='\n') for k,v in d.items()]" "archived: docs/_archive/progress-sidecars/phase_12.json#12.3"`

**No pre-compact copy is written when git already holds the pre-state** — tracked and unmodified is
the normal case at a hygiene pass, and the run tells you the sha to recover from. A copy is written
only when git cannot help (untracked, or already modified), stamped to the second, and it is a local
rollback to delete once the compaction is committed. The old rule copied every time, into the very
directory the instructions tell you to commit: one project had accumulated 7.1 MB of tracked copies
against 0.56 MB of real sidecars, so compaction was making the repo larger than it made it smaller.

**It refuses rather than guesses.** Duplicate JSON keys abort the run (rewriting would silently drop
one — the corruption `progress-check` is armed to catch, laundered before the commit hook could see
it); a gitignored sidecar directory *or* a pattern that ignores the sidecar files aborts it (the
pointers would dangle); a file with no readable `phases` is reported NOT EXAMINED, never as a clean
zero; a run that moves nothing does not rewrite the file at all. progress.json is written to a temp
file and renamed, so a failed write cannot truncate the file that holds the project's whole state.
After the rename the gate re-reads **from disk** and checks that every task id survived, that every
pointer it intended is actually in the file, and that each one resolves to the exact body it
replaced — rolling back byte-for-byte from memory if any of that fails. A dry-run additionally
reports pointers *already* in the file that no longer resolve, which nothing else in the estate
checks. `scripts/test-progress-compaction.sh` in syndicate-playbooks-examples runs this exact block,
extracted from this file, against fixtures.


## Step 5 — Record + close

1. Write `.claude/hygiene-state.json`:
   `{"last_pass": "<today YYYY-MM-DD>", "findings_fixed": N, "deferred": ["<item — named reason>"],
   "grounded": {"<file>": "<YYYY-MM-DD grounded>", ...}}`
   — merge this pass's Step 1a slice into the existing `grounded` map (never drop prior entries);
   the map is what makes the rotation converge to full coverage.
2. session_notes entry: dispositions summary, grounding-slice findings (claim/reality/fix),
   what was archived/updated, deferred items with reasons.
3. Commit (scoped to what this pass touched). A pass with unexecuted actionable dispositions is
   not complete — defer only with a named reason the next session can pick up.

## Guardrails

- **This is not a delete license.** Never remove protected artifacts: progress.json tasks
  (mark superseded), session_notes, incident/audit trail, product/data records. Prefer
  mark-superseded or move-to-`_archive/`; when unsure, leave it and note it.
- **Extract-then-archive** — a "closed" dir can hold live dependencies (a skill's default paths,
  a test fixture, a cited rule). Repoint every live inbound reference first; a currency check run
  after the move must show zero new broken refs.
- If in-progress work owns files (an active phase's handoff, an engine mid-rebuild), leave that
  work's files alone and note the dependency.
- **Bounded, never a crusade.** Steps 1a/3/3a run as bounded slices — small always-on consolidation
  beats large occasional remediation. If a slice uncovers a systemic problem (mass grounding rot,
  wholesale naming fragmentation), do NOT fan out into a remediation inside this pass: record the
  evidence, defer with the count, and let the operator decide whether to open dedicated work. The
  one-off 63-agent audit this mechanism exists to prevent started as exactly that fan-out.
