# -*- mode: python ; coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs


SPEC_DIR = Path(SPECPATH).resolve()
MAC_DIR = SPEC_DIR.parent
OVERLAY_DIR = MAC_DIR / "Overlay"
MODEL_DIR = MAC_DIR / "Model_inference"
MODELS_DIR = MAC_DIR / "Models"

BOOTSTRAP = SPEC_DIR / "signflow_app_bootstrap.py"

block_cipher = None


def _data(src: Path, dest: str):
    return (str(src), dest)


datas = [
    _data(OVERLAY_DIR / "default_settings.json", "."),
    _data(MODEL_DIR / "class_map.json", "Model_inference"),
    _data(MODELS_DIR, "Models"),
]

# Ensure third-party assets needed at runtime are bundled.
datas += collect_data_files("mediapipe")
datas += collect_data_files("cv2")

binaries = []
binaries += collect_dynamic_libs("mediapipe")
binaries += collect_dynamic_libs("cv2")

hiddenimports = [
    "PyQt5.sip",
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    "PyQt5.QtWidgets",
    "objc",
    "AppKit",
    "Foundation",
    "Quartz",
]

a = Analysis(
    [str(BOOTSTRAP)],
    pathex=[str(MAC_DIR), str(OVERLAY_DIR), str(MODEL_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    [],
    name="SignFlow",
    debug=False,
    bootloader_ignore_signals=False,
    exclude_binaries=True,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SignFlow",
)

app = BUNDLE(
    coll,
    name="SignFlow.app",
    icon=None,
    bundle_identifier="com.signflow.overlay",
    info_plist={
        "CFBundleName": "SignFlow",
        "CFBundleDisplayName": "SignFlow",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1",
        "NSCameraUsageDescription": "SignFlow uses your camera to detect hand landmarks for sign recognition.",
        "NSMicrophoneUsageDescription": "SignFlow can use your microphone for optional voice input.",
    },
)
