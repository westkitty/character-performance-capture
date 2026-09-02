from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QDesktopServices, QFont
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
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from cpc.session import SessionConfig
from cpc.ui.settings import AppSettings
from cpc.ui.widgets.clean_preview_window import CleanPreviewWindow
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
    """Calm, Stage-First Live Performance Studio workspace with Session Strip and Context Inspector."""

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
        self._active_preset_name: str = "Default Configuration"
        self._clean_preview_win: CleanPreviewWindow | None = None
        self._countdown_timer: QTimer | None = None
        self._countdown_remaining: int = 0

        self._init_ui()
        self._load_presets_menu()
        self.set_session_config(SessionConfig())

    def _init_ui(self) -> None:
        workspace_layout = QVBoxLayout(self)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        # -------------------------------------------------------------
        # 0. Minimal Studio Top Header
        # -------------------------------------------------------------
        self._header_bar = QWidget()
        self._header_bar.setObjectName("topHeaderBar")
        h_layout = QHBoxLayout(self._header_bar)
        h_layout.setContentsMargins(16, 8, 16, 8)
        h_layout.setSpacing(12)

        brand_lbl = QLabel("CPC STUDIO")
        brand_lbl.setObjectName("brandTitle")
        h_layout.addWidget(brand_lbl)

        privacy_badge = QLabel("LOCAL • 100% PRIVATE")
        privacy_badge.setObjectName("privacyBadge")
        h_layout.addWidget(privacy_badge)

        h_layout.addSpacing(8)

        # Contextual Readiness Pill
        self._preflight_pill = QLabel("● Ready to Perform")
        self._preflight_pill.setStyleSheet("font-weight: 600; font-size: 12px; color: #10b981;")
        h_layout.addWidget(self._preflight_pill)

        h_layout.addStretch(1)

        # Standalone Projector / Clean Preview
        self._clean_preview_btn = QPushButton("🗗 Projector")
        self._clean_preview_btn.setToolTip("Open standalone clean preview window for OBS / secondary monitor (Cmd+Shift+P)")
        self._clean_preview_btn.clicked.connect(self.open_clean_preview)
        h_layout.addWidget(self._clean_preview_btn)

        # Performance Mode Fullscreen Stage
        self._perf_mode_btn = QPushButton("⛶ Fullscreen Stage")
        self._perf_mode_btn.setToolTip("Toggle distraction-free full-preview stage (Cmd+P)")
        self._perf_mode_btn.clicked.connect(self.toggle_performance_mode)
        h_layout.addWidget(self._perf_mode_btn)

        # Toggle Inspector
        self._toggle_inspector_btn = QPushButton("⚙ Configure / Inspector")
        self._toggle_inspector_btn.setToolTip("Open or close the configuration and technical inspector panel")
        self._toggle_inspector_btn.clicked.connect(self.toggle_inspector)
        h_layout.addWidget(self._toggle_inspector_btn)

        workspace_layout.addWidget(self._header_bar)

        # -------------------------------------------------------------
        # 1. Main Stage & Inspector Splitter
        # -------------------------------------------------------------
        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setHandleWidth(2)

        # -------------------------------------------------------------
        # 1A. THE STAGE (Left / Main Working Surface)
        # -------------------------------------------------------------
        stage_widget = QWidget()
        stage_layout = QVBoxLayout(stage_widget)
        stage_layout.setContentsMargins(12, 12, 12, 10)
        stage_layout.setSpacing(8)

        # Primary Live Performance Canvas
        self.preview_widget = PreviewWidget()
        stage_layout.addWidget(self.preview_widget, 1)

        # Actionable Validation / Fix This Banner
        self._validation_banner_widget = QWidget()
        v_layout = QHBoxLayout(self._validation_banner_widget)
        v_layout.setContentsMargins(12, 8, 12, 8)
        self._validation_banner_lbl = QLabel("")
        self._validation_banner_lbl.setWordWrap(True)
        self._validation_banner_lbl.setStyleSheet("color: #fde68a; font-weight: 500; font-size: 12px;")
        v_layout.addWidget(self._validation_banner_lbl, 1)

        self._fix_this_btn = QPushButton("Fix This →")
        self._fix_this_btn.setMaximumWidth(100)
        self._fix_this_btn.clicked.connect(self._handle_fix_this)
        v_layout.addWidget(self._fix_this_btn)

        self._validation_banner_widget.setStyleSheet(
            "background-color: #3b1b06; border: 1px solid #78350f; border-radius: 6px;"
        )
        self._validation_banner_widget.setVisible(False)
        stage_layout.addWidget(self._validation_banner_widget)

        # Session Complete Summary Card (Dismissible)
        self._summary_card = QFrame()
        self._summary_card.setStyleSheet("background-color: #14141c; border: 1px solid #232330; border-radius: 8px; padding: 12px;")
        sum_layout = QVBoxLayout(self._summary_card)
        sum_layout.setSpacing(8)

        sum_title_row = QHBoxLayout()
        sum_title = QLabel("Take Session Complete")
        font_st = QFont(sum_title.font())
        font_st.setBold(True)
        sum_title.setFont(font_st)
        sum_title.setStyleSheet("color: #10b981; font-size: 14px;")
        sum_title_row.addWidget(sum_title, 1)

        sum_close_btn = QPushButton("✕")
        sum_close_btn.setMaximumWidth(32)
        sum_close_btn.clicked.connect(lambda: self._summary_card.setVisible(False))
        sum_title_row.addWidget(sum_close_btn)
        sum_layout.addLayout(sum_title_row)

        self._summary_stats_lbl = QLabel("")
        self._summary_stats_lbl.setStyleSheet("color: #d1d5db; font-size: 13px;")
        sum_layout.addWidget(self._summary_stats_lbl)

        sum_btns = QHBoxLayout()
        self._sum_open_folder_btn = QPushButton("📁 Reveal Take in Finder")
        self._sum_open_folder_btn.clicked.connect(self._reveal_last_take)
        sum_btns.addWidget(self._sum_open_folder_btn)

        self._sum_inspect_btn = QPushButton("📊 Open in Takes Studio")
        self._sum_inspect_btn.clicked.connect(self._open_in_takes_studio)
        sum_btns.addWidget(self._sum_inspect_btn)
        sum_btns.addStretch(1)
        sum_layout.addLayout(sum_btns)

        self._summary_card.setVisible(False)
        stage_layout.addWidget(self._summary_card)

        # -------------------------------------------------------------
        # 1B. THE SESSION STRIP (Quick Status & Jump Pills)
        # -------------------------------------------------------------
        self._session_strip = QWidget()
        self._session_strip.setObjectName("session_strip")
        strip_layout = QHBoxLayout(self._session_strip)
        strip_layout.setContentsMargins(8, 4, 8, 4)
        strip_layout.setSpacing(8)

        # Pill 1: Source
        self._pill_source = QPushButton("📷 Source: Camera 0")
        self._pill_source.setToolTip("Click to configure video/camera frame source")
        self._pill_source.clicked.connect(lambda: self.open_inspector_section(0))
        strip_layout.addWidget(self._pill_source)

        # Pill 2: Character
        self._pill_character = QPushButton("👤 Character: None (Passthrough)")
        self._pill_character.setToolTip("Click to configure character artwork and mesh rig")
        self._pill_character.clicked.connect(lambda: self.open_inspector_section(1))
        strip_layout.addWidget(self._pill_character)

        # Pill 3: Tracking
        self._pill_tracker = QPushButton("🎯 Tracker: MediaPipe Face")
        self._pill_tracker.setToolTip("Click to configure tracking model and compute delegate")
        self._pill_tracker.clicked.connect(lambda: self.open_inspector_section(2))
        strip_layout.addWidget(self._pill_tracker)

        # Pill 4: Outputs
        self._pill_outputs = QPushButton("📹 Output: Preview Only")
        self._pill_outputs.setToolTip("Click to configure recording (.cpc / MP4) and virtual camera")
        self._pill_outputs.clicked.connect(lambda: self.open_inspector_section(3))
        strip_layout.addWidget(self._pill_outputs)

        # Pill 5: Preset
        self._pill_preset = QPushButton("⚙ Preset: Default")
        self._pill_preset.setToolTip("Click to manage presets and countdown timing")
        self._pill_preset.clicked.connect(lambda: self.open_inspector_section(4))
        strip_layout.addWidget(self._pill_preset)

        strip_layout.addStretch(1)
        stage_layout.addWidget(self._session_strip)

        # -------------------------------------------------------------
        # 1C. THE TRANSPORT BAR
        # -------------------------------------------------------------
        self._transport_bar = QWidget()
        self._transport_bar.setObjectName("transport_bar")
        transport_layout = QHBoxLayout(self._transport_bar)
        transport_layout.setContentsMargins(0, 4, 0, 0)
        transport_layout.setSpacing(10)

        # Primary Start / Live Action
        self.start_btn = QPushButton("▶  Start Performing")
        self.start_btn.setProperty("primary", True)
        self.start_btn.setMinimumHeight(44)
        font = QFont(self.start_btn.font())
        font.setPointSize(14)
        font.setBold(True)
        self.start_btn.setFont(font)
        self.start_btn.clicked.connect(self.start_session)
        transport_layout.addWidget(self.start_btn, 3)

        # Recenter / Neutral Pose Calibration
        self.recenter_btn = QPushButton("🎯 Recenter Pose (Cmd+R)")
        self.recenter_btn.setToolTip("Calibrate neutral head and face position (C / Cmd+R)")
        self.recenter_btn.setMinimumHeight(44)
        self.recenter_btn.setEnabled(False)
        self.recenter_btn.clicked.connect(self.calibrate_neutral)
        transport_layout.addWidget(self.recenter_btn, 1)

        # Stop Session (visible/active while running)
        self.stop_btn = QPushButton("■  Stop Session (Esc)")
        self.stop_btn.setProperty("danger", True)
        self.stop_btn.setMinimumHeight(44)
        self.stop_btn.setFont(font)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_session)
        transport_layout.addWidget(self.stop_btn, 2)

        stage_layout.addWidget(self._transport_bar)

        self._splitter.addWidget(stage_widget)

        # -------------------------------------------------------------
        # 2. THE CONTEXT INSPECTOR (Right Collapsible Panel)
        # -------------------------------------------------------------
        self._inspector_container = QWidget()
        self._inspector_container.setObjectName("inspector_drawer")
        self._inspector_container.setMinimumWidth(320)
        self._inspector_container.setMaximumWidth(480)
        insp_layout = QVBoxLayout(self._inspector_container)
        insp_layout.setContentsMargins(8, 12, 12, 12)
        insp_layout.setSpacing(8)

        # Inspector Header
        insp_head = QHBoxLayout()
        insp_title = QLabel("Configuration & Inspector")
        insp_title_font = QFont(insp_title.font())
        insp_title_font.setBold(True)
        insp_title_font.setPointSize(13)
        insp_title.setFont(insp_title_font)
        insp_head.addWidget(insp_title, 1)

        btn_close_insp = QPushButton("✕")
        btn_close_insp.setMaximumWidth(32)
        btn_close_insp.setToolTip("Close Inspector panel")
        btn_close_insp.clicked.connect(lambda: self.set_inspector_visible(False))
        insp_head.addWidget(btn_close_insp)
        insp_layout.addLayout(insp_head)

        # Inspector Tabs
        self._inspector_tabs = QTabWidget()

        # Tab 0: Input Source
        self.source_panel = SourcePanel()
        self.source_panel.config_changed.connect(self._on_config_changed)
        self._inspector_tabs.addTab(self._wrap_scroll(self.source_panel), "📷 Ingest")

        # Tab 1: Character & Gains
        self.renderer_panel = RendererPanel()
        self.renderer_panel.config_changed.connect(self._on_config_changed)
        self.renderer_panel.open_character_workspace.connect(lambda: self.open_character_workspace.emit())
        self._inspector_tabs.addTab(self._wrap_scroll(self.renderer_panel), "👤 Character")

        # Tab 2: Performance Tracker
        self.tracker_panel = TrackerPanel()
        self.tracker_panel.config_changed.connect(self._on_config_changed)
        self._inspector_tabs.addTab(self._wrap_scroll(self.tracker_panel), "🎯 Tracker")

        # Tab 3: Outputs
        self.outputs_panel = OutputsPanel()
        self.outputs_panel.config_changed.connect(self._on_config_changed)
        self._inspector_tabs.addTab(self._wrap_scroll(self.outputs_panel), "📹 Outputs")

        # Tab 4: Session & Presets
        session_box = QWidget()
        sb_layout = QVBoxLayout(session_box)
        sb_layout.setContentsMargins(4, 4, 4, 4)
        sb_layout.setSpacing(10)

        # Presets row inside session tab
        preset_frame = QFrame()
        preset_frame.setStyleSheet("background-color: #14141c; border: 1px solid #232330; border-radius: 6px; padding: 8px;")
        pf_layout = QVBoxLayout(preset_frame)
        pf_layout.setSpacing(6)
        pf_layout.addWidget(QLabel("Session Presets:"))

        self._preset_combo = QComboBox()
        self._preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        pf_layout.addWidget(self._preset_combo)

        p_btns = QHBoxLayout()
        self._save_preset_btn = QPushButton("Save")
        self._save_preset_btn.clicked.connect(self._save_current_preset)
        p_btns.addWidget(self._save_preset_btn)

        self._save_as_preset_btn = QPushButton("Save As...")
        self._save_as_preset_btn.clicked.connect(self._save_as_new_preset)
        p_btns.addWidget(self._save_as_preset_btn)

        self._revert_preset_btn = QPushButton("Revert")
        self._revert_preset_btn.clicked.connect(self._revert_current_preset)
        p_btns.addWidget(self._revert_preset_btn)
        pf_layout.addLayout(p_btns)
        sb_layout.addWidget(preset_frame)

        self.advanced_panel = AdvancedPanel()
        self.advanced_panel.config_changed.connect(self._on_config_changed)
        sb_layout.addWidget(self.advanced_panel)

        self.cmd_preview = CommandPreviewWidget()
        sb_layout.addWidget(self.cmd_preview)
        sb_layout.addStretch(1)

        self._inspector_tabs.addTab(self._wrap_scroll(session_box), "⚙ Session")

        # Tab 5: Technical Details & Telemetry
        telemetry_box = QWidget()
        tb_layout = QVBoxLayout(telemetry_box)
        tb_layout.setContentsMargins(4, 4, 4, 4)
        tb_layout.setSpacing(8)

        self.telemetry_widget = TelemetryWidget()
        tb_layout.addWidget(self.telemetry_widget)

        tb_layout.addWidget(QLabel("Activity & Diagnostic Log:"))
        self._tech_text = QTextEdit()
        self._tech_text.setReadOnly(True)
        self._tech_text.setMinimumHeight(140)
        tb_layout.addWidget(self._tech_text, 1)

        self._copy_tech_btn = QPushButton("📋 Copy Technical Details")
        self._copy_tech_btn.clicked.connect(self._copy_technical_details)
        tb_layout.addWidget(self._copy_tech_btn)

        self._inspector_tabs.addTab(self._wrap_scroll(telemetry_box), "📊 Telemetry")

        insp_layout.addWidget(self._inspector_tabs, 1)
        self._splitter.addWidget(self._inspector_container)

        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 0)
        self._inspector_container.setVisible(False)  # Calm default: Inspector is closed

        workspace_layout.addWidget(self._splitter, 1)

    def _wrap_scroll(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        return scroll

    # -----------------------------------------------------------------
    # Inspector & Session Strip Management
    # -----------------------------------------------------------------
    def toggle_inspector(self) -> None:
        self.set_inspector_visible(not self._inspector_container.isVisible())

    def set_inspector_visible(self, visible: bool) -> None:
        self._inspector_container.setVisible(visible)
        if visible:
            self._toggle_inspector_btn.setText("✕ Close Inspector")
        else:
            self._toggle_inspector_btn.setText("⚙ Configure / Inspector")

    def open_inspector_section(self, tab_idx: int) -> None:
        self._inspector_tabs.setCurrentIndex(tab_idx)
        self.set_inspector_visible(True)

    def _update_session_strip(self, cfg: SessionConfig) -> None:
        # 1. Source pill
        if cfg.source_type == "camera":
            self._pill_source.setText(f"📷 Camera {cfg.camera_index} ●")
        else:
            v_name = cfg.video_path.name if cfg.video_path else "No Video"
            self._pill_source.setText(f"🎬 Video: {v_name} ●")

        # 2. Character pill
        if cfg.character_path and cfg.character_path.is_file():
            rig_str = "✓" if (cfg.rig_path and cfg.rig_path.is_file()) else "No Rig"
            self._pill_character.setText(f"👤 {cfg.character_path.stem} ({rig_str})")
        else:
            self._pill_character.setText("👤 Character: None (Passthrough)")

        # 3. Tracker pill
        if cfg.tracker_type == "mediapipe":
            self._pill_tracker.setText(f"🎯 MediaPipe ({cfg.tracker_delegate.upper()}) ●")
        else:
            self._pill_tracker.setText("🎯 Tracker: None (Baseline)")

        # 4. Outputs pill
        outs = []
        if cfg.record_performance_path:
            outs.append(".CPC")
        if cfg.record_video_path:
            outs.append("MP4")
        if cfg.virtual_camera:
            outs.append("VCam")
        out_str = " + ".join(outs) if outs else "Preview Only"
        self._pill_outputs.setText(f"📹 Output: {out_str}")

        # 5. Preset pill
        self._pill_preset.setText(f"⚙ Preset: {self._active_preset_name}")

    # -----------------------------------------------------------------
    # Preflight & Configuration Management
    # -----------------------------------------------------------------
    def _on_config_changed(self) -> None:
        cfg = self.get_session_config()
        self.cmd_preview.update_command(cfg)
        self._update_session_strip(cfg)
        self._update_preflight()
        self._update_preset_dirty_state()

    def _update_preflight(self) -> None:
        cfg = self.get_session_config()
        errors = cfg.validate()

        if errors:
            self.start_btn.setEnabled(False)
            self._validation_banner_lbl.setText("  •  ".join(errors))
            self._validation_banner_widget.setVisible(True)
            self._preflight_pill.setText(f"▲ {len(errors)} Issue{'s' if len(errors) > 1 else ''} (Needs Attention)")
            self._preflight_pill.setStyleSheet("font-weight: 600; font-size: 12px; color: #f59e0b;")
        else:
            self.start_btn.setEnabled(self._worker is None or not self._worker.isRunning())
            self._validation_banner_widget.setVisible(False)

            # Truthful contextual readiness
            if cfg.character_path and cfg.rig_path and cfg.tracker_type == "mediapipe":
                self._preflight_pill.setText("● Ready to Perform")
                self._preflight_pill.setStyleSheet("font-weight: 600; font-size: 12px; color: #10b981;")
            elif cfg.tracker_type == "mediapipe":
                self._preflight_pill.setText("● Tracking Ready (Passthrough)")
                self._preflight_pill.setStyleSheet("font-weight: 600; font-size: 12px; color: #10b981;")
            else:
                self._preflight_pill.setText("● Preview Ready (No Tracking)")
                self._preflight_pill.setStyleSheet("font-weight: 600; font-size: 12px; color: #38bdf8;")

    def _handle_fix_this(self) -> None:
        cfg = self.get_session_config()
        errors = cfg.validate()
        if not errors:
            return

        err = errors[0].lower()
        if "video" in err or "source" in err:
            self.open_inspector_section(0)
        elif "character" in err or "rig" in err:
            self.open_character_workspace.emit()
        elif "model" in err or "tracker" in err:
            self.open_inspector_section(2)
        elif "output" in err or "record" in err:
            self.open_inspector_section(3)
        else:
            self.open_inspector_section(0)

    def apply_character_setup(self, setup_dict: dict[str, Any]) -> None:
        """Apply complete setup carried over from Character Setup workspace."""
        cfg = self.get_session_config()
        if "character_path" in setup_dict:
            cfg.character_path = setup_dict["character_path"]
        if "rig_path" in setup_dict:
            cfg.rig_path = setup_dict["rig_path"]
        if "model_path" in setup_dict:
            cfg.model_path = setup_dict["model_path"]
        if "tracker_delegate" in setup_dict:
            cfg.tracker_delegate = setup_dict["tracker_delegate"]
        if "tracker_type" in setup_dict:
            cfg.tracker_type = setup_dict["tracker_type"]
        if "renderer_type" in setup_dict:
            cfg.renderer_type = setup_dict["renderer_type"]

        self.set_session_config(cfg)
        self._log_activity(f"Applied character setup for: {cfg.character_path.name if cfg.character_path else 'Character'}")

    def _update_preset_dirty_state(self) -> None:
        if self._preset_combo.count() == 0:
            return
        cfg = self.get_session_config()
        is_match = self._settings.is_config_matching_preset(self._active_preset_name, cfg)
        current_text = self._preset_combo.currentText()
        if not is_match and not current_text.endswith(" • Modified"):
            self._preset_combo.setItemText(self._preset_combo.currentIndex(), f"{self._active_preset_name} • Modified")
        elif is_match and current_text.endswith(" • Modified"):
            self._preset_combo.setItemText(self._preset_combo.currentIndex(), self._active_preset_name)

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
        self._update_session_strip(cfg)
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
        raw_name = self._preset_combo.itemText(idx).replace(" • Modified", "")
        self._active_preset_name = raw_name
        if idx == 0:
            return
        cfg = self._settings.load_preset(raw_name)
        if cfg is not None:
            self.set_session_config(cfg)
            self._log_activity(f"Loaded preset: {raw_name}")

    def _save_current_preset(self) -> None:
        cfg = self.get_session_config()
        name = self._active_preset_name
        if name == "Default Configuration":
            self._save_as_new_preset()
            return
        self._settings.save_preset(name, cfg)
        self._load_presets_menu()
        idx = self._preset_combo.findText(name)
        if idx >= 0:
            self._preset_combo.setCurrentIndex(idx)
        self._log_activity(f"Saved preset: {name}")

    def _save_as_new_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Session Preset", "Preset Name:")
        if ok and name.strip():
            clean_name = name.strip()
            cfg = self.get_session_config()
            self._settings.save_preset(clean_name, cfg)
            self._active_preset_name = clean_name
            self._load_presets_menu()
            idx = self._preset_combo.findText(clean_name)
            if idx >= 0:
                self._preset_combo.setCurrentIndex(idx)
            self._log_activity(f"Saved new preset: {clean_name}")

    def _revert_current_preset(self) -> None:
        if self._active_preset_name == "Default Configuration":
            self.set_session_config(SessionConfig())
        else:
            cfg = self._settings.load_preset(self._active_preset_name)
            if cfg is not None:
                self.set_session_config(cfg)
        self._load_presets_menu()
        idx = self._preset_combo.findText(self._active_preset_name)
        if idx >= 0:
            self._preset_combo.setCurrentIndex(idx)
        self._log_activity(f"Reverted to preset: {self._active_preset_name}")

    # -----------------------------------------------------------------
    # Session Transport Lifecycle
    # -----------------------------------------------------------------
    def start_session(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return

        cfg = self.get_session_config()
        errors = cfg.validate()
        if errors:
            QMessageBox.warning(self, "Invalid Configuration", "\n".join(errors))
            return

        cd_seconds = self._settings.get_countdown_seconds()
        if cd_seconds > 0 and self._countdown_timer is None:
            self._start_countdown(cd_seconds)
            return

        self._launch_worker()

    def _start_countdown(self, seconds: int) -> None:
        self._countdown_remaining = seconds
        self.start_btn.setText(f"⏳ Starting in {self._countdown_remaining}s... (Click to Cancel)")
        self.start_btn.setProperty("danger", True)
        self.start_btn.setStyle(self.start_btn.style())
        self.start_btn.clicked.disconnect()
        self.start_btn.clicked.connect(self._cancel_countdown)

        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)
        self._countdown_timer.start(1000)

    def _on_countdown_tick(self) -> None:
        self._countdown_remaining -= 1
        if self._countdown_remaining <= 0:
            self._cleanup_countdown()
            self._launch_worker()
        else:
            self.start_btn.setText(f"⏳ Starting in {self._countdown_remaining}s... (Click to Cancel)")

    def _cancel_countdown(self) -> None:
        self._cleanup_countdown()
        self._log_activity("Session countdown cancelled by user.")

    def _cleanup_countdown(self) -> None:
        if self._countdown_timer is not None:
            self._countdown_timer.stop()
            self._countdown_timer = None
        self.start_btn.setText("▶  Start Performing")
        self.start_btn.setProperty("danger", False)
        self.start_btn.setProperty("primary", True)
        self.start_btn.setStyle(self.start_btn.style())
        self.start_btn.clicked.disconnect()
        self.start_btn.clicked.connect(self.start_session)

    def _launch_worker(self) -> None:
        cfg = self.get_session_config()
        self._summary_card.setVisible(False)
        self._last_cpc_path = cfg.record_performance_path
        self._last_mp4_path = cfg.record_video_path

        self._session_token += 1
        current_token = self._session_token

        self._worker = SessionWorker(cfg, session_token=current_token, parent=self)
        self._worker.frame_ready.connect(lambda img, *_: self._on_frame_ready(current_token, img))
        self._worker.telemetry_updated.connect(lambda data: self._on_telemetry_updated(current_token, data))
        self._worker.session_finished.connect(lambda: self._on_session_finished(current_token))
        self._worker.error_occurred.connect(lambda err, tech: self._on_error_occurred(current_token, err, tech))

        self._update_transport_ui(running=True)
        self._log_activity("Launching session worker...")
        self._worker.start()

    def is_running(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def stop_session(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._log_activity("Stopping session worker...")
            self._worker.stop()
            self.stop_btn.setEnabled(False)
            self.stop_btn.setText("Stopping...")

    def calibrate_neutral(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.calibrate_neutral()
            self._log_activity("Neutral head pose calibrated.")

    def open_clean_preview(self) -> None:
        if self._clean_preview_win is None:
            self._clean_preview_win = CleanPreviewWindow()
            self._clean_preview_win.window_closed.connect(self._on_clean_preview_closed)
        self._clean_preview_win.show()
        self._clean_preview_win.raise_()
        self._clean_preview_win.activateWindow()

    def _on_clean_preview_closed(self) -> None:
        self._clean_preview_win = None

    def toggle_performance_mode(self) -> None:
        self._performance_mode = not self._performance_mode
        self._perf_mode_btn.setText("Exit Performance" if self._performance_mode else "⛶ Fullscreen Stage")
        self._session_strip.setVisible(not self._performance_mode)
        if self._performance_mode:
            self.set_inspector_visible(False)

    # -----------------------------------------------------------------
    # Session Worker Callbacks
    # -----------------------------------------------------------------
    def _on_session_started(self, token: int) -> None:
        if token != self._session_token:
            return
        self._log_activity("Session active and capturing frames.")

    def _on_frame_ready(self, token: int, img: Any) -> None:
        if token != self._session_token:
            return
        self.preview_widget.update_frame(img)
        if self._clean_preview_win is not None and self._clean_preview_win.isVisible():
            self._clean_preview_win.update_frame(img)

    def _on_telemetry_updated(self, token: int, data: dict[str, Any]) -> None:
        if token != self._session_token:
            return
        self.telemetry_widget.update_telemetry(data)
        self.preview_widget.update_telemetry(data)
        if self._clean_preview_win is not None and self._clean_preview_win.isVisible():
            self._clean_preview_win.update_telemetry(data)

    def _on_session_finished(self, token: int) -> None:
        if token != self._session_token:
            return
        self._worker = None
        self._update_transport_ui(running=False)
        self._log_activity("Session finished.")

        cpc_text = f"• .CPC Take: {self._last_cpc_path.name}\n" if self._last_cpc_path else ""
        mp4_text = f"• MP4 Video: {self._last_mp4_path.name}\n" if self._last_mp4_path else ""

        self._summary_stats_lbl.setText(
            f"Take Completed Successfully.\n{cpc_text}{mp4_text}"
        )
        self._summary_card.setVisible(True)

    def _on_error_occurred(self, token: int, error_msg: str, tech_details: str) -> None:
        if token != self._session_token:
            return
        self._last_error_details = tech_details
        self._log_activity(f"ERROR: {error_msg}")
        QMessageBox.critical(
            self,
            "Capture Session Error",
            f"{error_msg}\n\nTechnical details:\n{tech_details}",
        )

    def _update_transport_ui(self, running: bool) -> None:
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.stop_btn.setText("■  Stop Session (Esc)")
        self.recenter_btn.setEnabled(running)
        self.source_panel.setEnabled(not running)
        self.tracker_panel.setEnabled(not running)
        self.renderer_panel.setEnabled(not running)
        self.outputs_panel.setEnabled(not running)

        if running:
            self.start_btn.setText("● Live Capturing")
            self._preflight_pill.setText("● LIVE")
            self._preflight_pill.setStyleSheet("font-weight: 700; font-size: 12px; color: #ef4444;")
        else:
            self.start_btn.setText("▶  Start Performing")
            self._update_preflight()

    def _reveal_last_take(self) -> None:
        target = self._last_cpc_path or self._last_mp4_path
        if target and target.parent.is_dir():
            QDesktopServices.openUrl(f"file://{target.parent.resolve()}")

    def _open_in_takes_studio(self) -> None:
        if self._last_cpc_path and self._last_cpc_path.is_file():
            self.open_takes_workspace.emit(self._last_cpc_path)

    def _log_activity(self, msg: str) -> None:
        self._tech_text.append(f"[{Path('.').stat().st_mtime:.0f}] {msg}")

    def _copy_technical_details(self) -> None:
        text = self._tech_text.toPlainText()
        if self._last_error_details:
            text += f"\n\n--- Last Error Details ---\n{self._last_error_details}"
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", "Technical activity details copied to clipboard.")
