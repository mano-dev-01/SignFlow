from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from Model_inference.paths import BEST_MODEL_PATH, CLASS_MAP_PATH, MEDIAPIPE_MODELS_DIR

MAX_FRAMES = 64
NUM_LANDMARKS = 92
NUM_COORDS = 3
MIN_FRAMES_FOR_PREDICTION = 5
MAX_PREDICTION_WINDOW_FRAMES = 40
DEFAULT_SERVER_PORT = 8000

PACKAGE_DIR = Path(__file__).resolve().parent
MODEL_INFERENCE_DIR = PACKAGE_DIR.parent
PROJECT_DIR = MODEL_INFERENCE_DIR.parent
DEFAULT_MODEL_PATH = BEST_MODEL_PATH
DEFAULT_CLASS_MAP_PATH = CLASS_MAP_PATH
DEFAULT_MEDIAPIPE_MODELS_DIR = MEDIAPIPE_MODELS_DIR


@dataclass(frozen=True)
class ModelPaths:
    model_path: Path
    class_map_path: Path


def resolve_model_paths(
    model_path: str | Path | None = None,
    class_map_path: str | Path | None = None,
) -> ModelPaths:
    resolved_model_path = Path(model_path) if model_path is not None else DEFAULT_MODEL_PATH
    resolved_class_map_path = (
        Path(class_map_path) if class_map_path is not None else DEFAULT_CLASS_MAP_PATH
    )
    return ModelPaths(
        model_path=resolved_model_path.resolve(),
        class_map_path=resolved_class_map_path.resolve(),
    )
