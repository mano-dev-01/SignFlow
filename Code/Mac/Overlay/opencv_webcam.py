"""
Robust macOS webcam capture with permission handling and fallback strategies.
"""

import sys
import time
from typing import Optional, Tuple

import cv2
import numpy as np


class WebcamHandler:
    """
    Robust webcam access with fallback strategies and permission handling.
    """

    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self.cap = None
        self.is_open = False
        self.frame_count = 0
        self.last_frame = None
        
        self._initialize_webcam()

    def _initialize_webcam(self):
        """
        Try to initialize webcam with multiple backends and device indices.
        """
        backends_to_try = []
        
        if sys.platform == "darwin":
            # macOS specific backends
            backends_to_try = [
                (cv2.CAP_AVFOUNDATION, "AVFoundation"),
                (cv2.CAP_ANY, "ANY"),
            ]
        else:
            backends_to_try = [
                (cv2.CAP_ANY, "ANY"),
            ]

        device_indices_to_try = [self.device_index, 0, 1, 2]

        for device_idx in device_indices_to_try:
            for backend_id, backend_name in backends_to_try:
                try:
                    print(f"[WebcamHandler] Trying device {device_idx} with backend {backend_name}...")
                    
                    cap = cv2.VideoCapture(device_idx, backend_id)
                    
                    if cap is None or not cap.isOpened():
                        if cap:
                            cap.release()
                        continue

                    # Test capture
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        cap.release()
                        continue

                    print(f"[WebcamHandler] SUCCESS: Device {device_idx} ({backend_name}) "
                          f"opened - {frame.shape[1]}x{frame.shape[0]}")
                    
                    self.cap = cap
                    self.is_open = True
                    self._configure_camera()
                    return

                except Exception as e:
                    print(f"[WebcamHandler] Failed with device {device_idx}, backend {backend_name}: {e}")
                    continue

        print("[WebcamHandler] ERROR: Could not initialize webcam with any backend or device")
        self.is_open = False

    def _configure_camera(self):
        """
        Configure camera for optimal performance.
        """
        if not self.cap or not self.is_open:
            return

        try:
            # Set resolution (lower = faster)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # Set FPS (30 FPS target)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            # Reduce latency
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Auto-focus
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            print(f"[WebcamHandler] Configured: {actual_width}x{actual_height} @ {actual_fps} FPS")

        except Exception as e:
            print(f"[WebcamHandler] Error configuring camera: {e}")

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read frame from webcam.
        Returns (success, rgb_frame).
        """
        if not self.is_open or self.cap is None:
            return False, None

        try:
            ret, frame = self.cap.read()
            
            if not ret or frame is None:
                print("[WebcamHandler] Failed to read frame")
                return False, None

            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.last_frame = rgb_frame
            self.frame_count += 1
            
            return True, rgb_frame

        except Exception as e:
            print(f"[WebcamHandler] Error reading frame: {e}")
            return False, None

    def get_properties(self) -> dict:
        """Get camera properties."""
        if not self.is_open or self.cap is None:
            return {}

        return {
            "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": self.cap.get(cv2.CAP_PROP_FPS),
            "frame_count": self.frame_count,
        }

    def close(self):
        """Release webcam."""
        if self.cap:
            self.cap.release()
            self.is_open = False
            print("[WebcamHandler] Webcam released")

    def __del__(self):
        self.close()


def test_webcam():
    """Test script for webcam."""
    import cv2
    
    print("[TEST] Initializing webcam...")
    handler = WebcamHandler(device_index=0)
    
    if not handler.is_open:
        print("[TEST] FAILED: Could not open webcam")
        print("[TEST] TROUBLESHOOTING:")
        print("  1. Check System Preferences > Security & Privacy > Camera")
        print("  2. Ensure SignFlow is listed and enabled")
        print("  3. Kill and relaunch the app")
        print("  4. Try: sudo killall -9 com.apple.CoreMediaIO.VDC.Agent")
        return

    print("[TEST] Webcam opened successfully")
    print(f"[TEST] Properties: {handler.get_properties()}")
    
    print("[TEST] Capturing 30 frames...")
    for i in range(30):
        ret, frame = handler.read()
        if ret and frame is not None:
            print(f"[TEST] Frame {i+1}: {frame.shape}")
            
            if i == 0:
                # Save first frame
                bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                cv2.imwrite("/tmp/webcam_test.png", bgr)
                print("[TEST] Saved first frame to /tmp/webcam_test.png")
        else:
            print(f"[TEST] Frame {i+1}: FAILED")
            break
        
        time.sleep(0.05)
    
    handler.close()
    print("[TEST] Complete")


if __name__ == "__main__":
    test_webcam()
