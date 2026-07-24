#!/usr/bin/env bash
# connect.sh — give THIS machine a working route to the knowledge inbox, from two inputs: the
# ingest URL and a per-host token. One method for every host: deliver by HTTPS POST to the ingest
# endpoint (docs/knowledge-ingest-lambda-instruction.md). No ssh key, no box.json, no firewall.
#
# WHAT IT SETS UP (per machine, once — never per project):
#   ~/.syndicate-remote-secrets/ingest.json = {"url": "...", "token": "..."}   mode 600
#
# The route reads $HOME and nothing else, so once this succeeds EVERY project on this machine can
# report — including one under /mnt/c/... . Where the project lives is irrelevant by construction.
#
# ORDER IS DELIBERATE: the token is PROVEN against the endpoint before ingest.json is written. A
# config recording an unproven route is worse than none — it flips the resolver from "spool" (loud,
# recoverable) to "ingest" (confident, and wrong at the moment it matters).
#
# Usage:
#   bash connect.sh --url <ingest url> --token <host token>
#   bash connect.sh --url <ingest url>          # token read from stdin (paste, then Ctrl-D)
#
# Exit codes:
#   0 route proven and recorded        3 token rejected, or endpoint unreachable (nothing written)
#   1 usage / unsupported environment

set -uo pipefail

URL="" ; TOKEN=""
while [ $# -gt 0 ]; do
  case "$1" in
    --url)   URL="${2:-}"; shift 2 ;;
    --token) TOKEN="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 1 ;;
  esac
done

say()  { printf '%s\n' "$*"; }
fail() { printf 'FAILED: %s\n' "$1" >&2; exit "${2:-1}"; }

# --- environment ------------------------------------------------------------------------------
# ingest.json holds a bearer token; on a Windows mount it would be world-readable (0777, chmod a
# no-op) and the token would leak to every process. Refuse, as the ssh-key era did.
case "$HOME" in
  /mnt/*) fail "\$HOME is $HOME — a Windows mount, which cannot hold 0600. Run inside WSL (a real
        /home/<user> home), so the token file is not world-readable." 1 ;;
esac
# Under sudo, $HOME becomes /root and ingest.json lands where the session resolver never looks.
if [ "$(id -u)" -eq 0 ]; then
  fail "running as root${SUDO_USER:+ (sudo, invoked by $SUDO_USER)} — \$HOME is $HOME. This only
        writes inside your own home and needs no privilege; /update-progress resolves the route from
        the SESSION user's \$HOME, never /root. Re-run WITHOUT sudo." 1
fi
command -v curl >/dev/null 2>&1 || fail "curl not found — install curl" 1
[ -n "$URL" ] || fail "no --url given. The operator supplies the ingest endpoint URL and a per-host
        token (out of band, as the PEM used to be)." 1
case "$URL" in https://*) : ;; *) fail "--url must be an https:// endpoint, not '$URL'" 1 ;; esac

if [ -z "$TOKEN" ]; then
  [ -t 0 ] && say "Paste the host token, then press Ctrl-D:"
  TOKEN="$(cat)"
fi
TOKEN="$(printf '%s' "$TOKEN" | tr -d '\r\n ')"   # a pasted token often carries a trailing newline/CR
[ -n "$TOKEN" ] || fail "empty token" 1

# --- PROVE the token before recording it ------------------------------------------------------
# Probe = POST an EMPTY body. The endpoint checks auth FIRST, so:
#   401 -> token rejected            400 -> token ACCEPTED (auth passed, empty body refused)
#   000/5xx -> endpoint unreachable/erroring
# This validates the token WITHOUT delivering a file (no extraction is created by an empty body).
say "probing the endpoint with this token ..."
code=$(curl -sS -m 20 -X POST -H "Authorization: Bearer $TOKEN" --data "" \
       -o /dev/null -w '%{http_code}' "$URL" 2>/dev/null || echo 000)
case "$code" in
  400) say "token accepted (auth ok; empty probe body correctly refused)" ;;
  401|403) fail "token rejected by the endpoint (HTTP $code). Nothing written. Check the token with
        the operator." 3 ;;
  000) fail "endpoint unreachable (no HTTP response). Nothing written — this host stays on 'spool',
        loud, not silent. Check the URL and this machine's outbound HTTPS." 3 ;;
  5*)  fail "endpoint returned HTTP $code (server-side). Nothing written; retry later or tell the
        operator." 3 ;;
  *)   say "endpoint returned HTTP $code — treating auth as accepted" ;;
esac

# --- record -----------------------------------------------------------------------------------
mkdir -p "$HOME/.syndicate-remote-secrets" && chmod 700 "$HOME/.syndicate-remote-secrets"
CFG="$HOME/.syndicate-remote-secrets/ingest.json"
umask 177
python3 - "$URL" "$TOKEN" "$CFG" <<'PY'
import json, sys, os
url, token, cfg = sys.argv[1], sys.argv[2], sys.argv[3]
with open(cfg, "w") as f:
    json.dump({"url": url, "token": token}, f)
os.chmod(cfg, 0o600)
PY
say "config written: $CFG (mode 600)"

# --- the route, resolved exactly as /update-progress § 11.0 does ------------------------------
if   [ -d "$HOME/syndicate-playbook/knowledge_extraction" ]; then ROUTE=direct
elif [ -f "$HOME/.syndicate-remote-secrets/ingest.json" ];   then ROUTE=ingest
else ROUTE=spool; fi
say ""
say "ROUTE = $ROUTE"
[ "$ROUTE" = "spool" ] && fail "resolver still says spool — ingest.json is not where \$HOME points" 1
say "Done. Every project on this machine can now report by HTTPS, wherever it lives on disk."
