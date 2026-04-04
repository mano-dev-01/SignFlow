"""Compatibility entry point for the refactored remote overlay launcher."""

import traceback
import sys
import os
from pathlib import Path

# Setup error logging to file
log_path = Path.home() / '.signflow' / 'overlay.log'
log_path.parent.mkdir(exist_ok=True, parents=True)

class DualLogger:
    def __init__(self, file_path):
        self.file = open(file_path, 'a')
        self.stderr = sys.stderr
    
    def write(self, msg):
        self.file.write(msg)
        self.file.flush()
        self.stderr.write(msg)
    
    def flush(self):
        self.file.flush()
        self.stderr.flush()

# Redirect stderr to file
sys.stderr = DualLogger(log_path)

print(f'[overlay_remote.py] Log file: {log_path}')
print('[overlay_remote.py] Python version:', sys.version)
print('[overlay_remote.py] sys.path:', sys.path[:3], '...')

try:
    from signflow_overlay.remote_app import main
    print('[overlay_remote.py] ✓ Successfully imported signflow_overlay.remote_app')
except Exception as exc:
    print('[overlay_remote.py] ERROR: Failed importing signflow_overlay.remote_app')
    traceback.print_exc()
    raise


if __name__ == "__main__":
    try:
        print('[overlay_remote.py] Launching main()...')
        main()
    except Exception as exc:
        print('[overlay_remote.py] ERROR: main() failed')
        traceback.print_exc()
        raise
    finally:
        print('[overlay_remote.py] Shutdown complete')

