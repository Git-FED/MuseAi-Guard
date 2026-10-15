#!/usr/bin/env bash
#
# setup.sh — Bring a fresh box up to MSP-1 Phase 2 (guardrails first).
#
# This script is deliberately conservative. It:
#   1. Creates the runtime directories.
#   2. Locks the persona files read-only (chattr +i where possible, else chmod).
#   3. Initializes the kill switch to UNLOCKED but with an empty allowlist.
#   4. Writes the file-watcher baseline.
#   5. Prints the next manual steps (credentials, allowlist, first boot).
#
# It does NOT enable the agent. Enabling is a separate, human step. Cage first.
#
# Usage:  bash scripts/setup.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== Muse Guard setup =="
echo "project root: $ROOT"

# --- 1. directories -----------------------------------------------------------
echo "[1/5] creating runtime directories"
mkdir -p \
  logger/logs \
  guardrails/approval_queue \
  guardrails/kill_switch \
  proxy/credentials \
  executor/actions \
  memory/daily memory/topics memory/audit \
  monitor \
  workspace

# --- 2. lock persona files ----------------------------------------------------
echo "[2/5] locking persona files read-only"
for f in persona/SOUL.md persona/IDENTITY.md persona/MEMORY.md \
         persona/SYSTEM.md persona/RULES.md; do
  if [ -f "$f" ]; then
    # chmod first (always works), then try the stronger immutable bit.
    chmod 0444 "$f" || true
    if command -v chattr >/dev/null 2>&1; then
      chattr +i "$f" 2>/dev/null && echo "  immutable: $f" || echo "  read-only: $f (chattr unavailable)"
    else
      echo "  read-only: $f"
    fi
  else
    echo "  WARNING: missing $f"
  fi
done

# --- 3. initialize kill switch ------------------------------------------------
echo "[3/5] initializing kill switch (unlocked, empty allowlist)"
if [ ! -f guardrails/kill_switch/state.json ]; then
  cat > guardrails/kill_switch/state.json <<'JSON'
{"locked": false, "reason": null, "since": null}
JSON
  echo "  wrote default state.json"
else
  echo "  state.json already exists (left untouched)"
fi

# --- 4. file-watcher baseline -------------------------------------------------
echo "[4/5] recording persona baseline"
python3 monitor/file_watcher.py baseline || echo "  (baseline skipped)"

# --- 5. next steps ------------------------------------------------------------
echo "[5/5] done. Next manual steps:"
cat <<'NEXT'

  NEXT STEPS (do these by hand, deliberately):
    1. Put real credentials in proxy/credentials/ (never in the repo).
       See docs/CREDENTIAL_ROTATION.md.
    2. Edit proxy/allowlist.json to the exact domains you allow.
       No wildcards. Exact hostnames only.
    3. Run: python guardrails/notifier/notify.py "setup complete"
    4. Verify the cage:  python logger/integrity_check.py
    5. Only then consider enabling the agent (MSP-1 Phase 6).

  REMEMBER: the agent is OFF until you turn it on. Cage first.
NEXT
