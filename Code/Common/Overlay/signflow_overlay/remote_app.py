from __future__ import annotations

import argparse
import os
import sys
import warnings
from pathlib import Path

try:
    from PyQt5.QtCore import QTimer
    from PyQt5.QtWidgets import QApplication
except ImportError:
    QTimer = None
    QApplication = None
    print('[OVERLAY_REMOTE] WARNING: PyQt5 is not installed. run pip install pyqt5')

from overlay_preferences import ensure_preferences_files

from .config import AUTO_WEBCAM_DELAY_MS, CAMERA_SCAN_LIMIT, DEFAULT_SERVER_URL
from .remote_window import RemoteOverlayWindow


def configure_runtime():
    print('[OVERLAY_REMOTE] configure_runtime: injecting project root path and checking dependencies')
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    os.environ.setdefault("GLOG_minloglevel", "2")
    warnings.filterwarnings(
        "ignore",
        message=r"SymbolDatabase\.GetPrototype\(\) is deprecated.*",
    )

    # Ensure module import paths for this repo layout:
    root = Path(__file__).resolve().parents[2]
    model_dir = root / 'Model_inference'
    for path in [str(root), str(model_dir)]:
        if path not in sys.path:
            sys.path.insert(0, path)
            print(f"[OVERLAY_REMOTE] added to sys.path: {path}")

    try:
        import numpy  # noqa: F401
    except ImportError:
        print('[OVERLAY_REMOTE] WARNING: numpy is not installed. run pip install -r requirements.txt')


def scan_available_cameras(max_index: int = CAMERA_SCAN_LIMIT):
    print("[OVERLAY_REMOTE] Scanning for cameras...")
    try:
        import cv2
    except ImportError:
        print("[OVERLAY_REMOTE] cv2 not available - cannot scan cameras")
        return []

    found = []
    for camera_index in range(max_index):
        try:
            capture = cv2.VideoCapture(camera_index, cv2.CAP_ANY)
            if capture.isOpened():
                readable, _ = capture.read()
                if readable:
                    found.append(camera_index)
                    print(f"[OVERLAY_REMOTE]   Camera {camera_index}: OK (readable)")
                else:
                    print(f"[OVERLAY_REMOTE]   Camera {camera_index}: opens but read failed")
                capture.release()
        except Exception as exc:
            print(f"[OVERLAY_REMOTE]   Camera {camera_index}: error - {exc}")

    if found:
        print(f"[OVERLAY_REMOTE] Cameras found: {found}")
    else:
        print("[OVERLAY_REMOTE] WARNING: No readable cameras found!")
        print("[OVERLAY_REMOTE]   - Make sure no other app is using the camera")
        print("[OVERLAY_REMOTE]   - Try closing browser tabs / Teams / Zoom")
    return found


def build_argument_parser():
    parser = argparse.ArgumentParser(description="SignFlow overlay in remote-server mode")
    parser.add_argument("--server", type=str, default=DEFAULT_SERVER_URL)
    parser.add_argument(
        "--auto-webcam",
        action="store_true",
        help="Start webcam mode automatically after the overlay opens.",
    )
    parser.add_argument(
        "--no-webcam",
        action="store_true",
        help="Compatibility flag retained for older launch commands.",
    )
    return parser


def main(argv=None):
    configure_runtime()
    parser = build_argument_parser()
    args, qt_args = parser.parse_known_args(argv)

    print("[OVERLAY_REMOTE] ========================================")
    print("[OVERLAY_REMOTE] SignFlow Overlay - Remote Mode")
    print(f"[OVERLAY_REMOTE] Server: {args.server}")
    print("[OVERLAY_REMOTE] Camera starts when you click the webcam button")
    print("[OVERLAY_REMOTE] ========================================")

    scan_available_cameras()

    defaults, preferences = ensure_preferences_files()

    if QApplication is None:
        raise RuntimeError('PyQt5 is required to run the overlay. Please install it via pip install pyqt5')

    app = QApplication([sys.argv[0], *qt_args])
    app.setQuitOnLastWindowClosed(True)

    overlay = RemoteOverlayWindow(
        defaults=defaults,
        preferences=preferences,
        debug_captions=False,
        enable_logging=False,
        server_url=args.server,
    )
    overlay.show()
    overlay.raise_()

    if args.auto_webcam and not args.no_webcam:
        print(f"[OVERLAY_REMOTE] Scheduling webcam auto-start in {AUTO_WEBCAM_DELAY_MS}ms...")
        QTimer.singleShot(AUTO_WEBCAM_DELAY_MS, overlay.auto_start_webcam)

    sys.exit(app.exec_())
