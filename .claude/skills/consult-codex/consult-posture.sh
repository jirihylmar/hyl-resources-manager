#!/bin/bash
# consult-posture.sh — the reviewer's checkout, and the proof that it wrote nothing that persists.
# Task 30.5.  This is the 8-step sequence agreed in the dry run (consult_notes.md, round 2, #5):
#
#   1 snapshot both trees, INCLUDING consult_notes.md      -> snapshot
#   2 run the reviewer with output only to a scratch path  (caller)
#   3 stop the reviewer                                     (caller)
#   4 verify the complete snapshots, NO exclusions          -> verify
#   5 validate the scratch record structurally              -> append (first half)
#   6 only then let the skill append it to the real log     -> append (second half)
#   7 verify the log equals old bytes + validated append    -> append (asserts)
#   8 commit by named path                                  (caller; the skill owns that commit)
#
#   consult-posture.sh clone    <real> <clone>           # transient clone: no remotes, guard re-armed
#   consult-posture.sh snapshot <real> <clone> <state>   # step 1
#   consult-posture.sh verify   <real> <clone> <state>   # step 4 — exit 2 and a list on any drift
#   consult-posture.sh append   <real> <record> <state>  # steps 5–7 — exit 2 if the log is not old+record
#   consult-posture.sh refresh  <real> <state>           # re-baseline the REAL tree alone (see below)
#   consult-posture.sh header                            # the log's first lines, for a project that has none yet
#   consult-posture.sh destroy  <clone>
#
# Why a CLONE and not a worktree: a worktree shares origin and refs — a push from it succeeded
# with `git status` reading clean afterward (measured 2026-08-25). A clone with origin removed
# cannot reach anything — UNLESS the reviewer adds one back, which is why .git/ is fingerprinted.
# Why the clone path must not be one level under $HOME: estate-reach would discover it as a project.
# Why EVERY path is hashed, .git included (adversarial pass 2026-08-25, 27 holes): git's own view
# reports names, not content, and nothing under .git/ at all. A reviewer could plant
# .git/hooks/post-commit in the REAL checkout — code execution at the skill's own commit step —
# re-add origin, set core.hooksPath=/dev/null, write objects, add worktrees, flip index bits
# (assume-unchanged / skip-worktree / sparse), overwrite an already-listed untracked or ignored
# file, or commit inside a gitignored nested repo: every one of those read "posture: clean".
# Why append re-checks the real tree BEFORE touching the log: a write landing between verify and
# append used to be baselined as the skill's own. Why the log is NOT excluded from anything:
# excluding it made it the one path where a reviewer write would hide.
# What this still cannot do: a reviewer under bypass can rewrite the state dir and re-run
# `snapshot` itself. That is defence, not proof; the caller records the snapshot digest.
# Why `refresh` exists (task 31.1): when the skill ITSELF undoes a write it just made — a publication
# that could not be committed, rolled back out of the log — the step-4 baseline no longer describes
# the tree. Refreshing it is the skill re-baselining its own reversal, never the clone's; `refresh`
# deliberately does not touch clone.fp, so a reviewer write during that window is still caught.
set -u
LOG=consult_notes.md
die(){ echo "consult-posture: $*" >&2; exit 2; }

fp_tree(){  # $1=dir -> fingerprint of EVERY path under the tree, .git INCLUDED: git view + type/mode/size/link + content hash
  local d="$1"
  ( cd "$d" 2>/dev/null || { echo "TREE UNREADABLE $d"; exit 9; }
    echo "HEAD $(git rev-parse HEAD 2>/dev/null)"
    git for-each-ref --format='%(refname) %(objectname)' 2>&1 || echo "REFS FAILED"
    git status --porcelain --ignored --untracked-files=all 2>&1 || echo "STATUS FAILED"
    git stash list 2>&1
    find . -mindepth 1 ! -path './.git/index.lock' -printf '%y %m %s %P -> %l\n' 2>&1 | LC_ALL=C sort
    find . -type f ! -path './.git/index.lock' -print0 2>/dev/null | LC_ALL=C sort -z | xargs -0 -r sha256sum 2>&1
    [ -f "$LOG" ] && echo "LOG $(sha256sum "$LOG" | cut -d' ' -f1) $(wc -c < "$LOG")" || echo "LOG absent" )
}
# OWNED PATHS INSIDE A TREE THE SKILL DOES NOT OWN.
#
# The ownership rule (see `verify`) draws the line at what the skill is responsible for — and inside
# the real checkout two things still are, for reasons that are about the skill, not about a list of
# attacks someone thought of:
#
#   consult_notes.md   the skill WRITES it. Its whole integrity claim is "old bytes + record"; if
#                      something else rewrites it between verify and append, the append lands on
#                      tampered content and the claim is false. (Attack H7 in the suite.)
#   .git/hooks/** and  the skill's own `git commit` EXECUTES these. A file planted in either runs
#   .claude/hooks/**   as the operator at the skill's publication step. Both are listed because which
#                      one git uses depends on core.hooksPath, which /start-session Step 0.5 sets to
#                      .claude/hooks — so naming only one would leave the other open. (Attack B1.)
#
# Nothing else qualifies. A concurrent commit's objects and refs, a build's ignored files, a new
# untracked file, a nested repo, even the repo being flipped to bare — the skill neither wrote them
# nor runs them, so they are environment, and environment is recorded rather than refused.
owned_drift(){   # $1 = a diff against real.fp -> 0 (true) if a path the skill owns moved
  grep -qE '^[<>] LOG ' "$1" && return 0
  # Candidate paths out of the three shapes fp_tree emits: the find listing, the sha256sum listing,
  # and the porcelain status. TOP-LEVEL only — a nested repo's .git/hooks/ is not this repo's, and a
  # pattern that matched it would be refusing for a reason that is not true.
  { awk '/^[<>] [dfl] /{print $5}' "$1"
    sed -n 's/^[<>] [0-9a-f]\{64\}  \.\///p' "$1"
    sed -n 's/^[<>] [ ?ADMRU!][ ?ADMRU!] //p' "$1"
  } | grep -qE '^(consult_notes\.md|\.git/hooks/|\.claude/hooks/)'
}

# One sentence describing motion in a tree the skill does not own. Used by `verify` and `append`, so
# the round record and the log describe environmental change the same way wherever it is noticed.
real_summary(){   # $1 = a diff file produced against real.fp
  # NAMES the paths. A refusal that becomes a note is only an acceptable trade if the note is
  # ACTIONABLE — "3 lines differ" tells the operator nothing and would quietly convert detection into
  # silence, which is the failure this whole loop exists to avoid. With the paths named, a file the
  # reviewer had no business writing is visible BY NAME in the round record and in the closing
  # record, read at the next session start. Detection is kept; only the automatic refusal is dropped,
  # and only where attribution is impossible.
  local d="$1" paths n moved
  moved=$(grep -cE '^[<>] HEAD ' "$d" 2>/dev/null || true)
  paths=$(awk '/^[<>] [dfl] /{print $5}' "$d" 2>/dev/null | sort -u | head -8 | paste -sd, - || true)
  n=$(grep -cE '^[<>] ' "$d" 2>/dev/null || true)
  printf '%s%s line(s) differ%s' \
    "$( [ "${moved:-0}" -gt 0 ] && echo 'HEAD moved, ' )" \
    "${n:-0}" "${paths:+; paths: $paths}"
}

header(){ printf '# Consult log\n\nAppend-only. One `## cycle` per cycle, an opening and a closing record each. Never authoritative — progress.json is.\n'; }

case "${1:-}" in
  header) header;;
  clone)
    REAL="${2:?real}"; CL="${3:?clone}"
    [ "$(dirname "$(realpath -m "$CL")")" = "$HOME" ] && die "refusing a clone one level under \$HOME — estate-reach would discover it as a project"
    [ -e "$CL" ] && die "clone path exists: $CL"
    git clone -q --no-hardlinks "$REAL" "$CL" || die "clone failed"
    git -C "$CL" remote remove origin
    git -C "$CL" config core.hooksPath .claude/hooks
    [ -z "$(git -C "$CL" remote)" ] || die "clone still has a remote"
    echo "clone $CL at $(git -C "$CL" rev-parse --short HEAD), no remotes, hooksPath=$(git -C "$CL" config core.hooksPath)";;
  snapshot)
    # Every write is checked. Without this the two redirects could fail (a full state filesystem, a
    # read-only $ST) and the trailing echo would still supply exit 0 — consult.sh would proceed with
    # a missing or truncated baseline, believing posture protection was armed. Same swallowed-write
    # defect as `refresh` had; found by the reviewer in cycle 20260825-170103-b72153b, which noticed
    # the fix had been applied to one of the two and not the other.
    REAL="${2:?}"; CL="${3:?}"; ST="${4:?state dir}"; mkdir -p "$ST" || die "cannot create $ST"
    fp_tree "$REAL" > "$ST/real.fp"  || die "cannot write $ST/real.fp"
    fp_tree "$CL"   > "$ST/clone.fp" || die "cannot write $ST/clone.fp"
    echo "snapshot: real $(wc -l < "$ST/real.fp") lines, clone $(wc -l < "$ST/clone.fp") lines, digest $(cat "$ST/real.fp" "$ST/clone.fp" | sha256sum | cut -c1-16)";;
  verify)
    # THE OWNERSHIP RULE — this is the whole design, and it replaced a list of exceptions.
    #
    # A guard may hard-refuse only for what the skill OWNS. Motion it does not own is recorded as
    # evidence, never treated as a violation.
    #
    #   the CLONE is owned  — the skill creates it, nothing else on the machine touches it, and the
    #                         reviewer's process runs inside it. Drift there is attributable to the
    #                         reviewer and to nobody else. Hard refusal. Exit 2.
    #   the REAL tree is NOT owned — the operator, concurrent sessions, builds, deploys and CI all
    #                         write there. Drift there is dominated by environmental noise, so it can
    #                         prove nothing about the reviewer. RECORDED, never refused.
    #
    # Why this is a rule and not another exception (operator, 2026-08-26: "fix it in a way that no
    # simillar fault come again ... not everythign can be strict, it would become a never ending
    # list"). Until now this fingerprinted BOTH trees and refused on any difference — HEAD, every
    # ref, the stash list, `status --ignored --untracked-files=all`, and a sha256 of every file
    # INCLUDING .git/. In a live repo that fires on a concurrent session's commit, on a build writing
    # ignored files, even on someone else's `git fetch`. Measured in app-brm-manufacturing-products:
    # a phase-133 commit landing mid-cycle killed round 2 and LOST the author's response and that
    # round from the log. Carving an exception per symptom is the never-ending list; this draws the
    # line once, at the boundary of what the skill can actually be responsible for.
    #
    # What is NOT lost: real-tree motion is still fully described, in the round record and in the
    # closing record, so a write that should not have happened is visible to the operator at the next
    # session start. Detection is kept; the automatic refusal — the part that could not tell the
    # reviewer from the author — is what goes.
    REAL="${2:?}"; CL="${3:?}"; ST="${4:?}"
    if ! diff <(fp_tree "$CL") "$ST/clone.fp" > "$ST/clone.diff"; then
      echo "DRIFT in clone tree:"; sed 's/^/   /' "$ST/clone.diff" | head -40; exit 2; fi
    if [ -f "$ST/real.fp" ] && ! diff <(fp_tree "$REAL") "$ST/real.fp" > "$ST/real.diff"; then
      if owned_drift "$ST/real.diff"; then
        echo "DRIFT in a path the skill OWNS inside the real checkout:"; sed 's/^/   /' "$ST/real.diff" | head -40; exit 2; fi
      echo "posture: clean (clone) · real tree moved — $(real_summary "$ST/real.diff")"
      exit 0; fi
    echo "posture: clean";;
  append)
    REAL="${2:?}"; REC="${3:?record file}"; ST="${4:?}"
    # step 5 — structural validation of the scratch record
    [ -s "$REC" ] || die "record is empty"
    head -1 "$REC" | grep -qE '^(#{2,4} [^[:space:]]|\*\*(Opening|Closing) record\*\*|- publication: LOG-COMMITTED-NOT-PUSHED)' || die "record must begin with a heading with text, an **Opening/Closing record** marker, or the publication marker"
    tr -d '\n\t' < "$REC" | LC_ALL=C grep -q '[[:cntrl:]]' && die "record contains a control byte (NUL, CR, ESC, …)"
    # one structural marker per record — except that an opening record legitimately starts with its cycle heading
    tail -n +2 "$REC" | grep -qE '^(## cycle |\*\*Closing record\*\*)' && die "record carries a second cycle heading or a closing marker inside it"
    head -1 "$REC" | grep -q '^## cycle ' || { tail -n +2 "$REC" | grep -q '^\*\*Opening record\*\*' && die "record carries an opening marker but is not a cycle opening"; }
    # value shapes only — a key NAME in a diff or a regex is not a credential (a name-based rule refused its own diff once)
    grep -qE '(AKIA[0-9A-Z]{16}|aws_secret_access_key[[:space:]]*[=:][[:space:]]*[A-Za-z0-9/+]{30,}|X[-_]MCP[-_]Secret[[:space:]]*[:=][[:space:]]*[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{20,}|eyJ[A-Za-z0-9_-]{15,}\.)' "$REC" && die "record looks like it carries a credential"
    # step 6 — the real tree must still equal the step-4 baseline: a write landing between verify and append is NOT the skill's
    # step 6 — the real tree is NOT owned (see the ownership rule under `verify`). Motion here is
    # recorded and the baseline is refreshed so step 7 can still isolate the skill's own write. It
    # does NOT refuse: this line used to `die`, which is what killed a round whenever another session
    # committed — and it killed it AFTER the reviewer had been paid for, losing the round entirely.
    if [ -f "$ST/real.fp" ] && ! diff <(fp_tree "$REAL") "$ST/real.fp" > "$ST/real.diff"; then
      owned_drift "$ST/real.diff" && die "a path the skill OWNS moved since verify — refusing to append:$(sed 's/^/ /' "$ST/real.diff" | head -20 | tr '\n' ';')"
      echo "append: real tree moved before this write — $(real_summary "$ST/real.diff") (recorded, not refused)" >&2
      fp_tree "$REAL" > "$ST/real.fp"
    fi
    L="$REAL/$LOG"; OLD="$ST/log.before"
    [ -e "$OLD" ] && [ "$L" -ef "$OLD" ] && die "state dir aliases the log"
    [ -e "$ST/log.expected" ] && [ "$L" -ef "$ST/log.expected" ] && die "state dir aliases the log"
    if [ -f "$L" ]; then cp --remove-destination "$L" "$OLD" || die "cannot copy the log"; else header > "$OLD"; fi
    { cat "$OLD"; printf '\n'; cat "$REC"; } > "$ST/log.expected"
    cp --remove-destination "$ST/log.expected" "$L" || die "cannot write the log"
    # step 7 — prove old + record, AND that the only change in the real tree is the log; roll back otherwise
    cmp -s "$L" "$ST/log.expected" || { cp --remove-destination "$OLD" "$L"; die "log is not old bytes + record — rolled back"; }
    fp_tree "$REAL" > "$ST/real.fp.new"
    # The LOG is owned by the skill and its bytes are proved exactly, above (old + record, or rolled
    # back). Motion in the rest of the real tree during the write window belongs to the environment:
    # recorded, not rolled back. Rolling the log back because someone else committed during the
    # append discards a record the reviewer already earned.
    if [ -f "$ST/real.fp" ] && diff "$ST/real.fp.new" "$ST/real.fp" | grep -E '^[<>]' | grep -vF "$LOG" | grep -vE "^[<>] LOG " | grep -q .; then
      echo "append: real tree moved during this write — $(diff "$ST/real.fp.new" "$ST/real.fp" | grep -E '^[<>]' | grep -vF "$LOG" | grep -vE "^[<>] LOG " | wc -l) line(s) (recorded, not refused)" >&2; fi
    mv "$ST/real.fp.new" "$ST/real.fp"   # the skill's write is now the baseline; nothing else moved
    echo "append: +$(( $(wc -c < "$REC") + 1 )) bytes (newline + record) to $LOG, verified old+record";;
  refresh)
    # the REAL tree only, and only after the skill reversed its own write — see the header.
    REAL="${2:?}"; ST="${3:?state dir}"; mkdir -p "$ST"
    # the redirect is checked: without `|| die` a failed write leaves the OLD baseline in place and
    # the case arm still exits 0 through the following echo — a swallowed status in the one helper
    # whose whole job is to make a baseline true
    fp_tree "$REAL" > "$ST/real.fp" || die "cannot write $ST/real.fp"
    echo "refresh: real $(wc -l < "$ST/real.fp") lines";;
  destroy)
    CL="${2:?}"; [ -d "$CL/.git" ] || die "not a git dir: $CL"; chmod -R u+rwX "$CL" 2>/dev/null; rm -rf "$CL" || die "destroy failed: $CL"; [ -e "$CL" ] && die "still present: $CL"; echo "destroyed $CL";;
  *) sed -n '2,39p' "$0"; exit 1;;
esac
