#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"
TAURI_DIR="$FRONTEND_DIR/src-tauri"
RELEASE_DIR="$PROJECT_ROOT/release"

TARGET="${ZHANGSHU_MACOS_TARGET:-aarch64-apple-darwin}"
PYTHON_BIN="${ZHANGSHU_MACOS_PYTHON:-$BACKEND_DIR/.venv/bin/python}"
CODESIGN_IDENTITY="${ZHANGSHU_MACOS_CODESIGN_IDENTITY:--}"

SKIP_DEPS=0
SKIP_FRONTEND=0
SKIP_BACKEND=0
SKIP_SMOKE=0
SKIP_TAURI=0
SKIP_SIGN=0
SKIP_DMG=0

usage() {
  cat <<USAGE
Usage: scripts/package_macos.sh [options]

Build a macOS Apple Silicon release package for Zhangshu.

Options:
  --target TARGET       Rust target triple. Default: $TARGET
  --python PATH         Python inside the backend venv.
  --codesign IDENTITY   codesign identity. Default: ad-hoc signing (-).
  --skip-deps           Do not install Python dependencies.
  --skip-frontend       Reuse frontend/dist.
  --skip-backend        Reuse packaged backend.
  --skip-smoke          Skip packaged backend smoke test.
  --skip-tauri          Reuse an existing .app bundle.
  --skip-sign           Do not codesign the .app.
  --skip-dmg            Do not create the .dmg.
  -h, --help            Show this help.

Environment:
  ZHANGSHU_MACOS_TARGET             Override target triple.
  ZHANGSHU_MACOS_PYTHON             Override Python path.
  ZHANGSHU_MACOS_CODESIGN_IDENTITY  Override codesign identity.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET="${2:?--target requires a value}"
      shift 2
      ;;
    --python)
      PYTHON_BIN="${2:?--python requires a path}"
      shift 2
      ;;
    --codesign)
      CODESIGN_IDENTITY="${2:?--codesign requires an identity}"
      shift 2
      ;;
    --skip-deps)
      SKIP_DEPS=1
      shift
      ;;
    --skip-frontend)
      SKIP_FRONTEND=1
      shift
      ;;
    --skip-backend)
      SKIP_BACKEND=1
      shift
      ;;
    --skip-smoke)
      SKIP_SMOKE=1
      shift
      ;;
    --skip-tauri)
      SKIP_TAURI=1
      shift
      ;;
    --skip-sign)
      SKIP_SIGN=1
      shift
      ;;
    --skip-dmg)
      SKIP_DMG=1
      shift
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

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "[ERROR] macOS packaging must run on macOS." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "[ERROR] npm is required." >&2
  exit 1
fi

if ! command -v cargo >/dev/null 2>&1; then
  echo "[ERROR] Rust/cargo is required." >&2
  exit 1
fi

if ! command -v hdiutil >/dev/null 2>&1; then
  echo "[ERROR] hdiutil is required to create dmg files." >&2
  exit 1
fi

read_json_version() {
  /usr/bin/python3 - "$1" <<'PY'
import json
import sys
from pathlib import Path

print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["version"])
PY
}

read_cargo_version() {
  /usr/bin/python3 - "$1" <<'PY'
import re
import sys
from pathlib import Path

for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    match = re.match(r'\s*version\s*=\s*"([^"]+)"', line)
    if match:
        print(match.group(1))
        raise SystemExit(0)
raise SystemExit("version not found")
PY
}

APP_VERSION="$(read_json_version "$FRONTEND_DIR/package.json")"
CARGO_VERSION="$(read_cargo_version "$TAURI_DIR/Cargo.toml")"
TAURI_VERSION="$(read_json_version "$TAURI_DIR/tauri.conf.json")"

if [[ "$APP_VERSION" != "$CARGO_VERSION" || "$APP_VERSION" != "$TAURI_VERSION" ]]; then
  echo "[ERROR] Version mismatch: package.json=$APP_VERSION Cargo.toml=$CARGO_VERSION tauri.conf.json=$TAURI_VERSION" >&2
  exit 1
fi

echo "============================================"
echo "  Zhangshu macOS package build"
echo "============================================"
echo "[INFO] Version: $APP_VERSION"
echo "[INFO] Target:  $TARGET"

if [[ ! -x "$PYTHON_BIN" ]]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 is required to create backend/.venv." >&2
    exit 1
  fi
  echo "[INFO] Creating backend venv..."
  python3 -m venv "$BACKEND_DIR/.venv"
  PYTHON_BIN="$BACKEND_DIR/.venv/bin/python"
fi

if [[ "$SKIP_DEPS" -eq 0 ]]; then
  echo "[INFO] Installing backend packaging dependencies..."
  "$PYTHON_BIN" -m pip install --upgrade pip
  "$PYTHON_BIN" -m pip install -r "$BACKEND_DIR/requirements.txt" pyinstaller
fi

if [[ "$SKIP_FRONTEND" -eq 0 ]]; then
  echo "[INFO] Building frontend..."
  (
    cd "$FRONTEND_DIR"
    VITE_API_BASE_URL="http://127.0.0.1:8765" npm run build
  )
fi

BACKEND_DIST_ROOT="$TAURI_DIR/binaries/macos-$TARGET"
BACKEND_BUNDLE_DIR="$BACKEND_DIST_ROOT/zhangshu-backend"
BACKEND_EXE="$BACKEND_BUNDLE_DIR/zhangshu-backend"

if [[ "$SKIP_BACKEND" -eq 0 ]]; then
  echo "[INFO] Building backend sidecar with PyInstaller..."
  rm -rf "$BACKEND_BUNDLE_DIR"
  "$PYTHON_BIN" -m PyInstaller \
    --noconfirm \
    --clean \
    --onedir \
    --name zhangshu-backend \
    --distpath "$BACKEND_DIST_ROOT" \
    --workpath "$PROJECT_ROOT/build/pyinstaller-macos-$TARGET" \
    --specpath "$PROJECT_ROOT/build/spec-macos-$TARGET" \
    --hidden-import app.api.cloud \
    --hidden-import app.api.cloud_sync \
    --hidden-import app.api.knowledge_embedding \
    --hidden-import app.api.knowledge_retrieval \
    --hidden-import app.api.rag \
    "$BACKEND_DIR/tauri_sidecar_main.py"
  chmod +x "$BACKEND_EXE"
fi

if [[ ! -x "$BACKEND_EXE" ]]; then
  echo "[ERROR] Backend sidecar was not produced: $BACKEND_EXE" >&2
  exit 1
fi

if [[ "$SKIP_SMOKE" -eq 0 ]]; then
  "$SCRIPT_DIR/smoke_packaged_backend_macos.sh" --backend-exe "$BACKEND_EXE"
fi

if [[ "$SKIP_TAURI" -eq 0 ]]; then
  echo "[INFO] Building Tauri .app..."
  (
    cd "$FRONTEND_DIR"
    npx tauri build --target "$TARGET" --bundles app
  )
fi

APP_BUNDLE_DIR="$TAURI_DIR/target/$TARGET/release/bundle/macos"
if [[ ! -d "$APP_BUNDLE_DIR" ]]; then
  APP_BUNDLE_DIR="$TAURI_DIR/target/release/bundle/macos"
fi

APP_PATH="$(find "$APP_BUNDLE_DIR" -maxdepth 1 -name "*.app" -type d | head -n 1 || true)"
if [[ -z "$APP_PATH" || ! -d "$APP_PATH" ]]; then
  echo "[ERROR] Could not find built .app under: $APP_BUNDLE_DIR" >&2
  exit 1
fi

RESOURCES_DIR="$APP_PATH/Contents/Resources"
mkdir -p "$RESOURCES_DIR"

echo "[INFO] Installing sidecar resources into app bundle..."
rm -rf "$RESOURCES_DIR/zhangshu-backend" "$RESOURCES_DIR/frontend-dist"
cp -R "$BACKEND_BUNDLE_DIR" "$RESOURCES_DIR/zhangshu-backend"
cp -R "$FRONTEND_DIR/dist" "$RESOURCES_DIR/frontend-dist"
chmod +x "$RESOURCES_DIR/zhangshu-backend/zhangshu-backend"

if [[ "$SKIP_SIGN" -eq 0 ]]; then
  if ! command -v codesign >/dev/null 2>&1; then
    echo "[ERROR] codesign is required unless --skip-sign is used." >&2
    exit 1
  fi
  echo "[INFO] Signing app bundle with identity: $CODESIGN_IDENTITY"
  codesign --force --deep --sign "$CODESIGN_IDENTITY" "$APP_PATH"
fi

MAC_RELEASE_DIR="$RELEASE_DIR/macos-$TARGET"
mkdir -p "$MAC_RELEASE_DIR"

if [[ "$SKIP_DMG" -eq 0 ]]; then
  DMG_PATH="$MAC_RELEASE_DIR/Zhangshu_${APP_VERSION}_macos_arm64.dmg"
  echo "[INFO] Creating dmg: $DMG_PATH"
  rm -f "$DMG_PATH"
  hdiutil create -volname "Zhangshu" -srcfolder "$APP_PATH" -ov -format UDZO "$DMG_PATH"
fi

echo "============================================"
echo "  macOS package build complete"
echo "============================================"
echo "[OK] App: $APP_PATH"
if [[ "$SKIP_DMG" -eq 0 ]]; then
  echo "[OK] DMG: $DMG_PATH"
fi
