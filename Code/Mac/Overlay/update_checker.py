"""
Update checker for SignFlow macOS app.

Fetches version info from remote JSON and determines if update is available.
Runs in background thread to avoid UI blocking.
"""

import sys
import threading
import time
from typing import Optional, Dict, Callable
from pathlib import Path
from packaging import version as pkg_version

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from version import APP_VERSION, UPDATE_CHECK_URL


class UpdateCheckResult:
    """Result of an update check."""
    
    def __init__(self, 
                 has_update: bool = False,
                 current_version: str = "",
                 latest_version: str = "",
                 download_url: str = "",
                 release_notes: str = "",
                 error: Optional[str] = None):
        self.has_update = has_update
        self.current_version = current_version
        self.latest_version = latest_version
        self.download_url = download_url
        self.release_notes = release_notes
        self.error = error

    def __repr__(self):
        return (f"UpdateCheckResult(has_update={self.has_update}, "
                f"current={self.current_version}, latest={self.latest_version}, "
                f"error={self.error})")


class UpdateChecker:
    """
    Background update checker for SignFlow.
    """

    def __init__(self, check_url: str = UPDATE_CHECK_URL, timeout_seconds: int = 10):
        if not REQUESTS_AVAILABLE:
            print("[UpdateChecker] WARNING: requests not available")
        
        self.check_url = check_url
        self.timeout_seconds = timeout_seconds
        self.current_version = APP_VERSION
        self.last_check_time = None
        self.last_result = None
        self._check_thread = None
        self._callbacks = []
        
        print(f"[UpdateChecker] Initialized: current version {self.current_version}")

    def add_callback(self, callback: Callable):
        """
        Register callback for update check results.
        Signature: callback(result: UpdateCheckResult)
        """
        self._callbacks.append(callback)

    def _notify_callbacks(self, result: UpdateCheckResult):
        """Notify all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(result)
            except Exception as e:
                print(f"[UpdateChecker] Error in callback: {e}")

    @staticmethod
    def _parse_version_string(ver_str: str):
        """
        Parse version string. Returns packaging.version.Version or None.
        """
        try:
            return pkg_version.parse(ver_str)
        except Exception as e:
            print(f"[UpdateChecker] Error parsing version '{ver_str}': {e}")
            return None

    @staticmethod
    def _compare_versions(current: str, latest: str) -> bool:
        """
        Compare versions. Returns True if latest > current.
        """
        try:
            current_v = UpdateChecker._parse_version_string(current)
            latest_v = UpdateChecker._parse_version_string(latest)
            
            if current_v is None or latest_v is None:
                return False
            
            return latest_v > current_v
        except Exception as e:
            print(f"[UpdateChecker] Error comparing versions: {e}")
            return False

    def check_for_updates_sync(self) -> UpdateCheckResult:
        """
        Synchronously check for updates (blocking).
        """
        if not REQUESTS_AVAILABLE:
            return UpdateCheckResult(error="requests library not available")

        try:
            print(f"[UpdateChecker] Checking for updates: {self.check_url}")
            
            response = requests.get(
                self.check_url,
                timeout=self.timeout_seconds,
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            
            latest_version = data.get("version", "")
            download_url = data.get("download_url", "")
            release_notes = data.get("notes", "")
            
            if not latest_version:
                return UpdateCheckResult(error="Invalid remote data: missing 'version'")
            
            has_update = self._compare_versions(self.current_version, latest_version)
            
            print(f"[UpdateChecker] Latest version: {latest_version}, Has update: {has_update}")
            
            result = UpdateCheckResult(
                has_update=has_update,
                current_version=self.current_version,
                latest_version=latest_version,
                download_url=download_url,
                release_notes=release_notes,
            )
            
            self.last_result = result
            self.last_check_time = time.time()
            return result

        except requests.Timeout:
            error = "Update check timed out"
            print(f"[UpdateChecker] {error}")
            return UpdateCheckResult(error=error)
        
        except requests.ConnectionError as e:
            error = f"Connection error: {e}"
            print(f"[UpdateChecker] {error}")
            return UpdateCheckResult(error=error)
        
        except Exception as e:
            error = f"Update check failed: {e}"
            print(f"[UpdateChecker] {error}")
            return UpdateCheckResult(error=error)

    def check_for_updates_async(self):
        """
        Check for updates in background thread.
        Results are passed to registered callbacks.
        """
        if self._check_thread is not None and self._check_thread.is_alive():
            print("[UpdateChecker] Check already in progress")
            return

        def check_thread_func():
            try:
                result = self.check_for_updates_sync()
                self._notify_callbacks(result)
            except Exception as e:
                print(f"[UpdateChecker] Error in check thread: {e}")
                result = UpdateCheckResult(error=str(e))
                self._notify_callbacks(result)

        self._check_thread = threading.Thread(
            target=check_thread_func,
            daemon=True,
            name="UpdateChecker"
        )
        self._check_thread.start()

    def get_cached_result(self) -> Optional[UpdateCheckResult]:
        """Get last check result."""
        return self.last_result


def test_update_checker():
    """Test script for update checker."""
    print("[TEST] Update Checker Test")
    print("[TEST] ====================")
    
    checker = UpdateChecker()
    
    print(f"[TEST] Current version: {checker.current_version}")
    print(f"[TEST] Check URL: {checker.check_url}")
    
    print("[TEST] Checking for updates...")
    result = checker.check_for_updates_sync()
    
    print(f"[TEST] Result: {result}")
    if result.error:
        print(f"[TEST] Error: {result.error}")
    else:
        print(f"[TEST] Has update: {result.has_update}")
        if result.has_update:
            print(f"[TEST] Latest: {result.latest_version}")
            print(f"[TEST] Download: {result.download_url}")
            print(f"[TEST] Notes: {result.release_notes}")


if __name__ == "__main__":
    test_update_checker()
