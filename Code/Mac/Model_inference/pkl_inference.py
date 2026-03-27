from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Model_inference.paths import PKL_MODEL_PATH
from Model_inference.static_classifier import (
    PREDICTION_THRESHOLD,
    build_hand_features,
    load_model,
    zero_hand_features,
)


DEFAULT_MODEL_PATH = str(PKL_MODEL_PATH)


def main():
    parser = argparse.ArgumentParser(description="Run the legacy SignFlow .pkl model directly from Models/")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--camera", type=int, default=0)
    args = parser.parse_args()

    model = load_model(args.model)

    mp_hands = mp.solutions.hands
    mp_draw = mp.solutions.drawing_utils
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
    )

    capture = cv2.VideoCapture(args.camera)
    if not capture.isOpened():
        raise SystemExit("ERROR: camera failed")

    print("READY - Press Q to quit.")

    while True:
        ok, frame = capture.read()
        if not ok:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        prediction_text = "No Hand"
        probability_text = ""

        if results.multi_hand_landmarks:
            right_features = None
            left_features = None
            unknown_features = []

            for index, hand_landmarks in enumerate(results.multi_hand_landmarks):
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                features = build_hand_features(hand_landmarks.landmark)
                label = None
                if results.multi_handedness and len(results.multi_handedness) > index:
                    classifications = results.multi_handedness[index].classification
                    if classifications:
                        label = classifications[0].label

                if label == "Right":
                    right_features = features
                elif label == "Left":
                    left_features = features
                else:
                    unknown_features.append(features)

            if right_features is None and unknown_features:
                right_features = unknown_features.pop(0)
            if left_features is None and unknown_features:
                left_features = unknown_features.pop(0)

            primary = right_features if right_features is not None else zero_hand_features()
            secondary = left_features if left_features is not None else zero_hand_features()
            only_primary_hand = 1 if right_features is not None and left_features is None else 0

            features = np.array([only_primary_hand] + primary + secondary, dtype=np.float32).reshape(1, -1)
            probabilities = model.predict_proba(features)[0]
            max_probability = float(np.max(probabilities))

            if max_probability >= PREDICTION_THRESHOLD:
                prediction_text = str(model.predict(features)[0])
            else:
                prediction_text = "Uncertain"
            probability_text = f"{max_probability:.0%}"

        cv2.putText(
            frame,
            prediction_text,
            (10, 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            2,
        )
        if probability_text:
            cv2.putText(
                frame,
                probability_text,
                (10, 78),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 220, 255),
                2,
            )
        cv2.imshow("SignFlow PKL Inference", frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), ord("Q")):
            break

    capture.release()
    hands.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
