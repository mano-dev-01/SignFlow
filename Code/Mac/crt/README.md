# SignFlow macOS Product DMG

Use this to create a product-style DMG (Finder window layout, App + Applications shortcut, branded background/icon, optional signing/notarization).

## 1) Build the app bundle first

Example:

```bash
pyinstaller --noconfirm --clean --windowed \
  --name "SignFlow" \
  --paths Code/Mac/Overlay \
  --paths Code/Mac \
  --collect-submodules signflow_overlay \
  --collect-submodules Model_inference \
  --add-data "Code/Mac/Overlay/default_settings.json:." \
  --add-data "Code/Mac/Model_inference:Model_inference" \
  --add-data "Code/Mac/Models:Models" \
  --osx-bundle-identifier "com.signflow.overlay" \
  Code/Mac/Overlay/overlay_remote.py
```

This should produce:

`dist/SignFlow.app`

## 2) Branding source (auto)

By default, branding is auto-detected from your landing page logo:

`Code/Website-LandingPage/assets/logo.png`

If DMG assets are missing, the script auto-generates:

- `Code/Mac/crt/assets/generated/SignFlow.icns`
- `Code/Mac/crt/assets/generated/dmg-background.png`

You can override with:

```bash
export BRAND_LOGO_PATH="/custom/path/logo.png"
```

## 3) (Optional) Manual branding assets

Place files under:

`Code/Mac/crt/assets/`

- `dmg-background.png` (recommended resolution around 740x440)
- `SignFlow.icns` (volume icon)

If these files do not exist, the script auto-generates branded assets from your landing-page logo.

## 4) Build product-style DMG

```bash
./Code/Mac/crt/make_product_dmg.sh
```

Output:

`dist/SignFlow-mac.dmg`

## 5) (Optional) Signed + notarized release DMG

```bash
export CODESIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)"
export NOTARY_PROFILE="your-notarytool-profile"
./Code/Mac/crt/make_product_dmg.sh
```

Optional entitlements:

```bash
export ENTITLEMENTS_PATH="Code/Mac/crt/entitlements.plist"
```

## Notes

- The script requires macOS (`hdiutil`, Finder/AppleScript).
- Install Xcode command line tools for `codesign`, `xcrun`, `notarytool`, `stapler`.
