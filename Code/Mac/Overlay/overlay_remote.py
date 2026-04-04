"""Compatibility entry point for the refactored remote overlay launcher."""

import traceback

try:
    from signflow_overlay.remote_app import main
except Exception as exc:
    print('[overlay_remote.py] ERROR: Failed importing signflow_overlay.remote_app')
    traceback.print_exc()
    raise


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print('[overlay_remote.py] ERROR: main() failed')
        traceback.print_exc()
        raise
