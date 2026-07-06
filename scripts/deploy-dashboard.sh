#!/usr/bin/env bash
# Production dashboard deploy helper for Atlas Agent.
#
# Usage:
#   git clone https://github.com/theusamaaslam/AtlasAgent.git
#   cd AtlasAgent
#   bash scripts/deploy-dashboard.sh
#
# Optional environment:
#   ATLAS_HOST=0.0.0.0
#   ATLAS_PORT=9119
#   ATLAS_DASHBOARD_USER=admin
#   ATLAS_DASHBOARD_PASSWORD='change-me'
#   ATLAS_INSTALL_DIR=/opt/atlas-agent
#   ATLAS_HOME=/opt/atlas
#   ATLAS_INSTALL_SCRIPT=/path/to/install.sh
#   ATLAS_RESTART_EXISTING=0
#   ATLAS_PUBLIC_HOST=100.99.45.114

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATLAS_HOST="${ATLAS_HOST:-0.0.0.0}"
ATLAS_PORT="${ATLAS_PORT:-9119}"
ATLAS_DASHBOARD_USER="${ATLAS_DASHBOARD_USER:-atlas}"
ATLAS_INSTALL_SCRIPT="${ATLAS_INSTALL_SCRIPT:-$SCRIPT_DIR/install.sh}"
ATLAS_HOME="${ATLAS_HOME:-$HOME/.atlas}"
ATLAS_RESTART_EXISTING="${ATLAS_RESTART_EXISTING:-1}"
ATLAS_PUBLIC_HOST="${ATLAS_PUBLIC_HOST:-}"

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

if [ ! -f "$ATLAS_INSTALL_SCRIPT" ]; then
  echo "Atlas installer not found at $ATLAS_INSTALL_SCRIPT" >&2
  echo "Run this deploy helper from a cloned AtlasAgent repository, or set ATLAS_INSTALL_SCRIPT." >&2
  exit 1
fi

echo "Installing Atlas into $INSTALL_DIR..."
bash "$ATLAS_INSTALL_SCRIPT" \
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

list_port_pids() {
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp "sport = :$ATLAS_PORT" 2>/dev/null \
      | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' \
      | sort -u
  fi
}

cmdline_for_pid() {
  local pid="$1"
  if [ -r "/proc/$pid/cmdline" ]; then
    tr '\0' ' ' < "/proc/$pid/cmdline"
  elif command -v ps >/dev/null 2>&1; then
    ps -p "$pid" -o command= 2>/dev/null || true
  fi
}

stop_existing_dashboard_on_port() {
  local pids pid cmdline safe_pids
  pids="$(list_port_pids || true)"
  [ -n "$pids" ] || return 0

  safe_pids=""
  for pid in $pids; do
    cmdline="$(cmdline_for_pid "$pid")"
    case "$cmdline" in
      *atlas*" dashboard"*|*atlas-dashboard*)
        safe_pids="$safe_pids $pid"
        ;;
      *)
        echo "Port $ATLAS_PORT is already in use by PID $pid:" >&2
        echo "  $cmdline" >&2
        echo "Set ATLAS_PORT to another port, or stop that process first." >&2
        exit 1
        ;;
    esac
  done

  if [ "$ATLAS_RESTART_EXISTING" != "1" ]; then
    echo "An Atlas dashboard is already running on port $ATLAS_PORT." >&2
    echo "Set ATLAS_RESTART_EXISTING=1 to replace it, or ATLAS_PORT to use another port." >&2
    exit 1
  fi

  echo "Stopping existing Atlas dashboard on port $ATLAS_PORT..."
  for pid in $safe_pids; do
    kill "$pid" 2>/dev/null || true
  done

  for _ in 1 2 3 4 5; do
    sleep 1
    [ -z "$(list_port_pids || true)" ] && return 0
  done

  echo "Existing dashboard did not stop cleanly; forcing shutdown..."
  for pid in $safe_pids; do
    kill -9 "$pid" 2>/dev/null || true
  done
  sleep 1
}

print_dashboard_urls() {
  if [ -n "$ATLAS_PUBLIC_HOST" ]; then
    echo "URL:      http://$ATLAS_PUBLIC_HOST:$ATLAS_PORT"
    return
  fi

  if [ "$ATLAS_HOST" = "0.0.0.0" ] || [ "$ATLAS_HOST" = "::" ]; then
    echo "URLs:"
    echo "  http://127.0.0.1:$ATLAS_PORT"
    if command -v hostname >/dev/null 2>&1; then
      for ip in $(hostname -I 2>/dev/null || true); do
        echo "  http://$ip:$ATLAS_PORT"
      done
    fi
    return
  fi

  echo "URL:      http://$ATLAS_HOST:$ATLAS_PORT"
}

mkdir -p "$ATLAS_HOME/logs"
stop_existing_dashboard_on_port
echo "Starting Atlas dashboard on $ATLAS_HOST:$ATLAS_PORT..."
nohup "$ATLAS_BIN" dashboard \
  --host "$ATLAS_HOST" \
  --port "$ATLAS_PORT" \
  --no-open \
  > "$ATLAS_HOME/logs/dashboard.log" 2>&1 &
DASHBOARD_PID="$!"

CHECK_HOST="$ATLAS_HOST"
if [ "$CHECK_HOST" = "0.0.0.0" ] || [ "$CHECK_HOST" = "::" ]; then
  CHECK_HOST="127.0.0.1"
fi

STARTED=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsSI --max-time 2 "http://$CHECK_HOST:$ATLAS_PORT/" >/dev/null 2>&1; then
    STARTED=1
    break
  fi
  if ! kill -0 "$DASHBOARD_PID" 2>/dev/null; then
    break
  fi
  sleep 1
done

if [ "$STARTED" != "1" ]; then
  echo "Atlas dashboard did not start successfully." >&2
  echo "Logs: $ATLAS_HOME/logs/dashboard.log" >&2
  tail -40 "$ATLAS_HOME/logs/dashboard.log" >&2 || true
  exit 1
fi

echo ""
echo "Atlas dashboard is running."
print_dashboard_urls
echo "Username: $ATLAS_DASHBOARD_USER"
echo "Password: $ATLAS_DASHBOARD_PASSWORD"
echo "Logs:     $ATLAS_HOME/logs/dashboard.log"
