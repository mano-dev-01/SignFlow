#!/usr/bin/env bash
set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
OVERLAY_DIR="$SCRIPT_DIR/Overlay"
MODEL_DIR="$SCRIPT_DIR/Model_inference"
MODELS_DIR="$SCRIPT_DIR/Models"
SERVER_URL="${SIGNFLOW_SERVER_URL:-https://mano-dev-01-signflow-inference.hf.space}"

echo "========================================"
echo "SignFlow macOS Configuration"
echo "========================================"

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "ERROR: Virtual environment not found at $VENV_DIR"
    echo "Please run: python3.10 -m venv $VENV_DIR"
    exit 1
fi

# Check if Overlay directory exists
if [ ! -d "$OVERLAY_DIR" ]; then
    echo "ERROR: Overlay directory not found at $OVERLAY_DIR"
    exit 1
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Set macOS-specific environment variables
export PYTHONUNBUFFERED=1
export TF_CPP_MIN_LOG_LEVEL=2
export GLOG_minloglevel=2
export PYTHONPATH="$OVERLAY_DIR:$MODEL_DIR:$SCRIPT_DIR:${PYTHONPATH:-}"

# For macOS, enable proper framework support
if [[ "$OSTYPE" == "darwin"* ]]; then
    export DYLD_LIBRARY_PATH="/usr/local/lib:/opt/local/lib:${DYLD_LIBRARY_PATH:-}"
    echo "[INFO] macOS detected - enabling native framework support"
fi

echo "[INFO] Current folder: $SCRIPT_DIR"
echo "[INFO] Using Python from: $VENV_DIR/bin/python"
echo "[INFO] Server URL: $SERVER_URL"

cd "$OVERLAY_DIR"

echo "========================================"
echo "SignFlow - Starting Remote Overlay (macOS)"
echo "========================================"
echo "[1/1] Starting overlay client..."

# Run with proper Python from venv
"$VENV_DIR/bin/python" overlay_remote.py --server "$SERVER_URL"

