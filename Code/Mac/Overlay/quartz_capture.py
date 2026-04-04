"""
macOS-native screen capture using Quartz Framework (CGImage).

This replaces mss for more reliable screen capture on macOS, especially for:
- Capturing application windows correctly
- Respecting Screen Recording permissions
- Better Retina display support
"""

import sys
import time
from typing import Optional, Dict, Tuple

import numpy as np

if sys.platform != "darwin":
    raise ImportError("quartz_capture is macOS only")

try:
    from Quartz import (
        CGDisplayBounds,
        CGMainDisplayID,
        CGGetDisplaysWithPoint,
        CGGetDisplaysWithRect,
        CGGetActiveDisplayList,
        CGWindowListCreateImage,
        CGRectMake,
        CGPointMake,
        CGSizeMake,
        CGImageGetWidth,
        CGImageGetHeight,
        CGImageGetBytesPerRow,
        CGImageGetDataProvider,
        CGDataProviderCopyData,
        kCGWindowListOptionOnScreenOnly,
        kCGWindowListExcludeDesktopElements,
    )
    from AppKit import NSAutoreleasePool
    QUARTZ_AVAILABLE = True
except ImportError:
    QUARTZ_AVAILABLE = False
    print("[quartz_capture] WARNING: Quartz framework not available")


class QuartzScreenCapture:
    """
    High-performance macOS screen capture using Quartz Framework.
    """

    def __init__(self):
        if not QUARTZ_AVAILABLE:
            raise RuntimeError("Quartz framework not available. Install: pip install pyobjc-framework-Quartz")
        
        self.pool = NSAutoreleasePool.alloc().init()
        self.main_display = CGMainDisplayID()
        print(f"[QuartzScreenCapture] Initialized with display: {self.main_display}")

    def get_display_bounds(self, display_id: Optional[int] = None) -> Tuple[int, int, int, int]:
        """
        Get bounds (x, y, width, height) of a display.
        """
        if display_id is None:
            display_id = self.main_display
        
        bounds = CGDisplayBounds(display_id)
        return (
            int(bounds.origin.x),
            int(bounds.origin.y),
            int(bounds.size.width),
            int(bounds.size.height),
        )

    def list_displays(self) -> list:
        """
        List all active displays with their bounds.
        """
        from Quartz import CGGetActiveDisplayList
        
        display_count = 16
        displays = CGGetActiveDisplayList(display_count, None, None)
        
        results = []
        for disp_id in displays[1][:displays[0]]:
            x, y, w, h = self.get_display_bounds(disp_id)
            results.append({"id": disp_id, "x": x, "y": y, "width": w, "height": h})
        
        return results

    def capture_region(self, x: int, y: int, width: int, height: int) -> Optional[np.ndarray]:
        """
        Capture a specific region as RGB numpy array (height, width, 3).
        Returns None on error.
        """
        try:
            if width <= 0 or height <= 0:
                print(f"[QuartzScreenCapture] Invalid dimensions: {width}x{height}")
                return None

            rect = CGRectMake(float(x), float(y), float(width), float(height))
            
            # Capture with options to include windows
            cgimage = CGWindowListCreateImage(
                rect,
                kCGWindowListOptionOnScreenOnly,
                0,
                0
            )
            
            if cgimage is None:
                print("[QuartzScreenCapture] CGWindowListCreateImage returned None")
                return None

            return self._cgimage_to_numpy(cgimage)

        except Exception as e:
            print(f"[QuartzScreenCapture] Error capturing region ({x}, {y}, {width}x{height}): {e}")
            return None

    def capture_display(self, display_id: Optional[int] = None) -> Optional[np.ndarray]:
        """
        Capture entire display as RGB numpy array.
        """
        if display_id is None:
            display_id = self.main_display
        
        x, y, w, h = self.get_display_bounds(display_id)
        return self.capture_region(x, y, w, h)

    @staticmethod
    def _cgimage_to_numpy(cgimage) -> Optional[np.ndarray]:
        """
        Convert CGImage to RGB numpy array.
        """
        try:
            width = int(CGImageGetWidth(cgimage))
            height = int(CGImageGetHeight(cgimage))
            bytes_per_row = int(CGImageGetBytesPerRow(cgimage))
            
            if width <= 0 or height <= 0:
                return None

            # Get image data
            provider = CGImageGetDataProvider(cgimage)
            data = CGDataProviderCopyData(provider)
            
            # Convert bytes to numpy
            np_data = np.frombuffer(data, dtype=np.uint8)
            
            # Reshape: BGRA format typical on macOS
            reshaped = np_data.reshape(height, bytes_per_row // 4, 4)
            
            # Crop to actual width (in case of stride)
            cropped = reshaped[:, :width, :]
            
            # Convert BGRA to RGB
            rgb = cropped[:, :, [2, 1, 0]]  # BGR -> RGB
            
            return rgb.copy()

        except Exception as e:
            print(f"[QuartzScreenCapture] Error converting CGImage to numpy: {e}")
            return None

    def __del__(self):
        if self.pool:
            self.pool.drain()


# Singleton instance
_quartz_instance: Optional[QuartzScreenCapture] = None


def get_quartz_capture() -> QuartzScreenCapture:
    """Get or create singleton Quartz capture instance."""
    global _quartz_instance
    if _quartz_instance is None:
        _quartz_instance = QuartzScreenCapture()
    return _quartz_instance


def test_quartz_capture():
    """Test script for Quartz capture."""
    import cv2
    
    print("[TEST] Initializing Quartz capture...")
    capture = get_quartz_capture()
    
    print("[TEST] Available displays:")
    for display in capture.list_displays():
        print(f"  - Display {display['id']}: ({display['x']}, {display['y']}) "
              f"{display['width']}x{display['height']}")
    
    print("[TEST] Capturing main display...")
    frame = capture.capture_display()
    
    if frame is not None:
        print(f"[TEST] SUCCESS: Captured {frame.shape[0]}x{frame.shape[1]} RGB image")
        print(f"[TEST] Frame dtype: {frame.dtype}, shape: {frame.shape}")
        
        # Save test image
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imwrite("/tmp/quartz_test.png", bgr)
        print("[TEST] Saved to /tmp/quartz_test.png")
    else:
        print("[TEST] FAILED: Could not capture display")


if __name__ == "__main__":
    test_quartz_capture()
