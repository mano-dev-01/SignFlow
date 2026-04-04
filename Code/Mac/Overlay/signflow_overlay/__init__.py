# Ensure no BOM corrupts import path processing.
import sys
import os

# macOS-specific initialization
if sys.platform == "darwin":
    print("[signflow_overlay] Initializing for macOS")
    # Enable native macOS frameworks
    os.environ.setdefault("QT_QPA_PLATFORM", "cocoa")
    os.environ.setdefault("DYLD_LIBRARY_PATH", "/usr/local/lib:/opt/local/lib")

from .api_client import SignFlowAPIClient
from .remote_worker import RemoteHandTrackingWorker
from .remote_window import RemoteOverlayWindow

__all__ = [
    "RemoteHandTrackingWorker",
    "RemoteOverlayWindow",
    "SignFlowAPIClient",
]
