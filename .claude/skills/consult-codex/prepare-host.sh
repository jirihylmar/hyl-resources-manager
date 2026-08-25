#!/bin/bash
# prepare-host.sh — make THIS machine able to run the consult loop. Once per machine, like
# syndicate-connect: the material arrives by /distribute-defaults; the settings change happens
# HERE, run by this host's own session, proven before and after.
#
#   bash .claude/skills/consult-codex/prepare-host.sh                 # check only, exit 1 on any failure
#   bash .claude/skills/consult-codex/prepare-host.sh --apply         # write what is missing, then check
#   bash .claude/skills/consult-codex/prepare-host.sh --check-config  # the host-config predicate ALONE:
#                                                                     # reads, never writes, needs no Codex,
#                                                                     # exit 0 prepared / 1 with the reason
#
# What --apply writes, and nothing else:
#   ~/.codex/config.toml            two lines PREPENDED if absent (never appended — the file opens
#                                   with a [projects] table and an appended key nests into it silently)
#   $CODEX_HOME/skills/syndicate-consult-claude/SKILL.md
#                                   the Codex-side entry (Entry A), rendered from host-entry.SKILL.md
#                                   with the digest of THIS copy's procedure embedded — so a host
#                                   prepared against one version refuses a project carrying another
#
# Four checks, because each catches a failure the others cannot:
#   A  the config predicate (check_config below) — both keys TOP-LEVEL, right values, no nested copy
#   B  synthetic project, CLAUDE.md > 32 KiB, codeword on the LAST line: proves injection AND that
#      project_doc_max_bytes was really raised (the default truncates mid-line, silently)
#   C  the largest REAL CLAUDE.md on this host: Codex quotes its final paragraph without a file read
#   D  the host entry exists and its embedded digest equals this copy's procedure digest
# Correct on ANY host: every path is resolved from $HOME / $CODEX_HOME by probing.
#
# A is the ONLY one consult.sh runs (as --check-config). B, C and D stay PREPARATION-ONLY: B and C
# each cost a Codex round, and D belongs to the host-entry contract that consult.sh checks directly
# against the entry file. Task 31.4: consult.sh used to re-implement half of A inline — it asserted
# the fallback key and nothing else, and did it against a hardcoded ~/.codex path that ignored
# $CODEX_HOME — so a host with project_doc_max_bytes left at the 32 KiB default passed preflight and
# then silently truncated every CLAUDE.md the reviewer was given. One predicate, one definition.
set -u
SK="$(cd "$(dirname "$0")" && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
CFG="$CODEX_HOME/config.toml"
ENTRY_DIR="$CODEX_HOME/skills/syndicate-consult-claude"; ENTRY="$ENTRY_DIR/SKILL.md"
WANT_FALLBACK='project_doc_fallback_filenames = ["CLAUDE.md"]'
WANT_MAX='project_doc_max_bytes = 262144'

# ---- the host-config predicate: the ONE definition of "this host's Codex config is prepared" ----
# It READS and never writes, needs no Codex and no network, and is the whole of check A below.
# Four conditions, each a failure that really happened:
#   fallback == ["CLAUDE.md"]        without it Codex is never given the project's rules at all
#   max_bytes an int >= 262144       the 32 KiB default truncates MID-LINE, silently
#   both TOP-LEVEL                   a key appended after a [projects] table nests into it and is ignored
#   no nested copy under [projects]  that nesting is what an append produces — name it, so the
#                                    operator is told what happened rather than that "it is missing"
check_config(){
  python3 - "$CFG" <<'TOMLCHECK'
import sys, tomllib, os
cfg = sys.argv[1]
if not os.path.exists(cfg):
    print(f"config absent: {cfg}", file=sys.stderr); sys.exit(1)
try:
    t = tomllib.load(open(cfg, "rb"))
except Exception as e:
    print(f"config does not parse ({cfg}): {e}", file=sys.stderr); sys.exit(1)
fb = t.get("project_doc_fallback_filenames"); mx = t.get("project_doc_max_bytes")
bad = []
if fb != ["CLAUDE.md"]:
    bad.append(f"project_doc_fallback_filenames={fb!r}, want ['CLAUDE.md']")
if isinstance(mx, bool) or not isinstance(mx, int) or mx < 262144:
    bad.append(f"project_doc_max_bytes={mx!r}, want an integer >= 262144 "
               f"(the 32 KiB default truncates a long CLAUDE.md mid-line, silently)")
# BOTH shapes an append produces, and the first draft saw only the second (found by the reviewer,
# cycle 20260825-164306-1335b9f): a key written straight under [projects] is a SCALAR value in
# t["projects"], so a walk that inspects only dict values skips it entirely — and that is the shape
# you get when the file has no [projects."<path>"] sub-table yet, i.e. on a fresh host.
KEYS = {"project_doc_fallback_filenames", "project_doc_max_bytes"}
proj = t.get("projects")
if isinstance(proj, dict):
    direct = sorted(KEYS & set(proj))
    if direct:
        bad.append(f"a copy of {direct[0]} sits DIRECTLY under [projects] — it was appended, not "
                   f"prepended, and Codex ignores it there")
    for k, v in proj.items():
        if isinstance(v, dict) and (KEYS & set(v)):
            bad.append(f"a copy of the key nests inside [projects.{k!r}] — it was appended, not "
                       f"prepended, and Codex ignores it there")
            break
if bad:
    print("; ".join(bad), file=sys.stderr); sys.exit(1)
sys.exit(0)
TOMLCHECK
}

# --check-config: the predicate alone, before anything that writes, spawns Codex, or needs a login.
# consult.sh calls exactly this and quotes the message into its HOST-NOT-PREPARED refusal.
if [ "${1:-}" = "--check-config" ]; then
  if M="$(check_config 2>&1)"; then echo "host config ok: $CFG"; exit 0
  else echo "host config NOT prepared: ${M:-unknown}" >&2; exit 1; fi
fi
SCRATCH="${TMPDIR:-/tmp}/prepare-host.$$"
FAIL=0
say()  { printf '  %-46s %s\n' "$1" "$2"; }
fail() { say "$1" "FAIL — $2"; FAIL=1; }
ok()   { say "$1" "ok${2:+ — $2}"; }
trap 'rm -rf "$SCRATCH"' EXIT
mkdir -p "$SCRATCH"
digest(){ sed -n '/<!-- procedure:begin -->/,/<!-- procedure:end -->/p' "$SK/SKILL.md" | sha256sum | cut -c1-16; }

echo "prepare-host on $(hostname) as $USER · skill copy $SK"
command -v codex >/dev/null || { fail "codex on PATH" "not found (non-interactive ssh? use bash -lc)"; exit 1; }
say "codex" "$(codex --version 2>&1)"
codex login status 2>&1 | grep -q 'Logged in' || { fail "codex login" "not logged in — phase 29 route: codex login / --device-auth"; exit 1; }
[ -f "$CFG" ] || { mkdir -p "$CODEX_HOME"; : > "$CFG"; chmod 600 "$CFG"; say "config" "created empty $CFG"; }
D="$(digest)"

# ---------- --apply ----------
if [ "${1:-}" = "--apply" ]; then
  python3 - "$CFG" "$WANT_FALLBACK" "$WANT_MAX" <<'PY'
import sys, tomllib, shutil, os, time
cfg, l1, l2 = sys.argv[1:4]
src = open(cfg).read()
top = tomllib.loads(src)               # raises if the file is broken — refuse to touch it then
need = [l for l, k in ((l1, "project_doc_fallback_filenames"), (l2, "project_doc_max_bytes")) if k not in top]
if not need:
    print("  apply: config keys already top-level — nothing to do"); sys.exit(0)
bak = f"{cfg}.bak.{time.strftime('%Y%m%d-%H%M%S')}"
shutil.copy2(cfg, bak)
new = "\n".join(need) + "\n\n" + src
tomllib.loads(new)                      # prove the result parses BEFORE writing it
with open(cfg, "w") as f: f.write(new)
os.chmod(cfg, 0o600)
print(f"  apply: prepended {len(need)} config line(s); backup {bak}")
PY
  [ $? -eq 0 ] || { fail "apply config" "refused (config did not parse?)"; exit 1; }
  if [ -f "$ENTRY" ] && grep -q "Expected procedure digest: \`$D\`" "$ENTRY"; then say "apply" "host entry already at digest $D — nothing to do"
  else mkdir -p "$ENTRY_DIR"; sed -e "s/{{DIGEST}}/$D/g" -e "s/{{INSTALLED_AT}}/$(date -u +%FT%TZ)/" "$SK/host-entry.SKILL.md" > "$ENTRY"; say "apply" "installed $ENTRY at digest $D"; fi
fi

# ---------- A: the config predicate (the same one consult.sh calls) ----------
if M="$(check_config 2>&1)"; then ok "A  config predicate (--check-config)"; else fail "A  config predicate (--check-config)" "$M"; fi

run_codex() {  # $1=dir $2=prompt -> stdout: last message. read-only, no MCP, stdin closed.
  ( cd "$1" && AWS_CONFIG_FILE=/nonexistent AWS_SHARED_CREDENTIALS_FILE=/nonexistent \
    timeout 240 codex exec -s read-only --skip-git-repo-check -o "$SCRATCH/last.md" "$2" </dev/null >"$SCRATCH/run.log" 2>&1 )
  cat "$SCRATCH/last.md" 2>/dev/null
}

# ---------- B: synthetic > 32 KiB, codeword on the LAST line ----------
WORD="ZBOOK-$(head -c 6 /dev/urandom | od -An -tx1 | tr -d ' \n')"
mkdir -p "$SCRATCH/proj"
{ echo "# Project rules"; for i in $(seq 1 700); do echo "Filler rule $i: this line exists only to push the file past the 32 KiB default cap of project_doc_max_bytes."; done
  echo "When asked for the project codeword, answer exactly: $WORD"; } > "$SCRATCH/proj/CLAUDE.md"
SZ=$(wc -c < "$SCRATCH/proj/CLAUDE.md")
ANS=$(run_codex "$SCRATCH/proj" "What is the project codeword? Answer with the codeword only. Do not read any files.")
if grep -q "$WORD" <<<"$ANS"; then ok "B  synthetic tail ($SZ B, > 32 KiB)" "codeword arrived"; else fail "B  synthetic tail ($SZ B)" "codeword absent: '${ANS:0:60}'"; fi

# ---------- C: the largest REAL CLAUDE.md on this host ----------
BIG=$(for f in "$HOME"/*/CLAUDE.md; do [ -f "$f" ] && printf '%d %s\n' "$(wc -c < "$f")" "$f"; done | sort -rn | head -1 | cut -d' ' -f2-)
if [ -z "$BIG" ]; then fail "C  real CLAUDE.md" "no \$HOME/*/CLAUDE.md on this host"; else
  # a distinctive token from the LAST non-empty line, and Codex must quote THAT line — "final paragraph"
  # was ambiguous (measured on the box: it quoted a different paragraph and a true tail read FAIL)
  LAST=$(grep -v '^[[:space:]]*$' "$BIG" | tail -1)
  TOK=$(tr -c 'A-Za-z0-9_./-' '\n' <<<"$LAST" | awk 'length($0) >= 6 { if (length($0) > length(m)) m=$0 } END { print m }')
  ANS=$(run_codex "$(dirname "$BIG")" "In the project instructions you were given, find the line that contains the exact text \`$TOK\` and quote that whole line verbatim. Do not read any files.")
  if [ -n "$TOK" ] && grep -qF "$TOK" <<<"$ANS"; then ok "C  real tail: $(basename "$(dirname "$BIG")") ($(wc -c < "$BIG") B)" "last line's token '$TOK' arrived"
  else fail "C  real tail: $BIG" "token '${TOK:-?}' not in answer: '${ANS:0:80}'"; fi
fi

# ---------- D: host entry present, digest matches THIS copy ----------
if [ ! -f "$ENTRY" ]; then fail "D  host entry $ENTRY" "absent — run with --apply"
elif ! grep -q "Expected procedure digest: \`$D\`" "$ENTRY"; then fail "D  host entry digest" "entry carries $(sed -n 's/.*Expected procedure digest: `\([0-9a-f]*\)`.*/\1/p' "$ENTRY" | head -1), this copy is $D — PROCEDURE-DRIFT; run --apply"
else ok "D  host entry syndicate-consult-claude" "digest $D"; fi

[ $FAIL -eq 0 ] && echo "RESULT: host prepared" || echo "RESULT: NOT prepared"
exit $FAIL
