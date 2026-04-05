# Remote Model Inference Setup Guide

## Overview
SignFlow now supports remote model inference via Hugging Face Spaces. This allows the app to send hand gesture features to a remote inference endpoint and receive ASL sign predictions.

## Remote Endpoint
**URL:** `https://mano-dev-01-signflow-inference.hf.space`

## How It Works

1. **Hand Detection**: MediaPipe detects hands and extracts 21 landmark points per hand
2. **Feature Extraction**: Landmarks converted to numeric features (finger positions, angles, etc.)
3. **Remote Inference**: Features sent to remote model endpoint via HTTPS
4. **Prediction Returned**: Remote model returns ASL sign class prediction + confidence scores
5. **Display**: Prediction displayed in SignFlow UI with confidence level

## Architecture

```
WebcamFrame
    ↓
MediaPipe HandTracker (landmarks detection)
    ↓
RemoteInferenceClient (HTTP POST to endpoint)
    ↓
HF Spaces Model (runs inference)
    ↓
Prediction Result (sign name + confidence)
    ↓
UI Display
```

## Enable Remote Model

### Method 1: Environment Variables (Recommended)

```bash
# Set these before launching the app
export SIGNFLOW_USE_REMOTE_MODEL=1
export SIGNFLOW_REMOTE_ENDPOINT="https://mano-dev-01-signflow-inference.hf.space"

# Launch the app
open /Users/test/SignFlow/dist/SignFlow.app
```

### Method 2: Run Script

```bash
chmod +x /Users/test/SignFlow/run_with_remote_model.sh
/Users/test/SignFlow/run_with_remote_model.sh
```

### Method 3: Command Line

```bash
SIGNFLOW_USE_REMOTE_MODEL=1 open /Users/test/SignFlow/dist/SignFlow.app
```

## Implementation Details

### New Module: `remote_inference_client.py`
- **Location**: `Code/Mac/Overlay/remote_inference_client.py`
- **Class**: `RemoteInferenceClient`
- **Methods**:
  - `predict()` - Get sign prediction from features
  - `predict_proba()` - Get confidence probabilities
  - `_test_connectivity()` - Verify endpoint accessibility

### Integration Points

#### 1. HandTracker (`overlay_hand_tracking.py`)
- Added `use_remote_model` parameter to `__init__`
- Added `_remote_client` instance variable
- Modified `_load_model()` to initialize remote client
- Updated `process()` to use remote predictions

#### 2. HandTrackingWorker (`overlay_hand_tracking.py`)
- Added `use_remote_model` and `remote_endpoint` parameters
- Passes settings to HandTracker during initialization
- Debug logging for remote model operations

#### 3. OverlayWindow (`overlay_window.py`)
- Updated `_create_hand_worker()` to check environment variables
- Auto-enables remote model if `SIGNFLOW_USE_REMOTE_MODEL=1`

## Debug Logging

### Remote Inference Logs
**File**: `/tmp/signflow_remote_inference_debug.log`

Contains:
- Connectivity test results
- Prediction requests/responses
- Error details and retry counts

### Hand Tracking Logs
**File**: `/tmp/signflow_hand_tracking_debug.log`

Contains:
- MediaPipe initialization
- Feature extraction steps
- Model prediction details

## Error Handling

1. **Connection Timeout**: Returns "Timeout" prediction
2. **Connection Error**: Returns "NoConnection" 
3. **Integration Failure** (>5 errors): Falls back to "Model_Offline"
4. **Invalid Response**: Returns "Error" prediction

## Fallback Behavior

- If remote endpoint unreachable → no predictions shown
- Local model still works if available as fallback
- Feature extraction continues regardless of inference backend

## Performance Considerations

- **Latency**: ~100-500ms per prediction (network dependent)
- **Accuracy**: Same as remote model's accuracy
- **Batch Size**: Single frame (features) at a time
- **Concurrency**: Sequential processing (one prediction at a time)

## Testing

```bash
# Check endpoint is reachable
curl -I https://mano-dev-01-signflow-inference.hf.space

# Run with remote model enabled
SIGNFLOW_USE_REMOTE_MODEL=1 open /Users/test/SignFlow/dist/SignFlow.app

# Monitor logs in real-time
tail -f /tmp/signflow_remote_inference_debug.log
tail -f /tmp/signflow_hand_tracking_debug.log
```

## Configuration Summary

| Setting | Environment Variable | Default | Purpose |
|---------|---------------------|---------|---------|
| Enable Remote | `SIGNFLOW_USE_REMOTE_MODEL` | `0` (disabled) | Toggle remote inference |
| Endpoint URL | `SIGNFLOW_REMOTE_ENDPOINT` | Hardcoded HF Space URL | Remote model endpoint |

## API Contract

### Request Format
```json
{
  "data": [[feature1, feature2, ..., featureN]]
}
```

### Expected Response
```json
{
  "data": ["SIGN_CLASS"]
}
```

Or (for probabilities):
```json
{
  "data": [[prob1, prob2, prob3, ...]]
}
```

## Troubleshooting

### "Model_Offline"
- Check internet connectivity
- Verify endpoint URL is correct
- Check `/tmp/signflow_remote_inference_debug.log` for details

### "No predictions showing"
- Ensure `SIGNFLOW_USE_REMOTE_MODEL=1` is set
- Check app launched correctly with env vars
- Look for errors in debug logs

### Slow predictions
- Network latency is normal (check with `curl`)
- Remote model processing time varies
- Monitor `/tmp/signflow_remote_inference_debug.log` for timing

## Future Enhancements

1. Batch inference (multiple hand features at once)
2. Local caching of predictions
3. Fallback to local model if remote fails
4. Confidence threshold configuration
5. Async/parallel prediction pipeline
