#!/usr/bin/env python3
"""consult-log.py — the consult log's grammar, enforced.

    consult-log.py validate <consult_notes.md>            exit 0 clean, 2 with a list of violations
    consult-log.py ledger   <claims-file> <ledger-file>   exit 0 if the ledger covers exactly the
                                                          claim ids with a valid status each; prints
                                                          "examined=N unavailable=N skipped=N"

Grammar (one file per project, append-only):
  # Consult log                              — header, once, first
  ## cycle <id> — <target>                   — id unique; id = YYYYMMDD-HHMMSS-<sha7>
  **Opening record**                         — exactly one per cycle, first thing after the heading
  ### Round N — reviewer …  /  ### Author — round N …   — any number, N ascending, rounds ≤ 3
  **Closing record**                         — exactly one per cycle, LAST thing in the cycle:
      after it, only its own "- " bullet lines, "> " quote lines and blank lines may follow
  - outcome: `<one of five, exact>`          — mandatory; not-reviewed:<CODE> takes an upper-case code
  opening SHA / result SHA / procedure digest / rounds / claims — mandatory (as line content)
A cycle with no closing record is OPEN; more than one open cycle is a violation. A cycle with
no opening record is a violation. A blank record heading is a violation.
"""
import re, sys

EXACT = {"agreed-applied", "agreed-proposed", "agreed-nothing", "disputed"}
NR = re.compile(r"^not-reviewed:[A-Z][A-Za-z0-9:-]*$")   # NO-TARGET, NOT-REVIEWABLE:progress-json, …
CYCLE = re.compile(r"^## cycle (\d{8}-\d{6}-[0-9a-f]{7}) — (\S.*)$")
REQ_CLOSE = ("- outcome:", "opening SHA:", "result SHA:", "procedure digest:", "rounds:", "- claims:")
ROUND = re.compile(r"^### (?:Round (\d+) — reviewer|Author — round (\d+))")
AFTER_CLOSE_OK = re.compile(r"^(- |> |$)")


def validate(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    v = []
    if not lines or lines[0].strip() != "# Consult log":
        v.append("line 1: header must be '# Consult log'")
    ids, cur, open_cycles = {}, None, []
    seen_open = seen_close = False
    last_round, close_line = 0, 0

    def end_cycle(at):
        if cur is None: return
        if not seen_open: v.append(f"line {at}: cycle {cur} has no opening record")
        if not seen_close: open_cycles.append(cur)

    awaiting_open = False   # between a cycle heading and its opening record only blank lines and "> " notes may appear
    for n, ln in enumerate(lines, 1):
        m = CYCLE.match(ln)
        if m:
            end_cycle(n)
            cid = m.group(1)
            if cid in ids: v.append(f"line {n}: duplicate cycle id {cid} (first at line {ids[cid]})")
            ids[cid] = n; cur = cid; seen_open = seen_close = False; last_round = 0; close_line = 0
            awaiting_open = True
            continue
        if awaiting_open:
            if ln.startswith("**Opening record**"): awaiting_open = False
            elif ln.strip() and not ln.startswith("> "):
                v.append(f"line {n}: content before the opening record of cycle {cur}: {ln[:60]}"); awaiting_open = False
        if ln.startswith("## cycle") and not m:   # reviewer prose may use '## ' freely; a malformed CYCLE heading may not
            v.append(f"line {n}: malformed cycle heading: {ln[:60]}")
        if cur is not None and seen_close and not AFTER_CLOSE_OK.match(ln):
            v.append(f"line {n}: content after the closing record of cycle {cur}: {ln[:60]}")
        if ln.startswith("**Opening record**"):
            if cur is None: v.append(f"line {n}: opening record outside a cycle")
            elif seen_open: v.append(f"line {n}: second opening record in cycle {cur}")
            elif seen_close: v.append(f"line {n}: opening record after closing record in cycle {cur}")
            seen_open = True
        if ln.startswith("**Closing record**"):
            if cur is None: v.append(f"line {n}: closing record outside a cycle")
            elif not seen_open: v.append(f"line {n}: closing record before opening record in cycle {cur}")
            elif seen_close: v.append(f"line {n}: second closing record in cycle {cur}")
            seen_close = True; close_line = n
            block = []   # the closing record's own bullets, stopping at the next cycle heading — never across a boundary
            for b in lines[n:n + 14]:
                if CYCLE.match(b): break
                if b.startswith("- "): block.append(b)
            text = "\n".join(block)
            for req in REQ_CLOSE:
                if req not in text: v.append(f"line {n}: closing record lacks '{req}'")
            oc = re.search(r"- outcome: `([^`]*)`", text)
            val = oc.group(1) if oc else ""
            if not (val in EXACT or NR.match(val)): v.append(f"line {n}: outcome not one of the five (exact): '{val}'")
        rm = ROUND.match(ln)
        if rm:
            if cur is None: v.append(f"line {n}: round entry outside a cycle")
            else:
                r = int(rm.group(1) or rm.group(2))
                if seen_close: v.append(f"line {n}: round entry after the closing record in cycle {cur}")
                if r > 3: v.append(f"line {n}: round {r} exceeds the cap of 3")
                if r < last_round: v.append(f"line {n}: round {r} after round {last_round} — not ascending")
                last_round = max(last_round, r)
        if re.match(r"^#{2,4}\s*$", ln): v.append(f"line {n}: empty heading")
    end_cycle(len(lines))
    if len(open_cycles) > 1: v.append(f"more than one open cycle: {', '.join(open_cycles)}")
    return v, open_cycles


def ledger(claims_path, ledger_path):
    claim_ids = [ln.split(":", 1)[0].strip() for ln in open(claims_path, encoding="utf-8") if ln.strip()]
    text = open(ledger_path, encoding="utf-8").read() if ledger_path else ""
    body = re.search(r"LEDGER:\n(.*?)\nEND-LEDGER", text, re.S)
    if not body:
        print("examined=0 unavailable=0 skipped=0 error=no-ledger-block"); return 2
    seen, counts, bad = {}, {"examined": 0, "unavailable": 0, "skipped": 0}, []
    for ln in body.group(1).split("\n"):
        m = re.match(r"^- (.+?): (examined|unavailable|skipped)\b", ln.strip())
        if not m:
            if ln.strip(): bad.append(f"malformed: {ln.strip()[:60]}")
            continue
        cid, status = m.group(1).strip(), m.group(2)
        if cid not in claim_ids: bad.append(f"invented id: {cid[:60]}")
        elif cid in seen: bad.append(f"duplicate id: {cid[:60]}")
        else: seen[cid] = status; counts[status] += 1
    missing = [c for c in claim_ids if c not in seen]
    if missing: bad.append(f"missing ids: {', '.join(m[:40] for m in missing)}")
    print(f"examined={counts['examined']} unavailable={counts['unavailable']} skipped={counts['skipped']}"
          + (f" error={'; '.join(bad)}" if bad else ""))
    return 2 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "validate":
        viol, open_c = validate(sys.argv[2])
        for x in viol: print("consult-log:", x)
        print(f"consult-log: {'clean' if not viol else str(len(viol)) + ' violation(s)'}; open cycles: {', '.join(open_c) or 'none'}")
        sys.exit(2 if viol else 0)
    if len(sys.argv) >= 4 and sys.argv[1] == "ledger":
        sys.exit(ledger(sys.argv[2], sys.argv[3]))
    print(__doc__); sys.exit(1)
