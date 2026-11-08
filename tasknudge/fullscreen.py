"""Best-effort detection of fullscreen apps so TaskNudge can stay quiet.

Windows is the primary target. The check combines the shell's user-notification
state with a geometry fallback for borderless fullscreen windows.
"""

from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes

log = logging.getLogger(__name__)

# SHQueryUserNotificationState values.
_QUNS_NOT_PRESENT = 1
_QUNS_BUSY = 2
_QUNS_RUNNING_D3D_FULL_SCREEN = 3
_QUNS_PRESENTATION_MODE = 4
_QUNS_ACCEPTS_NOTIFICATIONS = 5
_QUNS_QUIET_TIME = 6

_SUPPRESS_STATES = {
    _QUNS_NOT_PRESENT,
    _QUNS_BUSY,
    _QUNS_RUNNING_D3D_FULL_SCREEN,
    _QUNS_PRESENTATION_MODE,
    _QUNS_QUIET_TIME,
}


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


def _windows_fullscreen() -> bool:
    try:
        shell32 = ctypes.windll.shell32
        user32 = ctypes.windll.user32

        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.IsWindowVisible.restype = wintypes.BOOL
        user32.IsIconic.argtypes = [wintypes.HWND]
        user32.IsIconic.restype = wintypes.BOOL
        user32.IsZoomed.argtypes = [wintypes.HWND]
        user32.IsZoomed.restype = wintypes.BOOL
        user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetClassNameW.restype = ctypes.c_int
        user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        user32.GetWindowRect.restype = wintypes.BOOL
        user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        user32.MonitorFromWindow.restype = ctypes.c_void_p
        user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(_MONITORINFO)]
        user32.GetMonitorInfoW.restype = wintypes.BOOL
        shell32.SHQueryUserNotificationState.argtypes = [ctypes.POINTER(ctypes.c_int)]
        shell32.SHQueryUserNotificationState.restype = ctypes.c_long

        state = ctypes.c_int()
        result = shell32.SHQueryUserNotificationState(ctypes.byref(state))
        if result == 0 and state.value in _SUPPRESS_STATES:
            return True

        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return False

        # A normal maximized window also fills the monitor visually, but the
        # taskbar is still present. Do not treat it as an interruption.
        if user32.IsZoomed(hwnd):
            return False

        class_buffer = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buffer, 256)
        if class_buffer.value in {"Progman", "WorkerW", "Shell_TrayWnd"}:
            return False

        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False

        monitor = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
        if not monitor:
            return False
        info = _MONITORINFO()
        info.cbSize = ctypes.sizeof(_MONITORINFO)
        if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return False

        bounds = info.rcMonitor
        tolerance = 2
        covers_monitor = (
            rect.left <= bounds.left + tolerance
            and rect.top <= bounds.top + tolerance
            and rect.right >= bounds.right - tolerance
            and rect.bottom >= bounds.bottom - tolerance
        )
        return bool(covers_monitor)
    except Exception:
        log.debug("Fullscreen detection failed", exc_info=True)
        return False


def is_fullscreen_app_active() -> bool:
    """Return True if a game, video, presentation or fullscreen app is active."""

    if sys.platform == "win32":
        return _windows_fullscreen()
    return False
