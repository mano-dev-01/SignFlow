import time
import sys

import cv2
import mss
from PyQt5.QtCore import QThread, pyqtSignal

from overlay_constants import CAPTURE_FPS


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
        
        # Validate region has required keys
        required_keys = {"x", "y", "width", "height"}
        if not all(key in self._region for key in required_keys):
            print(f"[ScreenCaptureThread] ERROR: Invalid region dict: {self._region}")
            return
        
        # macOS-specific screen capture setup
        if sys.platform == "darwin":
            # Ensure region coordinates are valid
            x = int(self._region["x"])
            y = int(self._region["y"])
            width = int(self._region["width"])
            height = int(self._region["height"])
            
            # Validate dimensions
            if width <= 0 or height <= 0:
                print(f"[ScreenCaptureThread] ERROR: Invalid dimensions: {width}x{height}")
                return
            
            monitor = {
                "left": x,
                "top": y,
                "width": width,
                "height": height,
            }
            print(f"[ScreenCaptureThread] macOS screen capture: x={x}, y={y}, w={width}, h={height}")
        else:
            monitor = {
                "left": int(self._region["x"]),
                "top": int(self._region["y"]),
                "width": int(self._region["width"]),
                "height": int(self._region["height"]),
            }
        
        frame_interval = 1.0 / float(CAPTURE_FPS)
        frame_count = 0
        try:
            with mss.mss() as sct:
                next_frame_time = time.perf_counter()
                while self._running:
                    try:
                        screenshot = sct.grab(monitor)
                        if screenshot is None:
                            print("[ScreenCaptureThread] ERROR: sct.grab() returned None")
                            time.sleep(0.1)
                            continue
                        
                        self.frame_captured.emit(
                            {
                                "rgb": screenshot.rgb,
                                "width": screenshot.width,
                                "height": screenshot.height,
                            }
                        )
                        frame_count += 1
                        if frame_count % 100 == 0:
                            print(f"[ScreenCaptureThread] Captured {frame_count} frames")
                        
                        next_frame_time += frame_interval
                        sleep_for = next_frame_time - time.perf_counter()
                        if sleep_for > 0:
                            time.sleep(sleep_for)
                        else:
                            next_frame_time = time.perf_counter()
                    except Exception as e:
                        print(f"[ScreenCaptureThread] Error capturing frame: {e}")
                        time.sleep(0.1)
        except Exception as e:
            print(f"[ScreenCaptureThread] Fatal error: {e}")

    def stop(self):
        self._running = False
        self.wait(500)


class WebcamCaptureThread(QThread):
    frame_captured = pyqtSignal(object)

    def __init__(self, device_index: int = 0, parent=None):
        super().__init__(parent)
        self._device_index = int(device_index)
        self._running = True

    def run(self):
        backends = [
            getattr(cv2, "CAP_DSHOW", 0),
            getattr(cv2, "CAP_MSMF", 0),
            getattr(cv2, "CAP_ANY", 0),
            0,
        ]
        tried = set()
        cap = None
        for index in [self._device_index, 0, 1, 2]:
            if index in tried:
                continue
            tried.add(index)
            for backend in backends:
                cap = cv2.VideoCapture(index, backend)
                if cap.isOpened():
                    break
            if cap is not None and cap.isOpened():
                break
        if cap is None or not cap.isOpened():
            return
        frame_interval = 1.0 / float(CAPTURE_FPS)
        next_frame_time = time.perf_counter()
        while self._running:
            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(0.01)
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            self.frame_captured.emit(
                {
                    "rgb": rgb.tobytes(),
                    "width": int(w),
                    "height": int(h),
                }
            )
            next_frame_time += frame_interval
            sleep_for = next_frame_time - time.perf_counter()
            if sleep_for > 0:
                time.sleep(sleep_for)
            else:
                next_frame_time = time.perf_counter()
        cap.release()

    def stop(self):
        self._running = False
        self.wait(500)
