from __future__ import annotations

import sys
import weakref
from ctypes import c_void_p
from typing import Dict, Optional

from PyQt5.QtCore import QEvent, QObject, Qt, QTimer
from PyQt5.QtGui import QGuiApplication

if sys.platform == "darwin":
    try:
        import AppKit
        import objc
        from Foundation import NSObject
    except Exception as exc:  # pragma: no cover - optional at runtime
        AppKit = None
        objc = None
        NSObject = object
        print(f"[macos_overlay_controller] AppKit import failed: {exc}")
else:  # pragma: no cover - non-macOS
    AppKit = None
    objc = None
    NSObject = object


def _appkit_int(name: str, default: int = 0) -> int:
    if AppKit is None:
        return int(default)
    return int(getattr(AppKit, name, default))


def _safe_call(target, method_name: str, *args):
    method = getattr(target, method_name, None)
    if callable(method):
        try:
            method(*args)
        except Exception:
            pass


if objc is not None:

    class _WorkspaceObserver(NSObject):
        def initWithController_(self, controller):
            self = objc.super(_WorkspaceObserver, self).init()
            if self is None:
                return None
            self._controller_ref = weakref.ref(controller)
            return self

        def _notify(self, reason: str):
            controller = self._controller_ref()
            if controller is not None:
                controller.schedule_reapply_all(reason)

        def activeSpaceDidChange_(self, _notification):
            self._notify("active_space_changed")

        def appActivated_(self, _notification):
            self._notify("app_activated")

        def appDeactivated_(self, _notification):
            self._notify("app_deactivated")

        def screenConfigChanged_(self, _notification):
            self._notify("screen_config_changed")


class MacOSOverlayController(QObject):
    """
    Single authority for native macOS window policy used by SignFlow overlay UIs.

    This keeps AppKit behavior centralized and event-driven instead of scattering
    many one-off style/level mutations across the UI codebase.
    """

    def __init__(self):
        super().__init__()
        self._windows: Dict[int, weakref.ReferenceType] = {}
        self._pending_window_ids: set[int] = set()
        self._watched_screen_ids: set[int] = set()
        self._app_signals_connected = False
        self._native_observers_installed = False
        self._app_policy_applied = False

        self._workspace_center = None
        self._default_center = None
        self._observer = None

        self._reapply_timer = QTimer(self)
        self._reapply_timer.setSingleShot(True)
        self._reapply_timer.setInterval(70)
        self._reapply_timer.timeout.connect(self._drain_reapply_queue)

        # Lightweight guard in case macOS silently resets window policy.
        self._watchdog_timer = QTimer(self)
        self._watchdog_timer.setInterval(4000)
        self._watchdog_timer.timeout.connect(lambda: self.schedule_reapply_all("watchdog"))

    def configure_app_policy(self):
        if sys.platform != "darwin" or AppKit is None or self._app_policy_applied:
            return
        try:
            app = AppKit.NSApplication.sharedApplication()
            if app is not None:
                policy = _appkit_int("NSApplicationActivationPolicyAccessory", 1)
                _safe_call(app, "setActivationPolicy_", policy)
            self._app_policy_applied = True
        except Exception as exc:
            print(f"[macos_overlay_controller] App policy setup failed: {exc}")

    def register_window(self, widget, role: str = "overlay"):
        if sys.platform != "darwin" or AppKit is None:
            return

        try:
            window_id = int(widget.winId())
        except Exception:
            return

        widget.setProperty("signflow_overlay_role", str(role or "overlay"))
        self._windows[window_id] = weakref.ref(widget)

        if not bool(widget.property("signflow_overlay_registered")):
            widget.setProperty("signflow_overlay_registered", True)
            widget.installEventFilter(self)
            widget.destroyed.connect(lambda *_: self._windows.pop(window_id, None))

        self._ensure_runtime_hooks()
        self.schedule_reapply_window(window_id, delay_ms=0)
        if self._windows and not self._watchdog_timer.isActive():
            self._watchdog_timer.start()

    def refresh_window(self, widget):
        if sys.platform != "darwin" or AppKit is None or widget is None:
            return
        try:
            window_id = int(widget.winId())
        except Exception:
            return
        self.schedule_reapply_window(window_id, delay_ms=40)

    def schedule_reapply_window(self, window_id: int, delay_ms: int = 70):
        if sys.platform != "darwin" or AppKit is None:
            return
        self._pending_window_ids.add(int(window_id))
        if delay_ms <= 0:
            self._drain_reapply_queue()
            return
        if not self._reapply_timer.isActive():
            self._reapply_timer.start(int(delay_ms))

    def schedule_reapply_all(self, _reason: str = ""):
        if sys.platform != "darwin" or AppKit is None:
            return
        self._pending_window_ids = {window_id for window_id in self._windows.keys()}
        if not self._reapply_timer.isActive():
            self._reapply_timer.start()

    def eventFilter(self, watched, event):
        result = super().eventFilter(watched, event)
        if sys.platform != "darwin" or AppKit is None:
            return result

        event_type = event.type()
        if event_type in (
            QEvent.Show,
            QEvent.Move,
            QEvent.Resize,
            QEvent.WindowStateChange,
            QEvent.WindowActivate,
            QEvent.WindowDeactivate,
            QEvent.ZOrderChange,
            QEvent.Polish,
            QEvent.PolishRequest,
        ):
            self.refresh_window(watched)
        elif event_type in (QEvent.Hide, QEvent.Close):
            self.refresh_window(watched)
        return result

    def _ensure_runtime_hooks(self):
        self.configure_app_policy()
        self._connect_qt_signals()
        self._install_native_observers()

    def _connect_qt_signals(self):
        if self._app_signals_connected:
            return
        app = QGuiApplication.instance()
        if app is None:
            return
        self._app_signals_connected = True

        try:
            app.applicationStateChanged.connect(
                lambda _state: self.schedule_reapply_all("qt_app_state")
            )
        except Exception:
            pass

        try:
            app.focusWindowChanged.connect(
                lambda _window: self.schedule_reapply_all("qt_focus_window")
            )
        except Exception:
            pass

        try:
            app.screenAdded.connect(self._on_screen_added)
            app.screenRemoved.connect(
                lambda _screen: self.schedule_reapply_all("qt_screen_removed")
            )
        except Exception:
            pass

        for screen in app.screens():
            self._watch_screen_geometry(screen)

    def _on_screen_added(self, screen):
        self._watch_screen_geometry(screen)
        self.schedule_reapply_all("qt_screen_added")

    def _watch_screen_geometry(self, screen):
        if screen is None:
            return
        sid = id(screen)
        if sid in self._watched_screen_ids:
            return
        self._watched_screen_ids.add(sid)
        try:
            screen.geometryChanged.connect(
                lambda _rect: self.schedule_reapply_all("qt_screen_geometry")
            )
        except Exception:
            pass

    def _install_native_observers(self):
        if self._native_observers_installed or objc is None or AppKit is None:
            return
        try:
            self._observer = _WorkspaceObserver.alloc().initWithController_(self)
            self._workspace_center = AppKit.NSWorkspace.sharedWorkspace().notificationCenter()
            self._default_center = AppKit.NSNotificationCenter.defaultCenter()

            space_changed = getattr(AppKit, "NSWorkspaceActiveSpaceDidChangeNotification", None)
            app_activated = getattr(AppKit, "NSWorkspaceDidActivateApplicationNotification", None)
            app_deactivated = getattr(AppKit, "NSWorkspaceDidDeactivateApplicationNotification", None)
            screen_changed = getattr(AppKit, "NSApplicationDidChangeScreenParametersNotification", None)

            if space_changed:
                self._workspace_center.addObserver_selector_name_object_(
                    self._observer,
                    objc.selector(self._observer.activeSpaceDidChange_, signature=b"v@:@"),
                    space_changed,
                    None,
                )
            if app_activated:
                self._workspace_center.addObserver_selector_name_object_(
                    self._observer,
                    objc.selector(self._observer.appActivated_, signature=b"v@:@"),
                    app_activated,
                    None,
                )
            if app_deactivated:
                self._workspace_center.addObserver_selector_name_object_(
                    self._observer,
                    objc.selector(self._observer.appDeactivated_, signature=b"v@:@"),
                    app_deactivated,
                    None,
                )
            if screen_changed:
                self._default_center.addObserver_selector_name_object_(
                    self._observer,
                    objc.selector(self._observer.screenConfigChanged_, signature=b"v@:@"),
                    screen_changed,
                    None,
                )
            self._native_observers_installed = True
        except Exception as exc:
            print(f"[macos_overlay_controller] Failed to install native observers: {exc}")

    def _drain_reapply_queue(self):
        if sys.platform != "darwin" or AppKit is None or objc is None:
            return
        if not self._pending_window_ids:
            return

        to_apply = list(self._pending_window_ids)
        self._pending_window_ids.clear()
        dead = []

        for window_id in to_apply:
            ref = self._windows.get(window_id)
            widget = ref() if ref is not None else None
            if widget is None:
                dead.append(window_id)
                continue
            self._apply_native_policy(widget)

        for window_id in dead:
            self._windows.pop(window_id, None)

        if not self._windows and self._watchdog_timer.isActive():
            self._watchdog_timer.stop()

    def _resolve_ns_window(self, widget):
        try:
            ns_view = objc.objc_object(c_void_p=int(widget.winId()))
            return ns_view.window()
        except Exception:
            return None

    def _target_level_for_role(self, role: str) -> int:
        normalized = (role or "overlay").strip().lower()
        if normalized == "preview":
            return _appkit_int("NSFloatingWindowLevel", 3)
        return _appkit_int("NSStatusWindowLevel", _appkit_int("NSFloatingWindowLevel", 3))

    def _apply_native_policy(self, widget):
        ns_window = self._resolve_ns_window(widget)
        if ns_window is None:
            return

        role = str(widget.property("signflow_overlay_role") or "overlay")
        target_level = self._target_level_for_role(role)

        # Keep the window in every Space + fullscreen contexts.
        behavior = (
            _appkit_int("NSWindowCollectionBehaviorCanJoinAllSpaces", 0)
            | _appkit_int("NSWindowCollectionBehaviorFullScreenAuxiliary", 0)
            | _appkit_int("NSWindowCollectionBehaviorStationary", 0)
            | _appkit_int("NSWindowCollectionBehaviorIgnoresCycle", 0)
        )

        nonactivating_mask = _appkit_int("NSWindowStyleMaskNonactivatingPanel", 0)
        if nonactivating_mask:
            try:
                style_mask = int(ns_window.styleMask())
                if (style_mask & nonactivating_mask) == 0:
                    ns_window.setStyleMask_(style_mask | nonactivating_mask)
            except Exception:
                pass

        _safe_call(ns_window, "setCollectionBehavior_", int(behavior))
        _safe_call(ns_window, "setLevel_", int(target_level))
        _safe_call(ns_window, "setHidesOnDeactivate_", False)
        _safe_call(ns_window, "setIgnoresCycle_", True)
        _safe_call(ns_window, "setReleasedWhenClosed_", False)
        _safe_call(ns_window, "setCanHide_", False)
        _safe_call(ns_window, "setBecomesKeyOnlyIfNeeded_", False)
        _safe_call(ns_window, "setWorksWhenModal_", True)
        _safe_call(ns_window, "setExcludedFromWindowsMenu_", True)

        # Respect click-through mode when enabled from Qt.
        ignore_mouse = bool(widget.testAttribute(Qt.WA_TransparentForMouseEvents))
        _safe_call(ns_window, "setIgnoresMouseEvents_", ignore_mouse)

        if widget.isVisible():
            _safe_call(ns_window, "orderFront_", None)


class _NoopOverlayController:
    def configure_app_policy(self):
        return None

    def register_window(self, widget, role: str = "overlay"):
        return None

    def refresh_window(self, widget):
        return None

    def schedule_reapply_all(self, _reason: str = ""):
        return None


_CONTROLLER: Optional[object] = None


def get_macos_overlay_controller():
    global _CONTROLLER
    if _CONTROLLER is None:
        if sys.platform == "darwin" and AppKit is not None and objc is not None:
            _CONTROLLER = MacOSOverlayController()
        else:
            _CONTROLLER = _NoopOverlayController()
    return _CONTROLLER
