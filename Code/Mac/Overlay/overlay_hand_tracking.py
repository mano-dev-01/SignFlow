import importlib
import os
import sys
import threading
import time
import traceback
from collections import deque
from pathlib import Path
from overlay_paths import get_models_dir

import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

from overlay_constants import SIGN_PREDICTION_MIN_CONFIDENCE

# Debug logging to file
_DEBUG_LOG_FILE = "/tmp/signflow_hand_tracking_debug.log"
def _debug_log(message):
    try:
        with open(_DEBUG_LOG_FILE, "a") as f:
            f.write(f"[{time.time():.2f}] {message}\n")
            f.flush()
    except:
        pass

_debug_log("=== overlay_hand_tracking module loaded ===")

ROOT_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT_DIR / "Model_inference"
for path in [str(ROOT_DIR), str(MODEL_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)
        print(f"[overlay_hand_tracking] added to sys.path: {path}")

try:
    from Model_inference.static_classifier import build_hand_features, zero_hand_features
except Exception as exc:
    print("[overlay_hand_tracking] ERROR: Failed to import Model_inference.static_classifier")
    traceback.print_exc()
    build_hand_features = None
    zero_hand_features = None


def _safe_import(module_name: str):
    try:
        return importlib.import_module(module_name)
    except Exception:  # pragma: no cover - allow runtime without optional deps
        return None

# Import remote inference client
try:
    from remote_inference_client import get_remote_client
    _remote_inference_available = True
except Exception:
    _remote_inference_available = False
    _debug_log("WARNING: remote_inference_client not available")

from overlay_constants import (
    DETECTION_MAX_DIM,
    DETECTION_MIN_DIM,
    ENABLE_DETECTION_RESIZE,
    ENABLE_DETECTION_SQUARE,
)


class HandTracker:
    def __init__(self, primary_hand_only: bool = True, use_remote_model: bool = False, remote_endpoint: str = None):
        self.available = False
        self._primary_hand_only = bool(primary_hand_only)
        self._initialized = False
        self._model = None
        self._model_name = None
        self._use_remote_model = bool(use_remote_model)
        self._remote_client = None
        self._remote_endpoint = remote_endpoint or "https://mano-dev-01-signflow-inference.hf.space"
        self.last_features = None
        self.last_left_features = None
        self.last_right_features = None
        self.last_status = {
            "hands_detected": 0,
            "left_conf": 0.0,
            "right_conf": 0.0,
            "prediction": "No Hand",
            "prediction_conf": 0.0,
        }
        self._joblib = None
        self._cv2 = None
        self._mp = None
        self._mp_hands = None
        self._mp_draw = None
        self._hands = None
        self._landmark_pb2 = None
        self._custom_model_path = None

    @property
    def primary_hand_only(self):
        return self._primary_hand_only

    def initialize(self):
        if self._initialized:
            return
        self._initialized = True
        self._joblib = _safe_import("joblib")
        self._cv2 = _safe_import("cv2")
        self._mp = _safe_import("mediapipe")
        msg = f"HandTracker.initialize: joblib={self._joblib is not None}, cv2={self._cv2 is not None}, mediapipe={self._mp is not None}"
        print(f"[{msg}]")
        _debug_log(msg)

        if self._joblib is not None:
            self._load_model()

        if self._mp is None:
            _debug_log("HandTracker.initialize: ERROR: mediapipe failed to import")
            print("[HandTracker.initialize] ERROR: mediapipe failed to import")
            self.available = False
            return

        try:
            self._mp_hands = self._mp.solutions.hands
            self._mp_draw = self._mp.solutions.drawing_utils
            _debug_log("HandTracker.initialize: mediapipe.solutions loaded successfully")
            print("[HandTracker.initialize] mediapipe.solutions loaded successfully")
        except Exception as e:
            msg = f"HandTracker.initialize: ERROR loading solutions: {e}"
            _debug_log(msg)
            print(f"[{msg}]")
            self.available = False
            return
        
        try:
            from mediapipe.framework.formats import landmark_pb2
        except Exception as e:
            print(f"[HandTracker.initialize] WARNING: landmark_pb2 import failed: {e}")
            landmark_pb2 = None
        self._landmark_pb2 = landmark_pb2
        self._build_hands()
        _debug_log(f"HandTracker.initialize: MediaPipe initialization complete. available={self.available}")
        print(f"[HandTracker.initialize] MediaPipe initialization complete. available={self.available}")

    def _load_model(self):
        self._model = None
        self._model_name = None
        
        # Try remote inference first if enabled
        if self._use_remote_model and _remote_inference_available:
            try:
                _debug_log(f"Loading remote model from {self._remote_endpoint}")
                self._remote_client = get_remote_client(self._remote_endpoint)
                if self._remote_client.available:
                    self._model_name = f"Remote:{self._remote_endpoint}"
                    self._model = self._remote_client
                    _debug_log("✅ Remote model client initialized")
                    return
            except Exception as e:
                _debug_log(f"Failed to initialize remote model: {e}")
        
        # Fallback to local model if available
        if self._joblib is None:
            return
        
        _debug_log("Falling back to local model")
        self._model = None
        self._model_name = None

        if self._custom_model_path:
            if self._try_load_model(Path(self._custom_model_path)):
                return
            # fallback to default model source when custom model fails
            self._custom_model_path = None

        models_dir = get_models_dir()
        candidate_paths = [
            models_dir / "static_model.pkl",
            models_dir / "model___.pkl",
        ]
        for model_path in candidate_paths:
            if self._try_load_model(model_path):
                break

    def _try_load_model(self, model_path: Path) -> bool:
        if model_path is None or not model_path.exists():
            return False
        try:
            self._model = self._joblib.load(os.fspath(model_path))
            self._model_name = model_path.name
            return True
        except Exception:
            self._model = None
            self._model_name = None
            return False

    def set_model_path(self, model_file: str) -> bool:
        if not model_file:
            return False
        model_path = Path(model_file)
        if not model_path.exists() or not model_path.is_file():
            return False

        if not self._joblib:
            return False

        self._custom_model_path = model_file
        if self._try_load_model(model_path):
            return True

        self._custom_model_path = None
        return False

    def clear_model_path(self):
        self._custom_model_path = None
        if self._joblib is not None:
            self._load_model()

    def _build_hands(self):
        if self._mp_hands is None:
            _debug_log("HandTracker._build_hands: ERROR: _mp_hands is None")
            print("[HandTracker._build_hands] ERROR: _mp_hands is None")
            self.available = False
            return
        max_hands = 1 if self._primary_hand_only else 2
        try:
            _debug_log(f"HandTracker._build_hands: Creating Hands detector with max_hands={max_hands}")
            print(f"[HandTracker._build_hands] Creating Hands detector with max_hands={max_hands}")
            self._hands = self._mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=max_hands,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.7,
            )
            self.available = True
            _debug_log("HandTracker._build_hands: Hands detector created successfully. available=True")
            print("[HandTracker._build_hands] Hands detector created successfully. available=True")
        except Exception as e:
            msg = f"HandTracker._build_hands: ERROR creating Hands detector: {e}"
            _debug_log(msg)
            print(f"[{msg}]")
            import traceback
            traceback.print_exc()
            self._hands = None
            self.available = False

    def reconfigure(self, primary_hand_only: bool):
        primary_hand_only = bool(primary_hand_only)
        if primary_hand_only == self._primary_hand_only and self._hands is not None:
            return
        self._primary_hand_only = primary_hand_only
        if not self._initialized:
            return
        self._close_hands()
        self._build_hands()

    def _close_hands(self):
        if self._hands is not None:
            try:
                self._hands.close()
            except Exception:
                pass
        self._hands = None

    def close(self):
        self._close_hands()

    def process(self, frame: dict, flip_horizontal: bool = False):
        if not self.available or self._hands is None or frame is None:
            if frame is not None and not self.available:
                print(f"[HandTracker.process] Skipping: available={self.available}, has_hands={self._hands is not None}")
            return frame, self.last_status

        rgb = frame.get("rgb")
        width = int(frame.get("width", 0) or 0)
        height = int(frame.get("height", 0) or 0)
        if rgb is None or width <= 0 or height <= 0:
            return frame, self.last_status

        start_time = time.perf_counter()
        image = np.frombuffer(rgb, dtype=np.uint8).reshape(height, width, 3).copy()
        if flip_horizontal:
            image = image[:, ::-1, :].copy()

        det_image = image
        resized = False
        padded = False
        scale = 1.0
        pad_x = 0
        pad_y = 0
        if ENABLE_DETECTION_RESIZE and self._cv2 is not None:
            max_dim = max(width, height)
            if max_dim > DETECTION_MAX_DIM:
                scale = DETECTION_MAX_DIM / float(max_dim)
            elif max_dim < DETECTION_MIN_DIM:
                scale = DETECTION_MIN_DIM / float(max_dim)
            if abs(scale - 1.0) > 1e-3:
                new_w = max(1, int(width * scale))
                new_h = max(1, int(height * scale))
                det_image = self._cv2.resize(
                    det_image,
                    (new_w, new_h),
                    interpolation=self._cv2.INTER_AREA if scale < 1.0 else self._cv2.INTER_LINEAR,
                )
                resized = True

        if ENABLE_DETECTION_SQUARE:
            h, w = det_image.shape[:2]
            side = max(h, w)
            if h != w:
                square = np.zeros((side, side, 3), dtype=det_image.dtype)
                pad_x = int((side - w) // 2)
                pad_y = int((side - h) // 2)
                square[pad_y : pad_y + h, pad_x : pad_x + w] = det_image
                det_image = square
                padded = True

        results = self._hands.process(det_image)

        left_features = None
        right_features = None
        left_conf = 0.0
        right_conf = 0.0
        unknown_features = []
        prediction_text = "No Hand"
        prediction_conf = 0.0
        label = None

        if results.multi_hand_landmarks:
            det_h, det_w = det_image.shape[:2]

            def draw_landmarks(hand_lms):
                if self._mp_draw is None or self._mp_hands is None:
                    return
                if self._landmark_pb2 is not None and det_w > 0 and det_h > 0:
                    adjusted = self._landmark_pb2.NormalizedLandmarkList()
                    for lm in hand_lms.landmark:
                        x_det = lm.x * det_w
                        y_det = lm.y * det_h
                        x_unpad = x_det - pad_x
                        y_unpad = y_det - pad_y
                        x_orig = x_unpad / scale
                        y_orig = y_unpad / scale
                        x_norm = x_orig / float(width)
                        y_norm = y_orig / float(height)
                        if x_norm < 0.0:
                            x_norm = 0.0
                        elif x_norm > 1.0:
                            x_norm = 1.0
                        if y_norm < 0.0:
                            y_norm = 0.0
                        elif y_norm > 1.0:
                            y_norm = 1.0
                        adjusted.landmark.append(
                            self._landmark_pb2.NormalizedLandmark(x=x_norm, y=y_norm, z=lm.z)
                        )
                    self._mp_draw.draw_landmarks(image, adjusted, self._mp_hands.HAND_CONNECTIONS)
                else:
                    self._mp_draw.draw_landmarks(image, hand_lms, self._mp_hands.HAND_CONNECTIONS)

            for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                if self._primary_hand_only and idx > 0:
                    break
                draw_landmarks(hand_landmarks)
                
                # Extract features if available
                if build_hand_features is None:
                    features = None
                    _debug_log("WARNING: build_hand_features is None, skipping feature extraction")
                else:
                    try:
                        features = build_hand_features(hand_landmarks.landmark)
                    except Exception as e:
                        _debug_log(f"ERROR extracting features: {e}")
                        features = None

                score = 0.0
                hand_label = None
                if results.multi_handedness and len(results.multi_handedness) > idx:
                    classification = results.multi_handedness[idx].classification
                    if classification:
                        hand_label = classification[0].label
                        score = float(classification[0].score)

                if label is None and hand_label:
                    label = hand_label

                if hand_label == "Right":
                    if right_features is None or score >= right_conf:
                        right_features = features
                        right_conf = score
                elif hand_label == "Left":
                    if left_features is None or score >= left_conf:
                        left_features = features
                        left_conf = score
                else:
                    unknown_features.append((features, score))

            if right_features is None and unknown_features:
                right_features, right_conf = unknown_features.pop(0)
            if left_features is None and unknown_features:
                left_features, left_conf = unknown_features.pop(0)

        if results.multi_hand_landmarks:
            primary = right_features if right_features is not None else zero_hand_features()
            secondary = left_features if left_features is not None else zero_hand_features()
            only_primary_hand = 1 if right_features is not None and left_features is None else 0

            self.last_features = [only_primary_hand] + primary + secondary
            self.last_left_features = left_features
            self.last_right_features = right_features

            if self._model is not None:
                features = np.array(self.last_features, dtype=np.float32).reshape(1, -1)
                
                # Handle remote model inference
                if self._remote_client is not None and isinstance(self._model, type(self._remote_client)):
                    try:
                        _debug_log("Using remote model for prediction")
                        prediction_text = self._model.predict(features)
                        probs = self._model.predict_proba(features)[0]
                        prediction_conf = float(np.max(probs)) if len(probs) > 0 else 0.0
                    except Exception as e:
                        _debug_log(f"Remote prediction failed: {e}")
                        prediction_text = "Error"
                        prediction_conf = 0.0
                # Handle local model inference
                else:
                    try:
                        probs = self._model.predict_proba(features)[0]
                        prediction_conf = float(np.max(probs))
                        if prediction_conf >= SIGN_PREDICTION_MIN_CONFIDENCE:
                            prediction_text = self._model.predict(features)[0]
                        else:
                            prediction_text = "Uncertain"
                    except Exception as e:
                        _debug_log(f"Local prediction failed: {e}")
                        prediction_text = "Error"
                        prediction_conf = 0.0
            else:
                prediction_text = "No Model"

        hands_detected = len(results.multi_hand_landmarks) if results.multi_hand_landmarks else 0
        det_h, det_w = det_image.shape[:2]
        processing_ms = (time.perf_counter() - start_time) * 1000.0

        self.last_status = {
            "hands_detected": hands_detected,
            "left_conf": left_conf,
            "right_conf": right_conf,
            "prediction": prediction_text,
            "prediction_conf": prediction_conf,
            "input_w": width,
            "input_h": height,
            "det_w": det_w,
            "det_h": det_h,
            "det_scale": scale,
            "pad_x": pad_x,
            "pad_y": pad_y,
            "flip": bool(flip_horizontal),
            "model_loaded": self._model is not None,
            "model_name": self._model_name if self._model is not None else None,
            "hand_label": label or "Unknown",
            "processing_ms": processing_ms,
        }

        out_frame = dict(frame)
        out_frame["rgb"] = image.tobytes()
        return out_frame, self.last_status


class HandTrackingWorker(QThread):
    status_updated = pyqtSignal(dict)
    frame_processed = pyqtSignal(object)
    fps_updated = pyqtSignal(float)
    prediction_updated = pyqtSignal(str)

    def __init__(self, flip_horizontal: bool = False, primary_hand_only: bool = True, use_remote_model: bool = False, remote_endpoint: str = None):
        super().__init__()
        self._tracker = None
        self._flip_horizontal = bool(flip_horizontal)
        self._primary_hand_only = bool(primary_hand_only)
        self._use_remote_model = bool(use_remote_model)
        self._remote_endpoint = remote_endpoint or "https://mano-dev-01-signflow-inference.hf.space"
        self._pending_reconfigure = False
        self._queue = deque(maxlen=1)
        self._lock = threading.Lock()
        self._config_lock = threading.Lock()
        self._event = threading.Event()
        self._running = True
        self._fps = 0.0
        self._last_time = None
        self._custom_model_file = None

    @property
    def available(self):
        return bool(self._tracker and self._tracker.available)

    def set_flip_horizontal(self, enabled: bool):
        with self._config_lock:
            self._flip_horizontal = bool(enabled)
        self._event.set()

    def set_primary_hand_only(self, enabled: bool):
        with self._config_lock:
            enabled = bool(enabled)
            if enabled != self._primary_hand_only:
                self._primary_hand_only = enabled
                self._pending_reconfigure = True
        self._event.set()

    def set_model_file(self, model_file: str) -> bool:
        if not model_file:
            return False
        if self._tracker is None:
            self._custom_model_file = model_file
            return True
        success = self._tracker.set_model_path(model_file)
        if success:
            self._custom_model_file = model_file
        return success

    def clear_model_file(self):
        if self._tracker is not None:
            self._tracker.clear_model_path()

    def _snapshot_config(self):
        with self._config_lock:
            flip = self._flip_horizontal
            primary_only = self._primary_hand_only
            reconfigure = self._pending_reconfigure
            self._pending_reconfigure = False
        return flip, primary_only, reconfigure

    def _ensure_tracker(self, primary_only: bool):
        if self._tracker is None:
            _debug_log(f"Creating HandTracker (primary_only={primary_only}, remote={self._use_remote_model})")
            print(f"[HandTrackingWorker._ensure_tracker] Creating HandTracker (primary_only={primary_only}, remote={self._use_remote_model})")
            self._tracker = HandTracker(
                primary_hand_only=primary_only,
                use_remote_model=self._use_remote_model,
                remote_endpoint=self._remote_endpoint
            )
            self._tracker.initialize()
            _debug_log(f"HandTracker initialized. available={self._tracker.available}")
            print(f"[HandTrackingWorker._ensure_tracker] HandTracker initialized. available={self._tracker.available}")
            if self._custom_model_file:
                self._tracker.set_model_path(self._custom_model_file)
            return
        if self._tracker.primary_hand_only != primary_only:
            self._tracker.reconfigure(primary_only)

    def submit(self, frame: dict):
        if frame is None or not self._running:
            return
        with self._lock:
            self._queue.clear()
            self._queue.append(frame)
        self._event.set()

    def run(self):
        flip, primary_only, _ = self._snapshot_config()
        self._ensure_tracker(primary_only)
        try:
            while self._running:
                if not self._event.wait(0.5):
                    continue
                self._event.clear()

                flip, primary_only, reconfigure = self._snapshot_config()
                if reconfigure:
                    self._ensure_tracker(primary_only)

                with self._lock:
                    frame = self._queue.pop() if self._queue else None
                if frame is None:
                    continue
                if self._tracker is None or not self._tracker.available:
                    continue

                processed, status = self._tracker.process(frame, flip_horizontal=flip)

                now = time.perf_counter()
                if self._last_time is not None:
                    delta = now - self._last_time
                    if delta > 1e-6:
                        instant = 1.0 / delta
                        self._fps = (self._fps * 0.85) + (instant * 0.15)
                        self.fps_updated.emit(self._fps)
                self._last_time = now

                if status is not None:
                    self.status_updated.emit(status)
                    prediction = status.get("prediction") if isinstance(status, dict) else None
                    if prediction is not None:
                        self.prediction_updated.emit(str(prediction))
                if processed is not None:
                    self.frame_processed.emit(processed)
        finally:
            if self._tracker is not None:
                self._tracker.close()
                self._tracker = None

    def stop(self):
        self._running = False
        self._event.set()
        self.wait(500)
