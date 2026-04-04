"""
CODE SNIPPETS FOR INTEGRATION
Integration examples ready to copy into your project
"""

# ============================================
# SNIPPET 1: overlay.py - Add Imports
# ============================================
# Add this at the top after existing imports

"""
# NEW IMPORTS - Background loading & updates
from PyQt5.QtCore import QTimer
import webbrowser

# Model loader (non-blocking)
from model_loader import get_model_loader

# Update system  
from update_checker import UpdateChecker, UpdateCheckResult
from update_dialog import show_update_dialog

# Capture improvements
from quartz_capture import get_quartz_capture
from opencv_webcam import WebcamHandler
from audio_handler import AudioHandler
"""


# ============================================
# SNIPPET 2: overlay.py - Update main() function
# ============================================

def main():
    """
    Updated main() with background model loading and update checking
    """
    defaults, preferences = ensure_preferences_files()
    configure_macos_app()
    
    # ===== NEW: Initialize model loader =====
    print("[DEBUG] Initializing model loader...")
    model_loader = get_model_loader()
    
    def on_model_loaded(success, error):
        if success:
            print("[DEBUG] ✓ Model loaded successfully!")
            overlay._model_loader = model_loader
        else:
            print(f"[DEBUG] ✗ Model loading failed: {error}")
            overlay._model_load_error = error
    
    model_loader.add_callback(on_model_loaded)
    model_loader.load_async()  # Non-blocking - returns immediately!
    print("[DEBUG] Model loading started in background...")
    
    # ===== NEW: Initialize update checker =====
    print("[DEBUG] Initializing update checker...")
    update_checker = UpdateChecker()
    
    def on_update_check_complete(result: UpdateCheckResult):
        if result.error:
            print(f"[DEBUG] Update check error: {result.error}")
        elif result.has_update:
            print(f"[DEBUG] ✓ Update available: {result.latest_version}")
            # Show dialog after startup is complete (don't block UI)
            QTimer.singleShot(3000, lambda: show_update_dialog(result, overlay))
        else:
            print(f"[DEBUG] App is up to date (v{result.current_version})")
    
    update_checker.add_callback(on_update_check_complete)
    update_checker.check_for_updates_async()  # Non-blocking!
    print("[DEBUG] Update check started in background...")
    
    # ===== EXISTING CODE (unchanged) =====
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    overlay = OverlayWindow(
        defaults=defaults,
        preferences=preferences,
        debug_captions=DEBUG_CAPTIONS,
        enable_logging=ENABLE_LOGGING,
    )
    overlay.show()
    
    # Store references for access in callbacks
    overlay._model_loader = None
    overlay._model_load_error = None

    def apply_overlay_config():
        _configure_macos_overlay_window(overlay)

    QTimer.singleShot(100, apply_overlay_config)
    QTimer.singleShot(300, apply_overlay_config)

    if DEBUG_CAPTIONS:
        overlay._caption_simulator = CaptionSimulator(overlay)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()


# ============================================
# SNIPPET 3: overlay_capture.py - Updated Imports
# ============================================

"""
Add these imports at top of overlay_capture.py

import time
import sys
import cv2
from PyQt5.QtCore import QThread, pyqtSignal

from overlay_constants import CAPTURE_FPS

# NEW IMPORTS
from quartz_capture import get_quartz_capture
from opencv_webcam import WebcamHandler
"""


# ============================================
# SNIPPET 4: overlay_capture.py - Quartz ScreenCaptureThread
# ============================================

"""
Replace the existing ScreenCaptureThread class with this:
"""

class ScreenCaptureThread(QThread):
    frame_captured = pyqtSignal(object)

    def __init__(self, region: dict, parent=None):
        super().__init__(parent)
        self._region = dict(region) if region else None
        self._running = True
        print(f"[ScreenCaptureThread] Initialized with region: {self._region}")

    def run(self):
        if not self._region:
            print("[ScreenCaptureThread] ERROR: No region defined")
            return
        
        try:
            if sys.platform == "darwin":
                # ===== NEW: Use Quartz on macOS =====
                print("[ScreenCaptureThread] Using macOS Quartz capture")
                quartz = get_quartz_capture()
                
                x = int(self._region.get("x", 0))
                y = int(self._region.get("y", 0))
                width = int(self._region.get("width", 1920))
                height = int(self._region.get("height", 1080))
                
                print(f"[ScreenCaptureThread] Region: x={x}, y={y}, {width}x{height}")
                
                frame_interval = 1.0 / float(CAPTURE_FPS)
                frame_count = 0
                next_frame_time = time.perf_counter()
                
                while self._running:
                    try:
                        # Capture using Quartz (gets app windows, not just desktop)
                        rgb_frame = quartz.capture_region(x, y, width, height)
                        
                        if rgb_frame is not None:
                            self.frame_captured.emit({
                                "rgb": rgb_frame.tobytes(),
                                "width": rgb_frame.shape[1],
                                "height": rgb_frame.shape[0],
                            })
                            frame_count += 1
                            
                            if frame_count % 100 == 0:
                                print(f"[ScreenCaptureThread] Captured {frame_count} frames")
                        else:
                            print("[ScreenCaptureThread] Quartz returned None")
                        
                        next_frame_time += frame_interval
                        sleep_for = next_frame_time - time.perf_counter()
                        if sleep_for > 0:
                            time.sleep(sleep_for)
                        else:
                            next_frame_time = time.perf_counter()
                    
                    except Exception as e:
                        print(f"[ScreenCaptureThread] Error in capture loop: {e}")
                        time.sleep(0.1)
            
            else:
                # Fallback for non-macOS (use mss or other)
                print("[ScreenCaptureThread] Non-macOS platform, using fallback")
                pass

        except Exception as e:
            print(f"[ScreenCaptureThread] Fatal error: {e}")

    def stop(self):
        self._running = False
        self.wait(500)


# ============================================
# SNIPPET 5: overlay_capture.py - WebcamCaptureThread with Robust Fallback
# ============================================

"""
Replace the existing WebcamCaptureThread class with this:
"""

class WebcamCaptureThread(QThread):
    frame_captured = pyqtSignal(object)

    def __init__(self, device_index: int = 0, parent=None):
        super().__init__(parent)
        self._device_index = device_index
        self._running = True
        self._handler = None
        print(f"[WebcamCaptureThread] Initialized with device index: {device_index}")

    def run(self):
        print("[WebcamCaptureThread] Starting...")
        
        # ===== NEW: Use robust WebcamHandler =====
        self._handler = WebcamHandler(device_index=self._device_index)
        
        if not self._handler.is_open:
            print("[WebcamCaptureThread] CRITICAL: Could not open webcam")
            print("[WebcamCaptureThread] TROUBLESHOOTING:")
            print("  1. System Preferences > Security & Privacy > Camera")
            print("  2. Ensure SignFlow is listed and enabled")
            print("  3. If not listed, remove SignFlow from list")
            print("  4. Restart SignFlow to re-request permission")
            print("  5. Try: sudo killall -9 com.apple.CoreMediaIO.VDC.Agent")
            return
        
        print(f"[WebcamCaptureThread] Webcam opened: {self._handler.get_properties()}")
        
        frame_interval = 1.0 / float(CAPTURE_FPS)
        frame_count = 0
        next_frame_time = time.perf_counter()
        
        while self._running:
            try:
                ret, rgb_frame = self._handler.read()
                
                if ret and rgb_frame is not None:
                    self.frame_captured.emit({
                        "rgb": rgb_frame.tobytes(),
                        "width": rgb_frame.shape[1],
                        "height": rgb_frame.shape[0],
                    })
                    frame_count += 1
                    
                    if frame_count % 100 == 0:
                        print(f"[WebcamCaptureThread] Captured {frame_count} frames")
                else:
                    print("[WebcamCaptureThread] Failed to read frame")
                    time.sleep(0.1)
                
                next_frame_time += frame_interval
                sleep_for = next_frame_time - time.perf_counter()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                else:
                    next_frame_time = time.perf_counter()
            
            except Exception as e:
                print(f"[WebcamCaptureThread] Error in capture loop: {e}")
                time.sleep(0.1)

    def stop(self):
        self._running = False
        if self._handler:
            self._handler.close()
        self.wait(500)


# ============================================
# SNIPPET 6: Using Model Loader in Inference
# ============================================

"""
Example of using the model loader in inference code:
"""

def run_inference_with_optimized_loader(landmarks_array):
    """
    Example inference function using optimized model loader
    """
    from model_loader import get_model_loader
    import torch
    
    try:
        # Get singleton loader
        loader = get_model_loader()
        
        # Check if ready
        if not loader.is_ready():
            print("[Inference] Model not ready yet")
            return None, 0.0
        
        # Get model (raises if not ready)
        model, class_names, device = loader.get_model()
        
        # Run inference
        with torch.no_grad():
            input_tensor = torch.from_numpy(landmarks_array).to(device)
            logits = model(input_tensor)
            probs = torch.softmax(logits, dim=-1)
            pred_idx = probs.argmax(dim=-1).item()
            confidence = probs[0, pred_idx].item()
        
        predicted_sign = class_names[pred_idx]
        print(f"[Inference] Predicted: {predicted_sign} ({confidence:.2%})")
        
        return predicted_sign, confidence
    
    except RuntimeError as e:
        print(f"[Inference] Model error: {e}")
        return None, 0.0
    except Exception as e:
        print(f"[Inference] Unexpected error: {e}")
        return None, 0.0


# ============================================
# SNIPPET 7: Audio Handler Usage Example
# ============================================

"""
Example of using audio handler:
"""

def record_audio_chunk():
    """
    Record a short audio chunk
    """
    from audio_handler import AudioHandler
    
    try:
        handler = AudioHandler(sample_rate=16000, channels=1)
        
        # Record 2 seconds
        audio = handler.record_chunk(duration_seconds=2)
        
        if audio is not None:
            print(f"[Audio] Recorded: {audio.shape}")
            # Send to speech-to-text service
            return audio
        else:
            print("[Audio] Recording failed")
            return None
    
    except Exception as e:
        print(f"[Audio] Error: {e}")
        return None


# ============================================
# SNIPPET 8: Real-Time Audio Callback Example
# ============================================

"""
Example of real-time audio processing with callback:
"""

def setup_audio_streaming():
    """
    Setup real-time audio streaming with callback
    """
    from audio_handler import AudioHandler
    import numpy as np
    
    handler = AudioHandler(sample_rate=16000)
    
    # Define callback
    def process_audio_chunk(chunk):
        # chunk is numpy array shaped (samples, channels)
        # Process for speech recognition, feature extraction, etc.
        print(f"[Audio] Processing chunk: {chunk.shape}")
        
        # Example: compute RMS level
        rms = np.sqrt(np.mean(chunk ** 2))
        print(f"[Audio] RMS level: {rms:.4f}")
    
    # Start recording with callback
    handler. start_recording(callback=process_audio_chunk)
    
    # ... do stuff ...
    # handler.stop_recording()


# ============================================
# SNIPPET 9: Update Dialog Manual Trigger
# ============================================

"""
Example of manually triggering update dialog (not just on startup):
"""

def check_for_updates_manual():
    """
    Manually check for updates (e.g., from menu action)
    """
    from update_checker import UpdateChecker
    from update_dialog import show_update_dialog
    from PyQt5.QtWidgets import QMessageBox
    
    checker = UpdateChecker()
    result = checker.check_for_updates_sync()
    
    if result.error:
        QMessageBox.critical(None, "Update Check Failed", result.error)
    elif result.has_update:
        show_update_dialog(result)
    else:
        QMessageBox.information(
            None,
            "No Update Available",
            f"You are running the latest version ({result.current_version})"
        )


# ============================================
# SNIPPET 10: Checking Model Loader Status in UI
# ============================================

"""
Example of displaying model loading status in UI:
"""

def update_status_display():
    """
    Update UI with model loading status
    """
    from model_loader import get_model_loader
    
    loader = get_model_loader()
    status = loader.get_status()
    
    # Display in UI
    status_text = f"""
    Model Status: {status['state']}
    Ready: {status['is_ready']}
    Device: {status['device']}
    Classes: {status['class_count']}
    Error: {status['error']}
    """
    
    print(status_text)


# ============================================
# END OF SNIPPETS
# ============================================
