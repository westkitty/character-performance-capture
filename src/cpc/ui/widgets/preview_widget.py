from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget


class PreviewWidget(QWidget):
    """High-performance aspect-preserving video preview widget with status overlays."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(480, 320)
        self._pixmap: QPixmap | None = None
        self._state: str = "idle"  # idle, initializing, running, tracking, tracking_lost, stopping, error
        self._fps_text: str = ""
        self._latency_text: str = ""
        self._badges: list[tuple[str, QColor]] = []
        self._hint_text: str = "Ready to capture — Configure source & click Start"

    def set_state(self, state: str) -> None:
        self._state = state
        self.update()

    def set_badges(self, badges: list[tuple[str, QColor]]) -> None:
        self._badges = badges
        self.update()

    def set_metrics(self, fps: float, latency_ms: float) -> None:
        self._fps_text = f"{fps:.1f} FPS" if fps > 0 else ""
        self._latency_text = f"{latency_ms:.1f} ms" if latency_ms > 0 else ""
        self.update()

    def update_frame(self, frame_bgr: np.ndarray) -> None:
        """Convert BGR NumPy ndarray to QPixmap and trigger repaint."""
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        bytes_per_line = 3 * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self._pixmap = QPixmap.fromImage(qimg)
        self.update()

    def clear_frame(self) -> None:
        self._pixmap = None
        self._badges.clear()
        self._fps_text = ""
        self._latency_text = ""
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        rect = self.rect()
        painter.fillRect(rect, QColor("#121214"))

        if self._pixmap is not None and not self._pixmap.isNull():
            # Aspect-fit video canvas
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            frame_rect = QRect(x, y, scaled.width(), scaled.height())
        else:
            # Draw placeholder when idle
            frame_rect = rect
            painter.setPen(QPen(QColor("#27272a"), 1, Qt.DashLine))
            inner = rect.adjusted(24, 24, -24, -24)
            painter.drawRoundedRect(inner, 8, 8)

            painter.setPen(QColor("#71717a"))
            font = QFont(painter.font())
            font.setPointSize(14)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(
                rect.adjusted(0, -20, 0, -20),
                Qt.AlignCenter,
                "Character Performance Capture",
            )

            font.setPointSize(11)
            font.setBold(False)
            painter.setFont(font)
            painter.setPen(QColor("#a1a1aa"))
            painter.drawText(
                rect.adjusted(0, 24, 0, 24),
                Qt.AlignCenter,
                self._hint_text,
            )

        # Draw Overlay Badges (Top-Left)
        badge_x = frame_rect.left() + 14
        badge_y = frame_rect.top() + 14

        # Primary state badge
        state_label = "IDLE"
        state_color = QColor("#71717a")
        if self._state == "initializing":
            state_label = "INITIALIZING"
            state_color = QColor("#38bdf8")
        elif self._state == "tracking":
            state_label = "TRACKING"
            state_color = QColor("#10b981")
        elif self._state == "tracking_lost":
            state_label = "TRACKING LOST"
            state_color = QColor("#f59e0b")
        elif self._state == "running":
            state_label = "RUNNING"
            state_color = QColor("#3b82f6")
        elif self._state == "stopping":
            state_label = "STOPPING"
            state_color = QColor("#f59e0b")
        elif self._state == "error":
            state_label = "ERROR"
            state_color = QColor("#ef4444")

        all_badges = [(state_label, state_color)] + self._badges

        font = QFont(painter.font())
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)

        for text, color in all_badges:
            text_rect = painter.fontMetrics().boundingRect(text)
            pad_x, pad_y = 8, 4
            bg_rect = QRectF(
                badge_x,
                badge_y,
                text_rect.width() + (pad_x * 2),
                text_rect.height() + (pad_y * 2),
            )

            # Draw badge background
            path = QPainterPath()
            path.addRoundedRect(bg_rect, 4, 4)
            painter.fillPath(path, QColor(24, 24, 27, 210))
            painter.strokePath(path, QPen(color, 1))

            # Draw text
            painter.setPen(color)
            painter.drawText(
                bg_rect,
                Qt.AlignCenter,
                text,
            )
            badge_x += bg_rect.width() + 8

        # Draw Bottom-Right Metrics (FPS / Latency)
        if self._fps_text or self._latency_text:
            metrics_str = f"{self._fps_text}   {self._latency_text}".strip()
            metrics_rect = painter.fontMetrics().boundingRect(metrics_str)
            pad_x, pad_y = 8, 4
            bg_rect = QRectF(
                frame_rect.right() - metrics_rect.width() - (pad_x * 2) - 14,
                frame_rect.bottom() - metrics_rect.height() - (pad_y * 2) - 14,
                metrics_rect.width() + (pad_x * 2),
                metrics_rect.height() + (pad_y * 2),
            )

            path = QPainterPath()
            path.addRoundedRect(bg_rect, 4, 4)
            painter.fillPath(path, QColor(24, 24, 27, 210))
            painter.strokePath(path, QPen(QColor("#3f3f46"), 1))

            painter.setPen(QColor("#e4e4e7"))
            painter.drawText(bg_rect, Qt.AlignCenter, metrics_str)

        painter.end()
