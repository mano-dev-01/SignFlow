# SignFlow macOS App Builder

This folder contains the macOS packaging pipeline that builds `SignFlow.app` and `SignFlow.dmg` from the code under `Code/Mac`.

## Files

- `build_signflow_app.sh`: one-command app build script.
- `build_signflow_dmg.sh`: DMG packaging script for `SignFlow.app`.
- `signflow_remote.spec`: PyInstaller build spec for the app bundle.
- `signflow_app_bootstrap.py`: runtime bootstrap and compatibility layer used as app entrypoint.

## Build App

```bash
cd /Users/test/SignFlow
./Code/Mac/mac_builder/build_signflow_app.sh --clean
```

App output:

- `/Users/test/SignFlow/Code/Mac/mac_builder/dist/SignFlow.app`

## Build DMG

```bash
cd /Users/test/SignFlow
./Code/Mac/mac_builder/build_signflow_dmg.sh --clean
```

DMG output:

- `/Users/test/SignFlow/Code/Mac/mac_builder/dist/SignFlow.dmg`

## Launch App

```bash
open /Users/test/SignFlow/Code/Mac/mac_builder/dist/SignFlow.app
```

Launch with custom server URL:

```bash
open /Users/test/SignFlow/Code/Mac/mac_builder/dist/SignFlow.app --args --server https://mano-dev-01-signflow-inference.hf.space
```

## Notes

- This builder is intentionally isolated to `Code/Mac/mac_builder`.
- The builder always uses Python from `Code/Mac/.venv-build`.
- PyInstaller cache/work output is forced under `Code/Mac/mac_builder` (`.pyinstaller/`, `build/`, `dist/`).
- Camera and microphone usage strings are embedded in the app plist through the spec file.
- The bootstrap includes a compatibility patch for older source snapshots where `RemoteOverlayWindow` references `_should_flip_input()`.
