#!/usr/bin/env bash
# SignFlow Application Launcher with Diagnostics
# Place this in /Applications/SignFlow/ directory

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="SignFlow"
LOG_DIR="$HOME/.signflow"
LOG_FILE="$LOG_DIR/launcher_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOG_DIR"

echo "[$(date)] SignFlow launcher starting..." | tee -a "$LOG_FILE"
echo "[$(date)] Script directory: $SCRIPT_DIR" | tee -a "$LOG_FILE"
echo "[$(date)] Python version: $(python3 --version 2>&1)" | tee -a "$LOG_FILE"

# Try to find the app bundle
if [[ -d "$SCRIPT_DIR/$APP_NAME.app" ]]; then
  APP_BUNDLE="$SCRIPT_DIR/$APP_NAME.app"
elif [[ -d "/Applications/$APP_NAME.app" ]]; then
  APP_BUNDLE="/Applications/$APP_NAME.app"
elif [[ -d "$HOME/Applications/$APP_NAME.app" ]]; then
  APP_BUNDLE="$HOME/Applications/$APP_NAME.app"
else
  echo "[$(date)] ERROR: Could not find $APP_NAME.app" | tee -a "$LOG_FILE"
  exit 1
fi

echo "[$(date)] Found app bundle: $APP_BUNDLE" | tee -a "$LOG_FILE"

# Set up environment
export SIGNFLOW_ROOT="$SCRIPT_DIR"
export DYLD_LIBRARY_PATH="/usr/local/lib:/opt/local/lib:$DYLD_LIBRARY_PATH"
export QT_QPA_PLATFORM="cocoa"

EXECUTABLE="$APP_BUNDLE/Contents/MacOS/$APP_NAME"

if [[ ! -x "$EXECUTABLE" ]]; then
  echo "[$(date)] ERROR: Executable not found or not executable: $EXECUTABLE" | tee -a "$LOG_FILE"
  exit 1
fi

echo "[$(date)] Launching: $EXECUTABLE" | tee -a "$LOG_FILE"
echo "[$(date)] Environment variables set:" | tee -a "$LOG_FILE"
echo "[$(date)]   SIGNFLOW_ROOT=$SIGNFLOW_ROOT" | tee -a "$LOG_FILE"
echo "[$(date)]   QT_QPA_PLATFORM=$QT_QPA_PLATFORM" | tee -a "$LOG_FILE"
echo "[$(date)] Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "[$(date)] =============================" | tee -a "$LOG_FILE"

# Launch and capture all output
"$EXECUTABLE" >> "$LOG_FILE" 2>&1 || {
  EXIT_CODE=$?
  echo "" | tee -a "$LOG_FILE"
  echo "[$(date)] ERROR: Exe exited with code $EXIT_CODE" | tee -a "$LOG_FILE"
  echo "[$(date)] Check the full log: open $LOG_FILE" | tee -a "$LOG_FILE"
  exit $EXIT_CODE
}

echo "[$(date)] SignFlow closed normally" | tee -a "$LOG_FILE"
