import os
import random
import sys
import ctypes
import ctypes.util

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
    """Configure NSWindow to keep overlay visible across Spaces and full-screen apps."""
    if sys.platform != "darwin":
        return

    try:
        objc_path = ctypes.util.find_library("objc")
        if not objc_path:
            return

        objc = ctypes.cdll.LoadLibrary(objc_path)

        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]

        msg_send_addr = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value
        if not msg_send_addr:
            return

        msg_ptr = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(msg_send_addr)
        msg_uint = ctypes.CFUNCTYPE(ctypes.c_ulonglong, ctypes.c_void_p, ctypes.c_void_p)(msg_send_addr)
        msg_set_uint = ctypes.CFUNCTYPE(
            None,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_ulonglong,
        )(msg_send_addr)
        msg_set_int = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long)(msg_send_addr)
        msg_set_bool = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool)(msg_send_addr)

        def _sel(name: str):
            return objc.sel_registerName(name.encode("utf-8"))

        def _msg_ptr(target, selector):
            return msg_ptr(ctypes.c_void_p(target), selector)

        ns_view = int(widget.winId())
        if not ns_view:
            return

        ns_window = _msg_ptr(ns_view, _sel("window"))
        if not ns_window:
            return

        # NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorFullScreenAuxiliary
        join_all_spaces_and_fullscreen_aux = (1 << 0) | (1 << 8)
        existing_behavior = msg_uint(ctypes.c_void_p(ns_window), _sel("collectionBehavior"))
        msg_set_uint(
            ctypes.c_void_p(ns_window),
            _sel("setCollectionBehavior:"),
            existing_behavior | join_all_spaces_and_fullscreen_aux,
        )

        # Keep it visible when app focus changes.
        msg_set_bool(ctypes.c_void_p(ns_window), _sel("setHidesOnDeactivate:"), False)

        # Floating level is sufficient with Qt's WindowStaysOnTopHint.
        msg_set_int(ctypes.c_void_p(ns_window), _sel("setLevel:"), 3)
    except Exception:
        # Best-effort only: keep overlay functional even if native calls are unavailable.
        pass
