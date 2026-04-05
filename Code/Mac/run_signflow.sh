#!/usr/bin/env bash
set -euo pipefail


# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv-build"
OVERLAY_DIR="$SCRIPT_DIR/Overlay"
MODEL_DIR="$SCRIPT_DIR/Model_inference"
MODELS_DIR="$SCRIPT_DIR/Models"
SERVER_URL="${SIGNFLOW_SERVER_URL:-https://mano-dev-01-signflow-inference.hf.space}"

echo "========================================"
echo "SignFlow - Starting Remote Overlay (Unix)"
echo "========================================"

cd "$ROOT_DIR"

echo "[1/1] Starting overlay client..."
echo "Using remote server: $SERVER_URL"
python3 overlay_remote.py --server "$SERVER_URL"
