from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cpc.ui.widgets.preview_widget import PreviewWidget


class CleanPreviewWindow(QWidget):
    """
    Dedicated projector / clean preview window for secondary monitor or OBS window capture.
    
    Operates independently of the main studio window and does not stop the session when closed.
    """

    window_closed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("CPC Studio — Clean Preview Window")
        self.setMinimumSize(480, 360)
        self.resize(800, 600)
        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet("""
            QWidget {
                background-color: #0b0b0e;
                color: #f4f4f6;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top Control Bar (minimal toolbar)
        self._toolbar = QWidget()
        self._toolbar.setStyleSheet("""
            QWidget {
                background-color: #14141a;
                border-bottom: 1px solid #22222a;
                padding: 4px 8px;
            }
            QCheckBox, QComboBox, QPushButton {
                font-size: 11px;
            }
        """)
        tb_layout = QHBoxLayout(self._toolbar)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.setSpacing(10)

        title_lbl = QLabel("Clean Preview")
        font = QFont(title_lbl.font())
        font.setBold(True)
        title_lbl.setFont(font)
        title_lbl.setStyleSheet("color: #60a5fa;")
        tb_layout.addWidget(title_lbl)

        # Always on top
        self._always_on_top_cb = QCheckBox("Always on Top")
        self._always_on_top_cb.toggled.connect(self._toggle_always_on_top)
        tb_layout.addWidget(self._always_on_top_cb)

        # HUD visibility
        tb_layout.addWidget(QLabel("HUD:"))
        self._hud_combo = QComboBox()
        self._hud_combo.addItems(["Full", "Minimal", "Hidden"])
        self._hud_combo.currentIndexChanged.connect(self._on_hud_changed)
        tb_layout.addWidget(self._hud_combo)

        tb_layout.addStretch(1)

        # Fullscreen button
        self._fullscreen_btn = QPushButton("⛶ Fullscreen (F11)")
        self._fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        tb_layout.addWidget(self._fullscreen_btn)

        layout.addWidget(self._toolbar)

        # Main preview canvas
        self.preview_widget = PreviewWidget()
        layout.addWidget(self.preview_widget, 1)

    def update_frame(self, frame_bgr: Any) -> None:
        """Forward live rendered frame to preview canvas."""
        self.preview_widget.update_frame(frame_bgr)

    def set_metrics(self, fps: float, latency_ms: float) -> None:
        self.preview_widget.set_metrics(fps, latency_ms)

    def set_state(self, state: str) -> None:
        self.preview_widget.set_state(state)

    def set_badges(self, badges: list[tuple[str, QColor]]) -> None:
        self.preview_widget.set_badges(badges)

    def clear_frame(self) -> None:
        self.preview_widget.clear_frame()

    def _toggle_always_on_top(self, enabled: bool) -> None:
        flag = Qt.WindowStaysOnTopHint
        if enabled:
            self.setWindowFlags(self.windowFlags() | flag)
        else:
            self.setWindowFlags(self.windowFlags() & ~flag)
        self.show()

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self._toolbar.setVisible(True)
            self._fullscreen_btn.setText("⛶ Fullscreen (F11)")
        else:
            self.showFullScreen()
            self._toolbar.setVisible(False)
            self._fullscreen_btn.setText("⛶ Exit Fullscreen (Esc)")

    def _on_hud_changed(self, idx: int) -> None:
        if idx == 0:
            # Full HUD
            self.preview_widget.set_performance_mode(False)
        elif idx == 1:
            # Minimal HUD
            self.preview_widget.set_performance_mode(True)
        else:
            # Hidden
            self.preview_widget.set_performance_mode(True)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_F11:
            self._toggle_fullscreen()
            event.accept()
        elif event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self._toggle_fullscreen()
                event.accept()
            else:
                self.close()
                event.accept()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        self.window_closed.emit()
        event.accept()
