"""
Robust audio input handler using sounddevice (better for PyInstaller bundling than PyAudio).
"""

from __future__ import annotations

import sys
from typing import Optional, Callable

try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    sd = None
    np = None


class AudioHandler:
    """
    High-level audio input handler with recording and real-time processing.
    """

    def __init__(self, 
                 sample_rate: int = 16000,
                 channels: int = 1,
                 blocksize: int = 2048):
        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError("sounddevice not available. Install: pip install sounddevice")

        self.sample_rate = sample_rate
        self.channels = channels
        self.blocksize = blocksize
        self.is_recording = False
        self.stream = None
        self.callback_func = None
        
        print(f"[AudioHandler] Initialized: {sample_rate}Hz, {channels} channel(s)")
        self._list_devices()

    def _list_devices(self):
        """List available audio input devices."""
        try:
            devices = sd.query_devices()
            print("[AudioHandler] Available input devices:")
            for i, device in enumerate(devices):
                if device["max_input_channels"] > 0:
                    print(f"  [{i}] {device['name']} ({device['max_input_channels']} in)")
        except Exception as e:
            print(f"[AudioHandler] Error listing devices: {e}")

    def start_recording(self, callback: Optional[Callable] = None):
        """
        Start recording audio. Optionally provide a callback for real-time processing.
        
        Callback signature: callback(audio_chunk: np.ndarray)
        """
        if self.is_recording:
            print("[AudioHandler] Already recording")
            return

        self.callback_func = callback
        
        try:
            def stream_callback(indata, frames, time_info, status):
                if status:
                    print(f"[AudioHandler] Stream status: {status}")
                
                # Copy frame (indata is read-only)
                audio_data = indata.copy()
                
                if self.callback_func:
                    self.callback_func(audio_data)

            self.stream = sd.InputStream(
                device=None,  # Default device
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.blocksize,
                callback=stream_callback,
                latency="low"
            )
            
            self.stream.start()
            self.is_recording = True
            print("[AudioHandler] Recording started")

        except Exception as e:
            print(f"[AudioHandler] Error starting recording: {e}")
            self.is_recording = False

    def stop_recording(self):
        """Stop recording audio."""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        self.is_recording = False
        print("[AudioHandler] Recording stopped")

    def record_chunk(self, duration_seconds: float) -> Optional[np.ndarray]:
        """
        Record a single chunk of audio.
        
        Returns: numpy array of shape (samples, channels)
        """
        try:
            print(f"[AudioHandler] Recording {duration_seconds}s...")
            audio_data = sd.rec(
                frames=int(self.sample_rate * duration_seconds),
                samplerate=self.sample_rate,
                channels=self.channels,
                blocking=True
            )
            print(f"[AudioHandler] Record complete: {audio_data.shape}")
            return audio_data

        except Exception as e:
            print(f"[AudioHandler] Error recording chunk: {e}")
            return None

    def close(self):
        """Stop and cleanup."""
        self.stop_recording()


def test_audio():
    """Test script for audio."""
    print("[TEST] Audio Handler Test")
    print("[TEST] =====================")
    
    try:
        handler = AudioHandler(sample_rate=16000)
        
        print("[TEST] Recording 3 seconds...")
        audio = handler.record_chunk(duration_seconds=3)
        
        if audio is not None:
            print(f"[TEST] SUCCESS: Recorded {audio.shape}")
            print(f"[TEST] Min: {audio.min():.4f}, Max: {audio.max():.4f}, Mean: {audio.mean():.4f}")
            
            # Save as WAV for verification
            try:
                import soundfile as sf
                sf.write("/tmp/audio_test.wav", audio, handler.sample_rate)
                print("[TEST] Saved to /tmp/audio_test.wav")
            except ImportError:
                print("[TEST] (soundfile not installed, skipped save)")
        else:
            print("[TEST] FAILED: Could not record audio")
            print("[TEST] TROUBLESHOOTING:")
            print("  1. Check System Preferences > Security & Privacy > Microphone")
            print("  2. Ensure SignFlow is listed and enabled")
            print("  3. Try: sudo killall -9 coreaudiod")
        
        handler.close()
        
    except Exception as e:
        print(f"[TEST] Error: {e}")
        print("[TEST] Install sounddevice: pip install sounddevice")


if __name__ == "__main__":
    test_audio()
