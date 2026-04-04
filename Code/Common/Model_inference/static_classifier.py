from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np

from Model_inference.paths import PKL_MODEL_PATH

PREDICTION_THRESHOLD = 0.8


def normalize_landmarks(landmarks):
    points = np.array([[lm.x, lm.y, lm.z] for lm in landmarks], dtype=np.float32)
    base = points[0]
    points = points - base
    scale = np.linalg.norm(points[9]) if points.shape[0] > 9 else 0.0
    if scale < 1e-6:
        scale = 1.0
    return points / scale


def angle_at(a, b, c):
    ba = a - b
    bc = c - b
    denom = np.linalg.norm(ba) * np.linalg.norm(bc)
    if denom < 1e-6:
        return 0.0
    cosine = float(np.dot(ba, bc) / denom)
    cosine = max(-1.0, min(1.0, cosine))
    return float(np.arccos(cosine))


def compute_angles(points):
    idx = lambda value: points[value]
    return [
        angle_at(idx(1), idx(2), idx(3)),
        angle_at(idx(2), idx(3), idx(4)),
        angle_at(idx(5), idx(6), idx(7)),
        angle_at(idx(6), idx(7), idx(8)),
        angle_at(idx(9), idx(10), idx(11)),
        angle_at(idx(10), idx(11), idx(12)),
        angle_at(idx(13), idx(14), idx(15)),
        angle_at(idx(14), idx(15), idx(16)),
        angle_at(idx(17), idx(18), idx(19)),
        angle_at(idx(18), idx(19), idx(20)),
    ]


def build_hand_features(landmarks):
    normalized = normalize_landmarks(landmarks)
    coords = normalized.flatten().tolist()
    angles = compute_angles(normalized)
    return coords + angles


def zero_hand_features():
    return [0.0] * 73


def load_model(model_path: str | Path = PKL_MODEL_PATH):
    resolved_path = Path(model_path)
    print(f"Loading .pkl model from {resolved_path}")
    return joblib.load(resolved_path)
