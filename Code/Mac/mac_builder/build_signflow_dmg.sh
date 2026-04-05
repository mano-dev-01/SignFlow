#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$SCRIPT_DIR/dist"
APP_PATH="$DIST_DIR/SignFlow.app"
DMG_PATH="$DIST_DIR/SignFlow.dmg"
STAGING_DIR="$SCRIPT_DIR/.dmg_staging"
VOLUME_NAME="SignFlow"

if [[ -n "${1:-}" && ("${1}" == "-h" || "${1}" == "--help") ]]; then
  echo "Usage: $(basename "$0") [--clean] [--skip-app-build]"
  echo "Creates SignFlow.dmg from dist/SignFlow.app"
  echo ""
  echo "Options:"
  echo "  --clean           Remove old dmg and staging dir before packaging"
  echo "  --skip-app-build  Fail if app is missing instead of building it"
  exit 0
fi

CLEAN="false"
SKIP_APP_BUILD="false"
for arg in "$@"; do
  case "$arg" in
    --clean)
      CLEAN="true"
      ;;
    --skip-app-build)
      SKIP_APP_BUILD="true"
      ;;
    *)
      echo "ERROR: Unknown option: $arg"
      exit 1
      ;;
  esac
done

if ! command -v hdiutil >/dev/null 2>&1; then
  echo "ERROR: hdiutil not found. This script must run on macOS."
  exit 1
fi

if [[ "$CLEAN" == "true" ]]; then
  rm -rf "$STAGING_DIR"
  rm -f "$DMG_PATH"
fi

if [[ ! -d "$APP_PATH" ]]; then
  if [[ "$SKIP_APP_BUILD" == "true" ]]; then
    echo "ERROR: App not found at $APP_PATH"
    exit 1
  fi
  "$SCRIPT_DIR/build_signflow_app.sh"
fi

mkdir -p "$DIST_DIR"
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"

cp -R "$APP_PATH" "$STAGING_DIR/"
ln -s /Applications "$STAGING_DIR/Applications"

if [[ -f "$DMG_PATH" ]]; then
  rm -f "$DMG_PATH"
fi

hdiutil create \
  -volname "$VOLUME_NAME" \
  -srcfolder "$STAGING_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

rm -rf "$STAGING_DIR"

echo ""
echo "DMG complete"
echo "DMG: $DMG_PATH"
