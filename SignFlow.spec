# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = []
hiddenimports += collect_submodules('signflow_overlay')
hiddenimports += collect_submodules('Model_inference')


a = Analysis(
    ['Code/Mac/Overlay/overlay_remote.py'],
    pathex=['Code/Mac/Overlay', 'Code/Mac'],
    binaries=[],
    datas=[('Code/Mac/Overlay/default_settings.json', '.'), ('Code/Mac/Model_inference', 'Model_inference'), ('Code/Mac/Models', 'Models')],
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
    bundle_identifier='com.signflow.overlay',
)
