from __future__ import annotations

"""
SignFlow Landmark Extractor — extracts 92 landmarks from webcam frames.

Produces landmarks in the EXACT format the model server expects:
    [0:40]  = 40 lip landmarks from face (selected by LIPS_FACE_IDXS)
    [40:61] = 21 left hand landmarks
    [61:82] = 21 right hand landmarks
    [82:92] = 10 upper body pose landmarks

This module runs MediaPipe (hands, face, pose) locally on the client machine,
then sends just the lightweight landmark coordinates to the server.

Every step prints to the console for debugging.
"""

import sys
from pathlib import Path

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Model_inference.paths import MEDIAPIPE_MODELS_DIR

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import mediapipe as mp_lib
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import (
        FaceLandmarker, FaceLandmarkerOptions,
        HandLandmarker, HandLandmarkerOptions,
        PoseLandmarker, PoseLandmarkerOptions,
        RunningMode,
    )
    HAS_TASK_API = True
except ImportError:
    HAS_TASK_API = False
    try:
        import mediapipe as mp_lib
    except ImportError:
        mp_lib = None

# Must match model training
NUM_LANDMARKS = 92
NUM_COORDS = 3

# These 40 face mesh indices correspond to the lip landmarks used in training
LIPS_FACE_IDXS = np.array([
    61, 185, 40, 39, 37, 0, 267, 269, 270, 409,
    291, 146, 91, 181, 84, 17, 314, 405, 321, 375,
    78, 191, 80, 81, 82, 13, 312, 311, 310, 415,
    95, 88, 178, 87, 14, 317, 402, 318, 324, 308,
], dtype=np.int32)

# Upper body pose landmark indices from the full 33 pose landmarks
POSE_UPPER_IDXS = np.array([0, 11, 12, 13, 14, 15, 16, 23, 24, 25], dtype=np.int32)


class LandmarkExtractorTask:
    """
    Uses MediaPipe Task API (the same one as the Model's sign_inference.py)
    to extract landmarks in the exact same format as training.
    """

    def __init__(self, mediapipe_models_dir=None):
        print("[EXTRACTOR] Initializing MediaPipe Task API landmark extractor...")

        self.face_available = True
        self.hands_available = True
        self.pose_available = True

        if mediapipe_models_dir is None:
            mediapipe_models_dir = str(MEDIAPIPE_MODELS_DIR)

        print(f"[EXTRACTOR] MediaPipe models dir: {mediapipe_models_dir}")

        # Face
        face_model_path = Path(mediapipe_models_dir) / "face_landmarker.task"
        if face_model_path.exists():
            try:
                self.face_lm = FaceLandmarker.create_from_options(FaceLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=str(face_model_path)),
                    running_mode=RunningMode.IMAGE, num_faces=1,
                    min_face_detection_confidence=0.3, min_face_presence_confidence=0.3,
                ))
                print("[EXTRACTOR] Face landmarker: OK")
            except Exception as e:
                self.face_available = False
                print(f"[EXTRACTOR] Face landmarker FAILED: {e}")
        else:
            self.face_available = False
            print(f"[EXTRACTOR] Face model not found at {face_model_path} — lips will be zeroed")

        # Hands
        hand_model_path = Path(mediapipe_models_dir) / "hand_landmarker.task"
        if hand_model_path.exists():
            try:
                self.hand_lm = HandLandmarker.create_from_options(HandLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=str(hand_model_path)),
                    running_mode=RunningMode.IMAGE, num_hands=2,
                    min_hand_detection_confidence=0.3, min_hand_presence_confidence=0.3,
                ))
                print("[EXTRACTOR] Hand landmarker: OK")
            except Exception as e:
                self.hands_available = False
                print(f"[EXTRACTOR] Hand landmarker FAILED: {e}")
        else:
            self.hands_available = False
            print(f"[EXTRACTOR] Hand model not found at {hand_model_path}")

        # Pose
        pose_model_path = Path(mediapipe_models_dir) / "pose_landmarker_heavy.task"
        if pose_model_path.exists():
            try:
                self.pose_lm = PoseLandmarker.create_from_options(PoseLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=str(pose_model_path)),
                    running_mode=RunningMode.IMAGE, num_poses=1,
                    min_pose_detection_confidence=0.3, min_pose_presence_confidence=0.3,
                ))
                print("[EXTRACTOR] Pose landmarker: OK")
            except Exception as e:
                self.pose_available = False
                print(f"[EXTRACTOR] Pose landmarker FAILED: {e}")
        else:
            self.pose_available = False
            print(f"[EXTRACTOR] Pose model not found at {pose_model_path}")

        print(f"[EXTRACTOR] Ready: face={self.face_available}, hands={self.hands_available}, pose={self.pose_available}")

    def extract(self, rgb_image):
        """
        Extract 92 landmarks from an RGB image.

        Args:
            rgb_image: numpy array of shape (H, W, 3) in RGB format

        Returns:
            landmarks: numpy array of shape (92, 3)
            hands_visible: bool — True if any hand landmarks detected
        """
        mp_img = mp_lib.Image(
            image_format=mp_lib.ImageFormat.SRGB,
            data=np.ascontiguousarray(rgb_image)
        )
        lm = np.zeros((NUM_LANDMARKS, NUM_COORDS), dtype=np.float32)

        # Face → lips
        if self.face_available:
            try:
                fr = self.face_lm.detect(mp_img)
                if fr.face_landmarks:
                    face = fr.face_landmarks[0]
                    for i, fi in enumerate(LIPS_FACE_IDXS):
                        if fi < len(face):
                            lm[i] = [face[fi].x, face[fi].y, face[fi].z]
            except Exception as e:
                print(f"[EXTRACTOR] Face detection error: {e}")

        # Hands
        if self.hands_available:
            try:
                hr = self.hand_lm.detect(mp_img)
                if hr.hand_landmarks and hr.handedness:
                    hands = []
                    for hinfo, hlms in zip(hr.handedness, hr.hand_landmarks):
                        label = hinfo[0].category_name
                        conf = hinfo[0].score
                        wrist_x = hlms[0].x
                        hands.append((label, conf, wrist_x, hlms))

                    # Fix collision when both labeled the same
                    if len(hands) == 2 and hands[0][0] == hands[1][0]:
                        if hands[0][2] > hands[1][2]:
                            hands[0] = ("Left", hands[0][1], hands[0][2], hands[0][3])
                            hands[1] = ("Right", hands[1][1], hands[1][2], hands[1][3])
                        else:
                            hands[0] = ("Right", hands[0][1], hands[0][2], hands[0][3])
                            hands[1] = ("Left", hands[1][1], hands[1][2], hands[1][3])

                    for label, conf, wrist_x, hlms in hands:
                        off = 40 if label == "Left" else 61
                        for li in range(min(21, len(hlms))):
                            lm[off + li] = [hlms[li].x, hlms[li].y, hlms[li].z]
            except Exception as e:
                print(f"[EXTRACTOR] Hand detection error: {e}")

        # Pose
        if self.pose_available:
            try:
                pr = self.pose_lm.detect(mp_img)
                if pr.pose_landmarks:
                    pose = pr.pose_landmarks[0]
                    for k, pidx in enumerate(POSE_UPPER_IDXS):
                        if pidx < len(pose):
                            lm[82 + k] = [pose[pidx].x, pose[pidx].y, pose[pidx].z]
            except Exception as e:
                print(f"[EXTRACTOR] Pose detection error: {e}")

        hands_visible = bool(np.any(lm[40:82] != 0))
        return lm, hands_visible

    def close(self):
        print("[EXTRACTOR] Closing MediaPipe resources...")
        if self.face_available:
            try:
                self.face_lm.close()
            except Exception:
                pass
        if self.hands_available:
            try:
                self.hand_lm.close()
            except Exception:
                pass
        if self.pose_available:
            try:
                self.pose_lm.close()
            except Exception:
                pass
        print("[EXTRACTOR] Closed")


class LandmarkExtractorLegacy:
    """
    Fallback extractor using the standard MediaPipe Solutions API
    (mp.solutions.hands + mp.solutions.pose).

    This is used when the Task API models (.task files) are not available.
    It only extracts hands + pose (no face/lips), which the model handles
    gracefully due to lip dropout training.
    """

    def __init__(self):
        print("[EXTRACTOR] Initializing legacy MediaPipe Solutions extractor...")
        print("[EXTRACTOR] NOTE: No face/lip landmarks — model handles this via dropout training")

        self._mp = mp_lib
        self._mp_hands = mp_lib.solutions.hands
        self._mp_pose = mp_lib.solutions.pose

        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._pose = self._mp_pose.Pose(
            static_image_mode=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        print("[EXTRACTOR] Legacy extractor ready (hands + pose only)")

    def extract(self, rgb_image):
        """Extract landmarks from RGB image. Returns (92x3 array, hands_visible)."""
        lm = np.zeros((NUM_LANDMARKS, NUM_COORDS), dtype=np.float32)

        # Hands
        h_results = self._hands.process(rgb_image)
        if h_results.multi_hand_landmarks and h_results.multi_handedness:
            hands = []
            for idx, hand_landmarks in enumerate(h_results.multi_hand_landmarks):
                label = None
                if h_results.multi_handedness and len(h_results.multi_handedness) > idx:
                    classification = h_results.multi_handedness[idx].classification
                    if classification:
                        label = classification[0].label

                hlms = hand_landmarks.landmark
                wrist_x = hlms[0].x
                hands.append((label, wrist_x, hlms))

            # Fix collision
            if len(hands) == 2 and hands[0][0] == hands[1][0]:
                if hands[0][1] > hands[1][1]:
                    hands[0] = ("Left", hands[0][1], hands[0][2])
                    hands[1] = ("Right", hands[1][1], hands[1][2])
                else:
                    hands[0] = ("Right", hands[0][1], hands[0][2])
                    hands[1] = ("Left", hands[1][1], hands[1][2])

            for label, wrist_x, hlms in hands:
                off = 40 if label == "Left" else 61
                for li in range(min(21, len(hlms))):
                    lm[off + li] = [hlms[li].x, hlms[li].y, hlms[li].z]

        # Pose
        p_results = self._pose.process(rgb_image)
        if p_results.pose_landmarks:
            pose = p_results.pose_landmarks.landmark
            for k, pidx in enumerate(POSE_UPPER_IDXS):
                if pidx < len(pose):
                    lm[82 + k] = [pose[pidx].x, pose[pidx].y, pose[pidx].z]

        hands_visible = bool(np.any(lm[40:82] != 0))
        return lm, hands_visible

    def close(self):
        print("[EXTRACTOR] Closing legacy MediaPipe resources...")
        try:
            self._hands.close()
        except Exception:
            pass
        try:
            self._pose.close()
        except Exception:
            pass
        print("[EXTRACTOR] Closed")


def create_extractor(mediapipe_models_dir=None):
    """
    Create the best available landmark extractor.

    Tries the Task API first (which matches training exactly),
    falls back to legacy Solutions API.
    """
    if HAS_TASK_API:
        try:
            return LandmarkExtractorTask(mediapipe_models_dir)
        except Exception as e:
            print(f"[EXTRACTOR] Task API failed ({e}), falling back to legacy...")

    if mp_lib is not None:
        return LandmarkExtractorLegacy()

    raise RuntimeError("[EXTRACTOR] MediaPipe not installed! Run: pip install mediapipe")
