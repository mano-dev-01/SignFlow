"""
Compatibility wrapper for the refactored server inference modules.

Existing imports keep working, but the actual implementation now lives under
`Model_inference/signflow_model/` so the model runtime can be shared cleanly
between the API server and local inference tools.
"""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT_DIR / "Model_inference"
for path in [str(ROOT_DIR), str(MODEL_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)

from Model_inference.signflow_model.architecture import (
    LandmarkEmbedding,
    LandmarkTransformer,
    LandmarkTransformerEmbedding,
    TransformerBlock,
)
from Model_inference.signflow_model.config import MAX_FRAMES, NUM_COORDS, NUM_LANDMARKS
from Model_inference.signflow_model.inference import prepare_input as _prepare_input, run_inference
from Model_inference.signflow_model.service import SignFlowModelService

SignFlowModel = SignFlowModelService

__all__ = [
    "LandmarkEmbedding",
    "LandmarkTransformer",
    "LandmarkTransformerEmbedding",
    "MAX_FRAMES",
    "NUM_COORDS",
    "NUM_LANDMARKS",
    "SignFlowModel",
    "TransformerBlock",
    "_prepare_input",
    "run_inference",
]
