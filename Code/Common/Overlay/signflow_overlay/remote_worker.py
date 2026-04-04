from __future__ import annotations

import threading
import time
from collections import deque

import numpy as np

try:
    from PyQt5.QtCore import QThread, pyqtSignal
except ImportError:
    print('[REMOTE_WORKER] WARNING: PyQt5 is not installed. overlay GUI will not work. run pip install pyqt5')

    class QThread:
        def __init__(self, *args, **kwargs):
            raise ImportError('PyQt5 is required for RemoteHandTrackingWorker')

        def start(self):
            raise ImportError('PyQt5 is required for RemoteHandTrackingWorker')

        def isRunning(self):
            return False

    def pyqtSignal(*args, **kwargs):
        def no_op(*a, **k):
            raise ImportError('PyQt5 is required for RemoteHandTrackingWorker')

        return no_op

from signflow_landmark_extractor import create_extractor

from .api_client import SignFlowAPIClient
from .config import (
    DEFAULT_SERVER_URL,
    EXTRACT_EVERY_N_FRAMES,
    NO_HANDS_BUFFER_RESET_FRAMES,
)

_HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
]
_POSE_CONNECTIONS = [(1, 2), (1, 3), (2, 4), (3, 5), (4, 6), (1, 7), (2, 8)]


def _draw_cached_landmarks(image, landmarks):
    if landmarks is None:
        return image

    try:
        import cv2
    except ImportError:
        return image

    height, width = image.shape[:2]
    output = image.copy()

    def point(index):
        return int(landmarks[index, 0] * width), int(landmarks[index, 1] * height)

    def visible(index):
        return landmarks[index, 0] != 0 or landmarks[index, 1] != 0

    for offset, line_color, dot_color in ((40, (0, 210, 90), (0, 255, 120)), (61, (80, 170, 255), (100, 200, 255))):
        for start, end in _HAND_CONNECTIONS:
            index_a = offset + start
            index_b = offset + end
            if visible(index_a) and visible(index_b):
                cv2.line(output, point(index_a), point(index_b), line_color, 2, cv2.LINE_AA)
        for index in range(offset, offset + 21):
            if visible(index):
                cv2.circle(output, point(index), 4, dot_color, -1, cv2.LINE_AA)

    for start, end in _POSE_CONNECTIONS:
        index_a = 82 + start
        index_b = 82 + end
        if index_a < 92 and index_b < 92 and visible(index_a) and visible(index_b):
            cv2.line(output, point(index_a), point(index_b), (255, 220, 0), 2, cv2.LINE_AA)
    for index in range(82, 92):
        if visible(index):
            cv2.circle(output, point(index), 5, (255, 240, 0), -1, cv2.LINE_AA)

    for index in range(40):
        if visible(index):
            cv2.circle(output, point(index), 2, (255, 130, 190), -1, cv2.LINE_AA)

    return output


class RemoteHandTrackingWorker(QThread):
    """Remote-mode worker that keeps UI display, extraction, and API calls decoupled."""

    status_updated = pyqtSignal(dict)
    frame_processed = pyqtSignal(object)
    fps_updated = pyqtSignal(float)
    prediction_updated = pyqtSignal(str)

    def set_model_file(self, model_file: str) -> bool:
        print(f"[REMOTE_WORKER] set_model_file called, not supported in remote mode: {model_file}")
        return False

    def clear_model_file(self):
        print("[REMOTE_WORKER] clear_model_file called")

    def __init__(
        self,
        server_url=DEFAULT_SERVER_URL,
        flip_horizontal=False,
        primary_hand_only=True,
        mediapipe_models_dir=None,
    ):
        super().__init__()
        self._server_url = server_url
        self._mediapipe_dir = mediapipe_models_dir
        self._running = True

        self._config_lock = threading.Lock()
        self._flip_horizontal = bool(flip_horizontal)
        self._primary_hand_only = bool(primary_hand_only)

        self._display_queue = deque(maxlen=1)
        self._display_lock = threading.Lock()
        self._display_event = threading.Event()

        self._extraction_queue = deque(maxlen=1)
        self._extraction_lock = threading.Lock()
        self._extraction_event = threading.Event()

        self._landmark_lock = threading.Lock()
        self._cached_landmarks = None
        self._hands_visible = False

        self._extractor = None
        self._extractor_ready = threading.Event()
        self._extractor_error = None
        self._api_client = None
        self._last_emitted_sign = None
        self._hands_lost_frames = 0

        print(f"[REMOTE_WORKER] Created  server={server_url}")

    @property
    def available(self):
        return True

    def set_flip_horizontal(self, enabled: bool):
        with self._config_lock:
            self._flip_horizontal = bool(enabled)
        print(f"[REMOTE_WORKER] flip_horizontal={enabled}")

    def set_primary_hand_only(self, enabled: bool):
        with self._config_lock:
            self._primary_hand_only = bool(enabled)

    def submit(self, frame: dict):
        if frame is None or not self._running:
            return
        with self._display_lock:
            self._display_queue.clear()
            self._display_queue.append(frame)
        self._display_event.set()

    def _init_extractor(self):
        print("[REMOTE_WORKER][ext-init] Loading MediaPipe models (background)...")
        try:
            self._extractor = create_extractor(self._mediapipe_dir)
            print("[REMOTE_WORKER][ext-init] MediaPipe ready!")
        except Exception as exc:
            self._extractor_error = str(exc)
            print(f"[REMOTE_WORKER][ext-init] FAILED: {exc}")
        finally:
            self._extractor_ready.set()

    def _queue_for_extraction(self, image, width, height):
        with self._extraction_lock:
            self._extraction_queue.clear()
            self._extraction_queue.append((image, width, height))
        self._extraction_event.set()

    def _read_extraction_input(self):
        with self._extraction_lock:
            return self._extraction_queue.pop() if self._extraction_queue else None

    def _update_cached_landmarks(self, landmarks, hands_visible):
        with self._landmark_lock:
            self._cached_landmarks = landmarks
            self._hands_visible = hands_visible

    def _read_cached_landmarks(self):
        with self._landmark_lock:
            return self._cached_landmarks, self._hands_visible

    def _extraction_thread(self):
        print("[REMOTE_WORKER][ext] Extraction thread started")
        self._extractor_ready.wait()

        if self._extractor is None:
            print(f"[REMOTE_WORKER][ext] No extractor ({self._extractor_error}) - thread exiting")
            return

        print("[REMOTE_WORKER][ext] Extraction loop running")
        extraction_count = 0

        while self._running:
            if not self._extraction_event.wait(1.0):
                continue
            self._extraction_event.clear()

            item = self._read_extraction_input()
            if item is None:
                continue

            image, width, height = item
            try:
                started = time.perf_counter()
                landmarks, hands_visible = self._extractor.extract(image)
                extraction_ms = (time.perf_counter() - started) * 1000

                self._update_cached_landmarks(landmarks, hands_visible)
                self._api_client.add_frame(landmarks)

                extraction_count += 1
                if extraction_count % 30 == 1:
                    print(
                        f"[REMOTE_WORKER][ext] #{extraction_count}  "
                        f"hands={'yes' if hands_visible else 'no'}  "
                        f"extr={extraction_ms:.0f}ms  "
                        f"buf={self._api_client.buffer_size}  "
                        f"server={'ok' if self._api_client.connected else 'connecting'}"
                    )
            except Exception as exc:
                print(f"[REMOTE_WORKER][ext] Extraction error: {exc}")

        print("[REMOTE_WORKER][ext] Extraction thread done")

    def _decode_frame(self, frame):
        rgb_bytes = frame.get("rgb")
        width = int(frame.get("width", 0) or 0)
        height = int(frame.get("height", 0) or 0)
        if not rgb_bytes or width <= 0 or height <= 0:
            return None, 0, 0

        with self._config_lock:
            flip_horizontal = self._flip_horizontal

        image = np.frombuffer(rgb_bytes, dtype=np.uint8).reshape(height, width, 3)
        if flip_horizontal:
            image = image[:, ::-1, :].copy()
        else:
            image = np.ascontiguousarray(image)
        return image, width, height

    def _emit_status(self, width, height, flip_horizontal, hands_visible):
        self.status_updated.emit(
            {
                "hands_detected": 1 if hands_visible else 0,
                "left_conf": 0.0,
                "right_conf": 0.0,
                "prediction": self._last_emitted_sign or "...",
                "prediction_conf": 0.0,
                "input_w": width,
                "input_h": height,
                "det_w": width,
                "det_h": height,
                "det_scale": 1.0,
                "pad_x": 0,
                "pad_y": 0,
                "flip": flip_horizontal,
                "model_loaded": self._api_client.connected,
                "model_name": "remote_server",
                "hand_label": "Remote",
                "processing_ms": 0.0,
            }
        )

    def _emit_prediction_if_needed(self):
        prediction = self._api_client.get_latest_prediction()
        if prediction is None:
            return
        sign = prediction.get("sign", "")
        confidence = prediction.get("confidence", 0.0)
        if sign and sign != self._last_emitted_sign:
            print(f"[REMOTE_WORKER] >>> Prediction: {sign} ({confidence:.0%})")
            self._last_emitted_sign = sign
            self.prediction_updated.emit(sign)

    def run(self):
        print("[REMOTE_WORKER] =============================================")
        print("[REMOTE_WORKER] Display thread started")

        threading.Thread(target=self._init_extractor, daemon=True, name="sf-mp-init").start()

        self._api_client = SignFlowAPIClient(server_url=self._server_url)
        self._api_client.start()
        print("[REMOTE_WORKER] API client started")

        extraction_thread = threading.Thread(
            target=self._extraction_thread,
            daemon=True,
            name="sf-extr",
        )
        extraction_thread.start()
        print("[REMOTE_WORKER] Extraction thread started")
        print("[REMOTE_WORKER] Display loop running - camera visible immediately")

        extract_frame_counter = 0
        last_fps_emit = 0.0
        last_status_emit = 0.0
        fps = 0.0
        last_frame_time = None

        try:
            while self._running:
                if not self._display_event.wait(0.5):
                    continue
                self._display_event.clear()

                with self._display_lock:
                    frame = self._display_queue.pop() if self._display_queue else None
                if frame is None:
                    continue

                try:
                    image, width, height = self._decode_frame(frame)
                except Exception as exc:
                    print(f"[REMOTE_WORKER] Decode error: {exc}")
                    continue
                if image is None:
                    continue

                with self._config_lock:
                    flip_horizontal = self._flip_horizontal

                extract_frame_counter += 1
                if extract_frame_counter >= EXTRACT_EVERY_N_FRAMES:
                    extract_frame_counter = 0
                    if self._extractor_ready.is_set() and self._extractor is not None:
                        self._queue_for_extraction(image, width, height)

                cached_landmarks, hands_visible = self._read_cached_landmarks()
                if cached_landmarks is not None:
                    annotated = _draw_cached_landmarks(image, cached_landmarks)
                    emit_frame = {
                        "rgb": annotated.tobytes(),
                        "width": width,
                        "height": height,
                    }
                else:
                    emit_frame = frame

                self.frame_processed.emit(emit_frame)

                if not hands_visible:
                    self._hands_lost_frames += 1
                    if self._hands_lost_frames == NO_HANDS_BUFFER_RESET_FRAMES:
                        print("[REMOTE_WORKER] No hands for 3s - clearing API buffer")
                        self._api_client.clear_buffer()
                        self._last_emitted_sign = None
                else:
                    self._hands_lost_frames = 0

                now = time.perf_counter()
                if last_frame_time is not None and (now - last_frame_time) > 1e-6:
                    fps = fps * 0.85 + (1.0 / (now - last_frame_time)) * 0.15
                last_frame_time = now

                if now - last_fps_emit > 0.1:
                    self.fps_updated.emit(fps)
                    last_fps_emit = now

                if now - last_status_emit > 0.2:
                    self._emit_status(width, height, flip_horizontal, hands_visible)
                    last_status_emit = now

                self._emit_prediction_if_needed()
        finally:
            print("[REMOTE_WORKER] Shutting down...")
            self._running = False
            self._extraction_event.set()
            if self._api_client is not None:
                self._api_client.stop()
            if self._extractor is not None:
                self._extractor.close()
            print("[REMOTE_WORKER] Done")

    def stop(self):
        print("[REMOTE_WORKER] stop() called")
        self._running = False
        self._display_event.set()
        self.wait(2000)
