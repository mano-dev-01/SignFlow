#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def _unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    output: list[Path] = []
    for item in paths:
        key = str(item.resolve()) if item.exists() else str(item)
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def _runtime_roots() -> list[Path]:
    roots: list[Path] = []
    exe_dir = Path(sys.executable).resolve().parent
    meipass = Path(getattr(sys, "_MEIPASS", exe_dir))
    resources_dir = exe_dir.parent / "Resources"

    roots.extend(
        [
            meipass,
            meipass / "_internal",
            exe_dir,
            exe_dir / "_internal",
            resources_dir,
            Path(__file__).resolve().parent.parent,
        ]
    )
    return _unique_paths(roots)


def _inject_source_paths() -> None:
    for root in _runtime_roots():
        for rel in ("Overlay", "Model_inference"):
            candidate = root / rel
            if candidate.exists():
                candidate_str = str(candidate)
                if candidate_str not in sys.path:
                    sys.path.insert(0, candidate_str)
                    print(f"[APP_BOOTSTRAP] added to sys.path: {candidate_str}")


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _patch_model_paths() -> None:
    """
    Keep model paths stable in frozen app layouts where the bundle may place
    resources in either <root>/Models or <root>/_internal/Models.
    """
    try:
        from Model_inference import paths as model_paths
    except Exception as exc:
        print(f"[APP_BOOTSTRAP] model paths patch skipped: {exc}")
        return

    candidates_models: list[Path] = []
    candidates_class_map: list[Path] = []

    for root in _runtime_roots():
        candidates_models.extend(
            [
                root / "Models",
                root / "models",
                root / "_internal" / "Models",
                root / "_internal" / "models",
            ]
        )
        candidates_class_map.extend(
            [
                root / "Model_inference" / "class_map.json",
                root / "_internal" / "Model_inference" / "class_map.json",
            ]
        )

    models_dir = _first_existing(candidates_models)
    class_map_path = _first_existing(candidates_class_map)

    if models_dir is not None:
        model_paths.MODELS_DIR = models_dir
        model_paths.MEDIAPIPE_MODELS_DIR = models_dir / "mediapipe_models"
        model_paths.BEST_MODEL_PATH = models_dir / "temporal_model.pth"
        model_paths.PKL_MODEL_PATH = models_dir / "static_model.pkl"
        print(f"[APP_BOOTSTRAP] MODELS_DIR -> {models_dir}")

    if class_map_path is not None:
        model_paths.CLASS_MAP_PATH = class_map_path
        print(f"[APP_BOOTSTRAP] CLASS_MAP_PATH -> {class_map_path}")


def _patch_remote_window_compat() -> None:
    """
    Compatibility shim for builds where RemoteOverlayWindow references
    _should_flip_input() but that helper is absent.
    """
    try:
        from signflow_overlay.remote_window import RemoteOverlayWindow
    except Exception as exc:
        print(f"[APP_BOOTSTRAP] remote window patch skipped: {exc}")
        return

    if hasattr(RemoteOverlayWindow, "_should_flip_input"):
        return

    def _should_flip_input(self) -> bool:
        return bool(getattr(self, "flip_input", True))

    setattr(RemoteOverlayWindow, "_should_flip_input", _should_flip_input)
    print("[APP_BOOTSTRAP] Applied _should_flip_input compatibility patch")


def main(argv: list[str] | None = None) -> None:
    _inject_source_paths()
    _patch_model_paths()
    _patch_remote_window_compat()

    from signflow_overlay.remote_app import main as remote_main

    remote_main(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    main()
