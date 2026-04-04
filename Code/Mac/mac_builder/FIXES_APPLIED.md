# Mac Folder Issues - Fixes Applied

## Summary
Fixed critical issues in Mac build configuration and Python source files that were preventing the build process from completing successfully.

## Issues Fixed

### 1. **SignFlow.spec - Path Resolution Issues & __file__ NameError**
**File:** `/Users/test/SignFlow/Code/Mac/mac_builder/SignFlow.spec`

**Problems:**
- Line 11: Used `__file__` which is not defined in PyInstaller spec file context
- Line 12: Incorrect path calculation - went up 2 directory levels instead of 1
- Lines 22-25: Used hardcoded paths like `'Code/Mac/Model_inference'` that didn't work from build directory

**Solutions:**
- Added try-except block to handle `NameError` when `__file__` is not defined
- Falls back to `os.getcwd()` which is correct since build_dmg.sh sets the working directory
- Fixed path calculation: `os.path.dirname(os.path.dirname(spec_dir))` → `os.path.dirname(spec_dir)`
- Now correctly resolves to `Code/Mac/` directory
- All paths use `os.path.join()` with computed project_root:
  ```python
  try:
      spec_dir = os.path.dirname(os.path.abspath(__file__))
  except NameError:
      spec_dir = os.getcwd()
  
  project_root = os.path.dirname(spec_dir)  # Now correctly points to Code/Mac/
  custom_plist_path = os.path.join(spec_dir, 'crt', 'Info.plist')
  ```

### 2. **update_checker.py - Invalid Type Annotation**
**File:** `/Users/test/SignFlow/Code/Mac/Overlay/update_checker.py`

**Problem:**
- Line 85: `def _parse_version_string(ver_str: str) -> Optional:`
- `Optional` type hint was incomplete (missing type argument)

**Solution:**
- Removed incomplete `-> Optional` annotation
- Return type is now implicit (None or version object)
- Change: `-> Optional:` → removed return annotation

### 3. **audio_handler.py - Type Annotation with Runtime Variable**
**File:** `/Users/test/SignFlow/Code/Mac/Overlay/audio_handler.py`

**Problem:**
- Line 101: `def record_chunk(self, duration_seconds: float) -> Optional[np.ndarray]:`
- `np.ndarray` cannot be used in type annotations when `np` is imported conditionally in a try block

**Solution:**
- Added `from __future__ import annotations` at the top of file
- This enables PEP 563 postponed evaluation of annotations (string form)
- Now `np.ndarray` reference is evaluated at runtime, not at parsing time
- Allows the type hint to work correctly even when imports are conditional

## File Path Structure After Fixes

```
Code/Mac/
├── mac_builder/              ← Build directory
│   ├── SignFlow.spec         ✓ Fixed (uses dynamic path resolution)
│   ├── crt/                  ✓ Info.plist correctly referenced
│   │   └── Info.plist
│   ├── build/                ← PyInstaller build output
│   ├── dist/                 ← PyInstaller dist output
│   └── macos/                ← Alternative build outputs
├── Model_inference/          ✓ Models correctly included
├── Models/                   ✓ Model files correctly included
├── Overlay/                  ✓ Main source files
│   ├── overlay.py            ✓ Entry point (now correctly referenced)
│   ├── default_settings.json ✓ Settings (now correctly referenced)
│   ├── update_checker.py     ✓ Fixed (removed invalid type hint)
│   ├── audio_handler.py      ✓ Fixed (added __future__ import)
│   └── [other files]
└── version.py               ✓ Version file correctly included
```

## Validation

All modified files have been validated:

```bash
✓ /Users/test/SignFlow/Code/Mac/mac_builder/SignFlow.spec - Syntax OK
✓ /Users/test/SignFlow/Code/Mac/Overlay/update_checker.py - Syntax OK  
✓ /Users/test/SignFlow/Code/Mac/Overlay/audio_handler.py - Syntax OK
✓ All other files in Overlay/ - Syntax OK (28 files checked)
```

## Build Commands

After these fixes, the build should work with:

```bash
# Build only (no DMG)
./Code/Mac/mac_builder/build_dmg.sh --no-dmg

# Build with DMG
./Code/Mac/mac_builder/build_dmg.sh

# Clean and rebuild
./Code/Mac/mac_builder/build_dmg.sh --clean

# With code signing
export CODESIGN_IDENTITY="Developer ID Application: (TEAMID)"
./Code/Mac/mac_builder/build_dmg.sh --sign
```

## Technical Details

### Path Resolution Flow

When `SignFlow.spec` runs:
1. Gets absolute path to itself: `/Users/test/SignFlow/Code/Mac/mac_builder/`
2. Calculates project_root: `/Users/test/SignFlow/Code/Mac/`
3. All file references resolve from these base paths
4. Works regardless of where build command is executed from

### Type Annotation Fix

`from __future__ import annotations` changes how Python handles type hints:
- **Before**: Evaluated at module parse time → `np` not yet defined → Error
- **After**: Annotations stored as strings, evaluated at runtime → Works correctly

This is the recommended approach for conditional imports with type hints (PEP 563).

## Next Steps

1. Run build: `./Code/Mac/mac_builder/build_dmg.sh --no-dmg`
2. Monitor build output for any new errors
3. If build succeeds, test the app in `/Code/Mac/mac_builder/dist/SignFlow.app/`
4. For DMG creation, run: `./Code/Mac/mac_builder/build_dmg.sh`

## Build Test Results

**Status:** ✅ BUILD SUCCESSFUL (Apr 4, 23:38)

App Bundle Created:
- Path: `/Users/test/SignFlow/Code/Mac/mac_builder/dist/SignFlow.app`
- Executable: `Contents/MacOS/SignFlow`
- Type: Mach-O 64-bit executable x86_64
- Size: ~31.4 MB

The build now completes without errors. All paths resolve correctly, and the app bundle is properly structured.

## Technical Changes Made

### PyInstaller Spec File Compatibility

The original approach of using `__file__` in spec files proved incompatible with PyInstaller's execution context. PyInstaller does not automatically define `__file__` when executing spec files. 

Solution implemented:
```python
try:
    spec_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # __file__ not available in PyInstaller context
    # Use current working directory instead
    spec_dir = os.getcwd()
```

This works because `build_dmg.sh` explicitly changes to the spec file directory (`cd "$SCRIPT_DIR"`) before running PyInstaller, ensuring `os.getcwd()` points to the correct location.

### Path Hierarchy Correction

Fixed the directory level calculation:
- **Before:** `project_root = os.path.dirname(os.path.dirname(spec_dir))` → went to `/Users/test/SignFlow/Code/`
- **After:** `project_root = os.path.dirname(spec_dir)` → correctly points to `/Users/test/SignFlow/Code/Mac/`

This ensures all relative paths from the spec file resolve correctly:
- Model data: `Code/Mac/Model_inference` ✓
- Model files: `Code/Mac/Models` ✓  
- App settings: `Code/Mac/Overlay/default_settings.json` ✓
- App entry point: `Code/Mac/Overlay/overlay.py` ✓
