from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent
MODELS_DIR = PROJECT_DIR / "Models"

MEDIAPIPE_MODELS_DIR = MODELS_DIR / "mediapipe_models"
BEST_MODEL_PATH = MODELS_DIR / "temporal_model.pth"
PKL_MODEL_PATH = MODELS_DIR / "static_model.pkl"
CLASS_MAP_PATH = PACKAGE_DIR / "class_map.json"
