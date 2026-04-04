# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs
import os
import plistlib

# ============================================
# LOAD CUSTOM INFO.PLIST
# ============================================

# Get the directory where this spec file is located
# In PyInstaller context, __file__ may not be defined, so we use the current directory
# (the build_dmg.sh script changes to the spec_dir before running PyInstaller)
try:
    spec_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    spec_dir = os.getcwd()

# project_root should be the Code/Mac directory (one level up from mac_builder)
project_root = os.path.dirname(spec_dir)

custom_plist_path = os.path.join(spec_dir, 'crt', 'Info.plist')
with open(custom_plist_path, 'rb') as f:
    custom_plist = plistlib.load(f)

# ============================================
# DATA & MODELS
# ============================================

datas = [
    (os.path.join(project_root, 'Model_inference'), 'Model_inference'),
    (os.path.join(project_root, 'Models'), 'Models'),
    (os.path.join(project_root, 'Overlay', 'default_settings.json'), '.'),
    (os.path.join(project_root, 'version.py'), '.'),  # Version file
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
    [os.path.join(project_root, 'Overlay', 'overlay.py')],
    pathex=[os.path.join(project_root, 'Overlay')],
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
