from __future__ import annotations

import argparse
import sys
import time

import cv2

from signflow_landmark_extractor import create_extractor

from .api_client import SignFlowAPIClient
from .config import DEFAULT_PREDICT_INTERVAL, DEFAULT_SERVER_URL, IPC_SERVER_NAME


def build_argument_parser():
    parser = argparse.ArgumentParser(description="SignFlow Remote Inference Runner")
    parser.add_argument(
        "--server",
        type=str,
        default=DEFAULT_SERVER_URL,
        help="URL of the SignFlow model server",
    )
    parser.add_argument("--camera", type=int, default=0, help="Camera device index")
    parser.add_argument(
        "--mediapipe-dir",
        type=str,
        default=None,
        help="Path to MediaPipe .task model files",
    )
    parser.add_argument(
        "--predict-interval",
        type=float,
        default=DEFAULT_PREDICT_INTERVAL,
        help="Seconds between prediction requests to the server",
    )
    parser.add_argument(
        "--ipc",
        action="store_true",
        help="Send predictions to the overlay via IPC (QLocalSocket)",
    )
    return parser


def build_ipc_sender(enabled: bool):
    if not enabled:
        print("[RUNNER] Step 3: IPC disabled (use --ipc to enable)\n")
        return None

    print("[RUNNER] Step 3: Initializing IPC to overlay...")
    try:
        from PyQt5.QtNetwork import QLocalSocket
        from PyQt5.QtWidgets import QApplication

        qt_app = QApplication.instance()
        if qt_app is None:
            qt_app = QApplication(sys.argv)

        def send_ipc(text):
            socket = QLocalSocket()
            socket.connectToServer(IPC_SERVER_NAME)
            if not socket.waitForConnected(500):
                return False
            payload = (text + "\n").encode("utf-8")
            socket.write(payload)
            socket.waitForBytesWritten(500)
            socket.disconnectFromServer()
            if socket.state() != QLocalSocket.UnconnectedState:
                socket.waitForDisconnected(200)
            return True

        print("[RUNNER] IPC ready\n")
        return send_ipc
    except ImportError:
        print("[RUNNER] WARNING: PyQt5 not installed, IPC disabled\n")
        return None


def open_camera(camera_index: int):
    print("[RUNNER] Step 4: Opening camera...")
    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        time.sleep(1)
        capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        return None
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    capture.set(cv2.CAP_PROP_FPS, 30)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    print("[RUNNER] Camera opened\n")
    return capture


def main(argv=None):
    args = build_argument_parser().parse_args(argv)

    print("=" * 60)
    print("  SignFlow Remote Inference Runner")
    print("=" * 60)
    print(f"  Server:           {args.server}")
    print(f"  Camera:           {args.camera}")
    print(f"  MediaPipe dir:    {args.mediapipe_dir or 'auto-detect'}")
    print(f"  Predict interval: {args.predict_interval}s")
    print(f"  IPC to overlay:   {args.ipc}")
    print("=" * 60)

    print("\n[RUNNER] Step 1: Initializing landmark extractor...")
    extractor = create_extractor(args.mediapipe_dir)
    print("[RUNNER] Landmark extractor ready\n")

    print("[RUNNER] Step 2: Initializing API client...")
    client = SignFlowAPIClient(server_url=args.server, predict_interval=args.predict_interval)
    client.start()
    print("[RUNNER] API client started\n")

    ipc_send = build_ipc_sender(args.ipc)
    capture = open_camera(args.camera)
    if capture is None:
        print("[RUNNER] ERROR: Could not open camera! Close other apps using it.")
        client.stop()
        extractor.close()
        sys.exit(1)

    print("[RUNNER] Camera warming up...")
    for _ in range(10):
        capture.read()
    print("[RUNNER] Camera warm\n")

    print("[RUNNER] Step 5: Starting main loop")
    print("[RUNNER] Show your hands to the camera and sign!")
    print("[RUNNER] Press Q in the preview window to quit\n")

    fps_counter = 0
    fps_time = time.time()
    fps = 0.0
    last_sign = None
    sentence = []
    sign_hold_count = 0
    hands_gone_count = 0
    sign_confirmed = False
    last_added_sign = None

    while True:
        readable, frame = capture.read()
        if not readable:
            print("[RUNNER] Camera read failed")
            time.sleep(0.01)
            continue

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        fps_counter += 1
        now = time.time()
        if now - fps_time >= 1.0:
            fps = fps_counter / (now - fps_time)
            fps_counter = 0
            fps_time = now

        landmarks, hands_visible = extractor.extract(rgb)

        if hands_visible:
            client.add_frame(landmarks)
            hands_gone_count = 0
        else:
            hands_gone_count += 1
            if hands_gone_count > 20:
                client.clear_buffer()

        prediction = client.get_latest_prediction()
        current_sign = None
        current_confidence = 0.0
        top5 = []
        if prediction:
            current_sign = prediction["sign"]
            current_confidence = prediction["confidence"]
            top5 = prediction.get("top5", [])

        if hands_visible and current_sign and current_confidence > 0.08:
            if current_sign == last_sign:
                sign_hold_count += 1
                if sign_hold_count >= 8:
                    sign_confirmed = True
            else:
                last_sign = current_sign
                sign_hold_count = 1
                sign_confirmed = False
        elif not hands_visible:
            if hands_gone_count == 10 and sign_confirmed and last_sign:
                if last_sign != last_added_sign or len(sentence) == 0:
                    sentence.append(last_sign)
                    last_added_sign = last_sign
                    sentence_text = " ".join(sentence)
                    print(f"\n[RUNNER] >>> Added: {last_sign.upper()}  |  Sentence: {sentence_text}")
                    if ipc_send:
                        ipc_send(sentence_text)
                        print(f"[RUNNER] Sent via IPC: {sentence_text}")
                sign_confirmed = False
                sign_hold_count = 0

        display = cv2.flip(frame, 1)
        height, width = display.shape[:2]

        cv2.rectangle(display, (0, 0), (width, 50), (0, 0, 0), -1)
        cv2.putText(display, "SIGNFLOW REMOTE", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        status = "CONNECTED" if client.connected else "CONNECTING..."
        status_color = (0, 255, 0) if client.connected else (0, 165, 255)
        cv2.putText(display, status, (8, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, status_color, 1)
        cv2.putText(
            display,
            f"FPS:{fps:.0f} Buf:{client.buffer_size}",
            (width - 140, 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (150, 150, 150),
            1,
        )

        if current_sign and current_confidence > 0.05:
            cv2.rectangle(display, (0, height - 80), (width, height), (0, 0, 0), -1)
            prediction_color = (0, 255, 100) if current_confidence > 0.4 else (0, 220, 255)
            cv2.putText(
                display,
                current_sign.upper(),
                (12, height - 45),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                prediction_color,
                2,
            )
            cv2.putText(
                display,
                f"{current_confidence:.0%}",
                (width - 60, height - 45),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                prediction_color,
                2,
            )

            for index, (sign, confidence) in enumerate(top5[:3]):
                y = height - 30 + index * 10
                bar_width = max(1, int(confidence * (width - 20)))
                cv2.rectangle(
                    display,
                    (8, y),
                    (8 + bar_width, y + 7),
                    prediction_color if index == 0 else (50, 50, 50),
                    -1,
                )
                cv2.putText(
                    display,
                    f"{sign} {confidence:.0%}",
                    (12, y + 6),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.25,
                    (255, 255, 255),
                    1,
                )

        if sentence:
            cv2.rectangle(display, (0, 52), (width, 75), (40, 40, 40), -1)
            cv2.putText(
                display,
                " ".join(sentence),
                (10, 68),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (180, 180, 180),
                1,
            )

        cv2.imshow("SignFlow Remote", display)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), ord("Q")):
            print("\n[RUNNER] Quit requested")
            break
        if key in (ord("c"), ord("C")):
            sentence.clear()
            last_added_sign = None
            sign_confirmed = False
            client.clear_buffer()
            print("[RUNNER] Sentence cleared")
        elif key in (ord("b"), ord("B")) and sentence:
            removed = sentence.pop()
            last_added_sign = sentence[-1] if sentence else None
            print(f"[RUNNER] Removed: {removed}  |  Sentence: {' '.join(sentence)}")

    print("[RUNNER] Cleaning up...")
    capture.release()
    cv2.destroyAllWindows()
    client.stop()
    extractor.close()
    print("[RUNNER] Done.")
