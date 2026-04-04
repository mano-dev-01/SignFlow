from __future__ import annotations

import time

import numpy as np

try:
    import torch
except ImportError:
    torch = None
    print('[MODEL] WARNING: torch is not installed. model inference is unavailable until torch is installed.')

from .config import MIN_FRAMES_FOR_PREDICTION, NUM_COORDS, NUM_LANDMARKS
from .inference import run_inference, trim_prediction_frames
from .loader import build_model, format_val_accuracy, load_checkpoint_bundle, warmup_model


class SignFlowModelService:
    """
    Loads the trained checkpoint once and exposes server-safe prediction helpers.
    """

    def __init__(self):
        self.model = None
        self.device = None
        self.class_names = {}
        self.num_classes = 0
        self.bundle = None

    def load(self, model_path=None, class_map_path=None):
        print("[SERVER] ========================================")
        print("[SERVER] SignFlow Model Server starting...")
        print("[SERVER] ========================================")

        if torch is None:
            raise RuntimeError("torch is required for SignFlow model loading. install with pip install torch")

        device_type = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device_type)
        print(f"[SERVER] Device: {self.device}")

        self.bundle = load_checkpoint_bundle(model_path, class_map_path, self.device)
        print(f"[SERVER] Loading model from: {self.bundle.model_path}")
        print(f"[SERVER] Number of classes: {self.bundle.num_classes}")
        print(f"[SERVER] Model config: {self.bundle.config}")

        self.class_names = self.bundle.class_names
        self.num_classes = self.bundle.num_classes
        print(f"[SERVER] Class map loaded: {len(self.class_names)} classes")

        self.model = build_model(self.bundle, self.device)
        print(
            f"[SERVER] Model loaded: {format_val_accuracy(self.bundle.best_val_acc)}% val accuracy"
        )

        print("[SERVER] Running warmup inference...")
        warmup_model(self.model, self.device)
        print("[SERVER] Warmup complete")
        print("[SERVER] Ready to serve predictions!")
        print("[SERVER] ========================================")

    def _parse_frames(self, frames_raw):
        try:
            return [np.array(frame, dtype=np.float32) for frame in frames_raw]
        except Exception as exc:
            return {"error": f"Failed to parse frames: {exc}"}

    def _validate_frames(self, frames_list):
        if len(frames_list) < MIN_FRAMES_FOR_PREDICTION:
            return {"error": "Need at least 5 frames", "received": len(frames_list)}

        for index, frame in enumerate(frames_list):
            if frame.shape != (NUM_LANDMARKS, NUM_COORDS):
                return {
                    "error": (
                        f"Frame {index} has shape {list(frame.shape)}, "
                        f"expected [{NUM_LANDMARKS}, {NUM_COORDS}]"
                    )
                }
        return None

    def predict(self, frames_raw):
        if self.model is None or self.device is None:
            return {"error": "Model is not loaded"}

        request_started = time.time()
        print("[SERVER] /predict called")

        frames_list = self._parse_frames(frames_raw)
        if isinstance(frames_list, dict):
            print(f"[SERVER] ERROR: {frames_list['error']}")
            return frames_list

        print(f"[SERVER] Received {len(frames_list)} frames")
        validation_error = self._validate_frames(frames_list)
        if validation_error is not None:
            print(f"[SERVER] ERROR: {validation_error['error']}")
            return validation_error

        trimmed_frames = trim_prediction_frames(frames_list)
        if len(trimmed_frames) != len(frames_list):
            print(f"[SERVER] Downsampled to {len(trimmed_frames)} frames")

        inference_started = time.time()
        probabilities = run_inference(self.model, trimmed_frames, self.device, use_mixed_precision=False)
        inference_ms = (time.time() - inference_started) * 1000
        print(f"[SERVER] Inference took {inference_ms:.1f}ms")

        if probabilities is None:
            print("[SERVER] ERROR: Inference returned None")
            return {"error": "Inference failed"}

        top_indices = np.argsort(probabilities)[::-1][:5]
        top_sign = self.class_names.get(int(top_indices[0]), "unknown")
        top_confidence = float(probabilities[top_indices[0]])
        top5 = [
            [self.class_names.get(int(index), "unknown"), float(probabilities[index])]
            for index in top_indices
        ]

        total_ms = (time.time() - request_started) * 1000
        print(f"[SERVER] Prediction: {top_sign} ({top_confidence:.2%})")
        print(f"[SERVER] Top 5: {' | '.join(f'{name}:{score:.0%}' for name, score in top5)}")
        print(f"[SERVER] Total request time: {total_ms:.1f}ms")

        return {
            "sign": top_sign,
            "confidence": top_confidence,
            "top5": top5,
            "inference_ms": round(inference_ms, 1),
            "total_ms": round(total_ms, 1),
        }
