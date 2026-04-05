#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAC_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -n "${1:-}" && ("${1}" == "-h" || "${1}" == "--help") ]]; then
  echo "Usage: $(basename "$0") [--clean]"
  echo "Builds SignFlow.app from Code/Mac sources using PyInstaller."
  echo ""
  echo "Options:"
  echo "  --clean    Remove previous build/dist output before building"
  exit 0
fi

CLEAN_BUILD="false"
if [[ "${1:-}" == "--clean" ]]; then
  CLEAN_BUILD="true"
fi

PYTHON_BIN="$MAC_DIR/.venv-build/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "ERROR: Python not found at:"
  echo "  - $PYTHON_BIN"
  exit 1
fi

SPEC_FILE="$SCRIPT_DIR/signflow_remote.spec"
DIST_DIR="$SCRIPT_DIR/dist"
BUILD_DIR="$SCRIPT_DIR/build"
PYI_CONFIG_DIR="$SCRIPT_DIR/.pyinstaller"

if [[ ! -f "$SPEC_FILE" ]]; then
  echo "ERROR: Spec file not found: $SPEC_FILE"
  exit 1
fi

if [[ "$CLEAN_BUILD" == "true" ]]; then
  rm -rf "$DIST_DIR" "$BUILD_DIR" "$PYI_CONFIG_DIR"
fi

echo "========================================"
echo "SignFlow macOS App Builder"
echo "========================================"
echo "Python: $PYTHON_BIN"
echo "Spec:   $SPEC_FILE"
echo ""

if ! "$PYTHON_BIN" -m PyInstaller --version >/dev/null 2>&1; then
  echo "[INFO] PyInstaller not found in venv. Installing..."
  "$PYTHON_BIN" -m pip install pyinstaller
fi

cd "$SCRIPT_DIR"
PYINSTALLER_CONFIG_DIR="$PYI_CONFIG_DIR" \
  "$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --clean \
  --distpath "$DIST_DIR" \
  --workpath "$BUILD_DIR" \
  "$SPEC_FILE"

APP_PATH="$DIST_DIR/SignFlow.app"
if [[ -d "$APP_PATH" ]]; then
  echo ""
  echo "Build complete"
  echo "App: $APP_PATH"
  echo ""
  echo "Run with:"
  echo "  open \"$APP_PATH\""
  echo ""
  echo "Pass args (example):"
  echo "  open \"$APP_PATH\" --args --server https://mano-dev-01-signflow-inference.hf.space"
else
  echo "ERROR: Build finished but app not found at $APP_PATH"
  exit 1
fi
