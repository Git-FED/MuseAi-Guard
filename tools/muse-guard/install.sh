#!/usr/bin/env bash
#
# install.sh — install muse-guard (kill switch + approval queue).
#
# No dependencies beyond Python 3.8+. Copies the package to a target directory
# (default: /opt/muse-guard) and drops a `muse-guard` launcher on PATH.
#
# Usage:
#   bash install.sh                 # install to /opt/muse-guard
#   PREFIX=$HOME/.local bash install.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${PREFIX:-/opt/muse-guard}"
BIN_DIR="${BIN_DIR:-/usr/local/bin}"

echo "== installing muse-guard =="
echo "prefix: $PREFIX"

mkdir -p "$PREFIX"
cp -r "$HERE/muse_guard" "$PREFIX/"

# Write the launcher.
LAUNCHER="$BIN_DIR/muse-guard"
mkdir -p "$BIN_DIR" 2>/dev/null || true
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec python3 -c "import sys; sys.path.insert(0, '$PREFIX'); from muse_guard.cli import main; sys.exit(main(sys.argv[1:]))" "\$@"
EOF
chmod +x "$LAUNCHER"

# Initialize a fail-closed kill state (locked until the operator unlocks).
if [ ! -f "$PREFIX/muse_guard/kill_state.json" ]; then
  cat > "$PREFIX/muse_guard/kill_state.json" <<'JSON'
{"locked": true, "reason": "fresh install (fail-closed)", "since": null}
JSON
  echo "  wrote fail-closed kill state (locked until you unlock)"
fi

echo "  installed to $PREFIX"
echo "  launcher: $LAUNCHER"
echo
echo "Try:  muse-guard status"
echo "      muse-guard unlock \"setup complete\""
