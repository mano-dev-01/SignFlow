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
        from quartz_capture import QuartzScreenCapture
        
        if not self._region:
            print("[ScreenCaptureThread] ERROR: No region defined")
            return
        
        capture = QuartzScreenCapture()
        frame_interval = 1.0 / float(CAPTURE_FPS)
        next_frame_time = time.perf_counter()
        
        while self._running:
            try:
                rgb_frame = capture.capture_region(
                    int(self._region["x"]),
                    int(self._region["y"]),
                    int(self._region["width"]),
                    int(self._region["height"]),
                )
                if rgb_frame is not None:
                    h, w = rgb_frame.shape[:2]
                    self.frame_captured.emit({
                        "rgb": rgb_frame.tobytes(),
                        "width": int(w),
                        "height": int(h),
                    })
                
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
        from opencv_webcam import WebcamHandler
        
        handler = WebcamHandler(device_index=self._device_index)
        if not handler.read():
            print(f"[WebcamCaptureThread] Failed to initialize webcam at index {self._device_index}")
            return
        
        frame_interval = 1.0 / float(CAPTURE_FPS)
        next_frame_time = time.perf_counter()
        
        while self._running:
            ok, frame = handler.read()
            if not ok or frame is None:
                time.sleep(0.01)
                continue
            
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            self.frame_captured.emit({
                "rgb": rgb.tobytes(),
                "width": int(w),
                "height": int(h),
            })
            
            next_frame_time += frame_interval
            sleep_for = next_frame_time - time.perf_counter()
            if sleep_for > 0:
                time.sleep(sleep_for)
            else:
                next_frame_time = time.perf_counter()
        
        handler.close()

    def stop(self):
        self._running = False
        self.wait(500)
