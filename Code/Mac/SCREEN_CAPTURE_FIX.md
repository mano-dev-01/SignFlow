# Screen Capture Region Selection Fix

## Problem
When selecting a screen region to capture, the overlay was capturing a random area instead of the selected region. This issue occurs on macOS with Retina displays due to DPI scaling.

## Root Cause
- macOS Retina displays have a device pixel ratio (usually 2.0) that scales logical coordinates to physical coordinates
- Qt uses logical coordinates, but `mss` library expects physical coordinates  
- The region coordinates were not being properly validated before being passed to the capture thread
- No debug logging made it hard to identify the problem

## Solution Applied

### 1. **Added Retina Display Scaling Validation** (`overlay_window.py`)
```python
def _set_capture_state_from_rect(self, rect: QRect):
    # For macOS, handle Retina display scaling properly
    if sys.platform == "darwin":
        rect = self._rect_to_physical(rect)
        print(f"[DEBUG] macOS Retina scaling applied...")
    # Set region with scaled coordinates
```

### 2. **Added Comprehensive Region Validation** (`overlay_capture.py`)
```python
def run(self):
    # Validate region has required keys
    required_keys = {"x", "y", "width", "height"}
    if not all(key in self._region for key in required_keys):
        print(f"[ERROR] Invalid region dict: {self._region}")
        return
    
    # Validate dimensions
    if width <= 0 or height <= 0:
        print(f"[ERROR] Invalid dimensions: {width}x{height}")
        return
```

### 3. **Added Debug Logging**
- Log when region is set
- Log when capture starts with coordinates
- Log frame count every 100 frames
- Log any errors in capturing

### 4. **Added Better Error Handling**
- Check if mss.grab() returns None
- Validate region dictionary structure
- Verify dimensions are positive

## Testing the Fix

```bash
cd /Users/test/SignFlow/Code/Mac
./run_signflow.sh

# Once overlay starts:
# 1. Click "Crop" button in overlay UI
# 2. Draw a rectangle on the screen to select capture area
# 3. Release mouse to confirm selection
# 4. The overlay should capture ONLY the selected area
# 5. Check console for debug messages confirming the region
```

## What to Look For

When selecting a region, you should see console output like:
```
[overlay_window] Starting screen capture with region: {'x': 0, 'y': 0, 'width': 1920, 'height': 1080}
[DEBUG] macOS Retina scaling applied: 0, 0, 3840, 2160
[DEBUG] Capture region set: {'x': 0, 'y': 0, 'width': 3840, 'height': 2160}
[ScreenCaptureThread] macOS screen capture: x=0, y=0, w=3840, h=2160
[ScreenCaptureThread] Captured 100 frames
```

## Troubleshooting

### Issue: Still capturing wrong area
1. Check console output for region dimensions
2. Verify dimensions match your selected area
3. On Retina displays, physical dimensions should be ~2x logical dimensions
4. Run with debug output enabled

### Issue: Capture is black/blank
1. Ensure selected region is not off-screen
2. Check that width and height are > 0
3. Try selecting a smaller, more obvious region first

### Issue: Capture is very small/large
1. This usually indicates scaling issue
2. Check if physical coordinates are correct
3. Try adjusting window position and reselecting

## Files Modified
- `overlay_window.py` - Added debug logging and validation
- `overlay_capture.py` - Added comprehensive region validation and logging

## Next Steps
If you continue to have issues:
1. Take a screenshot showing the selected area
2. Share the console debug output
3. Report the display resolution and DPI scaling factor
4. Description of what area is actually being captured instead
