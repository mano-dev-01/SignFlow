import os
import sys
from pathlib import Path

DEFAULT_DEPLOYED_SERVER_URL = "https://mano-dev-01-signflow-inference.hf.space"


def _read_installed_server_url() -> str | None:
    if not getattr(sys, "frozen", False):
        return None

    candidate = Path(sys.executable).resolve().parent / "server_url.txt"
    if not candidate.exists():
        return None

    try:
        value = candidate.read_text(encoding="utf-8").strip()
    except OSError:
        return None

    return value or None


DEFAULT_SERVER_URL = (
    os.environ.get("SIGNFLOW_SERVER_URL")
    or _read_installed_server_url()
    or DEFAULT_DEPLOYED_SERVER_URL
)
DEFAULT_PREDICT_INTERVAL = 0.15
SERVER_HEALTH_TIMEOUT_SECONDS = 5
SERVER_REQUEST_TIMEOUT_SECONDS = 10
SERVER_CONNECT_RETRIES = 10
SERVER_RETRY_DELAY_SECONDS = 2.0
MIN_SERVER_BUFFER_FRAMES = 5
EXTRACT_EVERY_N_FRAMES = 4
NO_HANDS_BUFFER_RESET_FRAMES = 90
CAMERA_SCAN_LIMIT = 5
AUTO_WEBCAM_DELAY_MS = 800
IPC_SERVER_NAME = "signflow_overlay_ipc_v2"
