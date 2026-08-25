#!/bin/bash
# prepare-host.sh — make THIS machine able to run the consult loop. Once per machine, like
# syndicate-connect: the material arrives by /distribute-defaults; the settings change happens
# HERE, run by this host's own session, proven before and after.
#
#   bash .claude/skills/consult-codex/prepare-host.sh            # check only, exit 1 on any failure
#   bash .claude/skills/consult-codex/prepare-host.sh --apply    # write what is missing, then check
#
# What --apply writes, and nothing else:
#   ~/.codex/config.toml            two lines PREPENDED if absent (never appended — the file opens
#                                   with a [projects] table and an appended key nests into it silently)
#   $CODEX_HOME/skills/syndicate-consult-claude/SKILL.md
#                                   the Codex-side entry (Entry A), rendered from host-entry.SKILL.md
#                                   with the digest of THIS copy's procedure embedded — so a host
#                                   prepared against one version refuses a project carrying another
#
# Three behavioural checks, because each catches a failure the others cannot:
#   A  tomllib: both keys are TOP-LEVEL in the parsed file (not nested, not missing)
#   B  synthetic project, CLAUDE.md > 32 KiB, codeword on the LAST line: proves injection AND that
#      project_doc_max_bytes was really raised (the default truncates mid-line, silently)
#   C  the largest REAL CLAUDE.md on this host: Codex quotes its final paragraph without a file read
#   D  the host entry exists and its embedded digest equals this copy's procedure digest
# Correct on ANY host: every path is resolved from $HOME / $CODEX_HOME by probing.
set -u
SK="$(cd "$(dirname "$0")" && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
CFG="$CODEX_HOME/config.toml"
ENTRY_DIR="$CODEX_HOME/skills/syndicate-consult-claude"; ENTRY="$ENTRY_DIR/SKILL.md"
WANT_FALLBACK='project_doc_fallback_filenames = ["CLAUDE.md"]'
WANT_MAX='project_doc_max_bytes = 262144'
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

# ---------- A: top-level keys ----------
python3 - "$CFG" <<'PY' || FAIL=1
import sys, tomllib
t = tomllib.load(open(sys.argv[1], "rb"))
fb = t.get("project_doc_fallback_filenames"); mx = t.get("project_doc_max_bytes")
bad = []
if fb != ["CLAUDE.md"]: bad.append(f"project_doc_fallback_filenames={fb!r}")
if not isinstance(mx, int) or mx < 262144: bad.append(f"project_doc_max_bytes={mx!r}")
nested = [k for k, v in t.get("projects", {}).items() if isinstance(v, dict) and "project_doc_fallback_filenames" in v]
if nested: bad.append(f"key nested inside [projects.{nested[0]!r}] — appended, not prepended")
print("  %-46s %s" % ("A  keys top-level (tomllib)", "ok" if not bad else "FAIL — " + "; ".join(bad)))
sys.exit(1 if bad else 0)
PY

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
  TOK=$(tail -c 400 "$BIG" | tr -c 'A-Za-z0-9_./-' '\n' | grep -E '[/_.-]' | awk '{ if (length($0) > length(m)) m=$0 } END { print m }')
  ANS=$(run_codex "$(dirname "$BIG")" "Quote the final paragraph of the project instructions you were given, verbatim. Do not read any files.")
  if [ -n "$TOK" ] && grep -qF "$TOK" <<<"$ANS"; then ok "C  real tail: $(basename "$(dirname "$BIG")") ($(wc -c < "$BIG") B)" "token '$TOK' arrived"
  else fail "C  real tail: $BIG" "token '${TOK:-?}' not in answer: '${ANS:0:80}'"; fi
fi

# ---------- D: host entry present, digest matches THIS copy ----------
if [ ! -f "$ENTRY" ]; then fail "D  host entry $ENTRY" "absent — run with --apply"
elif ! grep -q "Expected procedure digest: \`$D\`" "$ENTRY"; then fail "D  host entry digest" "entry carries $(sed -n 's/.*Expected procedure digest: `\([0-9a-f]*\)`.*/\1/p' "$ENTRY" | head -1), this copy is $D — PROCEDURE-DRIFT; run --apply"
else ok "D  host entry syndicate-consult-claude" "digest $D"; fi

[ $FAIL -eq 0 ] && echo "RESULT: host prepared" || echo "RESULT: NOT prepared"
exit $FAIL
