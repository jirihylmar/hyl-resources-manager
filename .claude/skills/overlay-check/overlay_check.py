#!/usr/bin/env python3
"""Validate this project's local-overlay splice directives before a distribution does it for you.

WHY THIS EXISTS. A project adds its own content to a distributed default by writing
`.claude/local-overlays/<cmd>.md`. Until 2026-09-07 it could not check that file: the overlay
engine lives in `syndicate-playbooks-examples`, which is LOCAL-ONLY by policy and never present on
a box. So an overlay was written blind and first validated at the next `/distribute-defaults` run —
and a bad overlay there is not a local problem. It is classified `broken-overlay`, `--apply` exits
3, and NOTHING is written to ANY project on that host.

WHAT IT CHECKS AGAINST, STATED HONESTLY. The engine always splices `_project-template`'s canonical.
This project does not have that file. What it has is `.claude/commands/<cmd>.md`, which is:

  * byte-identical to the canonical, IF this project's overlay has not been baked yet; or
  * the BAKED result (canonical + overlay), if it has.

In the second case this check is approximate, and it says so rather than pretending otherwise: an
anchor can appear to bind to a line the overlay itself inserted on a previous distribution. An
earlier version of this file asserted flatly that "the canonical is already here"; that is false
for any already-baked project, and the claim is corrected rather than quietly dropped.

WHY THE PARSING IS DUPLICATED FROM THE ENGINE, DELIBERATELY. The regexes and the block semantics
below are copied from `scripts/apply-overlay.py`, because the alternative — importing it — is
impossible on a host where the engine does not exist, and the alternative to duplicating is a
project that cannot check at all. The duplication is held by a test in the engine repo
(`scripts/test-overlay-check-parity.sh`) which runs BOTH tools over a fixture corpus and fails if
they ever disagree. Do not "simplify" either regex without running it.

MEASURED, 2026-09-07 — every one of these was a real divergence in the first version of this file,
found by adversarial review before it shipped:
  * a bare `<!-- splice-after -->` next to a valid block: this said ok, the engine exits 2 and
    freezes the host. A checker whose whole purpose is preventing that must not bless it.
  * `<!-- splice-after : "x" -->` (one stray space): this said ok, and the engine SILENTLY dropped
    the overlay — then distribution overwrote the project's customisation with bare canonical and
    reported success. That engine defect is fixed too; this catches the typo at authoring time.
  * a later block anchoring on a line an EARLIER block inserts: this said NOT FOUND, but the engine
    splices into a progressive buffer and binds it correctly. A false alarm that would send a
    project to edit a working overlay.

Exit 0 every directive is bindable · 1 at least one problem · 2 nothing to check.
"""
import collections
import glob
import os
import re
import sys

# Copied verbatim from scripts/apply-overlay.py — see the docstring note above.
DIRECTIVE_RE = re.compile(
    r'^\s*<!--\s*splice-(before|after|append)(?::\s*"((?:[^"\\]|\\.)*)")?\s*-->\s*$'
)
NEAR_MISS_RE = re.compile(r'^\s*<!--.*\bsplice-(?:before|after|append)\b.*-->\s*$')


def read_lines(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return None, f"not valid UTF-8 ({exc.reason} at byte {exc.start}) — the engine would crash"
    return text.splitlines(keepends=True), None


def parse(lines):
    """Mirror apply-overlay.py's parse_overlay, returning (blocks, error)."""
    blocks, directive, anchor, content = [], None, None, []
    for line in lines:
        bare = line.rstrip("\n")
        m = DIRECTIVE_RE.match(bare)
        if m:
            if directive is not None:
                blocks.append((directive, anchor, content))
            directive, anchor, content = m.group(1), m.group(2), []
            if directive in ("before", "after") and anchor is None:
                return None, (f'splice-{directive} with no quoted anchor: {bare.strip()!r} — '
                              f'the engine raises here and the distribution writes nothing to '
                              f'ANY project on this host')
        elif NEAR_MISS_RE.match(bare):
            return None, (f'looks like a directive but does not parse: {bare.strip()!r}\n'
                          f'      expected exactly:  <!-- splice-before: "ANCHOR" -->\n'
                          f'                         <!-- splice-after: "ANCHOR" -->\n'
                          f'                         <!-- splice-append -->')
        elif directive is not None:
            content.append(line)
    if directive is not None:
        blocks.append((directive, anchor, content))
    if not blocks:
        if not "".join(lines).strip():
            # An EMPTY file. The engine tolerates it (exit 0, canonical unchanged), so this must
            # too: a checker that predicts a refusal the engine never makes sends a project to
            # edit a working overlay under maximum perceived urgency. Reported, not failed.
            return [], "EMPTY"
        return None, "no splice-before/after/append directive — this overlay is a silent no-op"
    return blocks, None


def check_one(overlay, canon, rel, name):
    """Return (problems, notes). Simulates the engine's progressive buffer."""
    problems, notes = 0, []
    ov_lines, err = read_lines(overlay)
    if err:
        notes.append(("BAD ENCODING", rel, err))
        return 1, notes
    canon_lines, err = read_lines(canon)
    if err:
        notes.append(("BAD ENCODING", f".claude/commands/{name}", err))
        return 1, notes

    blocks, err = parse(ov_lines)
    if err == "EMPTY":
        notes.append(("NOTE", rel, "file is empty — the engine ignores it, but it does nothing"))
        return 0, notes
    if err:
        notes.append(("MALFORMED", rel, err))
        return 1, notes

    # The engine computes each insertion point against the CURRENT buffer, so a later block may
    # legitimately anchor on a line an earlier block inserted. Checking every anchor against the
    # untouched canonical reports those as missing — a false alarm on a working overlay.
    buf = list(canon_lines)
    for directive, anchor, content in blocks:
        if directive == "append":
            buf.extend(content)
            notes.append(("ok", rel, "splice-append (no anchor)"))
            continue
        matches = [i for i, l in enumerate(buf) if l.rstrip("\n") == anchor]
        if not matches:
            notes.append(("NOT FOUND", rel,
                          f'splice-{directive}  {anchor[:56]}\n'
                          f'      no line matches this exactly (whole line, spaces count)'))
            problems += 1
            continue
        if len(matches) > 1:
            notes.append(("AMBIGUOUS x%d" % len(matches), rel,
                          f'splice-{directive}  {anchor[:56]}\n'
                          f'      the engine takes the FIRST silently — extend it until unique'))
            problems += 1
        else:
            notes.append(("ok", rel, f"splice-{directive}  {anchor[:56]}"))
        at = matches[0] if directive == "before" else matches[0] + 1
        buf[at:at] = content

    # Is the file we checked against already a baked artifact rather than the canonical?
    body = [l for _, _, c in blocks for l in c if l.strip()]
    if body and all(l in canon_lines for l in body):
        notes.append(("NOTE", rel,
                      f".claude/commands/{name} already contains this overlay's content, so it is "
                      f"a BAKED file, not the canonical. Anchors were checked against it; an anchor "
                      f"may be binding to a line this overlay itself inserted."))
    return problems, notes


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    ovdir = os.path.join(root, ".claude", "local-overlays")
    cmddir = os.path.join(root, ".claude", "commands")
    if not os.path.isdir(root):
        print(f"overlay-check: no such project path: {root}")
        return 1
    overlays = sorted(glob.glob(os.path.join(ovdir, "*.md")))
    if not overlays:
        print("overlay-check: no overlays in .claude/local-overlays/ — nothing to check")
        return 2

    skip = set()
    sf = os.path.join(ovdir, ".skip")
    if os.path.exists(sf):
        for line in open(sf, encoding="utf-8", errors="replace"):
            line = line.strip()
            if line and not line.startswith("#"):
                skip.add(line)

    problems = 0
    for ov in overlays:
        name = os.path.basename(ov)
        rel = f".claude/local-overlays/{name}"
        canon = os.path.join(cmddir, name)
        if name in skip:
            print(f"  CONTRADICTION  {rel}: also listed in .skip — it will never be applied")
            problems += 1
            continue
        if not os.path.exists(canon):
            print(f"  NO CANONICAL   {rel}: .claude/commands/{name} does not exist")
            problems += 1
            continue
        p, notes = check_one(ov, canon, rel, name)
        problems += p
        for tag, where, msg in notes:
            print(f"  {tag:<14} {where}  {msg}")

    print()
    if problems:
        print(f"overlay-check: {problems} problem(s). A distribution would refuse this overlay and "
              f"write NOTHING to ANY project on this host.")
        return 1
    print(f"overlay-check: ok — {len(overlays)} overlay file(s), every directive parses and binds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
