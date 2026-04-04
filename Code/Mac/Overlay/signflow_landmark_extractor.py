"""
Compatibility wrapper for the shared landmark extractor.
"""

from pathlib import Path
import sys
import traceback

ROOT_DIR = Path(__file__).resolve().parents[1]  # Code/Mac
MODEL_DIR = ROOT_DIR / "Model_inference"
for path in [str(ROOT_DIR), str(MODEL_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)
        print(f"[signflow_landmark_extractor] added to sys.path: {path}")

try:
    from Model_inference.landmark_extractor import *  # noqa: F401,F403
except Exception as exc:
    print("[signflow_landmark_extractor] ERROR: Failed to import Model_inference.landmark_extractor")
    traceback.print_exc()
    raise

