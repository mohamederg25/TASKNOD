"""Windows login auto-start via HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "TaskNudge"


def is_supported() -> bool:
    return sys.platform == "win32"


def _command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable)}" --minimized'

    script = Path(__file__).resolve().parent.parent / "main.py"
    executable = Path(sys.executable)
    pythonw = executable.with_name("pythonw.exe")
    if pythonw.exists():
        executable = pythonw
    return f'"{executable}" "{script}" --minimized'


def is_enabled() -> bool:
    if not is_supported():
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
            return True
    except FileNotFoundError:
        return False
    except OSError as exc:
        log.warning("Could not read auto-start setting: %s", exc)
        return False


def set_enabled(enabled: bool) -> None:
    """Add or remove the login entry. Raises OSError if Windows rejects it."""

    if not is_supported():
        raise OSError("Auto-start setup is currently implemented for Windows only.")

    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _command())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass


def command_preview() -> str:
    """Useful for troubleshooting from the command line."""

    return _command()
