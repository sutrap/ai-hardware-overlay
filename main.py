"""ai-hardware-overlay - entry point.

Creates the overlay window and a background :class:`MonitorThread` that gathers
system, GPU and model data on a fixed interval and pushes a formatted text
snapshot to the UI. All blocking work (subprocess, HTTP) happens off the UI
thread.
"""

from __future__ import annotations

import sys
import time
from typing import Any, Callable, Dict, List

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QApplication

from app.config import load_config
from app.formatter import format_snapshot
from app.overlay import Overlay
from model_sources.detector import ModelDetector
from monitors.gpu_monitor import GpuMonitor
from monitors.system_monitor import SystemMonitor


class MonitorThread(QThread):
    """Background data collector. Emits a formatted snapshot each cycle."""

    updated = Signal(str)

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__()
        self.config = config
        self._interval_ms = max(100, int(config.get("refresh_interval_ms", 1000)))
        self._stop = False
        self._system = SystemMonitor()
        self._gpu = GpuMonitor(config)
        self._models = ModelDetector(config)

    def set_interval(self, milliseconds: int) -> None:
        self._interval_ms = max(100, int(milliseconds))

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        while not self._stop:
            started = time.monotonic()
            snapshot = self._collect()
            if self._stop:
                break
            self.updated.emit(snapshot)
            self._sleep_until(started)

        try:
            self._gpu.close()
        except Exception:
            pass

    def _collect(self) -> str:
        system = self._safe(self._system.get_stats, {})
        models = self._safe(self._models.get_models, [])
        gpus = self._safe(self._gpu.get_gpu_stats, [])
        try:
            return format_snapshot(system, models, gpus, self.config)
        except Exception:
            return "AI Hardware Overlay\n-------------------\nDaten nicht verf\u00fcgbar"

    def _sleep_until(self, started: float) -> None:
        # Sleep in short slices so interval changes and stop() react quickly.
        while not self._stop:
            remaining = (self._interval_ms / 1000.0) - (time.monotonic() - started)
            if remaining <= 0:
                return
            self.msleep(min(100, max(10, int(remaining * 1000))))

    @staticmethod
    def _safe(func: Callable[[], Any], default: Any) -> Any:
        try:
            return func()
        except Exception:
            return default


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("AI Hardware Overlay")

    config = load_config()
    overlay = Overlay(config)

    worker = MonitorThread(config)
    worker.updated.connect(overlay.set_text)
    overlay.interval_changed.connect(worker.set_interval)

    overlay.quit_requested.connect(app.quit)
    app.aboutToQuit.connect(overlay.save_state)
    app.aboutToQuit.connect(worker.stop)

    worker.start()
    overlay.show()

    exit_code = app.exec()

    worker.stop()
    worker.wait(2000)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
