#!/bin/bash
# Test SignFlow with Remote Model Inference
# Usage: ./run_with_remote_model.sh

# Set environment variables to enable remote inference
export SIGNFLOW_USE_REMOTE_MODEL=1
export SIGNFLOW_REMOTE_ENDPOINT="https://mano-dev-01-signflow-inference.hf.space"

# Optional: Check if endpoint is reachable
echo "Testing remote endpoint connectivity..."
curl -s -I "$SIGNFLOW_REMOTE_ENDPOINT" | head -1

echo ""
echo "Starting SignFlow with remote model inference..."
echo "Remote Endpoint: $SIGNFLOW_REMOTE_ENDPOINT"
echo ""

# Launch the app
/Users/test/SignFlow/Code/Mac/mac_builder/dist/SignFlow.app/Contents/MacOS/SignFlow

# After app closes, check the debug logs
echo ""
echo "=== Remote Inference Debug Log ===="
if [ -f /tmp/signflow_remote_inference_debug.log ]; then
    echo "Latest entries:"
    tail -20 /tmp/signflow_remote_inference_debug.log
fi

echo ""
echo "=== Hand Tracking Debug Log ===="
if [ -f /tmp/signflow_hand_tracking_debug.log ]; then
    echo "Latest entries:"
    tail -20 /tmp/signflow_hand_tracking_debug.log
fi
