#!/usr/bin/env bash
#
# export_forensics.sh — Bundle everything an investigator needs from a box.
#
# Use this when you have "pulled the plug" and want a single archive that
# captures the state of a machine before you touch anything. It gathers:
#   * the Muse Guard action log and approval queue
#   * persona + memory (so you can see what the agent believed)
#   * system-level evidence via the muse-forensics tool (cron, systemd, shell
#     history, ssh, cloud CLIs, logs)
#
# It does NOT delete anything and does NOT contain credential *values* — but
# treat the output as sensitive anyway (paths and history can leak).
#
# Usage:  bash scripts/export_forensics.sh [output_dir]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$ROOT/forensics-export-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$OUT"

echo "== exporting forensics =="
echo "into: $OUT"

# 1. Muse Guard's own artifacts ------------------------------------------------
echo "[1/3] copying Muse Guard artifacts"
for d in logger guardrails proxy executor persona memory monitor docs; do
  if [ -d "$ROOT/$d" ]; then
    mkdir -p "$OUT/muse-guard/$d"
    # Copy text/config; skip credential VALUES.
    rsync -a --exclude 'credentials/*' --exclude '*.bak.*' \
      "$ROOT/$d/" "$OUT/muse-guard/$d/" 2>/dev/null || \
      cp -r "$ROOT/$d" "$OUT/muse-guard/" 2>/dev/null || true
  fi
done

# 2. system evidence via muse-forensics ----------------------------------------
echo "[2/3] running muse-forensics"
if [ -f "$ROOT/tools/muse-forensics/forensic.py" ]; then
  python3 "$ROOT/tools/muse-forensics/forensic.py" --out "$OUT/system" || \
    echo "  (forensic.py reported issues; continuing)"
else
  echo "  muse-forensics not found; skipping system checks"
fi

# 3. manifest ------------------------------------------------------------------
echo "[3/3] writing manifest"
{
  echo "Muse Guard forensics export"
  echo "created: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "host: $(hostname 2>/dev/null || echo unknown)"
  echo
  echo "files:"
  find "$OUT" -type f -printf '  %P\n' | sort
} > "$OUT/MANIFEST.txt"

echo
echo "Done. Archive it with:  tar czf ${OUT}.tar.gz -C \"$(dirname "$OUT")\" \"$(basename "$OUT")\""
echo "Then move it OFF the box and keep it read-only."
