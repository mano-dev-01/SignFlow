from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import torch

from .architecture import build_landmark_transformer
from .config import MAX_FRAMES, NUM_COORDS, NUM_LANDMARKS, resolve_model_paths


@dataclass(frozen=True)
class LoadedCheckpoint:
    checkpoint: dict
    config: dict
    num_classes: int
    class_names: dict[int, str]
    model_path: Path
    class_map_path: Path
    best_val_acc: float


def _load_class_names(class_map_path: Path, checkpoint: dict) -> dict[int, str]:
    if class_map_path.exists():
        with class_map_path.open() as handle:
            return {int(key): value for key, value in json.load(handle).items()}
    return {index: name for index, name in enumerate(checkpoint.get("class_names", []))}


def load_checkpoint_bundle(
    model_path: str | Path | None,
    class_map_path: str | Path | None,
    device,
) -> LoadedCheckpoint:
    resolved_paths = resolve_model_paths(model_path, class_map_path)
    checkpoint = torch.load(
        resolved_paths.model_path,
        map_location=device,
        weights_only=False,
    )
    return LoadedCheckpoint(
        checkpoint=checkpoint,
        config=checkpoint.get("config", {}),
        num_classes=checkpoint.get("num_classes", 256),
        class_names=_load_class_names(resolved_paths.class_map_path, checkpoint),
        model_path=resolved_paths.model_path,
        class_map_path=resolved_paths.class_map_path,
        best_val_acc=checkpoint.get("best_val_acc", 0),
    )


def build_model(bundle: LoadedCheckpoint, device) -> torch.nn.Module:
    model = build_landmark_transformer(bundle.num_classes, bundle.config).to(device)
    model.load_state_dict(bundle.checkpoint["model_state_dict"])
    model.eval()
    return model


def format_val_accuracy(val_acc: float) -> str:
    return f"{val_acc * 100:.1f}" if val_acc < 1 else f"{val_acc:.1f}"


def warmup_model(model, device, repeat: int = 1, use_mixed_precision: bool = False) -> None:
    dummy_frames = torch.zeros(1, MAX_FRAMES, NUM_LANDMARKS, NUM_COORDS, device=device)
    dummy_indices = torch.full((1, MAX_FRAMES), -1.0, device=device)
    dummy_indices[0, 0] = 0.0

    with torch.no_grad():
        if use_mixed_precision and device.type == "cuda":
            with torch.amp.autocast("cuda"):
                for _ in range(max(1, int(repeat))):
                    model(dummy_frames, dummy_indices)
        else:
            for _ in range(max(1, int(repeat))):
                model(dummy_frames, dummy_indices)
