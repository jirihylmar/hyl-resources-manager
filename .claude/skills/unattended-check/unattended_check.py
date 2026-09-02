#!/usr/bin/env python3
"""unattended_check.py — the one implementation of PROJECT_CHARTER.md § 11, Unattended operations.

Two modes, one body of rules, because the pre-yield gate and the session-start reconciliation ask
the SAME question — "is this operation actually being watched?" — and answering it twice in prose
is how the two answers drift apart:

  --gate       before a final response.  Exit 3 if any operation must refuse the yield.
  --reconcile  at session start.         Exit 0 always; exit 3 if a watcher needs recovery FIRST.

WHY THIS EXISTS (models-trainer, 2026-09-01). An executor said it was monitoring an AWS capacity
operation. It then sent a final response, which ended polling. Its systemd supervisor went inactive
and nothing noticed. No retry happened for over eight hours. Promised 30-minute reports never fired.
The supervisor returned exit 0 for capacity exhaustion, so a FAILED DELIVERY READ AS SUCCESS. And
the next session did not reconcile the promised watcher against its live state before doing other
work. Every one of those is checkable from recorded state plus one host-owned liveness command, and
none of them was checked, because nothing was recorded and nothing ran.

HOST-OWNED vs TRAVELLING. `liveness_check` and `state_ref` are host-owned: they may name a systemd
unit, a launchd label, a cron entry, a pid file, an absolute path. Everything else travels between
hosts in progress.json and must stay portable — an absolute /home/... path in a travelling field is
reported, because progress.json is read on machines where it means nothing.
"""

import argparse
import datetime
import json
import os
import re
import shlex
import subprocess
import sys

TERMINAL_TASK = {"complete", "completed", "superseded", "done", "closed", "dropped",
                 "cancelled", "canceled", "resolved", "obsolete", "abandoned"}

MODES = ("session-watched", "durably-supervised", "unmonitored")

# The charter's six terminal outcome classes, plus the one non-terminal value. `delivered` is the
# ONLY one that means the outcome happened; every other terminal value is a non-delivery, and that
# separation is the whole point — a supervisor may exit 0 on capacity exhaustion and must not have
# that read as success.
DELIVERY_STATES = ("pending", "delivered", "capacity-exhausted", "workload-failed",
                   "controller-crashed", "cleanup-failed", "deadline-missed")
NON_DELIVERY_TERMINAL = ("capacity-exhausted", "workload-failed", "controller-crashed",
                         "cleanup-failed", "deadline-missed")

REQUIRED = ("operation_id", "supervisor_id", "supervisor_mode", "state_ref", "started_at",
            "last_observed_at", "next_action_at", "deadline_at", "retry_count", "retry_limit",
            "delivery_state", "cleanup_state", "cleanup_owner", "notification_state")

TRAVELLING = ("operation_id", "supervisor_id", "supervisor_mode", "started_at", "last_observed_at",
              "next_action_at", "deadline_at", "delivery_state", "cleanup_state", "cleanup_owner",
              "notification_state")

ABS_HOST_PATH = re.compile(r"(^|[\s\"'])(/home/|/Users/|/root/|[A-Za-z]:\\)")


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _ts(v):
    """Parse an ISO-8601 instant. Returns None if absent or unparseable — the caller decides what
    an unreadable time MEANS, because 'absent' and 'malformed' are both failures here but neither
    may be silently read as 'fine'."""
    if not v or not isinstance(v, str):
        return None
    s = v.strip().replace("Z", "+00:00")
    try:
        d = datetime.datetime.fromisoformat(s)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)


def _tasks(data):
    ph = data.get("phases") or {}
    items = ph.items() if isinstance(ph, dict) else enumerate(ph)
    for key, p in items:
        if not isinstance(p, dict):
            continue
        ts = p.get("tasks") or []
        ts = list(ts.values()) if isinstance(ts, dict) else ts
        for t in ts:
            if isinstance(t, dict):
                yield key, t


def _probe(cmd, timeout):
    """Run the project's own liveness command. NOT INTERPRETED, only run: this file must never
    learn what systemd is. A non-zero exit means 'not alive'; a missing command means 'unproved',
    and those are different answers (see classify)."""
    if not cmd or not isinstance(cmd, str):
        return None, "no liveness_check declared"
    try:
        r = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "liveness_check timed out after %ss" % timeout
    except Exception as e:                                   # noqa: BLE001 - report, never raise
        return False, "liveness_check could not run: %s" % e
    return (r.returncode == 0), (r.stdout or r.stderr or "").strip()[:200]


def classify(op, now, timeout):
    """Return (state, reasons, alive). One classification, used by both modes."""
    reasons = []
    mode = str(op.get("supervisor_mode") or "").strip().lower()
    delivery = str(op.get("delivery_state") or "").strip().lower()

    missing = [f for f in REQUIRED if op.get(f) in (None, "")]
    # retry_count 0 is legitimate and must not read as missing.
    missing = [f for f in missing if not (f in ("retry_count", "retry_limit")
                                          and isinstance(op.get(f), int))]
    if missing:
        reasons.append("missing required field(s): %s" % ", ".join(missing))
    if mode not in MODES:
        reasons.append("supervisor_mode %r is not one of %s" % (op.get("supervisor_mode"), ", ".join(MODES)))
    if delivery and delivery not in DELIVERY_STATES:
        reasons.append("delivery_state %r is not one of %s" % (op.get("delivery_state"), ", ".join(DELIVERY_STATES)))

    for f in TRAVELLING:
        v = op.get(f)
        if isinstance(v, str) and ABS_HOST_PATH.search(v):
            reasons.append("%s carries a host-specific absolute path; this field travels between "
                           "hosts in progress.json — use a portable identifier" % f)

    if delivery == "delivered":
        return "terminal-success", reasons, None
    if delivery in NON_DELIVERY_TERMINAL:
        reasons.append("delivery_state is %r — terminal, and NOT a delivery" % delivery)
        return "terminal-non-delivery", reasons, None

    alive, detail = (None, "")
    if mode == "durably-supervised":
        alive, detail = _probe(op.get("liveness_check"), timeout)
        if alive is None:
            reasons.append("claims durable supervision but declares no liveness_check, so the "
                           "supervisor cannot be proved alive")
        elif not alive:
            reasons.append("supervisor %r is NOT active (%s)" % (op.get("supervisor_id"), detail or "probe failed"))

    nxt, dl = _ts(op.get("next_action_at")), _ts(op.get("deadline_at"))
    if dl is not None and now > dl:
        reasons.append("deadline %s has passed with no terminal delivery_state" % op.get("deadline_at"))
        return "overdue", reasons, alive
    if nxt is None:
        reasons.append("next_action_at is absent or unparseable, so nothing is scheduled to happen")
        return ("watcher-missing" if mode == "durably-supervised" else "state-unknown"), reasons, alive
    if now > nxt:
        reasons.append("next_action_at %s has passed" % op.get("next_action_at"))
        return "overdue", reasons, alive

    if mode == "unmonitored":
        reasons.append("no watcher is running")
        return "unmonitored", reasons, alive
    if mode == "durably-supervised":
        return ("running-healthy" if alive else "watcher-missing"), reasons, alive
    return "session-watched", reasons, alive


def gate(ops, now, timeout):
    """The charter's six refusal conditions. A yield is refused if ANY fires."""
    refusals = []
    for key, tid, name, op in ops:
        state, reasons, _ = classify(op, now, timeout)
        why = []
        delivery = str(op.get("delivery_state") or "").strip().lower()
        mode = str(op.get("supervisor_mode") or "").strip().lower()
        terminal = delivery == "delivered" or delivery in NON_DELIVERY_TERMINAL

        if not terminal and mode != "durably-supervised":
            why.append("operation is non-terminal and no durable supervisor is proved "
                       "(supervisor_mode=%r)" % op.get("supervisor_mode"))
        if not terminal and state in ("watcher-missing",):
            why.append("supervisor is inactive before delivery")
        if not terminal and _ts(op.get("next_action_at")) is None:
            why.append("next observation time is absent")
        elif not terminal and _ts(op.get("next_action_at")) and now > _ts(op.get("next_action_at")):
            why.append("next observation time has already passed")
        dl = _ts(op.get("deadline_at"))
        if not terminal and dl is not None and now > dl:
            why.append("deadline has passed with no terminal result")
        if not str(op.get("cleanup_owner") or "").strip():
            why.append("no independent cleanup owner is named")
        if str(op.get("reports_every") or "").strip() and not str(op.get("notification_state") or "").strip():
            why.append("periodic reporting was promised but no scheduler and notification route exist")

        if why:
            refusals.append((tid, name, op.get("operation_id"), state, why + reasons))
    return refusals


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gate", action="store_true", help="pre-yield gate; exit 3 to refuse the yield")
    ap.add_argument("--reconcile", action="store_true", help="session-start classification")
    ap.add_argument("--file", default="progress.json")
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not (a.gate or a.reconcile):
        ap.error("choose --gate or --reconcile")

    try:
        with open(a.file) as fh:
            data = json.load(fh)
    except FileNotFoundError:
        print("unattended-check: no %s here — nothing to check" % a.file)
        return 0
    except Exception as e:                                   # noqa: BLE001
        print("unattended-check: CANNOT READ %s (%s) — the state of every unattended operation in "
              "this project is UNKNOWN, which is not the same as none" % (a.file, e))
        return 2

    ops = []
    for key, t in _tasks(data):
        op = t.get("unattended")
        if not isinstance(op, dict):
            continue
        if str(t.get("status") or "").strip().lower() in TERMINAL_TASK:
            continue
        ops.append((key, t.get("id"), str(t.get("name") or "")[:70], op))

    now = _now()

    if a.gate:
        refusals = gate(ops, now, a.timeout)
        if a.json:
            print(json.dumps({"operations": len(ops), "refusals": [
                {"task": r[0], "operation_id": r[2], "state": r[3], "reasons": r[4]} for r in refusals]},
                indent=1))
        elif not ops:
            print("unattended-check: no open task declares an unattended operation — yield permitted")
        elif not refusals:
            print("unattended-check: %d operation(s) proved — yield permitted" % len(ops))
            for key, tid, name, op in ops:
                print("  OK    %s  %s  supervisor=%s  next=%s  deadline=%s  delivery=%s"
                      % (tid, op.get("operation_id"), op.get("supervisor_id"),
                         op.get("next_action_at"), op.get("deadline_at"), op.get("delivery_state")))
        else:
            print("unattended-check: YIELD REFUSED — %d operation(s) cannot be left as they are."
                  % len(refusals))
            for tid, name, oid, state, why in refusals:
                print("  REFUSE %s (%s) [%s] — %s" % (tid, oid, state, name))
                for w in why:
                    print("           - %s" % w)
            print("\nFix the operation or say plainly that no watcher is running. Do NOT send a "
                  "final response describing this as monitored: see PROJECT_CHARTER.md section 11.")
        return 3 if refusals else 0

    # --reconcile
    rows, recover = [], []
    for key, tid, name, op in ops:
        state, reasons, _ = classify(op, now, a.timeout)
        rows.append((tid, op.get("operation_id"), state, reasons, name))
        if state in ("watcher-missing", "overdue", "state-unknown", "terminal-non-delivery"):
            recover.append((tid, op.get("operation_id"), state))
    if a.json:
        print(json.dumps({"operations": [
            {"task": r[0], "operation_id": r[1], "state": r[2], "reasons": r[3]} for r in rows],
            "recover_first": [{"task": r[0], "operation_id": r[1], "state": r[2]} for r in recover]},
            indent=1))
        return 3 if recover else 0
    if not ops:
        print("unattended-check: no open task declares an unattended operation")
        return 0
    print("**Unattended operations** (PROJECT_CHARTER.md section 11)\n")
    print("| Task | Operation | State | What it means |")
    print("|------|-----------|-------|---------------|")
    MEANING = {
        "running-healthy":       "a named supervisor answered and its next action is still ahead",
        "terminal-success":      "delivered",
        "terminal-non-delivery": "finished WITHOUT delivering — this is not success",
        "overdue":               "its own next action or deadline has passed",
        "watcher-missing":       "it claims a supervisor and none is running",
        "state-unknown":         "nothing recorded says what happens next",
        "session-watched":       "only watched inside an open turn — no turn is open now",
        "unmonitored":           "no watcher is running, and that is recorded honestly",
    }
    for tid, oid, state, reasons, name in rows:
        print("| %s | %s | **%s** | %s |" % (tid, oid, state, MEANING.get(state, state)))
    if recover:
        print("\n> **Recover these before any unrelated work** — charter section 11: a watcher that is "
              "missing, inactive or overdue makes its own recovery the first task of this session.")
        for tid, oid, state in recover:
            print(">  - %s (%s): %s" % (tid, oid, state))
    for tid, oid, state, reasons, name in rows:
        for r in reasons:
            print("  note %s: %s" % (tid, r))
    return 3 if recover else 0


if __name__ == "__main__":
    sys.exit(main())
