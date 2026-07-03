#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET="${ZHANGSHU_MACOS_TARGET:-aarch64-apple-darwin}"
PORT="${ZHANGSHU_MACOS_SMOKE_PORT:-18765}"
BACKEND_EXE="$PROJECT_ROOT/frontend/src-tauri/binaries/macos-$TARGET/zhangshu-backend/zhangshu-backend"

usage() {
  cat <<USAGE
Usage: scripts/smoke_packaged_backend_macos.sh [options]

Options:
  --backend-exe PATH   Path to the packaged backend executable.
  --port PORT          Port used for the smoke test. Default: $PORT
  -h, --help           Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend-exe)
      BACKEND_EXE="${2:?--backend-exe requires a path}"
      shift 2
      ;;
    --port)
      PORT="${2:?--port requires a value}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[ERROR] Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ! -x "$BACKEND_EXE" ]]; then
  echo "[ERROR] Backend executable is missing or not executable: $BACKEND_EXE" >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "[ERROR] curl is required for the backend smoke test." >&2
  exit 1
fi

TEMP_BASE="$(mktemp -d "${TMPDIR:-/tmp}/zhangshu-backend-smoke.XXXXXX")"
TEMP_DATA="$TEMP_BASE/data"
TEMP_LOGS="$TEMP_BASE/logs"
mkdir -p "$TEMP_DATA" "$TEMP_LOGS"

BACKEND_PID=""
cleanup() {
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
    sleep 0.2
    if kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
      kill -9 "$BACKEND_PID" >/dev/null 2>&1 || true
    fi
  fi
  rm -rf "$TEMP_BASE"
}
trap cleanup EXIT

echo "[INFO] Starting packaged backend smoke test..."
echo "[INFO] Backend: $BACKEND_EXE"
echo "[INFO] Port:    $PORT"

ZHANGSHU_BACKEND_HOST="127.0.0.1" \
ZHANGSHU_BACKEND_PORT="$PORT" \
ZHANGSHU_DATA_DIR="$TEMP_DATA" \
ZHANGSHU_LOG_DIR="$TEMP_LOGS" \
ZHANGSHU_DB_FILENAME="zhangshu.sqlite3" \
ZHANGSHU_FRONTEND_DIST="$PROJECT_ROOT/frontend/dist" \
PYTHONUNBUFFERED="1" \
  "$BACKEND_EXE" >"$TEMP_LOGS/stdout.log" 2>"$TEMP_LOGS/stderr.log" &

BACKEND_PID="$!"

HEALTH_URL="http://127.0.0.1:$PORT/health"
PROJECTS_URL="http://127.0.0.1:$PORT/api/projects"

for _ in $(seq 1 120); do
  if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    echo "[ERROR] Backend exited before becoming healthy." >&2
    cat "$TEMP_LOGS/stdout.log" >&2 || true
    cat "$TEMP_LOGS/stderr.log" >&2 || true
    exit 1
  fi

  if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

curl -fsS "$HEALTH_URL" >/dev/null
curl -fsS "$PROJECTS_URL" >/dev/null

echo "[OK] Packaged backend smoke test passed."
