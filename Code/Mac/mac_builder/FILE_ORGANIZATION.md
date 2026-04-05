# File Organization Summary

## Mac Build & Configuration Files (`Code/Mac/mac_builder/`)
Files related to Mac app building and packaging:
- `SignFlow.spec` - PyInstaller specification for building macOS app
- `run_with_remote_model.sh` - Script to launch app with remote model enabled
- `REMOTE_MODEL_SETUP.md` - Documentation for remote model inference setup

## Mac Runtime Files (`Code/Mac/Overlay/`)
Main application runtime files for macOS:
- `remote_inference_client.py` - Client for remote model inference API
- `overlay_hand_tracking.py` - MediaPipe hand tracking integration
- `model_loader.py` - Model loading logic
- `overlay_remote.py` - Remote overlay functionality
- Other standard overlay files (capture, panels, window, etc.)

## File Organization by Purpose

### Build & Deployment
```
Code/Mac/mac_builder/
├── SignFlow.spec              (PyInstaller config)
├── run_with_remote_model.sh   (Launch script)
└── REMOTE_MODEL_SETUP.md      (Setup documentation)
```

### Runtime & Application
```
Code/Mac/Overlay/
├── remote_inference_client.py (Remote model client)
├── overlay_hand_tracking.py   (Hand detection)
├── model_loader.py            (Model loading)
└── [other overlay modules]
```

### Root Level (Repository)
```
/Users/test/SignFlow/
├── SignFlow.spec              (Copied to mac_builder/)
├── run_with_remote_model.sh   (Copied to mac_builder/)
└── REMOTE_MODEL_SETUP.md      (Copied to mac_builder/)
```

## Structure Complete ✓

All Mac-specific files are now organized in their appropriate folders:
- **Build files** → `Code/Mac/mac_builder/` (DMG, app building, and configuration)
- **Runtime files** → `Code/Mac/Overlay/` (Application code that runs on macOS)
