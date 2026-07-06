#!/usr/bin/env bash
# Production dashboard deploy helper for Atlas Agent.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/theusamaaslam/AtlasAgent/main/scripts/deploy-dashboard.sh | bash
#
# Optional environment:
#   ATLAS_HOST=0.0.0.0
#   ATLAS_PORT=9119
#   ATLAS_DASHBOARD_USER=admin
#   ATLAS_DASHBOARD_PASSWORD='change-me'
#   ATLAS_INSTALL_DIR=/opt/atlas-agent
#   ATLAS_HOME=/opt/atlas
#   ATLAS_INSTALL_SCRIPT_URL=https://.../scripts/install.sh

set -euo pipefail

ATLAS_HOST="${ATLAS_HOST:-0.0.0.0}"
ATLAS_PORT="${ATLAS_PORT:-9119}"
ATLAS_DASHBOARD_USER="${ATLAS_DASHBOARD_USER:-atlas}"
ATLAS_INSTALL_SCRIPT_URL="${ATLAS_INSTALL_SCRIPT_URL:-https://raw.githubusercontent.com/theusamaaslam/AtlasAgent/main/scripts/install.sh}"
ATLAS_HOME="${ATLAS_HOME:-$HOME/.atlas}"

if [ -n "${ATLAS_INSTALL_DIR:-}" ]; then
  INSTALL_DIR="$ATLAS_INSTALL_DIR"
elif [ "$(id -u)" = "0" ] && [ "$(uname -s)" = "Linux" ]; then
  INSTALL_DIR="/usr/local/lib/atlas-agent"
else
  INSTALL_DIR="$ATLAS_HOME/atlas-agent"
fi

if [ -z "${ATLAS_DASHBOARD_PASSWORD:-}" ]; then
  if command -v python3 >/dev/null 2>&1; then
    ATLAS_DASHBOARD_PASSWORD="$(
      python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
    )"
  elif command -v openssl >/dev/null 2>&1; then
    ATLAS_DASHBOARD_PASSWORD="$(openssl rand -base64 24 | tr -d '\n')"
  else
    ATLAS_DASHBOARD_PASSWORD="atlas-$(date +%s)-$$"
  fi
fi

tmp_install="$(mktemp)"
cleanup() {
  rm -f "$tmp_install"
}
trap cleanup EXIT

echo "Downloading Atlas installer..."
curl -fsSL "$ATLAS_INSTALL_SCRIPT_URL" -o "$tmp_install"

echo "Installing Atlas into $INSTALL_DIR..."
bash "$tmp_install" \
  --skip-setup \
  --non-interactive \
  --dir "$INSTALL_DIR" \
  --atlas-home "$ATLAS_HOME"

ATLAS_BIN="${ATLAS_BIN:-}"
if [ -z "$ATLAS_BIN" ]; then
  if command -v atlas >/dev/null 2>&1; then
    ATLAS_BIN="$(command -v atlas)"
  elif [ -x "$HOME/.local/bin/atlas" ]; then
    ATLAS_BIN="$HOME/.local/bin/atlas"
  elif [ -x "/usr/local/bin/atlas" ]; then
    ATLAS_BIN="/usr/local/bin/atlas"
  else
    echo "atlas command not found after install" >&2
    exit 1
  fi
fi

PYTHON_BIN="$INSTALL_DIR/venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
  echo "managed Python not found at $PYTHON_BIN" >&2
  exit 1
fi

PASSWORD_HASH="$(
  cd "$INSTALL_DIR"
  ATLAS_DASHBOARD_PASSWORD="$ATLAS_DASHBOARD_PASSWORD" "$PYTHON_BIN" - <<'PY'
import os
from plugins.dashboard_auth.basic import hash_password
print(hash_password(os.environ["ATLAS_DASHBOARD_PASSWORD"]))
PY
)"

"$ATLAS_BIN" config set dashboard.basic_auth.username "$ATLAS_DASHBOARD_USER"
"$ATLAS_BIN" config set dashboard.basic_auth.password_hash "$PASSWORD_HASH"

mkdir -p "$ATLAS_HOME/logs"
echo "Starting Atlas dashboard on $ATLAS_HOST:$ATLAS_PORT..."
nohup "$ATLAS_BIN" dashboard \
  --host "$ATLAS_HOST" \
  --port "$ATLAS_PORT" \
  --no-open \
  > "$ATLAS_HOME/logs/dashboard.log" 2>&1 &

echo ""
echo "Atlas dashboard is starting."
echo "URL:      http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo "$ATLAS_HOST"):$ATLAS_PORT"
echo "Username: $ATLAS_DASHBOARD_USER"
echo "Password: $ATLAS_DASHBOARD_PASSWORD"
echo "Logs:     $ATLAS_HOME/logs/dashboard.log"
