#!/usr/bin/env bash
# connect.sh — give THIS machine a working route to the syndicate box, from one input: the PEM.
#
# WHAT IT SETS UP (per machine, once — never per project):
#   ~/.ssh/<key>.pem                        the private key, mode 600, on the LINUX filesystem
#   ~/.syndicate-remote-secrets/box.json    the config /update-progress § 11.0 resolves
#
# The knowledge route reads $HOME and nothing else, so once this succeeds EVERY project on this
# machine can report — including one living on /mnt/c/... . Where the project lives is irrelevant
# by construction; that is the property this script exists to guarantee.
#
# ORDER IS DELIBERATE: the key is installed and PROVEN against the box BEFORE box.json is written.
# A config file that records an unproven route is worse than no config: it flips the resolver from
# "spool" (loud, recoverable) to "remote" (confident, and wrong at the moment it matters).
#
# Usage:
#   bash connect.sh --host <box-address> [--pem <file>] [--user ubuntu]
#                   [--workspace /home/ubuntu] [--key-name syndicate-box]
#
#   With no --pem, the key is read from stdin — paste it, then press Ctrl-D. That is the intended
#   handover: the operator sends the command (which carries the address) and the PEM separately.
#
# Exit codes:
#   0 route works and is recorded      3 box unreachable with this key
#   1 usage / unsupported environment  4 key + box fine, but the inbox is missing or read-only
#   2 the pasted key is not a private key

set -uo pipefail

HOST="" ; PEM="" ; BUSER="ubuntu" ; WORKSPACE="" ; KEYNAME="syndicate-box"

while [ $# -gt 0 ]; do
  case "$1" in
    --host)      HOST="${2:-}"; shift 2 ;;
    --pem)       PEM="${2:-}"; shift 2 ;;
    --user)      BUSER="${2:-}"; shift 2 ;;
    --workspace) WORKSPACE="${2:-}"; shift 2 ;;
    --key-name)  KEYNAME="${2:-}"; shift 2 ;;
    -h|--help)   sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 1 ;;
  esac
done
[ -n "$WORKSPACE" ] || WORKSPACE="/home/$BUSER"

say()  { printf '%s\n' "$*"; }
fail() { printf 'FAILED: %s\n' "$1" >&2; exit "${2:-1}"; }   # $1 only — $* would print the code

# --- 0. environment ---------------------------------------------------------------------------
# $HOME on a Windows mount cannot hold 0600: the mount reports 0777 for every file and chmod is a
# no-op, so ssh would refuse the key no matter what this script does. Stop here rather than
# produce a setup that looks complete and fails at first use.
case "$HOME" in
  /mnt/*) fail "\$HOME is $HOME — a Windows mount, which cannot hold 0600 permissions.
        Run this inside WSL (a normal /home/<user> home), not from a C: drive shell." 1 ;;
esac

# Refuse sudo/root. This writes the key and box.json into $HOME, and /update-progress § 11.0
# resolves the route from the SESSION user's $HOME — never /root. Under sudo, $HOME becomes /root,
# so a "successful" run installs everything where the resolver will never look, and the host keeps
# resolving spool while every check says it is set up. Measured on exactly this handover.
if [ "$(id -u)" -eq 0 ]; then
  fail "running as root${SUDO_USER:+ (sudo, invoked by $SUDO_USER)} — \$HOME is $HOME.
        This only ever writes inside your own home, so it needs no privilege. Under sudo the key
        and box.json land in /root, where the resolver that runs your sessions never looks — it
        reads YOUR \$HOME. Re-run as your normal user, WITHOUT sudo." 1
fi

command -v ssh >/dev/null 2>&1 || fail "ssh not found — install openssh-client" 1
[ -n "$HOST" ] || fail "no --host given. The box address changes when it is stopped and started,
        so it is not baked into this file; the operator supplies it with the command." 1

# --host is the box's ADDRESS (IP or DNS), never a file. A path here is the common slip — someone
# points it at box.json or a key — and ssh then tries to resolve the path as a hostname and fails
# with a message about the path, not the mistake. Catch it before the probe.
case "$HOST" in
  */*|*" "*) fail "--host is '$HOST', which is a path, not a box address.
        Pass the box's IP or DNS name (e.g. --host 203.0.113.10). The KEY goes on stdin or via
        --pem; --host wants only the address." 1 ;;
esac
[ -e "$HOST" ] && fail "--host is '$HOST', which is an existing file, not a box address.
        Pass the box's IP or DNS name; the key goes on stdin or via --pem." 1

# --- 1. read the key --------------------------------------------------------------------------
if [ -n "$PEM" ]; then
  [ -f "$PEM" ] || fail "--pem $PEM does not exist" 1
  KEYDATA="$(cat "$PEM")"
else
  if [ -t 0 ]; then
    say "Paste the private key (the whole -----BEGIN ... END----- block), then press Ctrl-D:"
  fi
  KEYDATA="$(cat)"
fi

# Strip CR. A key pasted through a Windows clipboard arrives CRLF-terminated, and ssh rejects it
# with "invalid format" — an error that names the format, never the line endings, and has cost
# real time on exactly this handover path.
KEYDATA="$(printf '%s' "$KEYDATA" | tr -d '\r')"

case "$KEYDATA" in
  *"PRIVATE KEY"*) : ;;
  *) fail "that is not a private key (no 'PRIVATE KEY' marker). Public keys (.pub) and
        certificates will not work — it must be the PEM itself." 2 ;;
esac

# --- 2. install it on the Linux filesystem ----------------------------------------------------
mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
KEYPATH="$HOME/.ssh/${KEYNAME}.pem"
if [ -f "$KEYPATH" ] && ! printf '%s\n' "$KEYDATA" | cmp -s - "$KEYPATH"; then
  BACKUP="${KEYPATH}.bak-$(date +%Y%m%d%H%M%S)"
  cp "$KEYPATH" "$BACKUP" && chmod 600 "$BACKUP"
  say "note: a different key was already at $KEYPATH — kept as $BACKUP"
fi
printf '%s\n' "$KEYDATA" > "$KEYPATH"
chmod 600 "$KEYPATH"
PERMS="$(stat -c %a "$KEYPATH" 2>/dev/null || echo '?')"
[ "$PERMS" = "600" ] || fail "$KEYPATH is mode $PERMS, not 600 — ssh will refuse it" 1
say "key installed: $KEYPATH (mode 600)"

# --- 3. PROVE the route before recording it ---------------------------------------------------
# Per-run temp file — a fixed /tmp path is world-writable-directory bait: created by one user (or a
# stray earlier sudo run) it becomes unwritable to the next, and the probe dies on the error file
# instead of the network. mktemp gives a unique file owned by whoever runs this.
ERRFILE="$(mktemp 2>/dev/null || printf '%s' "$HOME/.syndicate-connect.$$.err")"
trap 'rm -f "$ERRFILE"' EXIT
say "probing ${BUSER}@${HOST} ..."
if ! ssh -i "$KEYPATH" -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
         -o ConnectTimeout=15 "${BUSER}@${HOST}" true 2>"$ERRFILE"; then
  say "--- ssh said: ---"; cat "$ERRFILE" >&2
  fail "cannot reach ${BUSER}@${HOST} with this key. Nothing was recorded.
        Timeout        -> the box is stopped, or its address changed (stop/start reassigns it)
        Permission denied -> wrong key for this box, or wrong --user
        No box.json was written, so this machine still resolves 'spool' — loud, not silent." 3
fi
say "ssh ok"

# --- 4. record the config ---------------------------------------------------------------------
mkdir -p "$HOME/.syndicate-remote-secrets" && chmod 700 "$HOME/.syndicate-remote-secrets"
CFG="$HOME/.syndicate-remote-secrets/box.json"
printf '{\n  "host": "%s",\n  "user": "%s",\n  "workspace": "%s",\n  "ssh_key": "%s"\n}\n' \
  "$HOST" "$BUSER" "$WORKSPACE" "$KEYPATH" > "$CFG"
chmod 600 "$CFG"
say "config written: $CFG (mode 600)"

# --- 5. verify what the config is FOR ---------------------------------------------------------
INBOX="$WORKSPACE/syndicate-playbook/knowledge_extraction"
if ! ssh -i "$KEYPATH" -o BatchMode=yes -o ConnectTimeout=15 "${BUSER}@${HOST}" \
     "[ -d '$INBOX' ] && touch '$INBOX/.connect-test' && rm -f '$INBOX/.connect-test'" 2>/dev/null; then
  fail "the box is reachable, but $INBOX is missing or not writable by $BUSER.
        box.json is written and correct; the inbox itself needs the operator's attention." 4
fi
say "inbox reachable and writable: ${BUSER}@${HOST}:$INBOX"

# --- 6. the route, resolved exactly as /update-progress § 11.0 does ---------------------------
if   [ -d "$HOME/syndicate-playbook/knowledge_extraction" ]; then ROUTE=direct
elif [ -f "$HOME/.syndicate-remote-secrets/box.json" ];      then ROUTE=remote
else ROUTE=spool; fi

say ""
say "ROUTE = $ROUTE"
[ "$ROUTE" = "spool" ] && fail "the resolver still says spool — box.json is not where \$HOME points" 1
say "Done. Every project on this machine can now report, wherever it lives on disk —"
say "the route reads \$HOME only, so a project under /mnt/c works the same as one under ~."
say "If the box is ever stopped and started, re-run this with the new --host."
