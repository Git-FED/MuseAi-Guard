#!/usr/bin/env bash
#
# health_check.sh — Quick liveness/health check, cron-friendly.
#
# Lighter than audit.sh: checks that the cage components are present and that
# the kill switch is in a known state. Prints one line and exits non-zero if
# anything is off, so a monitoring system can alert on it.
#
# Usage:  bash scripts/health_check.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PROBLEMS=0

check_file() {
  if [ -e "$1" ]; then
    printf '  ok   %s\n' "$1"
  else
    printf '  MISS %s\n' "$1"
    PROBLEMS=$((PROBLEMS + 1))
  fi
}

echo "Muse Guard health check — $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# core files
check_file persona/SOUL.md
check_file persona/RULES.md
check_file persona/SYSTEM.md
check_file guardrails/kill_switch/kill_switch.py
check_file guardrails/approval_queue/queue.py
check_file proxy/egress_proxy.py
check_file proxy/allowlist.json
check_file executor/executor.py
check_file logger/action_log.py

# kill switch must be readable and valid JSON
if [ -f guardrails/kill_switch/state.json ]; then
  if python3 -c "import json,sys;json.load(open('guardrails/kill_switch/state.json'))" 2>/dev/null; then
    printf '  ok   kill switch state is valid JSON\n'
  else
    printf '  BAD  kill switch state is corrupt (fail-closed)\n'
    PROBLEMS=$((PROBLEMS + 1))
  fi
else
  printf '  MISS kill switch state.json\n'
  PROBLEMS=$((PROBLEMS + 1))
fi

# log integrity (cheap)
if python3 logger/integrity_check.py >/dev/null 2>&1; then
  printf '  ok   action log chain intact\n'
else
  printf '  BAD  action log chain broken\n'
  PROBLEMS=$((PROBLEMS + 1))
fi

echo "----------------------------------------"
if [ "$PROBLEMS" -eq 0 ]; then
  echo "HEALTHY"
  exit 0
else
  echo "UNHEALTHY ($PROBLEMS problem(s))"
  exit 1
fi
