#!/bin/bash
# consult.sh — the mechanical half of the consult loop (Entry B). The author (Claude, the live
# session) is the other half: it reads each reviewer round from the log, writes its response to a
# file, and hands it back with `respond`. Nothing here writes progress.json. Ever.
#
#   consult.sh open    <target>           preflight -> clone -> identity -> claims -> opening record
#   consult.sh review                     run the next reviewer round (round 1 uses the template)
#   consult.sh respond <author.md>        append the author's entry, then run the next reviewer round
#   consult.sh close   <outcome> [sha]    closing record; log-only commit + FF push; destroy clone
#   consult.sh status
#
# Targets:  task:<id>  phase:<key>  file:<path>[,<path>…]  commit:<range>
# Outcomes: agreed-applied <result-sha> · agreed-proposed · agreed-nothing · disputed · not-reviewed:<why>
#
# Every refusal is RECORDED (opening + closing not-reviewed:<code>), committed, and pushed —
# a refusal that leaves no trace is the message a silent script never delivers.
set -u
SK="$(cd "$(dirname "$0")" && pwd)"
REAL="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "consult: not in a git checkout" >&2; exit 1; }
PROJ="$(basename "$REAL")"
WORK="$HOME/.cache/consult/$PROJ"; CL="$WORK/clone"; ST="$WORK/state"; SCR="$WORK/scratch"
LOG="$REAL/consult_notes.md"; CAP=3
POSTURE="$SK/consult-posture.sh"; HERE="$SK/codex-here"
mkdir -p "$ST" "$SCR"
st(){ cat "$ST/$1" 2>/dev/null; }; put(){ printf '%s' "$2" > "$ST/$1"; }
say(){ echo "consult: $*" >&2; }

procedure_digest(){ sed -n '/<!-- procedure:begin -->/,/<!-- procedure:end -->/p' "$SK/SKILL.md" | sha256sum | cut -c1-16; }

# ---- append a record to the real log through the posture path (the skill's ONE sanctioned write) ----
append(){  # validate OLD + CANDIDATE first; the real log is touched only if the result is grammatical
  { if [ -f "$LOG" ]; then cat "$LOG"; else "$POSTURE" header; fi; printf '\n'; cat "$1"; } > "$SCR/candidate.md"   # a missing log is created by the posture append, never here
  python3 "$SK/consult-log.py" validate "$SCR/candidate.md" >/dev/null || { say "record refused — the log would violate its grammar:"; python3 "$SK/consult-log.py" validate "$SCR/candidate.md" >&2; exit 2; }
  "$POSTURE" append "$REAL" "$1" "$ST" >/dev/null || { say "append refused"; exit 2; }; }

# ---- refuse: opening + closing not-reviewed, committed, pushed, exit 3 ----
refuse(){
  local code="$1" why="${2:-}"
  say "REFUSED $code${why:+ — $why}"
  # refusal records go through the SAME validated append as every other record — no side door.
  # But a refusal must never leave state behind or vanish silently: if the record itself cannot be
  # appended (measured 2026-08-25: a cycle id the grammar rejected), say so LOUDLY, clean up, still exit 3.
  local recorded=1
  pub_begin || pub_abort "the refusal $code"
  [ -f "$ST/opened" ] || { printf '## cycle %s — %s\n\n**Opening record**\n- entry: B · procedure digest: %s\n- preflight: REFUSED %s%s\n' \
      "$(st cycle)" "${T:-(no target)}" "$(procedure_digest)" "$code" "${why:+ — $why}" > "$SCR/open.md"; ( append "$SCR/open.md" ) || recorded=0; }
  printf '**Closing record**\n- outcome: `not-reviewed:%s`\n- opening SHA: %s · result SHA: -\n- procedure digest: %s · rounds: 0 of %s\n- claims: examined 0 · unavailable 0 · skipped 0\n- nothing written to progress.json by this cycle\n' \
      "$code" "$(git -C "$REAL" rev-parse HEAD)" "$(procedure_digest)" "$CAP" > "$SCR/close.md"
  if [ $recorded -eq 1 ] && ( append "$SCR/close.md" ); then
    publish_or_rollback "consult: refused $code" "the refusal $code was written to consult_notes.md but could not be COMMITTED, so it has been rolled back out of the log and out of the index. Nothing uncommitted is left behind and no record of this aborted cycle exists. The state dir and any clone are kept for diagnosis ($WORK). Fix the commit failure — a pre-commit hook, an unset git identity — and re-run the same 'open': the refusal will be recorded then."
  else pub_rollback   # the opening record may already have landed; leaving it uncommitted is the
                      # very thing task 31.1's invariant forbids, so the transaction is reversed here too
    say "REFUSAL-NOT-RECORDED — the refusal $code could not be written to consult_notes.md (see the grammar message above), so the log has been left exactly as it was. This is a defect in the skill, not in the project: report it through /syndicate-consult-loop."; fi
  [ -d "$CL" ] && "$POSTURE" destroy "$CL" >/dev/null; rm -rf "$ST"; exit 3
}
# ---- the publication transaction (task 31.1) ----------------------------------------------------
# publish_log's return code used to be discarded at BOTH call sites, so a commit that failed left an
# uncommitted closing or refusal record sitting in the worktree while the runner destroyed the state
# dir and the clone and reported success. That record could then never be published (its cycle's
# state was gone), and it made the checkout dirty, so the project's NEXT cycle refused DIRTY-CHECKOUT.
#
# So publication is a transaction with a rollback. Two things must be snapshotted, and each is easy
# to miss for its own reason:
#   the LOG   — consult-posture.sh takes its own log.before PER APPEND, which cannot cover a refusal:
#               a refusal appends TWICE (opening, then closing), so by the time publication fails,
#               log.before describes the state after the FIRST append, not before the transaction.
#   the INDEX — `git add consult_notes.md` runs before the failing commit, so restoring the worktree
#               file alone would leave the record staged and the checkout dirty anyway.
# 0 = a trustworthy pre-publication snapshot exists · 1 = it does NOT, so NOTHING may be published:
# publishing without a snapshot means a failed commit could not be rolled back, which is the whole
# guarantee. Every write is checked — the first draft assumed they could not fail and would arm
# `pub.begun` regardless (found by the reviewer, cycle 20260825-170103-b72153b).
pub_begin(){   # idempotent: refuse() calls it once and appends twice
  [ -f "$ST/pub.begun" ] && return 0
  mkdir -p "$ST" || { say "cannot create the state dir $ST"; return 1; }
  if [ -f "$LOG" ]; then
    cp --remove-destination "$LOG" "$ST/pub.log.before" || { say "cannot snapshot $LOG to $ST/pub.log.before"; return 1; }
    printf 'present' > "$ST/pub.log.state" || { say "cannot write $ST/pub.log.state"; return 1; }
  else
    rm -f "$ST/pub.log.before"
    printf 'absent' > "$ST/pub.log.state" || { say "cannot write $ST/pub.log.state"; return 1; }
  fi
  # an untracked log yields NO index entry, which is exactly the "remove it from the index" case
  if ! git -C "$REAL" ls-files --stage -- consult_notes.md > "$ST/pub.index.before" 2>/dev/null; then
    : > "$ST/pub.index.before" || { say "cannot write $ST/pub.index.before"; return 1; }
  fi
  printf '1' > "$ST/pub.begun" || { say "cannot write $ST/pub.begun"; return 1; }
}
pub_abort(){   # $1 = what was about to be written
  say "PUBLICATION-ABORTED — the pre-publication snapshot could not be taken (see above), so $1 was NOT written to consult_notes.md. Without that snapshot a failed commit could not be rolled back, and publishing anyway is exactly the guarantee this transaction exists to give. Free space or fix permissions under $WORK, then re-run."
  exit 2
}
pub_end(){ rm -f "$ST/pub.begun" "$ST/pub.log.state" "$ST/pub.log.before" "$ST/pub.index.before"; }
# Returns 0 when the pre-publication state is verifiably back, 2 when it is NOT — and in that case
# the snapshot is KEPT. The first draft of this function checked nothing, printed ROLLBACK-INCOMPLETE
# as a message rather than a state, and then called pub_end, which unlinks pub.log.before: the only
# surviving copy of the pre-publication bytes, deleted at the moment it is needed. A full disk — the
# commit-failure case the design record itself names — is exactly what makes the restoring `cp` fail.
# Found by the reviewer in cycle 20260825-164306-1335b9f: the same success-while-doing-nothing shape
# that task 31.1 exists to remove, one level down, introduced by the fix for it.
pub_rollback(){
  local bad=""
  if [ "$(cat "$ST/pub.log.state" 2>/dev/null)" = present ]; then
    cp --remove-destination "$ST/pub.log.before" "$LOG" || bad="restoring the log failed"
  else rm -f "$LOG" || bad="removing the log failed"; fi
  if [ -s "$ST/pub.index.before" ]; then
    local mode obj stage path
    read -r mode obj stage path < "$ST/pub.index.before"   # "<mode> <sha> <stage>\t<path>"
    git -C "$REAL" update-index --cacheinfo "$mode,$obj,consult_notes.md" 2>/dev/null || bad="${bad:+$bad; }restoring the index entry failed"
    git -C "$REAL" update-index -q --refresh -- consult_notes.md 2>/dev/null || :   # stat-only; reports "modified" harmlessly
  else
    git -C "$REAL" update-index --force-remove -- consult_notes.md 2>/dev/null || bad="${bad:+$bad; }removing the index entry failed"
  fi
  # the two things that must be true, CHECKED and not assumed
  git -C "$REAL" diff --cached --quiet -- consult_notes.md 2>/dev/null || bad="${bad:+$bad; }consult_notes.md is still STAGED"
  if [ "$(cat "$ST/pub.log.state" 2>/dev/null)" = present ] && ! cmp -s "$ST/pub.log.before" "$LOG" 2>/dev/null; then
    bad="${bad:+$bad; }consult_notes.md does not match its pre-publication bytes"
  fi
  if [ -n "$bad" ]; then
    # Name only the remedy that EXISTS. When the thing that failed is the snapshot itself, telling
    # the operator to copy from it is worse than saying nothing — the log's last good bytes are then
    # in git, not in the state dir.
    local remedy
    if [ -f "$ST/pub.log.before" ]; then
      remedy="cp $ST/pub.log.before $LOG"
    elif [ -f "$ST/log.before" ]; then
      remedy="the publication snapshot is gone (that copy is what failed). $ST/log.before holds the log as it stood before the LAST append, which is the right content after a close and one record short after a refusal:  cp $ST/log.before $LOG  — check it before trusting it"
    else
      remedy="neither snapshot survives, so the pre-publication bytes are not recoverable from the state dir. If consult_notes.md is committed, 'git -C $REAL restore --source=HEAD -- consult_notes.md' returns the last PUBLISHED log and loses only this cycle's unpublished records; if it is not, this cycle created the file and removing it is the clean state"
    fi
    say "ROLLBACK-INCOMPLETE — $bad. Whatever snapshot survives is KEPT, not deleted ($ST). Finish it by hand:  $remedy  && git -C $REAL restore --staged consult_notes.md  — and do not open another cycle in this project until 'git status' is clean."
    return 2
  fi
  # only now: the skill reversed its OWN write, so the step-4 baseline may describe the tree as it is.
  # Its failure is a ROLLBACK failure — refreshing is part of restoring the pre-publication state, and
  # ignoring it here would delete the snapshot (pub_end) on a rollback that did not finish. Found by
  # the recheck of cycle 20260825-164306-1335b9f, in the fix for the defect it had just named.
  if [ -f "$ST/real.fp" ] && ! "$POSTURE" refresh "$REAL" "$ST" >/dev/null 2>&1; then
    say "ROLLBACK-INCOMPLETE — the log and its index entry were restored, but the posture baseline could not be refreshed, so the next append would refuse on drift the skill itself caused. The snapshot is KEPT ($ST). Finish it by hand:  bash $POSTURE refresh $REAL $ST"
    return 2
  fi
  pub_end
}

# One place decides what happened, so the two messages can never both be printed. The callers used to
# announce "rolled back, nothing uncommitted is left behind" unconditionally — including after
# pub_rollback had just reported that it could NOT restore. Recheck finding, same cycle.
publish_or_rollback(){   # $1 = commit message · $2 = what to tell the operator on a COMPLETE rollback
  publish_log "$1" && { pub_end; return 0; }
  if pub_rollback; then say "PUBLICATION-FAILED — $2"
  else say "PUBLICATION-FAILED, and the ROLLBACK DID NOT COMPLETE — see the ROLLBACK-INCOMPLETE line above. Records from this cycle may still be sitting in consult_notes.md or staged in the index; this checkout needs the hand-fix named there before any further cycle in this project."; fi
  exit 2
}
publish_log(){  # scoped commit of the log alone, FF push; failure is recorded, not hidden
  ( cd "$REAL" && git add consult_notes.md && git -c commit.gpgsign=false commit -q -m "$1" -- consult_notes.md ) || { say "log commit failed"; return 1; }
  git -C "$REAL" remote get-url origin >/dev/null 2>&1 || { say "log committed (no origin)"; return 0; }
  git -C "$REAL" push -q origin HEAD 2>/dev/null && { say "log committed + pushed"; return 0; }
  # A failed push is ambiguous (the commit may have landed) — never amend; add the marker as its OWN
  # commit and retry the push once. A failed push is NOT rolled back: the commit landed, so the record
  # exists and rolling back would delete it.
  #
  # The commit above changed .git, so the step-4 baseline no longer describes the tree and `append`
  # would REFUSE with "real tree drifted since verify" before the marker could be written — the whole
  # marker path was dead, and no fixture could see it because every fixture has no origin. Found by
  # the reviewer, cycle 20260825-170103-b72153b. Re-baseline first: the skill made that change itself.
  say "LOG-COMMITTED-NOT-PUSHED"
  if [ -f "$ST/real.fp" ] && ! "$POSTURE" refresh "$REAL" "$ST" >/dev/null 2>&1; then
    say "MARKER-NOT-RECORDED — the log is committed but NOT pushed, and the posture baseline could not be refreshed, so the marker could not be appended. Push by hand: git -C $REAL push origin HEAD"; return 0; fi
  echo "- publication: LOG-COMMITTED-NOT-PUSHED $(date -u +%FT%TZ)" > "$SCR/marker.md"
  ( append "$SCR/marker.md" ) || { say "MARKER-NOT-RECORDED — the log is committed but NOT pushed, and the marker itself could not be appended (see the grammar or posture message above). Push by hand: git -C $REAL push origin HEAD"; return 0; }
  ( cd "$REAL" && git add consult_notes.md && git -c commit.gpgsign=false commit -q -m "consult: publication failed — marker" -- consult_notes.md ) \
    || { say "MARKER-NOT-COMMITTED — the marker was appended to consult_notes.md but its own commit failed, so the checkout is left MODIFIED and the next cycle here will refuse DIRTY-CHECKOUT. Commit it by hand: git -C $REAL commit -m 'consult: publication failed — marker' -- consult_notes.md"; return 0; }
  git -C "$REAL" push -q origin HEAD 2>/dev/null && say "marker pushed on retry" || say "marker committed locally; will travel with the next push"
  return 0
}

case "${1:-}" in
# =====================================================================================
open)
  T="${2:-}"; rm -rf "$ST"; mkdir -p "$ST"; put target "$T"
  put cycle "$(date -u +%Y%m%d-%H%M%S)-$(git -C "$REAL" rev-parse HEAD | cut -c1-7)"   # NOT --short: git widens it past 7 in a big repo (measured: 8 in app-brm-manufacturing-products) and the grammar is exact
  [ -n "$T" ] || refuse NO-TARGET "task:<id> | phase:<key> | file:<paths> | commit:<range>"
  command -v codex >/dev/null || refuse NO-CODEX "not on PATH (non-interactive ssh? bash -lc)"
  if ! codex login status 2>&1 | grep -q 'Logged in'; then
    # A config Codex cannot LOAD makes every codex command fail, this one included — and
    # NOT-LOGGED-IN would send the operator to re-authenticate, which cannot possibly help.
    # Measured 2026-08-25 while testing the predicate: a key written directly under [projects]
    # gives "invalid type: integer `1024`, expected struct ProjectConfig" and codex refuses to
    # start at all. So ask the config first, and only say NOT-LOGGED-IN when the config is fine.
    CFGMSG="$(bash "$SK/prepare-host.sh" --check-config 2>&1)" \
      || refuse HOST-NOT-PREPARED "$CFGMSG — and codex itself could not start, which this explains: a config Codex cannot load fails every codex command. Fix the config, not the login: bash .claude/skills/consult-codex/prepare-host.sh --apply"
    refuse NOT-LOGGED-IN
  fi
  # the host-config predicate has ONE definition, in prepare-host.sh; this calls it and quotes it.
  CFGMSG="$(bash "$SK/prepare-host.sh" --check-config 2>&1)" || refuse HOST-NOT-PREPARED "$CFGMSG — run: bash .claude/skills/consult-codex/prepare-host.sh --apply (once per machine)"
  ENTRY="${CODEX_HOME:-$HOME/.codex}/skills/syndicate-consult-claude/SKILL.md"
  [ -f "$ENTRY" ] || refuse HOST-NOT-PREPARED "host entry $ENTRY absent — run prepare-host.sh --apply"
  grep -q "Expected procedure digest: \`$(procedure_digest)\`" "$ENTRY" || refuse PROCEDURE-DRIFT "host entry carries $(sed -n 's/.*Expected procedure digest: `\([0-9a-f]*\)`.*/\1/p' "$ENTRY" | head -1), this project's procedure is $(procedure_digest) — re-run prepare-host.sh --apply or /distribute-defaults"
  [ -d "$HOME/.claude/skills/consult-codex" ] && refuse SHADOWED "~/.claude/skills/consult-codex/ would shadow the distributed skill"
  [ -z "$(git -C "$REAL" status --porcelain)" ] || refuse DIRTY-CHECKOUT "commit or stash first — a clone of HEAD would review stale state"
  if git -C "$REAL" remote get-url origin >/dev/null 2>&1; then
    git -C "$REAL" fetch -q origin 2>/dev/null || refuse NOT-ORIGIN-LATEST "origin unreachable"
    UP="$(git -C "$REAL" rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null)" || refuse NOT-ORIGIN-LATEST "no upstream"
    BEHIND=$(git -C "$REAL" rev-list --count HEAD.."$UP"); AHEAD=$(git -C "$REAL" rev-list --count "$UP"..HEAD)
    if [ "$BEHIND" -gt 0 ] && [ "$AHEAD" -gt 0 ]; then refuse NOT-ORIGIN-LATEST "diverged: $AHEAD ahead, $BEHIND behind"; fi
    [ "$BEHIND" -gt 0 ] && { git -C "$REAL" merge -q --ff-only "$UP" || refuse NOT-ORIGIN-LATEST "cannot fast-forward"; say "fast-forwarded $BEHIND"; }
    put sync "origin-latest"
  else put sync "local-only (no origin)"; fi
  python3 "$REAL/.claude/skills/progress-check/progress_check.py" --file "$REAL/progress.json" --quiet >/dev/null 2>&1 || refuse NOT-REVIEWABLE:progress-json
  [ -d "$REAL/.claude/commands" ] && [ -d "$REAL/.claude/skills" ] || refuse NOT-REVIEWABLE:no-claude-dir
  { [ -e "$REAL/.codex" ] || [ -e "$REAL/.agents/skills" ]; } && refuse NOT-REVIEWABLE:codex-roots-present
  # AWS binding — by command, via codex-here's own rules; 3 = refusal, else aws or no-infra
  B="$("$HERE" --project "$REAL" --dry-run exec x 2>&1 >/dev/null)"; rc=$?
  # Every other refusal code is a literal; this one is EXTRACTED, and it lands in `not-reviewed:<CODE>`,
  # which the grammar requires to be non-empty and upper-case. An extraction that matched nothing would
  # produce `not-reviewed:` — a record the log refuses — making the refusal itself unrecordable.
  [ $rc -eq 3 ] && { CODE="$(sed -n 's/codex-here: \([A-Z][A-Z0-9-]*\).*/\1/p' <<<"$B" | head -1)"; refuse "${CODE:-BINDING-REFUSED}" "$B"; }
  MODE="$(sed -n 's/.*mode=\([^ ]*\).*/\1/p' <<<"$B")"; put mode "$MODE"; put bind "$B"
  # claims from the target
  python3 - "$REAL" "$T" > "$ST/claims" 2> "$ST/claims.note" <<'PY' || refuse NOT-REVIEWABLE "target unreadable: $(tail -1 "$ST/claims.note" 2>/dev/null)"
import json,subprocess,sys,os,re
real,t=sys.argv[1:3]; kind,_,val=t.partition(':'); out=[]
if kind in('task','phase'):
    d=json.load(open(os.path.join(real,'progress.json')))
    raw=d.get('phases') or {}
    phases=list(raw.items()) if isinstance(raw,dict) else [(str(p.get('key') or p.get('id') or i),p) for i,p in enumerate(raw) if isinstance(p,dict)]
    def tasks(ph): return [tk for tk in (ph.get('tasks') or []) if isinstance(tk,dict)]
    def add(tk): out.append(f"{tk.get('id')}: {tk.get('name','')} — verify: {tk.get('verify','(none)')}")
    # 1. exact task id
    if kind=='task':
        for pk,ph in phases:
            for tk in tasks(ph):
                if str(tk.get('id'))==val: add(tk)
    # 2. a phase, by key OR by bare number — "task 132" / "phase 132" both mean phase_132_* when no task "132" exists
    if not out:
        for pk,ph in phases:
            if pk==val or re.match(r'^phase_'+re.escape(val)+r'(_|$)',pk) or (kind=='phase' and pk.endswith('_'+val)):
                for tk in tasks(ph): add(tk)
                if out: print(f"# resolved {t} -> phase {pk} ({len(out)} tasks)",file=sys.stderr)
    # 3. nothing — name the near misses so the operator can correct the target instead of guessing
    if not out:
        near=[str(tk.get('id')) for pk,ph in phases for tk in tasks(ph) if str(tk.get('id')).startswith(val)][:8]
        nearp=[pk for pk,ph in phases if val in pk][:4]
        hint=(" — did you mean " + ", ".join([f"task:{n}" for n in near]+[f"phase:{p}" for p in nearp]) if (near or nearp) else "")
        print(f"# no task or phase matches {t}{hint}",file=sys.stderr)
elif kind=='file':
    for f in val.split(','):
        if os.path.exists(os.path.join(real,f)) or os.path.isabs(f): out.append(f"{f}: the content and claims of this file")
elif kind=='commit':
    for f in subprocess.run(['git','-C',real,'diff','--name-only',val],capture_output=True,text=True).stdout.split():
        out.append(f"{f}: as changed in {val}")
print("\n".join(out))
PY
  [ -s "$ST/claims.note" ] && say "$(sed 's/^# //' "$ST/claims.note")"
  [ "$(grep -c . "$ST/claims")" -gt 0 ] || refuse NOT-REVIEWABLE:NO-REVIEWABLE-CLAIMS "target '$T' yields no claims$(sed -n 's/^# no task or phase matches [^ ]*//p' "$ST/claims.note" | head -1)"   # -s is fooled by a lone newline; the note names the near misses
  # clone + baseline
  rm -rf "$CL"; "$POSTURE" clone "$REAL" "$CL" >/dev/null || refuse CLONE-FAILED
  put sha "$(git -C "$CL" rev-parse HEAD)"; "$POSTURE" snapshot "$REAL" "$CL" "$ST" >/dev/null
  # identity, in aws mode: the reviewer's own server must answer with the declared account
  DECL="$(sed -n 's/.*declared=\([0-9-]*\).*/\1/p' <<<"$B")"; put declared "$DECL"; put identity "n/a"
  if [ "$MODE" = "aws-read-only" ]; then
    SRV="$(sed -n 's/.*server=\([^ ]*\).*/\1/p' <<<"$B")"
    ( cd "$CL" && timeout 240 "$HERE" --bind-from "$REAL" exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -o "$SCR/id.md" \
        "Call the MCP tool call_aws from the $SRV server with: aws sts get-caller-identity. Reply with the 12-digit Account only. Do not read files." >"$SCR/id.log" 2>&1 </dev/null )
    ACC="$(grep -oE '[0-9]{12}' "$SCR/id.md" 2>/dev/null | head -1)"; put identity "${ACC:-none}"
    "$POSTURE" verify "$REAL" "$CL" "$ST" >/dev/null || refuse POSTURE-BREACH "during identity check"
    [ -n "$ACC" ] && [ "$ACC" = "$DECL" ] || refuse ACCOUNT-MISMATCH "server answered '${ACC:-none}', declared '$DECL'"
  fi
  put round 0; put opened 1
  { printf '## cycle %s — %s\n\n**Opening record**\n' "$(st cycle)" "$T"
    printf -- '- entry: B (nested) · procedure digest: %s · reviewer: %s · mode: %s\n' "$(procedure_digest)" "$(codex --version 2>&1)" "$MODE"
    printf -- '- checkout: %s · opening SHA: %s · clone: %s (no remotes, guard re-armed)\n' "$(st sync)" "$(st sha)" "$CL"
    printf -- '- binding: %s\n- identity: %s (declared %s)\n- claims (%s):\n' "$B" "$(st identity)" "${DECL:--}" "$(grep -c . "$ST/claims")"
    sed 's/^/  - /' "$ST/claims"; } > "$SCR/open.md"
  append "$SCR/open.md"; say "opened cycle $(st cycle) · mode $MODE · $(grep -c . "$ST/claims") claim(s) · clone $CL"; echo "$(st cycle)";;
# =====================================================================================
review)
  [ -f "$ST/opened" ] || { say "no open cycle"; exit 1; }
  R=$(( $(st round) + 1 )); [ $R -le $CAP ] || { say "round cap $CAP reached — close the cycle"; exit 4; }
  if [ $R -eq 1 ]; then
    AWS_LINE=""; [ "$(st mode)" = "aws-read-only" ] && AWS_LINE="AWS: read-only MCP server $(sed -n 's/.*server=\([^ ]*\).*/\1/p' "$ST/bind"), account $(st identity) — use it to check claims against live state."
    NOTE="You have no AWS access in this session; say so once if it limits you, and never fake a check you could not run."
    [ "$(st mode)" = "aws-read-only" ] && NOTE="Every claim you mark examined must name the evidence — a file:line or the live call you made."
    python3 - "$SK/reviewer-prompt.md" "$(st cycle)" "$(st target)" "$(st mode)" "$AWS_LINE" "$ST/claims" "$NOTE" > "$SCR/r1.prompt" <<'PY'
import sys
tpl,cycle,target,mode,aws,claims,note=sys.argv[1:8]
s=open(tpl).read()
for k,v in {"CYCLE":cycle,"TARGET":target,"MODE":mode,"AWS_LINE":aws,"CLAIMS":open(claims).read().rstrip(),"MODE_NOTE":note}.items(): s=s.replace("{{"+k+"}}",v)
print(s)
PY
    P="$SCR/r1.prompt"; RESUME=()
  else P="$SCR/r$R.prompt"; [ -s "$P" ] || { say "no author response staged for round $R — use respond"; exit 1; }; RESUME=(resume "$(st thread)"); fi
  say "reviewer round $R…"
  ( cd "$CL" && timeout 900 "$HERE" --bind-from "$REAL" exec "${RESUME[@]}" --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -o "$SCR/r$R.out" "$(cat "$P")" >"$SCR/r$R.log" 2>&1 </dev/null ); RC=$?
  [ $R -eq 1 ] && put thread "$(grep -m1 -oE 'session id: [0-9a-f-]+' "$SCR/r$R.log" | awk '{print $3}')"
  TOK="$(grep -A1 '^tokens used' "$SCR/r$R.log" | tail -1)"
  if ! "$POSTURE" verify "$REAL" "$CL" "$ST" > "$SCR/r$R.posture" 2>&1; then POST="**POSTURE BREACH** — $(tr '\n' ' ' < "$SCR/r$R.posture" | cut -c1-300)"; put breach "round $R"; else POST="clean"; fi
  # a reviewer that crashed, timed out, or said nothing is a FAILED round, not a quiet one
  if [ $RC -ne 0 ] || [ ! -s "$SCR/r$R.out" ]; then put failed "round $R: rc $RC, $(wc -c < "$SCR/r$R.out" 2>/dev/null || echo 0) bytes"; STATUS="**REVIEWER FAILED** (rc $RC)"; else STATUS="ok"; put reviewed "$R"; fi   # `reviewed` is what every agreed-* outcome will require
  LEDGER="n/a"
  if [ $R -eq 1 ]; then sed -n '/^LEDGER:/,/^END-LEDGER/p' "$SCR/r1.out" > "$ST/ledger"
    LEDGER="$(python3 "$SK/consult-log.py" ledger "$ST/claims" "$ST/ledger")"; put ledger_counts "$LEDGER"
    grep -q 'error=' <<<"$LEDGER" && { put ledger_invalid 1; LEDGER="**LEDGER INVALID** $LEDGER"; }; fi
  { printf '### Round %s — reviewer (Codex, %s)\n\nstatus: %s · tokens %s · posture: %s · ledger: %s\n\n' "$R" "$(codex --version 2>&1 | awk '{print $2}')" "$STATUS" "${TOK:-?}" "$POST" "$LEDGER"; cat "$SCR/r$R.out" 2>/dev/null || echo "(no output)"; } > "$SCR/r$R.rec"
  append "$SCR/r$R.rec"; put round "$R"
  [ "$POST" = clean ] || say "posture breach recorded as a finding against the reviewer"
  [ "$STATUS" = ok ] || say "reviewer failed — only not-reviewed:REVIEWER-FAILED or disputed can close this cycle"
  say "round $R appended (rc $RC, posture $POST). Read the log, write your response, then: consult.sh respond <file>";;
# =====================================================================================
respond)
  [ -f "$ST/opened" ] || { say "no open cycle"; exit 1; }
  A="${2:?author response file}"; R=$(st round); N=$((R+1))
  { printf '### Author — round %s (Claude)\n\n' "$R"; cat "$A"; } > "$SCR/a$R.rec"; append "$SCR/a$R.rec"
  [ $N -le $CAP ] || { say "author response appended; cap reached — close the cycle"; exit 0; }
  cp "$A" "$SCR/r$N.prompt"; exec "$0" review;;
# =====================================================================================
close)
  [ -f "$ST/opened" ] || { say "no open cycle"; exit 1; }
  O="${2:?outcome}"; SHA="${3:-}"
  # ONE definition of a valid outcome, and it is the log grammar's (task 31.3). The shell `case`
  # that stood here accepted any not-reviewed:<anything> — including a lower-case suffix the grammar
  # refuses — so a typo passed the runner, ran the recheck (a full Codex round for agreed-applied),
  # and was rejected only by the validator at append time, after the cost had been paid.
  python3 "$SK/consult-log.py" check-outcome "$O" || exit 1
  LC="$(st ledger_counts)"; EX=$(sed -n 's/.*examined=\([0-9]*\).*/\1/p' <<<"$LC"); UN=$(sed -n 's/.*unavailable=\([0-9]*\).*/\1/p' <<<"$LC"); SKP=$(sed -n 's/.*skipped=\([0-9]*\).*/\1/p' <<<"$LC"); EX=${EX:-0}; UN=${UN:-0}; SKP=${SKP:-0}
  # no completed reviewer round at all forbids every "agreed" outcome — a cycle cannot agree with nobody
  if [ ! -f "$ST/reviewed" ]; then case "$O" in agreed-*) say "no successful reviewer round — recording not-reviewed:NO-REVIEW instead of $O"; O="not-reviewed:NO-REVIEW";; esac; fi
  # a failed reviewer round forbids every "agreed" outcome — the reviewer never got to agree
  if [ -f "$ST/failed" ]; then case "$O" in agreed-*) say "reviewer failed ($(st failed)) — recording not-reviewed:REVIEWER-FAILED instead of $O"; O="not-reviewed:REVIEWER-FAILED";; esac; fi
  # a reviewer that mutated either tree, or a ledger that does not cover the claims, forbids every "agreed" outcome too
  if [ -f "$ST/breach" ]; then case "$O" in agreed-*) say "posture breach in $(st breach) — recording not-reviewed:POSTURE-BREACH instead of $O"; O="not-reviewed:POSTURE-BREACH";; esac; fi
  if [ -f "$ST/ledger_invalid" ]; then case "$O" in agreed-*) say "ledger invalid ($LC) — recording not-reviewed:LEDGER-INVALID instead of $O"; O="not-reviewed:LEDGER-INVALID";; esac; fi
  if [ "$O" = agreed-nothing ] && { [ -f "$ST/ledger_invalid" ] || [ "$EX" -eq 0 ] || { [ "$(st mode)" = aws-read-only ] && [ "$(st identity)" != "$(st declared)" ]; }; }; then say "agreed-nothing needs a valid ledger with examined>0 and a matched identity — recording not-reviewed:NO-PROOF instead"; O="not-reviewed:NO-PROOF"; fi
  RECHECK="not run"
  if [ "$O" = agreed-applied ]; then
    [ -n "$SHA" ] || { say "agreed-applied needs the result SHA"; exit 1; }
    git -C "$REAL" cat-file -e "$SHA^{commit}" 2>/dev/null || { say "result SHA $SHA not in $REAL"; exit 1; }
    "$POSTURE" destroy "$CL" >/dev/null; "$POSTURE" clone "$REAL" "$CL" >/dev/null; git -C "$CL" checkout -q "$SHA"
    "$POSTURE" snapshot "$REAL" "$CL" "$ST" >/dev/null
    ( cd "$CL" && timeout 600 "$HERE" --bind-from "$REAL" exec resume "$(st thread)" --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -o "$SCR/recheck.out" \
      "The agreed changes were applied. You are now in a fresh clone at commit $SHA. Re-read progress.json and the changed files; state the commit SHA you are looking at (git rev-parse HEAD), and confirm in one paragraph whether the applied state matches what was agreed, naming any gap. End with exactly one line: RECHECK: confirmed  or  RECHECK: gap — <what>" >"$SCR/recheck.log" 2>&1 </dev/null ); RRC=$?
    "$POSTURE" verify "$REAL" "$CL" "$ST" >/dev/null && PV=clean || PV=BREACH
    # agreed-applied is EARNED by the recheck, not assumed: any of these downgrades the outcome to disputed
    if [ $RRC -ne 0 ] || [ ! -s "$SCR/recheck.out" ]; then O=disputed; RECHECK="recheck reviewer failed (rc $RRC) — downgraded to disputed"
    elif [ "$PV" != clean ]; then O=disputed; RECHECK="posture breach during recheck — downgraded to disputed"
    elif ! grep -q "$(git -C "$CL" rev-parse --short "$SHA")" "$SCR/recheck.out"; then O=disputed; RECHECK="reviewer did not name SHA $SHA — downgraded to disputed"
    elif [ "$(grep -c '^RECHECK:' "$SCR/recheck.out")" -ne 1 ]; then O=disputed; RECHECK="reviewer gave $(grep -c '^RECHECK:' "$SCR/recheck.out") RECHECK lines, not one — downgraded to disputed"
    elif ! grep -qE '^RECHECK: confirmed[[:space:]]*$' "$SCR/recheck.out"; then O=disputed; RECHECK="reviewer reported a gap at $SHA — downgraded to disputed"
    else RECHECK="confirmed at $SHA (posture clean)"; fi
    [ "$O" = disputed ] && say "$RECHECK"
  fi
  # the AUTHOR may have committed since the last reviewer round (that is the executor step); re-baseline the real tree
  # explicitly here so the closing append is measured against the tree as it is now, not as the reviewer last saw it.
  # The reviewer's posture was already judged after each round; this is the skill's own write.
  AUTHOR_COMMITS=$(git -C "$REAL" rev-list --count "$(st sha)"..HEAD 2>/dev/null || echo 0)
  [ -d "$CL/.git" ] && "$POSTURE" snapshot "$REAL" "$CL" "$ST" >/dev/null || { "$POSTURE" clone "$REAL" "$CL" >/dev/null; "$POSTURE" snapshot "$REAL" "$CL" "$ST" >/dev/null; }
  { printf '**Closing record**\n- outcome: `%s`\n- opening SHA: %s · reviewed SHA: %s · result SHA: %s · author commits since opening: %s\n' "$O" "$(st sha)" "$(git -C "$CL" rev-parse HEAD 2>/dev/null || st sha)" "${SHA:--}" "$AUTHOR_COMMITS"
    printf -- '- procedure digest: %s · rounds: %s of %s · mode: %s · identity: %s\n- claims: examined %s · unavailable %s · skipped %s\n- recheck: %s\n- nothing written to progress.json by this cycle\n' "$(procedure_digest)" "$(st round)" "$CAP" "$(st mode)" "$(st identity)" "$EX" "$UN" "$SKP" "$RECHECK"
    [ "$O" = agreed-applied ] && [ -s "$SCR/recheck.out" ] && { printf '\n> '; tr '\n' ' ' < "$SCR/recheck.out" | cut -c1-600; printf '\n'; }; } > "$SCR/close.md"
  pub_begin || pub_abort "the closing record"
  append "$SCR/close.md"
  publish_or_rollback "consult: close cycle $(st cycle) — $O" "the closing record could not be COMMITTED, so it has been rolled back out of consult_notes.md and out of the index. THE CYCLE IS STILL OPEN: its state dir and its clone are kept, and nothing uncommitted is left in the checkout. Fix the commit failure — a pre-commit hook, an unset git identity — and re-run the same close command."
  "$POSTURE" destroy "$CL" >/dev/null; rm -rf "$ST"; say "closed $O";;
# =====================================================================================
status) for k in cycle target mode sync sha identity declared round thread; do printf '%-9s %s\n' "$k" "$(st $k)"; done; [ -f "$ST/claims" ] && echo "claims    $(grep -c . "$ST/claims")";;
*) sed -n '2,16p' "$0"; exit 1;;
esac
