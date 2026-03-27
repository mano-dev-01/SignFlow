#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_URL="${SIGNFLOW_SERVER_URL:-https://mano-dev-01-signflow-inference.hf.space}"

echo "========================================"
echo "SignFlow - Starting Remote Overlay (Unix)"
echo "========================================"

cd "$ROOT_DIR"

echo "[1/1] Starting overlay client..."
echo "Using remote server: $SERVER_URL"
python3 overlay_remote.py --server "$SERVER_URL"
