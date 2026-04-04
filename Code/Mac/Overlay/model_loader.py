"""
Optimized model loader with singleton pattern and background loading.

Features:
- Singleton pattern: load model only once
- Background thread: load model without freezing UI
- Lazy loading: load on first use
- Warm-up: pre-run inference to ensure GPU is ready
"""

import sys
import threading
import time
from pathlib import Path
from typing import Optional, Tuple, Callable

import torch

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Model_inference.signflow_model.loader import (
    load_checkpoint_bundle,
    build_model,
    warmup_model,
)
from Model_inference.paths import CLASS_MAP_PATH, BEST_MODEL_PATH


class ModelLoaderState:
    """State machine for model loading."""
    NOT_STARTED = "not_started"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


class OptimizedModelLoader:
    """
    Singleton model loader with background loading and warmup.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.model = None
        self.class_names = None
        self.device = None
        self.state = ModelLoaderState.NOT_STARTED
        self.error_message = None
        self._load_thread = None
        self._callbacks = []
        self._ready_event = threading.Event()
        
        print("[ModelLoader] Initialized (singleton)")

    def add_callback(self, callback: Callable):
        """
        Add callback to be notified when model is loaded.
        Callback signature: callback(success: bool, error: str)
        """
        with self._lock:
            self._callbacks.append(callback)

    def _notify_callbacks(self, success: bool, error: str = ""):
        """Notify all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(success, error)
            except Exception as e:
                print(f"[ModelLoader] Error in callback: {e}")

    def _configure_device(self) -> torch.device:
        """Configure PyTorch device."""
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        if device.type == "cuda":
            torch.backends.cudnn.benchmark = True
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            print(f"[ModelLoader] GPU available: {torch.cuda.get_device_name(0)}")
        else:
            print("[ModelLoader] Using CPU (no GPU available)")
        
        return device

    def _load_model_sync(self, model_path: Path, class_map_path: Path) -> bool:
        """
        Synchronous model loading (runs in background thread).
        Returns True on success.
        """
        try:
            self.state = ModelLoaderState.LOADING
            print(f"[ModelLoader] Loading model: {model_path}")
            
            start_time = time.time()
            
            # Configure device
            self.device = self._configure_device()
            
            # Load checkpoint
            print("[ModelLoader] Loading checkpoint...")
            bundle = load_checkpoint_bundle(
                model_path=str(model_path),
                class_map_path=str(class_map_path),
                device=self.device,
            )
            
            # Build model
            print("[ModelLoader] Building model architecture...")
            self.model = build_model(bundle, self.device)
            self.class_names = bundle.class_names
            
            # Warmup
            print("[ModelLoader] Warming up model...")
            if self.device.type == "cuda":
                warmup_model(self.model, self.device, repeat=3, use_mixed_precision=True)
                torch.cuda.empty_cache()
            else:
                warmup_model(self.model, self.device, repeat=1, use_mixed_precision=False)
            
            # Set to evaluation mode
            self.model.eval()
            
            elapsed = time.time() - start_time
            print(f"[ModelLoader] Model loaded successfully in {elapsed:.2f}s")
            
            self.state = ModelLoaderState.READY
            self._ready_event.set()
            return True

        except Exception as e:
            error_msg = f"Failed to load model: {e}"
            print(f"[ModelLoader] ERROR: {error_msg}")
            self.state = ModelLoaderState.ERROR
            self.error_message = error_msg
            self._ready_event.set()
            return False

    def load_async(self, 
                   model_path: Optional[Path] = None,
                   class_map_path: Optional[Path] = None) -> bool:
        """
        Load model in background thread. Returns immediately.
        Use wait_ready() or add_callback() to be notified when done.
        """
        with self._lock:
            if self._load_thread is not None and self._load_thread.is_alive():
                print("[ModelLoader] Load already in progress")
                return False
            
            if self.state == ModelLoaderState.READY:
                print("[ModelLoader] Model already loaded")
                return True

            if model_path is None:
                model_path = BEST_MODEL_PATH
            if class_map_path is None:
                class_map_path = CLASS_MAP_PATH

            model_path = Path(model_path).resolve()
            class_map_path = Path(class_map_path).resolve()

            if not model_path.exists():
                self.error_message = f"Model file not found: {model_path}"
                self.state = ModelLoaderState.ERROR
                print(f"[ModelLoader] ERROR: {self.error_message}")
                return False

            self._ready_event.clear()
            self._load_thread = threading.Thread(
                target=lambda: self._load_model_sync(model_path, class_map_path),
                daemon=True,
                name="ModelLoader"
            )
            self._load_thread.start()
            return True

    def wait_ready(self, timeout_seconds: float = 60) -> bool:
        """
        Block until model is ready or timeout.
        Returns True if ready, False if timed out or error.
        """
        if self.state == ModelLoaderState.READY:
            return True

        print(f"[ModelLoader] Waiting for model (timeout: {timeout_seconds}s)...")
        ready = self._ready_event.wait(timeout=timeout_seconds)
        
        if not ready:
            print("[ModelLoader] TIMEOUT: Model took too long to load")
            return False

        if self.state != ModelLoaderState.READY:
            print(f"[ModelLoader] ERROR: {self.error_message}")
            return False

        return True

    def is_ready(self) -> bool:
        """Check if model is ready to use."""
        return self.state == ModelLoaderState.READY

    def get_model(self) -> Tuple[Optional[torch.nn.Module], Optional[list], Optional[torch.device]]:
        """
        Get loaded model. Returns (model, class_names, device).
        Raises RuntimeError if not ready.
        """
        if self.state != ModelLoaderState.READY:
            raise RuntimeError(f"Model not ready. State: {self.state}. Error: {self.error_message}")

        return self.model, self.class_names, self.device

    def get_status(self) -> dict:
        """Get loading status."""
        return {
            "state": self.state,
            "is_ready": self.is_ready(),
            "error": self.error_message,
            "has_model": self.model is not None,
            "device": str(self.device) if self.device else None,
            "class_count": len(self.class_names) if self.class_names else 0,
        }


# Global singleton instance
_loader = None


def get_model_loader() -> OptimizedModelLoader:
    """Get or create singleton model loader."""
    global _loader
    if _loader is None:
        _loader = OptimizedModelLoader()
    return _loader


def test_model_loader():
    """Test script for model loader."""
    print("[TEST] Model Loader Test")
    print("[TEST] ==================")
    
    loader = get_model_loader()
    
    print("[TEST] Starting async load...")
    loader.load_async()
    
    print("[TEST] Waiting for model (max 60s)...")
    ready = loader.wait_ready(timeout_seconds=60)
    
    if ready:
        model, class_names, device = loader.get_model()
        print(f"[TEST] SUCCESS: Model loaded on {device}")
        print(f"[TEST] Classes: {len(class_names)}")
        print(f"[TEST] Model: {type(model).__name__}")
    else:
        print(f"[TEST] FAILED: {loader.get_status()}")


if __name__ == "__main__":
    test_model_loader()
