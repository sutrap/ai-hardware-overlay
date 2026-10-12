"""The always-on-top HUD overlay window."""

from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QLabel, QMenu, QVBoxLayout, QWidget

from .config import config_path, save_config
from .styles import build_stylesheet


MIN_OPACITY = 0.20
MAX_OPACITY = 1.00
OPACITY_STEP = 0.05


class Overlay(QWidget):
    """Frameless, draggable, semi-transparent overlay with a context menu."""

    quit_requested = Signal()
    interval_changed = Signal(int)

    def __init__(
        self,
        config: Dict[str, Any],
        config_file: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.config = config
        self.config_file = config_file or config_path()
        self._drag_offset: Optional[QPoint] = None

        self.setObjectName("Overlay")
        self.setWindowTitle("AI Hardware Overlay")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.label = QLabel("AI Hardware Overlay\n-------------------")
        self.label.setObjectName("OverlayText")
        self.label.setTextInteractionFlags(Qt.NoTextInteraction)
        # Let mouse events reach the parent widget so dragging works.
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.addWidget(self.label)

        self.setStyleSheet(build_stylesheet(config.get("font_size", 13)))

        opacity = self._clamp_opacity(config.get("opacity", 0.85))
        self.setWindowOpacity(opacity)

        self.move(
            int(config.get("window_x", 50)),
            int(config.get("window_y", 50)),
        )
        self.adjustSize()

    # ------------------------------------------------------------------ state

    @staticmethod
    def _clamp_opacity(value: Any) -> float:
        try:
            opacity = float(value)
        except (TypeError, ValueError):
            opacity = 0.85
        return max(MIN_OPACITY, min(MAX_OPACITY, opacity))

    def set_text(self, text: str) -> None:
        """Update the displayed snapshot and resize the window to fit."""
        self.label.setText(text)
        self.adjustSize()

    def save_state(self) -> None:
        """Persist position and opacity to config.json."""
        try:
            position = self.pos()
            self.config["window_x"] = int(position.x())
            self.config["window_y"] = int(position.y())
            self.config["opacity"] = round(self.windowOpacity(), 3)
            save_config(self.config, self.config_file)
        except Exception:
            pass

    # ------------------------------------------------------------- interaction

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() != Qt.LeftButton:
            return
        # Wayland (and modern X11) want the compositor to drive the move. This
        # works on both platforms; if it is unavailable we fall back to a manual
        # drag using the recorded grab offset.
        started = False
        handle = self.windowHandle()
        if handle is not None:
            try:
                started = bool(handle.startSystemMove())
            except Exception:
                started = False
        if not started:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._drag_offset = None
        event.accept()

    def contextMenuEvent(self, event) -> None:  # type: ignore[override]
        menu = QMenu(self)

        quit_action = QAction("Beenden", self)
        quit_action.triggered.connect(self._request_quit)
        menu.addAction(quit_action)

        menu.addSeparator()

        more_transparent = QAction("Transparenz erh\u00f6hen", self)
        more_transparent.triggered.connect(lambda: self._change_opacity(-OPACITY_STEP))
        menu.addAction(more_transparent)

        less_transparent = QAction("Transparenz verringern", self)
        less_transparent.triggered.connect(lambda: self._change_opacity(OPACITY_STEP))
        menu.addAction(less_transparent)

        menu.addSeparator()

        interval_menu = menu.addMenu("Aktualisierungsintervall")
        interval_group = QActionGroup(self)
        interval_group.setExclusive(True)
        current = self.config.get("refresh_interval_ms", 1000)
        for milliseconds in (500, 1000, 2000):
            action = QAction(f"{milliseconds} ms", self)
            action.setCheckable(True)
            action.setChecked(int(current) == milliseconds)
            action.triggered.connect(
                lambda _checked=False, ms=milliseconds: self._set_interval(ms)
            )
            interval_group.addAction(action)
            interval_menu.addAction(action)

        menu.exec(event.globalPos())

    def _change_opacity(self, delta: float) -> None:
        opacity = self._clamp_opacity(self.windowOpacity() + delta)
        self.setWindowOpacity(opacity)
        self.config["opacity"] = round(opacity, 3)

    def _set_interval(self, milliseconds: int) -> None:
        self.config["refresh_interval_ms"] = int(milliseconds)
        self.interval_changed.emit(int(milliseconds))

    def _request_quit(self) -> None:
        self.close()
        self.quit_requested.emit()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.save_state()
        super().closeEvent(event)
