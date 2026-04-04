from __future__ import annotations

import argparse
import collections
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Model_inference.landmark_extractor import create_extractor
from Model_inference.paths import CLASS_MAP_PATH
from Model_inference.signflow_model.config import DEFAULT_MEDIAPIPE_MODELS_DIR, DEFAULT_MODEL_PATH
from Model_inference.signflow_model.inference import run_inference
from Model_inference.signflow_model.loader import (
    build_model,
    format_val_accuracy,
    load_checkpoint_bundle,
    warmup_model,
)


def configure_device():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    if device.type == "cuda":
        torch.backends.cudnn.benchmark = True
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    return device


def load_runtime(model_path: str, device):
    bundle = load_checkpoint_bundle(
        model_path=model_path,
        class_map_path=CLASS_MAP_PATH,
        device=device,
    )
    model = build_model(bundle, device)
    print(
        f"Loaded: {bundle.num_classes} classes, "
        f"{format_val_accuracy(bundle.best_val_acc)}% val acc"
    )
    if device.type == "cuda":
        warmup_model(model, device, repeat=5, use_mixed_precision=True)
        torch.cuda.empty_cache()
        print("GPU warm")
    return model, bundle.class_names


def draw_status(frame, sign, confidence, top5, fps, buffer_size, hands_visible):
    height, width = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (width, 56), (0, 0, 0), -1)
    cv2.putText(
        frame,
        "SIGNFLOW PTH INFERENCE",
        (10, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2,
    )
    cv2.putText(
        frame,
        f"FPS:{fps:.0f} Buf:{buffer_size} Hands:{'Y' if hands_visible else 'N'}",
        (10, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (180, 180, 180),
        1,
    )

    if sign:
        cv2.rectangle(frame, (0, height - 110), (width, height), (0, 0, 0), -1)
        color = (0, 255, 100) if confidence > 0.4 else (0, 220, 255)
        cv2.putText(
            frame,
            sign.upper(),
            (12, height - 72),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            color,
            2,
        )
        cv2.putText(
            frame,
            f"{confidence:.0%}",
            (width - 90, height - 72),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2,
        )
        for index, (label, score) in enumerate(top5[:3]):
            y = height - 42 + (index * 14)
            cv2.putText(
                frame,
                f"{label}: {score:.0%}",
                (14, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (255, 255, 255),
                1,
            )


def main():
    parser = argparse.ArgumentParser(description="Run the .pth SignFlow model directly from Models/")
    parser.add_argument("--model", type=str, default=str(DEFAULT_MODEL_PATH))
    parser.add_argument(
        "--mediapipe-dir",
        type=str,
        default=str(DEFAULT_MEDIAPIPE_MODELS_DIR),
    )
    parser.add_argument("--camera", type=int, default=0)
    args = parser.parse_args()

    print("Loading model...")
    device = configure_device()
    model, class_names = load_runtime(args.model, device)

    print("Loading MediaPipe...")
    extractor = create_extractor(args.mediapipe_dir)

    capture = cv2.VideoCapture(args.camera)
    if not capture.isOpened():
        time.sleep(1)
        capture = cv2.VideoCapture(args.camera)
    if not capture.isOpened():
        print("ERROR: camera failed - close other apps using the camera and retry")
        extractor.close()
        raise SystemExit(1)

    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    capture.set(cv2.CAP_PROP_FPS, 30)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    print("Camera warming up...")
    for _ in range(10):
        capture.read()

    frame_buffer = collections.deque(maxlen=60)
    previous_probs = None
    current_sign = None
    current_confidence = 0.0
    current_top5 = []
    hands_missing_frames = 0
    frame_index = 0
    fps_counter = 0
    fps_time = time.time()
    fps = 0.0

    print("READY - Show your hands to the camera. Press Q to quit.")

    while True:
        ok, frame = capture.read()
        if not ok:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        landmarks, hands_visible = extractor.extract(rgb)

        fps_counter += 1
        now = time.time()
        if now - fps_time >= 1.0:
            fps = fps_counter / (now - fps_time)
            fps_counter = 0
            fps_time = now

        if hands_visible:
            frame_buffer.append(landmarks.copy())
            hands_missing_frames = 0
        else:
            hands_missing_frames += 1
            if hands_missing_frames > 20:
                frame_buffer.clear()
                previous_probs = None
                current_sign = None
                current_confidence = 0.0
                current_top5 = []

        if frame_index % 2 == 0 and len(frame_buffer) >= 5:
            probs = run_inference(
                model,
                list(frame_buffer),
                device,
                use_mixed_precision=(device.type == "cuda"),
            )
            if probs is not None:
                probs = np.nan_to_num(probs, nan=0.0)
                if previous_probs is not None:
                    probs = 0.7 * probs + 0.3 * previous_probs
                previous_probs = probs

                top_indices = np.argsort(probs)[::-1][:5]
                current_sign = class_names.get(int(top_indices[0]), "?")
                current_confidence = float(probs[top_indices[0]])
                current_top5 = [
                    (class_names.get(int(index), "?"), float(probs[index]))
                    for index in top_indices
                ]

        display = cv2.flip(frame, 1)
        draw_status(
            display,
            current_sign,
            current_confidence,
            current_top5,
            fps,
            len(frame_buffer),
            hands_visible,
        )
        cv2.imshow("SignFlow PTH Inference", display)

        frame_index += 1
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), ord("Q")):
            break
        if key in (ord("c"), ord("C")):
            frame_buffer.clear()
            previous_probs = None
            current_sign = None
            current_confidence = 0.0
            current_top5 = []

    capture.release()
    cv2.destroyAllWindows()
    extractor.close()


if __name__ == "__main__":
    main()
