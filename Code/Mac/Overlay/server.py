"""
Compatibility entry point for the SignFlow Flask server.

The implementation now lives in `Model_inference.signflow_model.server_app` so
the HTTP layer, runtime loading, and shared inference helpers stay modular.
"""

from pathlib import Path
import sys
import traceback

# Ensure the project root is on module path.
# `server.py` lives in Code/Common/Overlay; model package lives in Code/Model_inference.
ROOT_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT_DIR / "Model_inference"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

try:
    from Model_inference.signflow_model.server_app import app, main
except Exception as exc:
    print("[server.py] ERROR: Failed to import Model_inference.signflow_model.server_app")
    traceback.print_exc()
    raise

__all__ = ["app", "main"]


if __name__ == "__main__":
    main()
