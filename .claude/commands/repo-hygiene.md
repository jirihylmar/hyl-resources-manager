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

```bash
python3 - <<'PY'
import json, re, shutil, sys, time
from pathlib import Path
APPLY = "--apply" in sys.argv
KEEP_RECENT = 2           # newest N completed phases keep verbose bodies
MIN_LEN = 300             # only bodies longer than this move
root = Path.cwd(); pj = root/"progress.json"
data = json.loads(pj.read_text())
phases = data.get("phases", {})
# `phases` is a DICT in some projects ({"phase_2": {...}}) and a LIST in others ([{...}, ...]).
# Normalise to (key, phase) pairs before touching it. This block used to call phases.items()
# unconditionally, so on a list-shaped progress.json the whole compaction died with
# AttributeError the first time it was due — and because the weight gate (D) fires only above
# 300KB, it could sit latent for the entire life of a repo and then fail exactly when it was
# finally needed. Same failure class as the last_pass-is-null crash in check A. Do not "simplify".
if isinstance(phases, dict):
    items = list(phases.items())
elif isinstance(phases, list):
    # No keys in a list — synthesise a stable sidecar filename from id/name, falling back to index.
    items = [(re.sub(r"[^a-z0-9._-]+", "-", str(p.get("id") or p.get("name") or f"phase_{i}").lower()).strip("-") or f"phase_{i}", p)
             for i, p in enumerate(phases) if isinstance(p, dict)]
else:
    items = []
completed = [(k,v) for k,v in items if isinstance(v,dict) and v.get("status")=="complete" and v.get("completed_at")]
completed.sort(key=lambda kv: str(kv[1].get("completed_at")))
targets = completed[:-KEEP_RECENT] if len(completed)>KEEP_RECENT else []
side_dir = root/"docs/_archive/progress-sidecars"; moved = 0
for key, ph in targets:
    side_p = side_dir/f"{key}.json"
    side = json.loads(side_p.read_text()) if side_p.exists() else {}
    tasks = ph.get("tasks"); tasks = tasks if isinstance(tasks,list) else list(tasks.values()) if isinstance(tasks,dict) else []
    for t in tasks:
        if not isinstance(t,dict): continue
        for fld in ("findings","verify_result","notes"):
            val = t.get(fld)
            if isinstance(val,str) and len(val)>MIN_LEN and not val.startswith("archived:"):
                side.setdefault(t.get("id","?"),{})[fld] = val
                if APPLY: t[fld] = f"archived: docs/_archive/progress-sidecars/{key}.json#{t.get('id','?')}"
                moved += 1
    if APPLY and side:
        side_dir.mkdir(parents=True, exist_ok=True)
        side_p.write_text(json.dumps(side, indent=1, ensure_ascii=False))
if APPLY and moved:
    bak = root/f"docs/_archive/progress-sidecars/progress.json.pre-compact.{time.strftime('%Y%m%d')}"
    bak.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(pj, bak)
    pj.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    json.loads(pj.read_text())  # re-parse gate
print(f"{'APPLIED' if APPLY else 'DRY-RUN'}: {moved} verbose bodies from {len(targets)} old completed phases -> sidecars")
PY
```

Run **dry-run first**, review the count, then re-run with `--apply`. Rules: tasks/ids/status/names/
`verify` never change; only completed phases older than the newest `KEEP_RECENT` are touched; a
pre-compact backup + the sidecars are committed together with the shrunk progress.json.

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
