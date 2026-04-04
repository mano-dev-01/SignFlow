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
    model_state = random.choice(["Idle", "Detecting Hands", "Processing Frame", "Waiting for Input"])
    capture_state = "Active" if system_state == "Running" else ("Paused" if system_state == "Paused" else "Idle")
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


def _set_window_excluded_from_capture(widget):
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = int(widget.winId())
        affinity = 0x11 if EXCLUDE_OVERLAY_FROM_CAPTURE else 0x00
        ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, affinity)
    except Exception:
        pass


def _configure_macos_overlay_window(widget):
    """Configure Qt window as a non-activating NSPanel visible on all Spaces."""
    if sys.platform != "darwin":
        return

    try:
        import objc
        from AppKit import (
            NSFloatingWindowLevel,
            NSWindowCollectionBehaviorCanJoinAllSpaces,
            NSWindowCollectionBehaviorFullScreenAuxiliary,
            NSWindowStyleMaskNonactivatingPanel,
        )

        ns_view_ptr = int(widget.winId())
        if not ns_view_ptr:
            return

        ns_view = objc.objc_object(c_void_p=ns_view_ptr)
        ns_window = ns_view.window()
        if ns_window is None:
            return

        panel_class = objc.lookUpClass("NSPanel")
        if not ns_window.isKindOfClass_(panel_class):
            libobjc_path = ctypes.util.find_library("objc")
            if libobjc_path:
                libobjc = ctypes.cdll.LoadLibrary(libobjc_path)
                object_set_class = libobjc.object_setClass
                object_set_class.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
                object_set_class.restype = ctypes.c_void_p
                object_set_class(
                    ctypes.c_void_p(objc.pyobjc_id(ns_window)),
                    ctypes.c_void_p(objc.pyobjc_id(panel_class)),
                )
                ns_window = objc.objc_object(c_void_p=objc.pyobjc_id(ns_window))

        style = int(ns_window.styleMask()) | int(NSWindowStyleMaskNonactivatingPanel)
        ns_window.setStyleMask_(style)
        ns_window.setFloatingPanel_(True)
        ns_window.setBecomesKeyOnlyIfNeeded_(False)
        ns_window.setWorksWhenModal_(True)

        behavior = int(ns_window.collectionBehavior())
        behavior |= int(NSWindowCollectionBehaviorCanJoinAllSpaces)
        behavior |= int(NSWindowCollectionBehaviorFullScreenAuxiliary)
        ns_window.setCollectionBehavior_(behavior)

        ns_window.setLevel_(int(NSFloatingWindowLevel))
        ns_window.setHidesOnDeactivate_(False)
        if hasattr(ns_window, "setCanBecomeKeyWindow_"):
            ns_window.setCanBecomeKeyWindow_(False)
        if hasattr(ns_window, "setCanBecomeMainWindow_"):
            ns_window.setCanBecomeMainWindow_(False)

        ignores_mouse = bool(widget.testAttribute(Qt.WA_TransparentForMouseEvents))
        ns_window.setIgnoresMouseEvents_(ignores_mouse)
        ns_window.orderFrontRegardless()
    except Exception:
        pass
