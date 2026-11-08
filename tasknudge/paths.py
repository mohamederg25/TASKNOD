"""Filesystem locations used by TaskNudge."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def data_dir() -> Path:
    """Return the per-user directory for the database, config and logs.

    Set ``TASKNUDGE_DATA_DIR`` to keep everything in a different folder (useful
    for portable installs and for running the app from a USB stick).
    """

    override = os.environ.get("TASKNUDGE_DATA_DIR")
    if override:
        path = Path(override).expanduser()
    elif sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        path = Path(base) / "TaskNudge"
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / "TaskNudge"
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        path = Path(base) / "TaskNudge"

    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return data_dir() / "config.json"


def database_path() -> Path:
    return data_dir() / "tasks.db"


def log_path() -> Path:
    return data_dir() / "tasknudge.log"


def sound_path() -> Path:
    return data_dir() / "sounds" / "chime.wav"
