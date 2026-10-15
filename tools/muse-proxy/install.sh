#!/usr/bin/env bash
#
# install.sh — install muse-proxy (the credential-holding egress proxy).
#
# Copies the package to a target directory (default: /opt/muse-proxy), creates a
# locked-down credential store, and drops a `muse-proxy` launcher on PATH.
#
# Usage:
#   bash install.sh
#   PREFIX=$HOME/.local bash install.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${PREFIX:-/opt/muse-proxy}"
BIN_DIR="${BIN_DIR:-/usr/local/bin}"

echo "== installing muse-proxy =="
echo "prefix: $PREFIX"

mkdir -p "$PREFIX"
cp -r "$HERE/muse_proxy" "$PREFIX/"

# Create the credential store with tight permissions.
STORE="$PREFIX/muse_proxy/credentials"
mkdir -p "$STORE"
chmod 700 "$STORE"
cat > "$STORE/README.md" <<'MD'
# Credential store

One secret per file, mode 0600. The proxy reads these; the agent never can.

    printf '%s' "$SECRET" > bluesky && chmod 600 bluesky

Never commit this directory. Never log these values.
MD
chmod 600 "$STORE/README.md" 2>/dev/null || true

# Launcher.
LAUNCHER="$BIN_DIR/muse-proxy"
mkdir -p "$BIN_DIR" 2>/dev/null || true
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec python3 -c "import sys; sys.path.insert(0, '$PREFIX'); from muse_proxy.proxy import _main; sys.exit(_main(sys.argv[1:]))" "\$@"
EOF
chmod +x "$LAUNCHER"

echo "  installed to $PREFIX"
echo "  credential store: $STORE (0700)"
echo "  launcher: $LAUNCHER"
echo
echo "Next:"
echo "  1. Edit $PREFIX/muse_proxy/allowlist.json (exact hosts, no wildcards)."
echo "  2. Put credentials in $STORE (0600)."
echo "  3. Run: muse-proxy --selftest"
