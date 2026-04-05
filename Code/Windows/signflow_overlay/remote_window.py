from __future__ import annotations

from overlay_window import OverlayWindow

from .config import DEFAULT_SERVER_URL
from .remote_worker import RemoteHandTrackingWorker


class RemoteOverlayWindow(OverlayWindow):
    """Overlay window variant that delegates prediction to the remote API server."""

    def __init__(self, *args, server_url=DEFAULT_SERVER_URL, **kwargs):
        self._remote_server_url = server_url
        super().__init__(*args, **kwargs)
        print(f"[OVERLAY_REMOTE] Window initialized. Server: {server_url}")

    def _prediction_init_message(self) -> str:
        return "connecting to model server..."

    def _create_hand_worker(self):
        print("[OVERLAY_REMOTE] Creating RemoteHandTrackingWorker...")
        return RemoteHandTrackingWorker(
            server_url=self._remote_server_url,
            flip_horizontal=self.flip_input,
            primary_hand_only=self.primary_hand_only,
        )

    def auto_start_webcam(self):
        print("[OVERLAY_REMOTE] Auto-starting webcam mode...")
        self.secondary_panel.set_webcam_active(True)
        self.on_webcam_toggled(True)
