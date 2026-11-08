"""A tiny generated chime, played only while reminders are visible."""

from __future__ import annotations

import logging
import math
import struct
import wave
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QUrl

from tasknudge.paths import sound_path

log = logging.getLogger(__name__)

try:
    from PyQt6.QtMultimedia import QSoundEffect

    _MULTIMEDIA_AVAILABLE = True
except Exception:  # pragma: no cover - depends on the machine's Qt install
    QSoundEffect = None  # type: ignore[assignment]
    _MULTIMEDIA_AVAILABLE = False


def _write_chime(path: Path) -> None:
    """Create a short, soft two-note chime using only the standard library."""

    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 44100
    duration = 0.62
    frames = int(sample_rate * duration)
    notes = [
        (880.00, 0.00, 0.30, 0.55),  # A5
        (1174.66, 0.17, 0.42, 0.42),  # D6
    ]
    samples: list[int] = []
    for index in range(frames):
        moment = index / sample_rate
        value = 0.0
        for frequency, start, length, amplitude in notes:
            local = moment - start
            if 0.0 <= local < length:
                attack = min(1.0, local / 0.012)
                release = min(1.0, (length - local) / 0.09)
                decay = math.exp(-2.8 * local / length)
                envelope = attack * release * decay
                tone = (
                    math.sin(2.0 * math.pi * frequency * local)
                    + 0.18 * math.sin(2.0 * math.pi * frequency * 2.0 * local)
                    + 0.07 * math.sin(2.0 * math.pi * frequency * 3.0 * local)
                )
                value += tone * envelope * amplitude
        samples.append(int(max(-0.95, min(0.95, value * 0.52)) * 32767))

    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))


class SoundPlayer(QObject):
    def __init__(self, enabled: bool = True, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.enabled = enabled
        self._effect = None
        self._failed = False
        if not _MULTIMEDIA_AVAILABLE:
            log.info("Qt Multimedia is unavailable; reminders will be silent.")
            return
        try:
            chime = sound_path()
            if not chime.exists():
                _write_chime(chime)
            self._effect = QSoundEffect(self)
            self._effect.setSource(QUrl.fromLocalFile(str(chime)))
            self._effect.setLoopCount(1)
            self._effect.setVolume(0.22)
        except Exception:
            log.info("Could not initialise reminder sound", exc_info=True)
            self._effect = None

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def play(self, force: bool = False) -> None:
        if (not self.enabled and not force) or self._effect is None or self._failed:
            return
        try:
            self._effect.play()
        except Exception:
            self._failed = True
            log.info("Reminder sound could not be played", exc_info=True)
