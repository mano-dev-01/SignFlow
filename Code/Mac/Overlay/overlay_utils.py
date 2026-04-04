import os
import random
import sys
import ctypes
import ctypes.util

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage

from overlay_constants import EXCLUDE_OVERLAY_FROM_CAPTURE

FRAME_DISPATCHER = None


def set_frame_dispatcher(callback):
    global FRAME_DISPATCHER
    FRAME_DISPATCHER = callback


def process_frame(frame):
    if callable(FRAME_DISPATCHER):
        FRAME_DISPATCHER(frame)


def stop_capture():
    pass


def restart_current_process():
    if getattr(sys, "frozen", False):
        os.execv(sys.executable, [sys.executable] + sys.argv[1:])
    else:
        script_path = os.path.abspath(sys.argv[0])
        os.execv(sys.executable, [sys.executable, script_path] + sys.argv[1:])


def generate_fake_status(system_state: str):
    hands = random.randint(0, 2)
    left_conf = random.random() if hands >= 1 else 0.0
    right_conf = random.random() if hands == 2 else 0.0
    fps = random.randint(20, 30)
    model_state = random.choice(
        ["Idle", "Detecting Hands", "Processing Frame", "Waiting for Input"]
    )
    capture_state = (
        "Active"
        if system_state == "Running"
        else ("Paused" if system_state == "Paused" else "Idle")
    )

    return {
        "System": system_state,
        "Capture Region": capture_state,
        "Hands Detected": hands,
        "Left Hand Confidence": left_conf,
        "Right Hand Confidence": right_conf,
        "Processing FPS": fps,
        "Model State": model_state,
    }


def _frame_to_qimage(frame):
    if not isinstance(frame, dict):
        return None

    rgb = frame.get("rgb")
    width = int(frame.get("width", 0) or 0)
    height = int(frame.get("height", 0) or 0)

    if rgb is None or width <= 0 or height <= 0:
        return None

    bytes_per_line = width * 3
    image = QImage(rgb, width, height, bytes_per_line, QImage.Format_RGB888)
    return image.copy()


# ---------------- WINDOWS ----------------
def _set_window_excluded_from_capture(widget):
    if sys.platform != "win32":
        return

    try:
        hwnd = int(widget.winId())
        affinity = 0x11 if EXCLUDE_OVERLAY_FROM_CAPTURE else 0x00
        ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, affinity)
    except Exception:
        pass


# ---------------- MACOS ----------------
def configure_macos_app():
    """Run once at app startup - BEFORE QApplication is created"""
    if sys.platform != "darwin":
        return

    try:
        import objc
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory

        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    except Exception as e:
        print("App policy error:", e)


def configure_macos_overlay(widget):
    """Configure Qt window as non-intrusive macOS overlay"""
    if sys.platform != "darwin":
        return

    try:
        import objc
        from AppKit import (
            NSFloatingWindowLevel,
            NSWindowStyleMaskNonactivatingPanel,
            NSWindowCollectionBehaviorCanJoinAllSpaces,
            NSWindowCollectionBehaviorFullScreenAuxiliary,
            NSWindowCollectionBehaviorMoveToActiveSpace,
            NSWindowCollectionBehaviorTransient,
        )

        ns_view = objc.objc_object(c_void_p=int(widget.winId()))
        ns_window = ns_view.window()

        if ns_window is None:
            return

        # --- STYLE ---
        style = int(ns_window.styleMask())
        style |= int(NSWindowStyleMaskNonactivatingPanel)
        ns_window.setStyleMask_(style)

        # --- BEHAVIOR ---
        ns_window.setFloatingPanel_(True)
        ns_window.setBecomesKeyOnlyIfNeeded_(False)
        ns_window.setWorksWhenModal_(True)

        # --- SPACES - Use all available behaviors ---
        behavior = (
            int(NSWindowCollectionBehaviorCanJoinAllSpaces) |
            int(NSWindowCollectionBehaviorFullScreenAuxiliary) |
            int(NSWindowCollectionBehaviorTransient) |
            int(NSWindowCollectionBehaviorMoveToActiveSpace)
        )
        ns_window.setCollectionBehavior_(behavior)

        # Force to ALL spaces using private API if available
        try:
            ns_window.setValue_forKey_(True, "collectionBehaviorCanJoinAllSpaces")
        except Exception:
            pass

        # Try to set on all spaces directly
        if hasattr(ns_window, "setIsOnAllSpaces_"):
            ns_window.setIsOnAllSpaces_(True)

        # --- LEVEL ---
        ns_window.setLevel_(int(NSFloatingWindowLevel))

        # 🔥 IMPORTANT FIX
        ns_window.setHidesOnDeactivate_(False)

        # Keep overlay out of normal app window cycling
        if hasattr(ns_window, "setIgnoresCycle_"):
            ns_window.setIgnoresCycle_(True)
        if hasattr(ns_window, "setReleasedWhenClosed_"):
            ns_window.setReleasedWhenClosed_(False)

        # --- NO FOCUS ---
        if hasattr(ns_window, "setCanBecomeKeyWindow_"):
            ns_window.setCanBecomeKeyWindow_(False)
        if hasattr(ns_window, "setCanBecomeMainWindow_"):
            ns_window.setCanBecomeMainWindow_(False)

        # --- MOUSE PASSTHROUGH ---
        ignores_mouse = widget.testAttribute(Qt.WA_TransparentForMouseEvents)
        ns_window.setIgnoresMouseEvents_(bool(ignores_mouse))

        # --- SHOW SAFELY ---
        ns_window.orderFront_(None)

        # Final push to all spaces
        ns_window.setCollectionBehavior_(behavior)

    except Exception as e:
        print("Overlay config error:", e)


def _configure_macos_overlay_window(widget):
    """Compatibility wrapper used by overlay window modules."""
    configure_macos_overlay(widget)