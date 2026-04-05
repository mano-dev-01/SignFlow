from __future__ import annotations

import json
import threading
import time
import traceback
from collections import deque

try:
    import numpy as np
except ImportError:
    np = None
    print('[CLIENT] WARNING: numpy is not installed. falling back to list-based operations. run `pip install numpy` for best results.')

import urllib.error
import urllib.request

from .config import (
    DEFAULT_PREDICT_INTERVAL,
    DEFAULT_SERVER_URL,
    MIN_SERVER_BUFFER_FRAMES,
    SERVER_CONNECT_RETRIES,
    SERVER_HEALTH_TIMEOUT_SECONDS,
    SERVER_REQUEST_TIMEOUT_SECONDS,
    SERVER_RETRY_DELAY_SECONDS,
)


class SignFlowAPIClient:
    """
    Background client that buffers landmark frames and periodically queries the
    remote SignFlow prediction API.
    """

    def __init__(self, server_url=DEFAULT_SERVER_URL, predict_interval=DEFAULT_PREDICT_INTERVAL):
        self.server_url = server_url.rstrip("/")
        self.predict_interval = predict_interval

        self._buffer = deque(maxlen=60)
        self._lock = threading.Lock()
        self._latest_prediction = None
        self._running = True
        self._connected = False
        self._last_error = None
        self._thread = threading.Thread(target=self._predict_loop, daemon=True, name="sf-api-client")

        print("[CLIENT] SignFlowAPIClient created")
        print(f"[CLIENT]   Server URL: {self.server_url}")
        print(f"[CLIENT]   Predict interval: {self.predict_interval}s")

    def start(self):
        print("[CLIENT] Starting background prediction thread...")
        self._thread.start()
        print("[CLIENT] Background thread started")

    def stop(self):
        print("[CLIENT] Stopping...")
        self._running = False
        if self._thread.is_alive():
            self._thread.join(timeout=3)
        print("[CLIENT] Stopped")

    @property
    def buffer_size(self):
        with self._lock:
            return len(self._buffer)

    @property
    def connected(self):
        return self._connected

    def _request_json(self, path: str, *, method: str, payload: bytes | None = None, timeout: int = 5):
        request = urllib.request.Request(
            f"{self.server_url}{path}",
            data=payload,
            headers={"Content-Type": "application/json"} if payload is not None else {},
            method=method,
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode())

    def check_server(self):
        print(f"[CLIENT] Checking server health at {self.server_url}/health...")
        try:
            data = self._request_json(
                "/health",
                method="GET",
                timeout=SERVER_HEALTH_TIMEOUT_SECONDS,
            )
            self._connected = data.get("status", "unknown") == "ok"
            print(
                f"[CLIENT] Server health: status={data.get('status', 'unknown')}, "
                f"device={data.get('device', 'unknown')}"
            )
            return self._connected
        except Exception as exc:
            self._connected = False
            self._last_error = str(exc)
            print(f"[CLIENT] Server health check FAILED: {exc}")
            return False

    def add_frame(self, landmarks):
        if landmarks is None:
            return

        if np is None:
            # Structure-check fallback when numpy is unavailable.
            try:
                landmarks = list(landmarks)
                if len(landmarks) != 92 or any(len(row) != 3 for row in landmarks):
                    raise ValueError
            except Exception:
                print("[CLIENT] WARNING: Ignoring frame with bad shape (fallback check). expected 92x3")
                return
            with self._lock:
                self._buffer.append(landmarks)
            return

        if not isinstance(landmarks, np.ndarray):
            try:
                landmarks = np.array(landmarks, dtype=np.float32)
            except Exception as err:
                print(f"[CLIENT] WARNING: Failed to convert landmarks to numpy array: {err}")
                return

        if getattr(landmarks, 'shape', None) != (92, 3):
            print(
                f"[CLIENT] WARNING: Ignoring frame with bad shape {getattr(landmarks, 'shape', None)}, expected (92, 3)"
            )
            return

        with self._lock:
            self._buffer.append(landmarks.copy())

    def clear_buffer(self):
        with self._lock:
            self._buffer.clear()
        print("[CLIENT] Buffer cleared")

    def get_latest_prediction(self):
        with self._lock:
            return self._latest_prediction

    def _snapshot_buffer(self):
        with self._lock:
            if len(self._buffer) < MIN_SERVER_BUFFER_FRAMES:
                return None
            return list(self._buffer)

    def _store_prediction(self, prediction: dict):
        with self._lock:
            self._latest_prediction = prediction

    def _predict_loop(self):
        print("[CLIENT] Prediction loop started")

        for attempt in range(SERVER_CONNECT_RETRIES):
            if not self._running:
                return
            if self.check_server():
                break
            print(
                f"[CLIENT] Server not ready, attempt {attempt + 1}/{SERVER_CONNECT_RETRIES}, "
                f"retrying in {SERVER_RETRY_DELAY_SECONDS:.0f}s..."
            )
            time.sleep(SERVER_RETRY_DELAY_SECONDS)

        if not self._connected:
            print("[CLIENT] WARNING: Could not connect to server during startup.")
            print("[CLIENT] Will keep retrying in the background...")

        while self._running:
            time.sleep(self.predict_interval)
            if not self._running:
                break

            frames = self._snapshot_buffer()
            if frames is None:
                continue

            if not self._connected and not self.check_server():
                continue

            try:
                payload = json.dumps({"frames": [frame.tolist() for frame in frames]}).encode("utf-8")
                started = time.time()
                data = self._request_json(
                    "/predict",
                    method="POST",
                    payload=payload,
                    timeout=SERVER_REQUEST_TIMEOUT_SECONDS,
                )
                roundtrip_ms = (time.time() - started) * 1000

                prediction = {
                    "sign": data.get("sign", "unknown"),
                    "confidence": data.get("confidence", 0.0),
                    "top5": data.get("top5", []),
                    "inference_ms": data.get("inference_ms", 0),
                    "roundtrip_ms": round(roundtrip_ms, 1),
                }
                print(
                    f"[CLIENT] Prediction: {prediction['sign']} ({prediction['confidence']:.0%}) "
                    f"| server={prediction['inference_ms']}ms | roundtrip={roundtrip_ms:.0f}ms "
                    f"| buf={len(frames)}"
                )
                self._store_prediction(prediction)
                self._connected = True
            except urllib.error.URLError as exc:
                self._connected = False
                self._last_error = str(exc)
                print(f"[CLIENT] Server request failed: {exc}")
            except Exception as exc:
                self._last_error = str(exc)
                print(f"[CLIENT] Prediction error: {exc}")

        print("[CLIENT] Prediction loop ended")
