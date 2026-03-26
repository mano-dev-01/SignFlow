#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON_OVERLAY="$SCRIPT_DIR/../Common/Overlay"
SERVER_URL="${SIGNFLOW_SERVER_URL:-https://mano-dev-01-signflow-inference.hf.space}"

echo "========================================"
echo "SignFlow - Running from Code/Linux -> Code/Common/Overlay"
echo "========================================"

echo "[DEBUG] Current folder: $(pwd)"

if [ ! -d "$COMMON_OVERLAY" ]; then
  echo "ERROR: $COMMON_OVERLAY not found"
  exit 1
fi

cd "$COMMON_OVERLAY"

if [ -f "run_signflow.sh" ]; then
  bash "run_signflow.sh"
else
  echo "No run_signflow.sh in Common/Overlay; launching overlay directly."
  echo "Using remote server: $SERVER_URL"
  python3 overlay_remote.py --server "$SERVER_URL"
fi
