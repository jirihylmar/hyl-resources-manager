---
name: overlay-check
description: Validate this project's local-overlay splice anchors against its own delivered commands, before a distribution does it for you. Invoke after writing or editing anything in .claude/local-overlays/, when a distribution reported broken-overlay, or when adding project-specific content to a distributed default.
---

# overlay-check

A project adds its own content to a distributed default by writing
`.claude/local-overlays/<command>.md` — a splice fragment anchored to an exact line of the
canonical. This checks that those anchors actually bind, **here, now**, without needing anything
this project does not already have.

## Why it exists

Until 2026-09-07 a project could not check its own overlay. The overlay engine lives in
`syndicate-playbooks-examples`, which is **local-only by policy** and is never present on a box —
so an overlay was written blind and first validated at the next `/distribute-defaults` run.

That is not a local problem. A bad anchor is classified `broken-overlay`, and the engine's blast
radius is the **host**, not the file:

> One `divergent`/`broken-overlay` file in one project makes `--apply` exit 3 and write
> **nothing to any project on that machine**.

So one untested overlay can freeze distribution for every project on the box, and the symptom
surfaces somewhere else entirely — as a project quietly running month-old defaults.

**The engine is not needed to check this — with one honest limit.** The engine splices
`_project-template`'s canonical, which this project does not have. What it has is the delivered
`.claude/commands/<command>.md`, and that is:

- **byte-identical to the canonical** if this project's overlay has not been baked yet — the
  normal case when you have just written one, and the case this skill exists for; or
- the **baked result** (canonical + overlay) if it has.

In the second case the check is approximate and says so: an anchor may appear to bind to a line
the overlay itself inserted on an earlier distribution. An earlier draft of this skill asserted
flatly that "the canonical is already here". That is false for any already-baked project, and it
is corrected here rather than quietly dropped.

*Reported by a project on 2026-09-07: "I could not validate the overlay splice:
syndicate-playbooks-examples isn't on this host. The format follows the spec, but it's untested
until a distribution runs."*

## Run it

```bash
python3 .claude/skills/overlay-check/overlay_check.py          # this project
python3 .claude/skills/overlay-check/overlay_check.py <path>   # another checkout
```

| Exit | Meaning |
|---|---|
| `0` | every anchor binds to exactly one line |
| `1` | at least one problem — a distribution would refuse |
| `2` | no overlays here; nothing to check |

## What it checks, and why each one blocks a distribution

- **The anchor matches exactly one line.** Zero is `broken-overlay` and blocks. **More than one is
  worse than an error**: the engine resolves it first-match-wins, silently, so the author gets a
  placement they never chose and nothing reports it. Extend the anchor until it is unique.
- **The directive parses at all.** A line that means to be a directive and is not — a stray space
  in `splice-after : "x"`, trailing text after the `-->`, an unescaped quote inside the anchor —
  used to be swallowed in silence by the engine, which then produced bare canonical, exited 0, and
  let the distribution **overwrite the project's customisation and report success**. That engine
  defect is fixed; this catches the typo at authoring time, before it travels.
- **Whole-line equality, not substring** — exactly as `apply-overlay.py` does
  (`line.rstrip('\n') == anchor`). This is why a fenced *example* that quotes an anchor inside
  `<!-- splice-after: "..." -->` can never be matched: the example line carries the comment
  wrapper, so it is a different line. That was reported as a defect on 2026-09-07; it does not
  reproduce, and the checker encodes the reason rather than leaving it to be re-derived.
- **Anchors are resolved against a progressive buffer**, as the engine does — so a later block may
  legitimately anchor on a line an earlier block inserted, and that is not reported as missing.
- **A directive is present at all.** An overlay with no `splice-before`/`after`/`append` is a no-op
  that will never be noticed — it looks installed and does nothing.
- **No contradiction with `.skip`.** A command listed in `.claude/local-overlays/.skip` is fully
  forked; an overlay file for that same command will never be applied.

## Writing an anchor that survives

The canonical is centrally maintained and will change. An anchor is a bet that one line stays
byte-identical, so bet on the most stable line available:

- Prefer a **heading** (`### 7. Update Project Documentation (If Registered)`) over a sentence of
  prose — headings are renumbered rarely and rewritten less often than the text under them.
- A line inside a fenced block is **not** automatically a bad anchor — `### Upcoming Work` in
  `start-session.md` sits inside a fence and is deliberately load-bearing, carrying its own
  "DO NOT RENAME THIS ONE" note. What to avoid is anchoring on the *body* of an illustrative
  example, which gets rewritten whenever the example is improved.
- After any distribution that changed the command you anchor to, re-run this check.

## Related skills
- `/progress-check` — the same idea for `progress.json`: catch it at the commit, not later.
