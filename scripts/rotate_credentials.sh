#!/usr/bin/env bash
#
# rotate_credentials.sh — Rotate one or all credentials in the proxy store.
#
# Credentials live only in proxy/credentials/ and are read by the proxy, never
# by the agent. This script helps you replace them safely:
#   * It never prints secret values.
#   * It backs up the old file (encrypted-at-rest is your responsibility).
#   * It reminds you to revoke the old credential at the provider.
#
# Usage:
#   bash scripts/rotate_credentials.sh                 # list what's present
#   bash scripts/rotate_credentials.sh bluesky         # rotate one by name
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CRED_DIR="$ROOT/proxy/credentials"

echo "== credential rotation =="
echo "store: $CRED_DIR"

if [ ! -d "$CRED_DIR" ]; then
  echo "No credential directory. Run scripts/setup.sh first."
  exit 1
fi

if [ $# -eq 0 ]; then
  echo "Present credentials (names only, values never shown):"
  find "$CRED_DIR" -maxdepth 1 -type f ! -name 'README.md' ! -name '.gitkeep' \
    -printf '  %f\n' 2>/dev/null || ls -1 "$CRED_DIR"
  echo
  echo "To rotate one:  bash scripts/rotate_credentials.sh <name>"
  exit 0
fi

NAME="$1"
TARGET="$CRED_DIR/$NAME"

echo "Rotating: $NAME"
if [ -f "$TARGET" ]; then
  STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
  cp "$TARGET" "$TARGET.bak.$STAMP"
  chmod 600 "$TARGET.bak.$STAMP"
  echo "  backed up old value to $(basename "$TARGET").bak.$STAMP"
fi

echo "  Enter the NEW credential value (input hidden):"
read -r -s NEWVAL
echo
printf '%s' "$NEWVAL" > "$TARGET"
chmod 600 "$TARGET"
unset NEWVAL

cat <<NEXT

  Done. Two more things, by hand:
    1. REVOKE the old credential at the provider. A rotated-but-still-valid
       credential is not rotated.
    2. Restart the proxy so it picks up the new value.

  Reminder: credentials must never appear in logs, memory, or the repo.
NEXT
