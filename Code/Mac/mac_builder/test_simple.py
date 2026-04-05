#!/usr/bin/env python3
import sys
sys.stdout = sys.stderr  # Force unbuffered output

print("TEST START")
sys.stdout.flush()

try:
    print("Importing mediapipe...")
    sys.stdout.flush()
    import mediapipe
    print("SUCCESS: mediapipe imported")
    sys.stdout.flush()
except Exception as e:
    print(f"FAILED: {e}")
    sys.stdout.flush()
    import traceback
    traceback.print_exc()
