#!/usr/bin/env bash
#
# audit.sh — One-shot health and integrity audit of a running Muse Guard box.
#
# Runs every check that matters and prints a single PASS/FAIL summary. Designed
# to be run by a human who is worried, or by cron who is watchful.
#
# Usage:  bash scripts/audit.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { printf '  [PASS] %s\n' "$1"; }
fail() { printf '  [FAIL] %s\n' "$1"; FAIL=1; }
info() { printf '  [info] %s\n' "$1"; }

echo "== Muse Guard audit =="
echo "root: $ROOT"
echo

# 1. kill switch state ---------------------------------------------------------
echo "kill switch:"
if [ -f guardrails/kill_switch/state.json ]; then
  STATE="$(python3 -c "import json;print(json.load(open('guardrails/kill_switch/state.json')).get('locked'))" 2>/dev/null || echo unknown)"
  info "locked=$STATE"
  if [ "$STATE" = "True" ]; then info "agent is LOCKED (this is the safe state)"; fi
else
  fail "no kill switch state file"
fi
echo

# 2. action log integrity ------------------------------------------------------
echo "action log:"
if python3 logger/integrity_check.py >/tmp/mg_integrity.txt 2>&1; then
  pass "hash chain intact"
else
  fail "hash chain BROKEN — investigate now"
  cat /tmp/mg_integrity.txt
fi
echo

# 3. persona drift -------------------------------------------------------------
echo "persona files:"
if python3 monitor/file_watcher.py check >/tmp/mg_persona.txt 2>&1; then
  pass "no drift"
else
  fail "persona drift detected"
  cat /tmp/mg_persona.txt
fi
echo

# 4. network egress ------------------------------------------------------------
echo "network:"
if python3 monitor/network_watcher.py check >/tmp/mg_net.txt 2>&1; then
  pass "no unexpected egress"
else
  fail "unexpected outbound connections"
  cat /tmp/mg_net.txt
fi
echo

# 5. processes -----------------------------------------------------------------
echo "processes:"
if python3 monitor/process_watcher.py check >/tmp/mg_proc.txt 2>&1; then
  pass "no suspicious processes"
else
  fail "suspicious processes present"
  cat /tmp/mg_proc.txt
fi
echo

# 6. approval queue ------------------------------------------------------------
echo "approval queue:"
PENDING="$(python3 agent/propose.py pending 2>/dev/null | grep -c '^\[' || true)"
info "pending proposals: ${PENDING:-0}"
echo

# summary ----------------------------------------------------------------------
echo "========================================"
if [ "$FAIL" -eq 0 ]; then
  echo "AUDIT: PASS — cage is intact."
  exit 0
else
  echo "AUDIT: FAIL — see [FAIL] lines above."
  exit 1
fi
