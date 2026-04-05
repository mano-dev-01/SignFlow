from __future__ import annotations

import numpy as np
import torch

from .config import (
    MAX_FRAMES,
    MAX_PREDICTION_WINDOW_FRAMES,
    MIN_FRAMES_FOR_PREDICTION,
    NUM_COORDS,
    NUM_LANDMARKS,
)


def prepare_input(frames_list, device):
    """Convert raw landmark frames into the padded tensor layout expected by the model."""
    frame_count = len(frames_list)
    if frame_count < MIN_FRAMES_FOR_PREDICTION:
        return None, None

    if frame_count > MAX_FRAMES:
        indices = np.linspace(0, frame_count - 1, MAX_FRAMES, dtype=int)
        frames_list = [frames_list[index] for index in indices]
        frame_count = MAX_FRAMES

    array = np.stack(frames_list, axis=0).astype(np.float32)
    if frame_count < MAX_FRAMES:
        padding = np.zeros((MAX_FRAMES - frame_count, NUM_LANDMARKS, NUM_COORDS), dtype=np.float32)
        array = np.concatenate([array, padding], axis=0)

    non_empty = np.any(array != 0, axis=(1, 2))
    non_empty_indices = np.where(non_empty, np.arange(MAX_FRAMES, dtype=np.float32), -1.0)

    frames_tensor = torch.from_numpy(array).unsqueeze(0).to(device)
    indices_tensor = torch.from_numpy(non_empty_indices).unsqueeze(0).to(device)
    return frames_tensor, indices_tensor


def trim_prediction_frames(frames_list):
    frame_count = len(frames_list)
    if frame_count <= MAX_PREDICTION_WINDOW_FRAMES:
        return frames_list
    step = max(1, frame_count // MAX_PREDICTION_WINDOW_FRAMES)
    return frames_list[-MAX_PREDICTION_WINDOW_FRAMES * step :: step][:MAX_PREDICTION_WINDOW_FRAMES]


def run_inference(model, frames_list, device, use_mixed_precision: bool = False):
    if len(frames_list) < MIN_FRAMES_FOR_PREDICTION:
        return None

    prepared_frames = trim_prediction_frames(frames_list)
    frames_tensor, indices_tensor = prepare_input(prepared_frames, device)
    if frames_tensor is None:
        return None

    with torch.no_grad():
        if use_mixed_precision and device.type == "cuda":
            with torch.amp.autocast("cuda"):
                logits = model(frames_tensor, indices_tensor)
        else:
            logits = model(frames_tensor, indices_tensor)
        return torch.softmax(logits, dim=1)[0].cpu().numpy()
