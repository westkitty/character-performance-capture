from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from cpc.session import SessionConfig
from cpc.ui.widgets.command_preview import CommandPreviewWidget
from cpc.ui.widgets.panels import (
    AdvancedPanel,
    OutputsPanel,
    RendererPanel,
    SourcePanel,
    TrackerPanel,
)
from cpc.ui.widgets.preview_widget import PreviewWidget
from cpc.ui.widgets.telemetry_widget import TelemetryWidget
from cpc.ui.worker import SessionWorker


class LiveWorkspace(QWidget):
    """Primary Live Performance Capture Studio workspace."""

    open_character_workspace = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._worker: SessionWorker | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)

        # -------------------------------------------------------------
        # 1. Left Column: Setup Controls (Scroll Area)
        # -------------------------------------------------------------
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumWidth(320)
        scroll_area.setMaximumWidth(460)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(12)

        self.source_panel = SourcePanel()
        self.source_panel.config_changed.connect(self._on_config_changed)
        left_layout.addWidget(self.source_panel)

        self.tracker_panel = TrackerPanel()
        self.tracker_panel.config_changed.connect(self._on_config_changed)
        left_layout.addWidget(self.tracker_panel)

        self.renderer_panel = RendererPanel()
        self.renderer_panel.config_changed.connect(self._on_config_changed)
        self.renderer_panel.open_character_workspace.connect(lambda: self.open_character_workspace.emit())
        left_layout.addWidget(self.renderer_panel)

        self.outputs_panel = OutputsPanel()
        self.outputs_panel.config_changed.connect(self._on_config_changed)
        left_layout.addWidget(self.outputs_panel)

        self.advanced_panel = AdvancedPanel()
        self.advanced_panel.config_changed.connect(self._on_config_changed)
        left_layout.addWidget(self.advanced_panel)

        self.cmd_preview = CommandPreviewWidget()
        left_layout.addWidget(self.cmd_preview)

        left_layout.addStretch(1)
        scroll_area.setWidget(left_widget)
        splitter.addWidget(scroll_area)

        # -------------------------------------------------------------
        # 2. Center Column: Live Preview & Transport Bar
        # -------------------------------------------------------------
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(10, 10, 10, 10)
        center_layout.setSpacing(10)

        self.preview_widget = PreviewWidget()
        center_layout.addWidget(self.preview_widget, 1)

        # Status / Validation Message Banner
        self._validation_banner = QLabel("")
        self._validation_banner.setWordWrap(True)
        self._validation_banner.setAlignment(Qt.AlignCenter)
        self._validation_banner.setStyleSheet("padding: 6px; border-radius: 4px; font-weight: 500;")
        self._validation_banner.setVisible(False)
        center_layout.addWidget(self._validation_banner)

        # Transport Bar
        transport_bar = QWidget()
        transport_layout = QHBoxLayout(transport_bar)
        transport_layout.setContentsMargins(0, 0, 0, 0)
        transport_layout.setSpacing(12)

        self.start_btn = QPushButton("▶  Start Session")
        self.start_btn.setProperty("primary", True)
        self.start_btn.setMinimumHeight(42)
        font = QFont(self.start_btn.font())
        font.setPointSize(14)
        font.setBold(True)
        self.start_btn.setFont(font)
        self.start_btn.clicked.connect(self.start_session)
        transport_layout.addWidget(self.start_btn, 1)

        self.stop_btn = QPushButton("■  Stop Session")
        self.stop_btn.setProperty("danger", True)
        self.stop_btn.setMinimumHeight(42)
        self.stop_btn.setFont(font)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_session)
        transport_layout.addWidget(self.stop_btn, 1)

        center_layout.addWidget(transport_bar)
        splitter.addWidget(center_widget)

        # -------------------------------------------------------------
        # 3. Right Column: Telemetry
        # -------------------------------------------------------------
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setMinimumWidth(240)
        right_scroll.setMaximumWidth(320)

        self.telemetry_widget = TelemetryWidget()
        right_scroll.setWidget(self.telemetry_widget)
        splitter.addWidget(right_scroll)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        main_layout.addWidget(splitter)
        self._on_config_changed()

    def get_session_config(self) -> SessionConfig:
        """Read active UI inputs into a SessionConfig."""
        cfg = SessionConfig()
        self.source_panel.apply_to_config(cfg)
        self.tracker_panel.apply_to_config(cfg)
        self.renderer_panel.apply_to_config(cfg)
        self.outputs_panel.apply_to_config(cfg)
        self.advanced_panel.apply_to_config(cfg)
        return cfg

    def set_session_config(self, cfg: SessionConfig) -> None:
        """Apply a SessionConfig to all panels."""
        self.source_panel.load_from_config(cfg)
        self.tracker_panel.load_from_config(cfg)
        self.renderer_panel.load_from_config(cfg)
        self.outputs_panel.load_from_config(cfg)
        self.advanced_panel.load_from_config(cfg)
        self._on_config_changed()

    def _on_config_changed(self) -> None:
        cfg = self.get_session_config()
        self.cmd_preview.update_command(cfg)

        if self._worker is not None and self._worker.isRunning():
            return

        errors = cfg.validate()
        if errors:
            self.start_btn.setEnabled(False)
            self._validation_banner.setText(f"⚠ {errors[0]}")
            self._validation_banner.setStyleSheet("background: #451a03; color: #fbbf24; border: 1px solid #78350f;")
            self._validation_banner.setVisible(True)
        else:
            self.start_btn.setEnabled(True)
            self._validation_banner.setVisible(False)

    def start_session(self) -> None:
        """Initialize and launch the background capture session worker."""
        cfg = self.get_session_config()
        errors = cfg.validate()
        if errors:
            QMessageBox.warning(self, "Invalid Configuration", "\n".join(errors))
            return

        self._set_ui_locked(True)
        self.preview_widget.clear_frame()
        self.preview_widget.set_state("initializing")

        badges: list[tuple[str, QColor]] = []
        if cfg.record_performance_path is not None:
            badges.append(("● REC .CPC", QColor("#ef4444")))
        if cfg.record_video_path is not None:
            badges.append(("● REC MP4", QColor("#ef4444")))
        if cfg.virtual_camera:
            badges.append(("● VCAM", QColor("#8b5cf6")))
        self.preview_widget.set_badges(badges)

        self._worker = SessionWorker(cfg, self)
        self._worker.frame_ready.connect(self._on_frame_ready)
        self._worker.telemetry_updated.connect(self.telemetry_widget.update_telemetry)
        self._worker.state_changed.connect(self.preview_widget.set_state)
        self._worker.error_occurred.connect(self._on_session_error)
        self._worker.session_finished.connect(self._on_session_finished)
        self._worker.start()

    def stop_session(self) -> None:
        """Signal the running session worker to stop cleanly."""
        if self._worker is not None and self._worker.isRunning():
            self.stop_btn.setEnabled(False)
            self.preview_widget.set_state("stopping")
            self._worker.stop()

    def _on_frame_ready(self, frame_bgr: Any, performance: Any, metrics: Any) -> None:
        self.preview_widget.update_frame(frame_bgr)
        self.preview_widget.set_metrics(metrics.fps, metrics.processing_ms)

    def _on_session_error(self, user_msg: str, tech_details: str) -> None:
        self.preview_widget.set_state("error")
        QMessageBox.critical(
            self,
            "Capture Session Error",
            f"{user_msg}\n\nTechnical details:\n{tech_details}",
        )

    def _on_session_finished(self) -> None:
        self._set_ui_locked(False)
        self.preview_widget.set_state("idle")
        self.telemetry_widget.reset()
        self._worker = None
        self._on_config_changed()

    def _set_ui_locked(self, running: bool) -> None:
        self.source_panel.setEnabled(not running)
        self.tracker_panel.setEnabled(not running)
        self.renderer_panel.setEnabled(not running)
        self.outputs_panel.setEnabled(not running)
        self.advanced_panel.setEnabled(not running)
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)

    def is_running(self) -> bool:
        return self._worker is not None and self._worker.isRunning()
