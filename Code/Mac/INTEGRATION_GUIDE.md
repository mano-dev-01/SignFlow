"""
INTEGRATION GUIDE: SignFlow macOS Production Updates

This file documents how to integrate all the new fixes and features into overlay.py.
"""

# ============================================
# INTEGRATION STEPS
# ============================================

# STEP 1: Update requirements_macos.txt
# Run:
#   pip install -r Code/Mac/Overlay/requirements_macos.txt
#
# Key additions:
#   - sounddevice (replaces PyAudio)
#   - pyobjc-framework-Quartz (macOS screen capture)
#   - requests, packaging (update system)


# ============================================
# STEP 2: Update Info.plist
# Already done! Added:
#   - NSScreenCaptureUsageDescription (for Quartz capture)
#   - UIBackgroundModes (for background processing)
#   - LSEnvironment (framework path)


# ============================================
# STEP 3: Update PyInstaller spec file
# Already done! SignFlow.spec now includes:
#   - All hidden imports for new modules
#   - Quartz, sounddevice, requests frameworks
#   - version.py in data files


# ============================================
# STEP 4: INTEGRATE INTO overlay.py
# ============================================

# Add these imports at the top of overlay.py:

"""
# NEW IMPORTS - Add after existing imports

# Model loading (background)
from model_loader import get_model_loader

# Update system
from update_checker import UpdateChecker, UpdateCheckResult
from update_dialog import show_update_dialog

# Screen capture - Quartz (macOS native)
from quartz_capture import get_quartz_capture, QuartzScreenCapture

# Webcam - improved OpenCV
from opencv_webcam import WebcamHandler

# Audio input
from audio_handler import AudioHandler

# Timers
from PyQt5.QtCore import QTimer, pyqtSignal

import webbrowser
"""


# Add to main() function BEFORE creating OverlayWindow:

"""
def main():
    # ... existing code ...
    
    # NEW: Initialize model loading in background
    print("[Startup] Initializing model loader...")
    model_loader = get_model_loader()
    
    def on_model_loaded(success, error):
        if success:
            print("[Startup] Model loaded successfully!")
        else:
            print(f"[Startup] Model loading failed: {error}")
    
    model_loader.add_callback(on_model_loaded)
    model_loader.load_async()  # Non-blocking!
    
    # NEW: Initialize update checker
    print("[Startup] Initializing update checker...")
    update_checker = UpdateChecker()
    
    def on_update_check_complete(result: UpdateCheckResult):
        if result.has_update:
            print(f"[Startup] Update available: {result.latest_version}")
            # Show dialog on main thread later
            QTimer.singleShot(2000, lambda: show_update_dialog(result, overlay))
        elif result.error:
            print(f"[Startup] Update check error: {result.error}")
    
    update_checker.add_callback(on_update_check_complete)
    update_checker.check_for_updates_async()  # Non-blocking!
    
    # ... rest of existing code ...
    app = QApplication(sys.argv)
    overlay = OverlayWindow(...)
"""


# STEP 5: Update ScreenCaptureThread in overlay_capture.py
# Replace with Quartz-based capture:

"""
import sys
from quartz_capture import get_quartz_capture

class ScreenCaptureThread(QThread):
    frame_captured = pyqtSignal(object)
    
    def __init__(self, region: dict, parent=None):
        super().__init__(parent)
        self._region = dict(region) if region else None
        self._running = True
    
    def run(self):
        if not self._region:
            print("[ScreenCaptureThread] ERROR: No region defined")
            return
        
        try:
            if sys.platform == "darwin":
                # Use Quartz on macOS
                print("[ScreenCaptureThread] Using Quartz capture on macOS")
                quartz = get_quartz_capture()
                
                x = int(self._region.get("x", 0))
                y = int(self._region.get("y", 0))
                width = int(self._region.get("width", 1920))
                height = int(self._region.get("height", 1080))
                
                frame_interval = 1.0 / CAPTURE_FPS
                frame_count = 0
                next_frame_time = time.perf_counter()
                
                while self._running:
                    try:
                        rgb_frame = quartz.capture_region(x, y, width, height)
                        
                        if rgb_frame is not None:
                            self.frame_captured.emit({
                                "rgb": rgb_frame.tobytes(),
                                "width": rgb_frame.shape[1],
                                "height": rgb_frame.shape[0],
                            })
                            frame_count += 1
                        
                        next_frame_time += frame_interval
                        sleep_for = next_frame_time - time.perf_counter()
                        if sleep_for > 0:
                            time.sleep(sleep_for)
                        else:
                            next_frame_time = time.perf_counter()
                    
                    except Exception as e:
                        print(f"[ScreenCaptureThread] Error: {e}")
                        time.sleep(0.1)
            else:
                # Fallback for other platforms (mss)
                pass
        
        except Exception as e:
            print(f"[ScreenCaptureThread] Fatal error: {e}")
    
    def stop(self):
        self._running = False
        self.wait(500)
"""


# STEP 6: Update WebcamCaptureThread in overlay_capture.py

"""
import cv2
from opencv_webcam import WebcamHandler

class WebcamCaptureThread(QThread):
    frame_captured = pyqtSignal(object)
    
    def __init__(self, device_index: int = 0, parent=None):
        super().__init__(parent)
        self._device_index = device_index
        self._running = True
        self._handler = None
    
    def run(self):
        print("[WebcamCaptureThread] Starting...")
        
        # Use improved WebcamHandler
        self._handler = WebcamHandler(device_index=self._device_index)
        
        if not self._handler.is_open:
            print("[WebcamCaptureThread] ERROR: Failed to open webcam")
            print("[WebcamCaptureThread] Troubleshooting:")
            print("  1. System Preferences > Security & Privacy > Camera")
            print("  2. Enable SignFlow if listed")
            print("  3. Kill CoreMediaIO agent: sudo killall -9 com.apple.CoreMediaIO.VDC.Agent")
            return
        
        frame_interval = 1.0 / CAPTURE_FPS
        frame_count = 0
        next_frame_time = time.perf_counter()
        
        while self._running:
            ret, rgb_frame = self._handler.read()
            
            if ret and rgb_frame is not None:
                self.frame_captured.emit({
                    "rgb": rgb_frame.tobytes(),
                    "width": rgb_frame.shape[1],
                    "height": rgb_frame.shape[0],
                })
                frame_count += 1
            
            next_frame_time += frame_interval
            sleep_for = next_frame_time - time.perf_counter()
            if sleep_for > 0:
                time.sleep(sleep_for)
            else:
                next_frame_time = time.perf_counter()
    
    def stop(self):
        self._running = False
        if self._handler:
            self._handler.close()
        self.wait(500)
"""


# ============================================
# TESTING THE FIXES
# ============================================

# Test each component individually:

# 1. Test Quartz screen capture:
#    python3 Code/Mac/Overlay/quartz_capture.py

# 2. Test webcam:
#    python3 Code/Mac/Overlay/opencv_webcam.py

# 3. Test audio:
#    python3 Code/Mac/Overlay/audio_handler.py

# 4. Test model loader:
#    python3 Code/Mac/Overlay/model_loader.py

# 5. Test update checker:
#    python3 Code/Mac/Overlay/update_checker.py

# 6. Test update dialog (with mock result):
#    python3 Code/Mac/Overlay/update_dialog.py


# ============================================
# PYINSTALLER BUILD
# ============================================

# Build with updated spec:
#   pyinstaller SignFlow.spec --noconfirm --clean

# Verify bundled items:
#   file dist/SignFlow.app/Contents/MacOS/SignFlow
#   otool -L dist/SignFlow.app/Contents/MacOS/SignFlow | grep -E "(Quartz|sounddevice|requests)"

# Create DMG:
#   ./Code/Mac/crt/make_product_dmg.sh


# ============================================
# REMOTE UPDATE SOURCE SETUP
# ============================================

# Create updates.json on GitHub:

"""
{
  "version": "1.1.0",
  "download_url": "https://github.com/YOUR-REPO/SignFlow/releases/download/v1.1.0/SignFlow-mac.dmg",
  "notes": "Bug fixes and performance improvements\n- Fixed screen capture for app windows\n- Optimized model loading\n- Added audio input support"
}
"""

# Update Code/Mac/version.py:
#   UPDATE_CHECK_URL = "https://raw.githubusercontent.com/YOUR-REPO/SignFlow/main/Code/Mac/updates.json"


# ============================================
# TROUBLESHOOTING
# ============================================

# PERMISSION ISSUES:
# If camera/mic/screen capture not working after install:
#
# Full reset:
#   System Preferences > Security & Privacy > Camera
#   Remove SignFlow from list
#   Restart app (will re-request permission)
#
# For screen recording:
#   System Preferences > Security & Privacy > Screen Recording
#   Remove SignFlow, add again


# MODEL LOADING HANGS:
# - Check that PyTorch is properly installed: python3 -c "import torch; print(torch.cuda.is_available())"
# - Verify model files exist: ls Code/Mac/Models/
# - Check permissions: chmod +r Code/Mac/Models/*


# QUARTZ CAPTURE EMPTY:
# - Ensure pyobjc-framework-Quartz is installed: pip list | grep pyobjc
# - Try: xcode-select --install


# SOUNDDEVICE ERRORS:
# - Install PortAudio: brew install portaudio
# - Reinstall: pip install --force-reinstall sounddevice


# ============================================
# CHECKLIST FOR PRODUCTION
# ============================================

#  [ ] Updated requirements_macos.txt
#  [ ] Updated Info.plist with permissions
#  [ ] Updated SignFlow.spec with hiddenimports
#  [ ] Created model_loader.py (singleton)
#  [ ] Created update_checker.py 
#  [ ] Created update_dialog.py
#  [ ] Created quartz_capture.py
#  [ ] Created opencv_webcam.py
#  [ ] Created audio_handler.py
#  [ ] Updated overlay.py with imports
#  [ ] Updated overlay_capture.py with Quartz/WebcamHandler
#  [ ] Tested all components individually
#  [ ] Built DMG with PyInstaller
#  [ ] Tested on clean macOS machine
#  [ ] Set up remote updates.json
#  [ ] Updated Code/Mac/version.py with correct URL
#  [ ] Signed and notarized DMG
