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
    REAL="${2:?}"; CL="${3:?}"; ST="${4:?}"; bad=0
    for pair in "real:$REAL" "clone:$CL"; do n=${pair%%:*}; d=${pair#*:}
      if ! diff <(fp_tree "$d") "$ST/$n.fp" > "$ST/$n.diff"; then bad=1; echo "DRIFT in $n tree:"; sed 's/^/   /' "$ST/$n.diff" | head -40; fi
    done
    [ $bad -eq 0 ] && echo "posture: clean" || exit 2;;
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
    if [ -f "$ST/real.fp" ]; then diff <(fp_tree "$REAL") "$ST/real.fp" > "$ST/real.diff" || die "real tree drifted since verify — refusing to append:$(sed 's/^/ /' "$ST/real.diff" | head -20 | tr '\n' ';')"; fi
    L="$REAL/$LOG"; OLD="$ST/log.before"
    [ -e "$OLD" ] && [ "$L" -ef "$OLD" ] && die "state dir aliases the log"
    [ -e "$ST/log.expected" ] && [ "$L" -ef "$ST/log.expected" ] && die "state dir aliases the log"
    if [ -f "$L" ]; then cp --remove-destination "$L" "$OLD" || die "cannot copy the log"; else header > "$OLD"; fi
    { cat "$OLD"; printf '\n'; cat "$REC"; } > "$ST/log.expected"
    cp --remove-destination "$ST/log.expected" "$L" || die "cannot write the log"
    # step 7 — prove old + record, AND that the only change in the real tree is the log; roll back otherwise
    cmp -s "$L" "$ST/log.expected" || { cp --remove-destination "$OLD" "$L"; die "log is not old bytes + record — rolled back"; }
    fp_tree "$REAL" > "$ST/real.fp.new"
    if [ -f "$ST/real.fp" ] && diff "$ST/real.fp.new" "$ST/real.fp" | grep -E '^[<>]' | grep -vF "$LOG" | grep -vE "^[<>] LOG " | grep -q .; then
      cp --remove-destination "$OLD" "$L"; die "a write other than the log landed during append — rolled back:$(diff "$ST/real.fp.new" "$ST/real.fp" | grep -E '^[<>]' | grep -vF "$LOG" | grep -vE "^[<>] LOG " | head -10 | tr '\n' ';')"; fi
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
