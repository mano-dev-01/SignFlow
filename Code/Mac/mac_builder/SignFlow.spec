# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs
import os
import plistlib

# ============================================
# LOAD CUSTOM INFO.PLIST
# ============================================

custom_plist_path = 'Code/Mac/crt/Info.plist'
with open(custom_plist_path, 'rb') as f:
    custom_plist = plistlib.load(f)

# ============================================
# DATA & MODELS
# ============================================

datas = [
    ('Code/Mac/Model_inference', 'Model_inference'),
    ('Code/Mac/Models', 'Models'),
    ('Code/Common/Overlay/default_settings.json', '.'),
    ('Code/Mac/version.py', '.'),  # Version file
]

# ============================================
# BINARIES
# ============================================

binaries = []

# Collect MediaPipe binaries
tmp_ret = collect_all('mediapipe')
datas += tmp_ret[0]
binaries += tmp_ret[1]

# ============================================
# HIDDEN IMPORTS
# ============================================

hiddenimports = [
    # Core computer vision & ML
    'cv2',
    'mediapipe',
    'torch',
    'torch.utils.data',
    'torch.nn',
    'torch.optim',
    
    # Audio
    'sounddevice',
    'sounddevice._sounddevice',
    
    # Screen capture (Quartz)
    'Quartz',
    'Quartz.CoreGraphics',
    'AppKit',
    'Foundation',
    'objc',
    
    # Update system
    'requests',
    'requests.adapters',
    'requests.packages',
    'packaging',
    'packaging.version',
    'packaging.tags',
    'packaging.specifiers',
    
    # Utilities
    'joblib',
    'sklearn',
    'numpy',
    'mss',
    'flask',
    'flask_cors',
    'webbrowser',
]

# Collect all mediapipe sub-modules
tmp_ret = collect_all('mediapipe')
hiddenimports += tmp_ret[2]


a = Analysis(
    ['Code/Mac/Overlay/overlay.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SignFlow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
    upx=True,
    upx_exclude=[],
    name='SignFlow',
)
app = BUNDLE(
    coll,
    name='SignFlow.app',
    icon=None,
    bundle_identifier=None,
    info_plist=custom_plist,
)
