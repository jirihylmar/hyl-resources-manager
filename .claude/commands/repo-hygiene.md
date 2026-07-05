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
state_p = root/".claude/hygiene-state.json"
if state_p.exists():
    st = json.loads(state_p.read_text())
    age = (time.time() - time.mktime(time.strptime(st.get("last_pass","1970-01-01"), "%Y-%m-%d"))) / 86400
    if age > 30: findings.append(f"A: hygiene pass overdue ({age:.0f} days since {st.get('last_pass')})")
else:
    findings.append("A: hygiene never recorded (.claude/hygiene-state.json absent)")

# (B) stale working dirs under docs/
for d in sorted((root/"docs").glob("*")) if (root/"docs").exists() else []:
    if d.is_dir() and re.match(r"^(phase-|wip-|tmp-|scratch)", d.name):
        findings.append(f"B: working dir docs/{d.name}/ — extract-then-archive when its work closes")

# (C) broken repo-relative doc refs from live surfaces (docs + commands)
ref_re = re.compile(r"(?<![\w/])(docs/[A-Za-z0-9_\-./]+\.(?:md|tsv|json|py|png|html))")
surfaces = list((root/"docs").rglob("*.md")) + list((root/".claude/commands").glob("*.md"))
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
meta_re = re.compile(r"\b(?:Phase|Session)\s+\d+\b|\btask\s+\d+\.\d+\b", re.I)
mcount = mfiles = 0
for f in surfaces:
    if "_archive" in f.parts: continue
    try: text = f.read_text(errors="ignore")
    except OSError: continue
    n = len(meta_re.findall(text))
    if n: mcount += n; mfiles += 1
if mcount > 20: findings.append(f"F: {mcount} phase/session/task refs across {mfiles} canonical files — de-phase slice due (Step 3)")

# (G) terminology registry presence (Step 3a)
if (root/"docs").exists() and not list((root/"docs").rglob("terminology.md")):
    findings.append("G: no terminology registry under docs/ — bootstrap one (Step 3a)")

for f in findings: print(" -", f)
print(f"\nHYGIENE-CHECK findings: {len(findings)}")
PY
```

If the project ships its own richer checker (e.g. a `tools/docs_currency_check.py`), run that too —
project checkers are authoritative over this generic one; this one is the floor every repo gets.

**(E) Overlay discipline** — if `.claude/local-overlays/` exists: the distributed defaults
(`start-session.md`, `update-progress.md`, …) must equal **canonical + overlay**, never carry
hand-edits. Hand-edits do not survive the next `/distribute-defaults`: a file WITH an overlay
classifies `overlay-stale` and is silently rebaked from canonical+overlay (the edit is lost); a
file WITHOUT an overlay classifies `divergent` and blocks that file's distribution until resolved.
Either outcome is a defect. Fix by folding the intended change into the overlay fragment (splice
blocks) in `.claude/local-overlays/<file>`; the next `/distribute-defaults` rebakes canonical+overlay
centrally (via the engine's `scripts/apply-overlay.py`) and redistributes — you do not rebake by
hand in the project. Project-specific session steps belong in the overlay, period. (When auditing
git history for stray hand-edits, ignore the engine's own sync commits — message
`chore(playbook): sync default commands` — which legitimately rewrite command files without touching
overlays.)

## Step 1 — Per-file sweep (the judgment work)

Go through **every file** in `docs/` (excluding `_archive/`) and **every skill** in
`.claude/commands/`. For each, assign one disposition:

| Disposition | Meaning | Action |
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
4. **Record per finding**: claim / reality / fix — then fix in place. At scale (many findings, or
   subagent fan-out), add an independent refutation step before reporting so the worklist stays
   confirmed-only: a finding that survives an adversarial attempt to refute it is a fact, not a maybe.
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

Grep the **whole canonical tree** — docs, skills, and any externally-served knowledge base — for
process metadata (`Session N`, `Phase N`, dotted task IDs, dated anchors) that leaked in since the
last pass (quick check F sizes this). Phase/task/session numbering is never load-bearing content
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
import json, shutil, sys, time
from pathlib import Path
APPLY = "--apply" in sys.argv
KEEP_RECENT = 2           # newest N completed phases keep verbose bodies
MIN_LEN = 300             # only bodies longer than this move
root = Path.cwd(); pj = root/"progress.json"
data = json.loads(pj.read_text())
phases = data.get("phases", {})
completed = [(k,v) for k,v in phases.items() if isinstance(v,dict) and v.get("status")=="complete" and v.get("completed_at")]
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
