from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget


class PreviewWidget(QWidget):
    """High-performance aspect-preserving video preview widget with backpressure handling, countdown, and HUD overlays."""

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
        self._performance_mode: bool = False
        self._frame_count: int = 0
        self._countdown_count: int | None = None
        self._calibrated_toast_text: str = ""

    def set_performance_mode(self, enabled: bool) -> None:
        self._performance_mode = enabled
        self.update()

    def set_state(self, state: str) -> None:
        self._state = state
        self.update()

    def set_badges(self, badges: list[tuple[str, QColor]]) -> None:
        self._badges = badges
        self.update()

    def set_countdown_number(self, count: int | None) -> None:
        self._countdown_count = count
        self.update()

    def set_calibration_toast(self, text: str) -> None:
        self._calibrated_toast_text = text
        self.update()

    def set_metrics(self, fps: float, latency_ms: float) -> None:
        self._fps_text = f"{fps:.1f} FPS" if fps > 0 else ""
        self._latency_text = f"{latency_ms:.1f} ms" if latency_ms > 0 else ""
        self.update()

    def update_frame(self, frame_bgr: np.ndarray) -> None:
        """Convert BGR NumPy ndarray with safe memory ownership to QPixmap."""
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        bytes_per_line = 3 * w
        # Make a deep copy to ensure QImage owns its memory buffer independently
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        self._pixmap = QPixmap.fromImage(qimg)
        self._frame_count += 1
        self.update()

    def clear_frame(self) -> None:
        self._pixmap = None
        self._badges.clear()
        self._fps_text = ""
        self._latency_text = ""
        self._frame_count = 0
        self._countdown_count = None
        self._calibrated_toast_text = ""
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        rect = self.rect()
        # Canvas background
        painter.fillRect(rect, QColor("#0a0a0d"))

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
            painter.setPen(QPen(QColor("#22222a"), 1, Qt.DashLine))
            inner = rect.adjusted(32, 32, -32, -32)
            painter.drawRoundedRect(inner, 10, 10)

            painter.setPen(QColor("#71717a"))
            font = QFont(painter.font())
            font.setPointSize(15)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(
                rect.adjusted(0, -24, 0, -24),
                Qt.AlignCenter,
                "Character Performance Capture Studio",
            )

            font.setPointSize(12)
            font.setBold(False)
            painter.setFont(font)
            painter.setPen(QColor("#a1a1aa"))
            painter.drawText(
                rect.adjusted(0, 24, 0, 24),
                Qt.AlignCenter,
                self._hint_text,
            )

        # -------------------------------------------------------------
        # Overlay Badges (Top-Left)
        # -------------------------------------------------------------
        badge_x = frame_rect.left() + 16
        badge_y = frame_rect.top() + 16

        # Primary state badge
        state_label = "IDLE"
        state_color = QColor("#71717a")
        if self._state == "initializing":
            state_label = "● INITIALIZING"
            state_color = QColor("#38bdf8")
        elif self._state == "tracking":
            state_label = "● TRACKING (478 pts)"
            state_color = QColor("#10b981")
        elif self._state == "tracking_lost":
            state_label = "▲ TRACKING LOST"
            state_color = QColor("#f59e0b")
        elif self._state == "running":
            state_label = "● RUNNING"
            state_color = QColor("#3b82f6")
        elif self._state == "stopping":
            state_label = "■ STOPPING"
            state_color = QColor("#f59e0b")
        elif self._state == "error":
            state_label = "✕ ERROR"
            state_color = QColor("#ef4444")

        all_badges = [(state_label, state_color)] + self._badges

        if self._calibrated_toast_text:
            all_badges.append((self._calibrated_toast_text, QColor("#10b981")))

        font = QFont(painter.font())
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)

        for text, color in all_badges:
            text_rect = painter.fontMetrics().boundingRect(text)
            pad_x, pad_y = 10, 5
            bg_rect = QRectF(
                badge_x,
                badge_y,
                text_rect.width() + (pad_x * 2),
                text_rect.height() + (pad_y * 2),
            )

            # Draw badge background
            path = QPainterPath()
            path.addRoundedRect(bg_rect, 6, 6)
            painter.fillPath(path, QColor(14, 14, 18, 220))
            painter.strokePath(path, QPen(QColor(color.red(), color.green(), color.blue(), 160), 1))

            # Draw text
            painter.setPen(color)
            painter.drawText(
                bg_rect,
                Qt.AlignCenter,
                text,
            )
            badge_x += bg_rect.width() + 8

        # -------------------------------------------------------------
        # Countdown Overlay (Center Canvas)
        # -------------------------------------------------------------
        if self._countdown_count is not None and self._countdown_count > 0:
            cd_font = QFont(painter.font())
            cd_font.setPointSize(72)
            cd_font.setBold(True)
            painter.setFont(cd_font)

            cd_text = str(self._countdown_count)
            cd_rect = painter.fontMetrics().boundingRect(cd_text)

            circle_size = max(cd_rect.width(), cd_rect.height()) + 80
            cx = (self.width() - circle_size) / 2
            cy = (self.height() - circle_size) / 2
            circle_rect = QRectF(cx, cy, circle_size, circle_size)

            painter.setPen(QPen(QColor("#3b82f6"), 4))
            painter.setBrush(QColor(10, 10, 15, 200))
            painter.drawEllipse(circle_rect)

            painter.setPen(QColor("#ffffff"))
            painter.drawText(circle_rect, Qt.AlignCenter, cd_text)

        # -------------------------------------------------------------
        # Metrics HUD (Bottom-Right)
        # -------------------------------------------------------------
        if self._fps_text or self._latency_text:
            metrics_str = f"{self._fps_text}   {self._latency_text}".strip()
            metrics_rect = painter.fontMetrics().boundingRect(metrics_str)
            pad_x, pad_y = 10, 5
            bg_rect = QRectF(
                frame_rect.right() - metrics_rect.width() - (pad_x * 2) - 16,
                frame_rect.bottom() - metrics_rect.height() - (pad_y * 2) - 16,
                metrics_rect.width() + (pad_x * 2),
                metrics_rect.height() + (pad_y * 2),
            )

            path = QPainterPath()
            path.addRoundedRect(bg_rect, 6, 6)
            painter.fillPath(path, QColor(14, 14, 18, 220))
            painter.strokePath(path, QPen(QColor("#2e2e38"), 1))

            painter.setPen(QColor("#e4e4e7"))
            painter.drawText(bg_rect, Qt.AlignCenter, metrics_str)

        # Performance Mode Watermark Indicator (Top-Right)
        if self._performance_mode:
            perf_text = "⛶ PERFORMANCE MODE (Cmd+P to Exit)"
            perf_rect = painter.fontMetrics().boundingRect(perf_text)
            bg_rect = QRectF(
                frame_rect.right() - perf_rect.width() - 20 - 16,
                frame_rect.top() + 16,
                perf_rect.width() + 20,
                perf_rect.height() + 10,
            )
            path = QPainterPath()
            path.addRoundedRect(bg_rect, 6, 6)
            painter.fillPath(path, QColor(14, 14, 18, 220))
            painter.strokePath(path, QPen(QColor("#3b82f6"), 1))
            painter.setPen(QColor("#60a5fa"))
            painter.drawText(bg_rect, Qt.AlignCenter, perf_text)

        painter.end()
