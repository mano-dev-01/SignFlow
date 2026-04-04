#!/usr/bin/env python3
"""Test MediaPipe directly in the context of the app."""
import sys
import cv2
import numpy as np
from pathlib import Path

# Add paths like the app does
ROOT_DIR = Path(__file__).resolve().parent
MODEL_DIR = ROOT_DIR / "Code/Mac/Model_inference"
for path in [str(ROOT_DIR), str(MODEL_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Now test MediaPipe
try:
    import mediapipe as mp
    print("✅ MediaPipe imported")
    
    mp_hands = mp.solutions.hands
    mp_draw = mp.solutions.drawing_utils
    print("✅ MediaPipe solutions loaded")
    
    # Try to create hands detector
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
    )
    print("✅ Hands detector created")
    
    # Create a dummy frame
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    print(f"✅ Created dummy frame: {dummy_frame.shape}")
    
    # Try to process it
    results = hands.process(dummy_frame)
    print(f"✅ Processed frame - landmarks: {results.multi_hand_landmarks}")
    print(f"   Hands detected: {len(results.multi_hand_landmarks) if results.multi_hand_landmarks else 0}")
    
    print("\n✅✅✅ ALL TESTS PASSED - MediaPipe is working correctly!")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
