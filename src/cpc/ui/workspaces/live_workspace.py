from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from cpc.session import SessionConfig
from cpc.ui.settings import AppSettings
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
    """Primary Live Performance Capture Studio workspace with preflight, presets, and performance mode."""

    open_character_workspace = Signal()
    open_takes_workspace = Signal(Path)
    open_diagnostics_workspace = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._worker: SessionWorker | None = None
        self._session_token: int = 0
        self._settings = AppSettings()
        self._performance_mode: bool = False
        self._last_error_details: str = ""
        self._last_cpc_path: Path | None = None
        self._last_mp4_path: Path | None = None

        self._init_ui()
        self._load_presets_menu()
        self._update_preflight()

    def _init_ui(self) -> None:
        workspace_layout = QVBoxLayout(self)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        # -------------------------------------------------------------
        # 0. Studio Header Toolbar
        # -------------------------------------------------------------
        self._header_bar = QWidget()
        self._header_bar.setObjectName("topHeaderBar")
        h_layout = QHBoxLayout(self._header_bar)
        h_layout.setContentsMargins(14, 8, 14, 8)
        h_layout.setSpacing(12)

        brand_lbl = QLabel("CPC STUDIO")
        brand_lbl.setObjectName("brandTitle")
        h_layout.addWidget(brand_lbl)

        privacy_badge = QLabel("LOCAL • 100% PRIVATE")
        privacy_badge.setObjectName("privacyBadge")
        h_layout.addWidget(privacy_badge)

        h_layout.addSpacing(12)

        # Presets selector
        h_layout.addWidget(QLabel("Preset:"))
        self._preset_combo = QComboBox()
        self._preset_combo.setMinimumWidth(160)
        self._preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        h_layout.addWidget(self._preset_combo)

        self._save_preset_btn = QPushButton("Save Preset...")
        self._save_preset_btn.clicked.connect(self._save_current_preset)
        h_layout.addWidget(self._save_preset_btn)

        h_layout.addStretch(1)

        # Preflight Readiness Pill
        self._preflight_pill = QLabel("● Ready")
        self._preflight_pill.setStyleSheet("font-weight: 600; font-size: 12px; color: #10b981;")
        h_layout.addWidget(self._preflight_pill)

        # Performance Mode Toggle Button
        self._perf_mode_btn = QPushButton("⛶ Performance Mode")
        self._perf_mode_btn.setToolTip("Toggle low-distraction full preview view (Cmd+P)")
        self._perf_mode_btn.clicked.connect(self.toggle_performance_mode)
        h_layout.addWidget(self._perf_mode_btn)

        workspace_layout.addWidget(self._header_bar)

        # -------------------------------------------------------------
        # First-Run Quick Start Card (Dismissible)
        # -------------------------------------------------------------
        self._first_run_card = QFrame()
        self._first_run_card.setStyleSheet(
            "background-color: #141b2d; border: 1px solid #1e3a8a; border-radius: 8px; margin: 8px 14px 0 14px; padding: 14px;"
        )
        fr_layout = QVBoxLayout(self._first_run_card)
        fr_layout.setContentsMargins(12, 12, 12, 12)
        fr_layout.setSpacing(10)

        fr_header_row = QHBoxLayout()
        fr_title = QLabel("Welcome to Character Performance Capture Studio")
        fr_font = QFont(fr_title.font())
        fr_font.setPointSize(14)
        fr_font.setBold(True)
        fr_title.setFont(fr_font)
        fr_title.setStyleSheet("color: #60a5fa; font-weight: 700;")
        fr_header_row.addWidget(fr_title, 1)

        fr_close_btn = QPushButton("✕ Dismiss")
        fr_close_btn.setMinimumWidth(100)
        fr_close_btn.clicked.connect(self._dismiss_first_run)
        fr_header_row.addWidget(fr_close_btn)
        fr_layout.addLayout(fr_header_row)

        fr_desc = QLabel(
            "Local-first, model-agnostic performance capture engine. All tracking and mesh-warp rendering runs 100% locally on your machine — zero network calls, zero cloud telemetry, and camera pixels are never stored."
        )
        fr_desc.setStyleSheet("color: #cbd5e1; font-size: 13px; line-height: 1.4;")
        fr_desc.setWordWrap(True)
        fr_layout.addWidget(fr_desc)

        fr_btns_row = QHBoxLayout()
        fr_btns_row.setSpacing(10)
        btn_cam = QPushButton("📹 Start with Camera")
        btn_cam.setMinimumHeight(32)
        btn_cam.clicked.connect(lambda: self._quick_start("camera"))
        btn_vid = QPushButton("🎬 Open Performer Video")
        btn_vid.setMinimumHeight(32)
        btn_vid.clicked.connect(lambda: self._quick_start("video"))
        btn_char = QPushButton("🎨 Set Up Character && Rig")
        btn_char.setMinimumHeight(32)
        btn_char.clicked.connect(lambda: self.open_character_workspace.emit())
        btn_diag = QPushButton("🩺 Run Hardware Check")
        btn_diag.setMinimumHeight(32)
        btn_diag.clicked.connect(lambda: self.open_diagnostics_workspace.emit())

        fr_btns_row.addWidget(btn_cam)
        fr_btns_row.addWidget(btn_vid)
        fr_btns_row.addWidget(btn_char)
        fr_btns_row.addWidget(btn_diag)
        fr_layout.addLayout(fr_btns_row)

        if self._settings.is_first_run_completed():
            self._first_run_card.setVisible(False)

        workspace_layout.addWidget(self._first_run_card)

        # -------------------------------------------------------------
        # Main Splitter (Left Setup, Center Canvas, Right Telemetry)
        # -------------------------------------------------------------
        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setHandleWidth(2)

        # 1. Left Column: Setup Controls
        self._left_scroll = QScrollArea()
        self._left_scroll.setWidgetResizable(True)
        self._left_scroll.setMinimumWidth(320)
        self._left_scroll.setMaximumWidth(460)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
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
        self._left_scroll.setWidget(left_widget)
        self._splitter.addWidget(self._left_scroll)

        # 2. Center Column: Live Preview & Transport Controls
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
        self._validation_banner.setStyleSheet("padding: 8px 12px; border-radius: 6px; font-weight: 500; font-size: 12px;")
        self._validation_banner.setVisible(False)
        center_layout.addWidget(self._validation_banner)

        # Session Summary Card (Shown after session stop)
        self._summary_card = QFrame()
        self._summary_card.setStyleSheet("background-color: #181820; border: 1px solid #2e2e38; border-radius: 8px; padding: 12px;")
        sum_layout = QVBoxLayout(self._summary_card)
        sum_layout.setSpacing(8)

        sum_title_row = QHBoxLayout()
        sum_title = QLabel("Session Complete")
        font_st = QFont(sum_title.font())
        font_st.setBold(True)
        sum_title.setFont(font_st)
        sum_title.setStyleSheet("color: #10b981;")
        sum_title_row.addWidget(sum_title, 1)

        sum_close_btn = QPushButton("✕")
        sum_close_btn.setMaximumWidth(32)
        sum_close_btn.clicked.connect(lambda: self._summary_card.setVisible(False))
        sum_title_row.addWidget(sum_close_btn)
        sum_layout.addLayout(sum_title_row)

        self._sum_stats_lbl = QLabel("")
        self._sum_stats_lbl.setWordWrap(True)
        sum_layout.addWidget(self._sum_stats_lbl)

        sum_btns_row = QHBoxLayout()
        self._btn_reveal_cpc = QPushButton("📁 Reveal .CPC Take")
        self._btn_reveal_cpc.clicked.connect(self._reveal_cpc_take)
        self._btn_reveal_mp4 = QPushButton("🎬 Reveal Video")
        self._btn_reveal_mp4.clicked.connect(self._reveal_mp4_video)
        self._btn_inspect_take = QPushButton("🔍 Open in Takes Studio")
        self._btn_inspect_take.clicked.connect(self._open_in_takes_studio)

        sum_btns_row.addWidget(self._btn_reveal_cpc)
        sum_btns_row.addWidget(self._btn_reveal_mp4)
        sum_btns_row.addWidget(self._btn_inspect_take)
        sum_layout.addLayout(sum_btns_row)

        self._summary_card.setVisible(False)
        center_layout.addWidget(self._summary_card)

        # Transport Bar
        self._transport_bar = QWidget()
        transport_layout = QHBoxLayout(self._transport_bar)
        transport_layout.setContentsMargins(0, 0, 0, 0)
        transport_layout.setSpacing(12)

        self.start_btn = QPushButton("▶  Start Session")
        self.start_btn.setProperty("primary", True)
        self.start_btn.setMinimumHeight(44)
        font = QFont(self.start_btn.font())
        font.setPointSize(14)
        font.setBold(True)
        self.start_btn.setFont(font)
        self.start_btn.clicked.connect(self.start_session)
        transport_layout.addWidget(self.start_btn, 1)

        self.stop_btn = QPushButton("■  Stop Session")
        self.stop_btn.setProperty("danger", True)
        self.stop_btn.setMinimumHeight(44)
        self.stop_btn.setFont(font)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_session)
        transport_layout.addWidget(self.stop_btn, 1)

        center_layout.addWidget(self._transport_bar)

        # Technical Details Drawer (Collapsible)
        self._details_drawer = QWidget()
        dd_layout = QVBoxLayout(self._details_drawer)
        dd_layout.setContentsMargins(0, 0, 0, 0)
        dd_layout.setSpacing(6)

        dd_header = QHBoxLayout()
        dd_lbl = QLabel("Activity && Technical Details")
        dd_lbl.setProperty("secondary", True)
        dd_header.addWidget(dd_lbl, 1)

        self._copy_tech_btn = QPushButton("Copy Technical Details")
        self._copy_tech_btn.setMaximumWidth(160)
        self._copy_tech_btn.clicked.connect(self._copy_technical_details)
        self._copy_tech_btn.setVisible(False)
        dd_header.addWidget(self._copy_tech_btn)

        dd_layout.addLayout(dd_header)

        self._tech_text = QTextEdit()
        self._tech_text.setMaximumHeight(90)
        self._tech_text.setReadOnly(True)
        dd_layout.addWidget(self._tech_text)

        self._details_drawer.setVisible(False)
        center_layout.addWidget(self._details_drawer)

        self._splitter.addWidget(center_widget)

        # 3. Right Column: Telemetry Dashboard
        self._right_scroll = QScrollArea()
        self._right_scroll.setWidgetResizable(True)
        self._right_scroll.setMinimumWidth(240)
        self._right_scroll.setMaximumWidth(320)

        self.telemetry_widget = TelemetryWidget()
        self._right_scroll.setWidget(self.telemetry_widget)
        self._splitter.addWidget(self._right_scroll)

        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setStretchFactor(2, 0)

        workspace_layout.addWidget(self._splitter, 1)

    # -----------------------------------------------------------------
    # Preflight & Configuration Management
    # -----------------------------------------------------------------
    def _on_config_changed(self) -> None:
        cfg = self.get_session_config()
        self.cmd_preview.update_command(cfg)
        self._update_preflight()

    def _update_preflight(self) -> None:
        cfg = self.get_session_config()
        errors = cfg.validate()

        if errors:
            self.start_btn.setEnabled(False)
            self._validation_banner.setText("  •  ".join(errors))
            self._validation_banner.setStyleSheet("background-color: #451a03; color: #fde68a; border: 1px solid #78350f; padding: 8px 12px; border-radius: 6px;")
            self._validation_banner.setVisible(True)
            self._preflight_pill.setText(f"▲ {len(errors)} Issue{'s' if len(errors) > 1 else ''}")
            self._preflight_pill.setStyleSheet("font-weight: 600; font-size: 12px; color: #f59e0b;")
        else:
            self.start_btn.setEnabled(self._worker is None or not self._worker.isRunning())
            self._validation_banner.setVisible(False)
            self._preflight_pill.setText("● All Systems Ready")
            self._preflight_pill.setStyleSheet("font-weight: 600; font-size: 12px; color: #10b981;")

    def get_session_config(self) -> SessionConfig:
        cfg = SessionConfig()
        self.source_panel.apply_to_config(cfg)
        self.tracker_panel.apply_to_config(cfg)
        self.renderer_panel.apply_to_config(cfg)
        self.outputs_panel.apply_to_config(cfg)
        self.advanced_panel.apply_to_config(cfg)
        return cfg

    def set_session_config(self, cfg: SessionConfig) -> None:
        self.source_panel.load_from_config(cfg)
        self.tracker_panel.load_from_config(cfg)
        self.renderer_panel.load_from_config(cfg)
        self.outputs_panel.load_from_config(cfg)
        self.advanced_panel.load_from_config(cfg)
        self.cmd_preview.update_command(cfg)
        self._update_preflight()

    # -----------------------------------------------------------------
    # Presets Management
    # -----------------------------------------------------------------
    def _load_presets_menu(self) -> None:
        self._preset_combo.blockSignals(True)
        self._preset_combo.clear()
        self._preset_combo.addItem("Default Configuration")
        presets = self._settings.list_presets()
        for p in presets:
            self._preset_combo.addItem(p)
        self._preset_combo.blockSignals(False)

    def _on_preset_selected(self, idx: int) -> None:
        if idx == 0:
            return
        name = self._preset_combo.currentText()
        cfg = self._settings.load_preset(name)
        if cfg is not None:
            self.set_session_config(cfg)
            self._log_activity(f"Loaded preset: {name}")

    def _save_current_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Session Preset", "Preset Name:")
        if ok and name.strip():
            cfg = self.get_session_config()
            self._settings.save_preset(name.strip(), cfg)
            self._load_presets_menu()
            # Select the newly saved preset
            idx = self._preset_combo.findText(name.strip())
            if idx >= 0:
                self._preset_combo.setCurrentIndex(idx)
            self._log_activity(f"Saved session preset: {name.strip()}")

    # -----------------------------------------------------------------
    # First-Run Quick Start Actions
    # -----------------------------------------------------------------
    def _dismiss_first_run(self) -> None:
        self._first_run_card.setVisible(False)
        self._settings.set_first_run_completed(True)

    def _quick_start(self, kind: str) -> None:
        self._dismiss_first_run()
        cfg = self.get_session_config()
        if kind == "camera":
            cfg.source_type = "camera"
            cfg.camera_index = 0
        elif kind == "video":
            cfg.source_type = "video"
        self.set_session_config(cfg)

    # -----------------------------------------------------------------
    # Performance Mode Toggle
    # -----------------------------------------------------------------
    def toggle_performance_mode(self) -> None:
        self._performance_mode = not self._performance_mode
        self._left_scroll.setVisible(not self._performance_mode)
        self._right_scroll.setVisible(not self._performance_mode)
        self.preview_widget.set_performance_mode(self._performance_mode)
        self._perf_mode_btn.setText("⛶ Exit Performance Mode" if self._performance_mode else "⛶ Performance Mode")

    # -----------------------------------------------------------------
    # Session Execution & Lifecycle Management
    # -----------------------------------------------------------------
    def is_running(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def start_session(self) -> None:
        """Start live capture, tracking, and rendering pipeline in background thread."""
        if self.is_running():
            return

        cfg = self.get_session_config()
        errors = cfg.validate()
        if errors:
            QMessageBox.warning(self, "Invalid Configuration", "\n".join(errors))
            return

        self._set_ui_locked(True)
        self._summary_card.setVisible(False)
        self._details_drawer.setVisible(False)
        self._copy_tech_btn.setVisible(False)
        self.preview_widget.clear_frame()
        self.preview_widget.set_state("initializing")

        # Set active badges on preview
        badges: list[tuple[str, QColor]] = []
        if cfg.record_performance_path is not None:
            badges.append(("● REC .CPC", QColor("#ef4444")))
            self._last_cpc_path = cfg.record_performance_path
        else:
            self._last_cpc_path = None

        if cfg.record_video_path is not None:
            badges.append(("● REC MP4", QColor("#ef4444")))
            self._last_mp4_path = cfg.record_video_path
        else:
            self._last_mp4_path = None

        if cfg.virtual_camera:
            badges.append(("● VCAM", QColor("#8b5cf6")))

        self.preview_widget.set_badges(badges)

        self._session_token += 1
        current_token = self._session_token

        self._worker = SessionWorker(cfg, session_token=current_token, parent=self)
        self._worker.frame_ready.connect(self._on_frame_ready)
        self._worker.telemetry_updated.connect(self.telemetry_widget.update_telemetry)
        self._worker.state_changed.connect(self.preview_widget.set_state)
        self._worker.error_occurred.connect(self._on_session_error)
        self._worker.session_finished.connect(self._on_session_finished)

        self._log_activity(f"Starting performance session (Source: {cfg.source_type}, Tracker: {cfg.tracker_type}, Renderer: {cfg.renderer_type})...")
        self._worker.start()

    def stop_session(self) -> None:
        """Signal the running session worker to stop cleanly."""
        if self._worker is not None and self._worker.isRunning():
            self.stop_btn.setEnabled(False)
            self.preview_widget.set_state("stopping")
            self._log_activity("Stopping session cleanly...")
            self._worker.stop()

    def _on_frame_ready(self, frame_bgr: Any, performance: Any, metrics: Any) -> None:
        self.preview_widget.update_frame(frame_bgr)
        self.preview_widget.set_metrics(metrics.fps, metrics.processing_ms)

    def _on_session_error(self, user_msg: str, tech_details: str) -> None:
        self.preview_widget.set_state("error")
        self._last_error_details = tech_details
        self._log_activity(f"ERROR: {user_msg}\n{tech_details}")
        self._details_drawer.setVisible(True)
        self._copy_tech_btn.setVisible(True)
        QMessageBox.critical(self, "Session Error", f"{user_msg}\n\nCheck the technical details drawer below for troubleshooting.")

    def _on_session_finished(self) -> None:
        self._set_ui_locked(False)
        self._worker = None
        self._log_activity("Session stopped.")

        # Display summary card if outputs were created
        if self._last_cpc_path is not None or self._last_mp4_path is not None:
            stats_text = "Generated Session Outputs:\n"
            if self._last_cpc_path:
                stats_text += f" • .CPC Take: {self._last_cpc_path.name}\n"
                self._btn_reveal_cpc.setVisible(True)
                self._btn_inspect_take.setVisible(True)
            else:
                self._btn_reveal_cpc.setVisible(False)
                self._btn_inspect_take.setVisible(False)

            if self._last_mp4_path:
                stats_text += f" • Rendered Video: {self._last_mp4_path.name}\n"
                self._btn_reveal_mp4.setVisible(True)
            else:
                self._btn_reveal_mp4.setVisible(False)

            self._sum_stats_lbl.setText(stats_text.strip())
            self._summary_card.setVisible(True)

    def _reveal_cpc_take(self) -> None:
        if self._last_cpc_path and self._last_cpc_path.exists():
            QDesktopServices.openUrl(f"file://{self._last_cpc_path.parent.resolve()}")

    def _reveal_mp4_video(self) -> None:
        if self._last_mp4_path and self._last_mp4_path.exists():
            QDesktopServices.openUrl(f"file://{self._last_mp4_path.parent.resolve()}")

    def _open_in_takes_studio(self) -> None:
        if self._last_cpc_path and self._last_cpc_path.exists():
            self.open_takes_workspace.emit(self._last_cpc_path)

    def _copy_technical_details(self) -> None:
        if self._last_error_details:
            QApplication.clipboard().setText(self._last_error_details)
            QMessageBox.information(self, "Copied", "Technical details copied to clipboard.")

    def _log_activity(self, message: str) -> None:
        self._tech_text.append(message)

    def _set_ui_locked(self, locked: bool) -> None:
        self.start_btn.setEnabled(not locked)
        self.stop_btn.setEnabled(locked)
        self.source_panel.setEnabled(not locked)
        self.tracker_panel.setEnabled(not locked)
        self.renderer_panel.setEnabled(not locked)
        self.outputs_panel.setEnabled(not locked)
        self.advanced_panel.setEnabled(not locked)
        self._preset_combo.setEnabled(not locked)
        self._save_preset_btn.setEnabled(not locked)
