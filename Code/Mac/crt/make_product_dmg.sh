#!/usr/bin/env bash
set -euo pipefail

# Product-style DMG builder for SignFlow macOS app bundles.
#
# Usage:
#   ./Code/Mac/crt/make_product_dmg.sh [path/to/SignFlow.app] [output.dmg]
#
# Optional env vars:
#   VOLUME_NAME="SignFlow"
#   BRAND_LOGO_PATH="Code/Website-LandingPage/assets/logo.png"
#   BG_IMAGE_PATH="Code/Mac/crt/assets/dmg-background.png"
#   APP_ICON_ICNS_PATH="Code/Mac/crt/assets/SignFlow.icns"
#   CODESIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)"
#   ENTITLEMENTS_PATH="Code/Mac/crt/entitlements.plist"
#   NOTARY_PROFILE="notarytool-profile-name"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEFAULT_APP_PATH="$ROOT_DIR/dist/SignFlow.app"
DEFAULT_DMG_PATH="$ROOT_DIR/dist/SignFlow-mac.dmg"
DEFAULT_BG_PATH="$ROOT_DIR/Code/Mac/crt/assets/dmg-background.png"
DEFAULT_ICON_PATH="$ROOT_DIR/Code/Mac/crt/assets/SignFlow.icns"
DEFAULT_LOGO_PATH="$ROOT_DIR/Code/Website-LandingPage/assets/logo.png"
GENERATED_ASSETS_DIR="$ROOT_DIR/Code/Mac/crt/assets/generated"

APP_PATH="${1:-$DEFAULT_APP_PATH}"
OUTPUT_DMG="${2:-$DEFAULT_DMG_PATH}"
VOLUME_NAME="${VOLUME_NAME:-SignFlow}"
BRAND_LOGO_PATH="${BRAND_LOGO_PATH:-$DEFAULT_LOGO_PATH}"
BG_IMAGE_PATH="${BG_IMAGE_PATH:-$DEFAULT_BG_PATH}"
APP_ICON_ICNS_PATH="${APP_ICON_ICNS_PATH:-$DEFAULT_ICON_PATH}"
CODESIGN_IDENTITY="${CODESIGN_IDENTITY:-}"
ENTITLEMENTS_PATH="${ENTITLEMENTS_PATH:-}"
NOTARY_PROFILE="${NOTARY_PROFILE:-}"

if ! command -v hdiutil >/dev/null 2>&1; then
  echo "[ERROR] hdiutil not found (macOS required)."
  exit 1
fi

if ! command -v sips >/dev/null 2>&1; then
  echo "[ERROR] sips not found (macOS image tool is required)."
  exit 1
fi

if [[ ! -d "$APP_PATH" ]]; then
  echo "[ERROR] App bundle not found: $APP_PATH"
  exit 1
fi

APP_BUNDLE_NAME="$(basename "$APP_PATH")"
APP_NAME="${APP_BUNDLE_NAME%.app}"
APP_PARENT_DIR="$(cd "$(dirname "$APP_PATH")" && pwd)"
APP_ABS_PATH="$APP_PARENT_DIR/$APP_BUNDLE_NAME"
OUTPUT_DMG_PARENT="$(cd "$(dirname "$OUTPUT_DMG")" && pwd)"
OUTPUT_DMG_ABS_PATH="$OUTPUT_DMG_PARENT/$(basename "$OUTPUT_DMG")"

ensure_brand_assets_from_logo() {
  local logo_path="$1"
  local desired_bg="$2"
  local desired_icns="$3"

  if [[ ! -f "$logo_path" ]]; then
    return 0
  fi

  mkdir -p "$GENERATED_ASSETS_DIR"
  local generated_bg="$GENERATED_ASSETS_DIR/dmg-background.png"
  local generated_icns="$GENERATED_ASSETS_DIR/SignFlow.icns"

  if [[ ! -f "$desired_icns" ]]; then
    generate_icns_from_logo "$logo_path" "$generated_icns"
    if [[ -f "$generated_icns" ]]; then
      APP_ICON_ICNS_PATH="$generated_icns"
      echo "[INFO] Using generated icon: $APP_ICON_ICNS_PATH"
    fi
  fi

  if [[ ! -f "$desired_bg" ]]; then
    generate_dmg_background "$logo_path" "$generated_bg"
    if [[ -f "$generated_bg" ]]; then
      BG_IMAGE_PATH="$generated_bg"
      echo "[INFO] Using generated DMG background: $BG_IMAGE_PATH"
    fi
  fi
}

generate_icns_from_logo() {
  local logo_path="$1"
  local output_icns="$2"

  if ! command -v iconutil >/dev/null 2>&1; then
    echo "[WARN] iconutil not found; skipping auto icon generation."
    return 0
  fi

  local iconset_dir
  iconset_dir="$(mktemp -d "/tmp/signflow-iconset.XXXXXX.iconset")"

  if ! sips -s format png "$logo_path" --out "$iconset_dir/source.png" >/dev/null 2>&1; then
    rm -rf "$iconset_dir" || true
    return 0
  fi

  sips -z 16 16 "$iconset_dir/source.png" --out "$iconset_dir/icon_16x16.png" >/dev/null
  sips -z 32 32 "$iconset_dir/source.png" --out "$iconset_dir/icon_16x16@2x.png" >/dev/null
  sips -z 32 32 "$iconset_dir/source.png" --out "$iconset_dir/icon_32x32.png" >/dev/null
  sips -z 64 64 "$iconset_dir/source.png" --out "$iconset_dir/icon_32x32@2x.png" >/dev/null
  sips -z 128 128 "$iconset_dir/source.png" --out "$iconset_dir/icon_128x128.png" >/dev/null
  sips -z 256 256 "$iconset_dir/source.png" --out "$iconset_dir/icon_128x128@2x.png" >/dev/null
  sips -z 256 256 "$iconset_dir/source.png" --out "$iconset_dir/icon_256x256.png" >/dev/null
  sips -z 512 512 "$iconset_dir/source.png" --out "$iconset_dir/icon_256x256@2x.png" >/dev/null
  sips -z 512 512 "$iconset_dir/source.png" --out "$iconset_dir/icon_512x512.png" >/dev/null
  sips -z 1024 1024 "$iconset_dir/source.png" --out "$iconset_dir/icon_512x512@2x.png" >/dev/null

  iconutil -c icns "$iconset_dir" -o "$output_icns" >/dev/null 2>&1 || true
  rm -rf "$iconset_dir" || true
}

generate_dmg_background() {
  local logo_path="$1"
  local output_png="$2"

  python3 - "$logo_path" "$output_png" <<'PY' || true
import sys
from pathlib import Path

logo = Path(sys.argv[1])
out = Path(sys.argv[2])
out.parent.mkdir(parents=True, exist_ok=True)

try:
    from PIL import Image, ImageDraw, ImageFilter
except Exception:
    try:
        import cv2
        import numpy as np
    except Exception:
        # Last fallback: use a plain resized logo as the background.
        import subprocess
        subprocess.run(
            ["sips", "-z", "440", "740", str(logo), "--out", str(out)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        raise SystemExit(0)

    w, h = 740, 440
    gradient = np.zeros((h, w, 3), dtype=np.uint8)
    top = np.array([44, 24, 18], dtype=np.float32)      # BGR
    bottom = np.array([92, 54, 30], dtype=np.float32)   # BGR
    for y in range(h):
        t = y / max(1, h - 1)
        gradient[y, :, :] = ((1.0 - t) * top + t * bottom).astype(np.uint8)

    logo_img = cv2.imread(str(logo), cv2.IMREAD_UNCHANGED)
    if logo_img is None:
        cv2.imwrite(str(out), gradient)
        raise SystemExit(0)

    if logo_img.shape[2] == 3:
        alpha = np.full((logo_img.shape[0], logo_img.shape[1], 1), 255, dtype=np.uint8)
        logo_img = np.concatenate([logo_img, alpha], axis=2)

    max_h = int(h * 0.50)
    max_w = int(w * 0.36)
    scale = min(max_w / logo_img.shape[1], max_h / logo_img.shape[0], 1.0)
    new_w = max(1, int(logo_img.shape[1] * scale))
    new_h = max(1, int(logo_img.shape[0] * scale))
    logo_img = cv2.resize(logo_img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    x = 85
    y = (h - new_h) // 2 - 8
    y = max(0, y)
    x2 = min(w, x + new_w)
    y2 = min(h, y + new_h)
    lx = x2 - x
    ly = y2 - y
    if lx > 0 and ly > 0:
        logo_crop = logo_img[:ly, :lx, :]
        alpha = (logo_crop[:, :, 3:4].astype(np.float32) / 255.0)
        bg_crop = gradient[y:y2, x:x2, :].astype(np.float32)
        fg_crop = logo_crop[:, :, :3].astype(np.float32)
        blended = (fg_crop * alpha) + (bg_crop * (1.0 - alpha))
        gradient[y:y2, x:x2, :] = blended.astype(np.uint8)

    cv2.imwrite(str(out), gradient)
    raise SystemExit(0)

w, h = 740, 440
base = Image.new("RGB", (w, h), (18, 24, 44))
draw = ImageDraw.Draw(base)

for y in range(h):
    t = y / max(1, h - 1)
    r = int(18 + (30 - 18) * t)
    g = int(24 + (54 - 24) * t)
    b = int(44 + (92 - 44) * t)
    draw.line([(0, y), (w, y)], fill=(r, g, b))

logo_img = Image.open(logo).convert("RGBA")
max_h = int(h * 0.50)
max_w = int(w * 0.36)
logo_img.thumbnail((max_w, max_h), Image.LANCZOS)

shadow = Image.new("RGBA", logo_img.size, (0, 0, 0, 120))
shadow = shadow.filter(ImageFilter.GaussianBlur(8))
lx = 85
ly = (h - logo_img.size[1]) // 2 - 8
base_rgba = base.convert("RGBA")
base_rgba.alpha_composite(shadow, (lx + 6, ly + 8))
base_rgba.alpha_composite(logo_img, (lx, ly))

overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
odraw = ImageDraw.Draw(overlay)
odraw.rounded_rectangle((390, 130, 700, 310), radius=24, fill=(255, 255, 255, 28))
base_rgba = Image.alpha_composite(base_rgba, overlay)

base_rgba.convert("RGB").save(out, format="PNG", optimize=True)
PY
}

ensure_brand_assets_from_logo "$BRAND_LOGO_PATH" "$BG_IMAGE_PATH" "$APP_ICON_ICNS_PATH"

if [[ -n "$CODESIGN_IDENTITY" ]]; then
  echo "[INFO] Signing app bundle..."
  CODESIGN_ARGS=(
    --force
    --deep
    --timestamp
    --options runtime
    --sign "$CODESIGN_IDENTITY"
  )
  if [[ -n "$ENTITLEMENTS_PATH" ]]; then
    CODESIGN_ARGS+=(--entitlements "$ENTITLEMENTS_PATH")
  fi
  codesign "${CODESIGN_ARGS[@]}" "$APP_ABS_PATH"
  codesign --verify --deep --strict --verbose=2 "$APP_ABS_PATH"
fi

STAGING_DIR="$(mktemp -d "/tmp/signflow-dmg-stage.XXXXXX")"
RW_DMG="$(mktemp "/tmp/signflow-rw.XXXXXX.dmg")"
cleanup() {
  rm -rf "$STAGING_DIR" || true
  rm -f "$RW_DMG" || true
}
trap cleanup EXIT

echo "[INFO] Preparing staging folder..."
cp -R "$APP_ABS_PATH" "$STAGING_DIR/" || {
  echo "[ERROR] Failed to copy app bundle: $APP_ABS_PATH"
  exit 1
}
ln -s /Applications "$STAGING_DIR/Applications"

HAS_BG=0
if [[ -f "$BG_IMAGE_PATH" ]]; then
  echo "[INFO] Applying background image: $BG_IMAGE_PATH"
  mkdir -p "$STAGING_DIR/.background"
  cp "$BG_IMAGE_PATH" "$STAGING_DIR/.background/background.png"
  HAS_BG=1
fi

if [[ -f "$APP_ICON_ICNS_PATH" ]]; then
  echo "[INFO] Applying volume icon: $APP_ICON_ICNS_PATH"
  cp "$APP_ICON_ICNS_PATH" "$STAGING_DIR/.VolumeIcon.icns"
  /usr/bin/SetFile -a C "$STAGING_DIR" 2>/dev/null || true
fi

echo "[INFO] Creating read-write DMG..."
hdiutil create \
  -volname "$VOLUME_NAME" \
  -srcfolder "$STAGING_DIR" \
  -ov \
  -format UDRW \
  "$RW_DMG" >/dev/null

echo "[INFO] Attaching DMG for Finder layout..."
ATTACH_OUTPUT="$(hdiutil attach "$RW_DMG" -readwrite -noverify -noautoopen)"
DEVICE="$(echo "$ATTACH_OUTPUT" | awk '/\/Volumes\// {print $1; exit}')"
MOUNT_POINT="$(echo "$ATTACH_OUTPUT" | awk -F '\t' '/\/Volumes\// {print $NF; exit}')"

if [[ -z "$DEVICE" || -z "$MOUNT_POINT" ]]; then
  echo "[ERROR] Failed to mount DMG for layout."
  echo "$ATTACH_OUTPUT"
  exit 1
fi

if [[ "$HAS_BG" -eq 1 ]]; then
  BG_ALIAS=".background:background.png"
else
  BG_ALIAS=""
fi

osascript <<APPLESCRIPT
tell application "Finder"
  tell disk "$VOLUME_NAME"
    open
    delay 0.5
    set current view of container window to icon view
    set toolbar visible of container window to false
    set statusbar visible of container window to false
    set bounds of container window to {100, 100, 900, 600}
    set icon_opts to the icon view options of container window
    set arrangement of icon_opts to not arranged
    set icon size of icon_opts to 128
    set text size of icon_opts to 14
    if "$BG_ALIAS" is not equal to "" then
      try
        set background picture of icon_opts to file "$BG_ALIAS"
      end try
    end if
    delay 1
    try
      -- Move SignFlow to left side
      set position of item "$APP_BUNDLE_NAME" of container window to {200, 300}
      log "Positioned SignFlow at {200, 300}"
    on error errMsg
      log "Error positioning SignFlow: " & errMsg
    end try
    try
      -- Move Applications to right side
      set position of item "Applications" of container window to {550, 300}
      log "Positioned Applications at {550, 300}"
    on error errMsg
      log "Error positioning Applications: " & errMsg
    end try
    delay 1
    close
    open
    update without registering applications
    delay 1
  end tell
end tell
APPLESCRIPT

sync
hdiutil detach "$DEVICE" -quiet

mkdir -p "$OUTPUT_DMG_PARENT"
rm -f "$OUTPUT_DMG_ABS_PATH"

echo "[INFO] Converting to compressed product DMG..."
hdiutil convert "$RW_DMG" \
  -ov \
  -format UDZO \
  -imagekey zlib-level=9 \
  -o "$OUTPUT_DMG_ABS_PATH" >/dev/null

if [[ -n "$CODESIGN_IDENTITY" ]]; then
  echo "[INFO] Signing DMG..."
  codesign --force --timestamp --sign "$CODESIGN_IDENTITY" "$OUTPUT_DMG_ABS_PATH"
  codesign --verify --verbose=2 "$OUTPUT_DMG_ABS_PATH"
fi

if [[ -n "$NOTARY_PROFILE" ]]; then
  echo "[INFO] Submitting DMG for notarization..."
  xcrun notarytool submit "$OUTPUT_DMG_ABS_PATH" --keychain-profile "$NOTARY_PROFILE" --wait
  echo "[INFO] Stapling notarization ticket..."
  xcrun stapler staple "$OUTPUT_DMG_ABS_PATH"
fi

echo "[DONE] Product DMG created:"
echo "       $OUTPUT_DMG_ABS_PATH"
