from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from cpc.session import SessionConfig


class SourcePanel(QGroupBox):
    """Configuration panel for Camera vs Video frame source."""

    config_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Frame Ingest Source", parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(10)

        # Source Selection Tabs / Radio Toggle
        type_row = QHBoxLayout()
        type_row.setSpacing(16)
        self._combo_source_type = QComboBox()
        self._combo_source_type.addItems(["Physical Camera (Webcam)", "Local Video File (MP4/MOV)"])
        self._combo_source_type.currentIndexChanged.connect(self._on_type_changed)
        type_row.addWidget(QLabel("Source Kind:"))
        type_row.addWidget(self._combo_source_type, 1)
        layout.addLayout(type_row)

        # -------------------------------------------------------------
        # 1. Camera Controls
        # -------------------------------------------------------------
        self._camera_widget = QWidget()
        cam_layout = QGridLayout(self._camera_widget)
        cam_layout.setContentsMargins(0, 0, 0, 0)
        cam_layout.setSpacing(8)

        # Camera Index
        cam_layout.addWidget(QLabel("Camera Device:"), 0, 0)
        self._cam_index_spin = QSpinBox()
        self._cam_index_spin.setRange(0, 32)
        self._cam_index_spin.setValue(0)
        self._cam_index_spin.valueChanged.connect(lambda: self.config_changed.emit())

        self._rescan_btn = QPushButton("Refresh")
        self._rescan_btn.setToolTip("Refresh camera device list")
        self._rescan_btn.clicked.connect(self._rescan_cameras)

        cam_idx_row = QHBoxLayout()
        cam_idx_row.addWidget(self._cam_index_spin, 1)
        cam_idx_row.addWidget(self._rescan_btn)
        cam_layout.addLayout(cam_idx_row, 0, 1)

        # Requested Resolution & FPS
        cam_layout.addWidget(QLabel("Negotiation:"), 1, 0)
        res_row = QHBoxLayout()
        self._combo_res = QComboBox()
        self._combo_res.addItems(["Auto (Native Sensor)", "1920 x 1080 (1080p)", "1280 x 720 (720p)", "640 x 480 (VGA)"])
        self._combo_res.currentIndexChanged.connect(lambda: self.config_changed.emit())
        res_row.addWidget(self._combo_res, 1)

        self._combo_fps = QComboBox()
        self._combo_fps.addItems(["Auto FPS", "60 FPS", "30 FPS", "24 FPS"])
        self._combo_fps.currentIndexChanged.connect(lambda: self.config_changed.emit())
        res_row.addWidget(self._combo_fps)
        cam_layout.addLayout(res_row, 1, 1)

        layout.addWidget(self._camera_widget)

        # -------------------------------------------------------------
        # 2. Video File Controls
        # -------------------------------------------------------------
        self._video_widget = QWidget()
        vid_layout = QGridLayout(self._video_widget)
        vid_layout.setContentsMargins(0, 0, 0, 0)
        vid_layout.setSpacing(8)

        vid_layout.addWidget(QLabel("Video Path:"), 0, 0)
        self._video_edit = QLineEdit()
        self._video_edit.setPlaceholderText("Select performer video (.mp4, .mov, .avi)...")
        self._video_edit.textChanged.connect(lambda: self.config_changed.emit())

        self._browse_vid_btn = QPushButton("Browse...")
        self._browse_vid_btn.clicked.connect(self._browse_video)

        vid_path_row = QHBoxLayout()
        vid_path_row.addWidget(self._video_edit, 1)
        vid_path_row.addWidget(self._browse_vid_btn)
        vid_layout.addLayout(vid_path_row, 0, 1)

        # Loop Toggle
        self._loop_checkbox = QCheckBox("Loop video playback continuously")
        self._loop_checkbox.setChecked(True)
        self._loop_checkbox.stateChanged.connect(lambda: self.config_changed.emit())
        vid_layout.addWidget(self._loop_checkbox, 1, 1)

        self._video_widget.setVisible(False)
        layout.addWidget(self._video_widget)

        # Common: Mirror source
        self._mirror_checkbox = QCheckBox("Mirror ingest source horizontally")
        self._mirror_checkbox.setChecked(False)
        self._mirror_checkbox.stateChanged.connect(lambda: self.config_changed.emit())
        layout.addWidget(self._mirror_checkbox)

    def _on_type_changed(self, idx: int) -> None:
        is_cam = (idx == 0)
        self._camera_widget.setVisible(is_cam)
        self._video_widget.setVisible(not is_cam)
        self.config_changed.emit()

    def _rescan_cameras(self) -> None:
        self.config_changed.emit()

    def _browse_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Performer Video",
            os.path.expanduser("~"),
            "Video Files (*.mp4 *.mov *.avi *.mkv);;All Files (*)",
        )
        if path:
            self._video_edit.setText(path)

    def apply_to_config(self, cfg: SessionConfig) -> None:
        if self._combo_source_type.currentIndex() == 0:
            cfg.source_type = "camera"
            cfg.camera_index = self._cam_index_spin.value()
            cfg.video_path = None
        else:
            cfg.source_type = "video"
            vid_str = self._video_edit.text().strip()
            cfg.video_path = Path(vid_str) if vid_str else None
            cfg.loop_video = self._loop_checkbox.isChecked()

        cfg.mirror = self._mirror_checkbox.isChecked()

        # Parse resolution
        res_idx = self._combo_res.currentIndex()
        if res_idx == 1:
            cfg.requested_width, cfg.requested_height = 1920, 1080
        elif res_idx == 2:
            cfg.requested_width, cfg.requested_height = 1280, 720
        elif res_idx == 3:
            cfg.requested_width, cfg.requested_height = 640, 480
        else:
            cfg.requested_width, cfg.requested_height = None, None

        # Parse FPS
        fps_idx = self._combo_fps.currentIndex()
        if fps_idx == 1:
            cfg.requested_fps = 60.0
        elif fps_idx == 2:
            cfg.requested_fps = 30.0
        elif fps_idx == 3:
            cfg.requested_fps = 24.0
        else:
            cfg.requested_fps = None

    def load_from_config(self, cfg: SessionConfig) -> None:
        if cfg.source_type == "video":
            self._combo_source_type.setCurrentIndex(1)
            self._video_edit.setText(str(cfg.video_path) if cfg.video_path else "")
            self._loop_checkbox.setChecked(cfg.loop_video)
        else:
            self._combo_source_type.setCurrentIndex(0)
            self._cam_index_spin.setValue(cfg.camera_index)

        self._mirror_checkbox.setChecked(cfg.mirror)

        if cfg.requested_width == 1920 and cfg.requested_height == 1080:
            self._combo_res.setCurrentIndex(1)
        elif cfg.requested_width == 1280 and cfg.requested_height == 720:
            self._combo_res.setCurrentIndex(2)
        elif cfg.requested_width == 640 and cfg.requested_height == 480:
            self._combo_res.setCurrentIndex(3)
        else:
            self._combo_res.setCurrentIndex(0)

        if cfg.requested_fps == 60.0:
            self._combo_fps.setCurrentIndex(1)
        elif cfg.requested_fps == 30.0:
            self._combo_fps.setCurrentIndex(2)
        elif cfg.requested_fps == 24.0:
            self._combo_fps.setCurrentIndex(3)
        else:
            self._combo_fps.setCurrentIndex(0)


class TrackerPanel(QGroupBox):
    """Configuration panel for Performance Tracker selection."""

    config_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Performance Tracker", parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(8)

        # Tracker Selection
        layout.addWidget(QLabel("Backend:"), 0, 0)
        self._tracker_combo = QComboBox()
        self._tracker_combo.addItems([
            "No Tracking (Passthrough / Baseline)",
            "MediaPipe Face Landmarker (478 pts + 52 Blendshapes)",
        ])
        self._tracker_combo.currentIndexChanged.connect(self._on_tracker_changed)
        layout.addWidget(self._tracker_combo, 0, 1)

        # Model Path Picker
        self._lbl_model = QLabel("Model Asset (.task):")
        layout.addWidget(self._lbl_model, 1, 0)

        self._model_edit = QLineEdit()
        self._model_edit.setPlaceholderText("Path to face_landmarker.task...")
        self._model_edit.textChanged.connect(lambda: self.config_changed.emit())

        self._browse_model_btn = QPushButton("Browse...")
        self._browse_model_btn.clicked.connect(self._browse_model)

        model_row = QHBoxLayout()
        model_row.addWidget(self._model_edit, 1)
        model_row.addWidget(self._browse_model_btn)
        layout.addLayout(model_row, 1, 1)

        # Execution Delegate
        self._lbl_delegate = QLabel("Compute Delegate:")
        layout.addWidget(self._lbl_delegate, 2, 0)

        self._delegate_combo = QComboBox()
        self._delegate_combo.addItems([
            "CPU (Recommended / Validated)",
            "GPU (Experimental on macOS)",
        ])
        self._delegate_combo.currentIndexChanged.connect(lambda: self.config_changed.emit())
        layout.addWidget(self._delegate_combo, 2, 1)

        self._update_visibility()

    def _on_tracker_changed(self) -> None:
        self._update_visibility()
        self.config_changed.emit()

    def _update_visibility(self) -> None:
        is_mp = (self._tracker_combo.currentIndex() == 1)
        self._lbl_model.setVisible(is_mp)
        self._model_edit.setVisible(is_mp)
        self._browse_model_btn.setVisible(is_mp)
        self._lbl_delegate.setVisible(is_mp)
        self._delegate_combo.setVisible(is_mp)

    def _browse_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select MediaPipe Face Landmarker Task Model",
            os.path.expanduser("~"),
            "Task Models (*.task);;All Files (*)",
        )
        if path:
            self._model_edit.setText(path)

    def apply_to_config(self, cfg: SessionConfig) -> None:
        if self._tracker_combo.currentIndex() == 1:
            cfg.tracker_type = "mediapipe"
            model_str = self._model_edit.text().strip()
            cfg.model_path = Path(model_str) if model_str else None
            cfg.tracker_delegate = "gpu" if self._delegate_combo.currentIndex() == 1 else "cpu"
        else:
            cfg.tracker_type = "null"
            cfg.model_path = None
            cfg.tracker_delegate = "cpu"

    def load_from_config(self, cfg: SessionConfig) -> None:
        if cfg.tracker_type == "mediapipe":
            self._tracker_combo.setCurrentIndex(1)
            self._model_edit.setText(str(cfg.model_path) if cfg.model_path else "")
            self._delegate_combo.setCurrentIndex(1 if cfg.tracker_delegate == "gpu" else 0)
        else:
            self._tracker_combo.setCurrentIndex(0)
        self._update_visibility()


class RendererPanel(QGroupBox):
    """Configuration panel for Character Artwork and 2D Mesh-Warp Renderer."""

    config_changed = Signal()
    open_character_workspace = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Character && Renderer", parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(8)

        # Renderer Selection
        layout.addWidget(QLabel("Renderer:"), 0, 0)
        self._renderer_combo = QComboBox()
        self._renderer_combo.addItems([
            "Passthrough (Show Ingest Frames)",
            "2D Rig-Warp (Drive Character Reference)",
        ])
        self._renderer_combo.currentIndexChanged.connect(self._on_renderer_changed)
        layout.addWidget(self._renderer_combo, 0, 1)

        # Character Image Picker
        self._lbl_char = QLabel("Character Image:")
        layout.addWidget(self._lbl_char, 1, 0)

        self._char_edit = QLineEdit()
        self._char_edit.setPlaceholderText("Select character reference image (.png, .jpg)...")
        self._char_edit.textChanged.connect(lambda: self.config_changed.emit())

        self._browse_char_btn = QPushButton("Browse...")
        self._browse_char_btn.clicked.connect(self._browse_character)

        char_row = QHBoxLayout()
        char_row.addWidget(self._char_edit, 1)
        char_row.addWidget(self._browse_char_btn)
        layout.addLayout(char_row, 1, 1)

        # Explicit Rig Path Picker
        self._lbl_rig = QLabel("Rig Definition:")
        layout.addWidget(self._lbl_rig, 2, 0)

        self._rig_edit = QLineEdit()
        self._rig_edit.setPlaceholderText("Auto: <character>.rig.json")
        self._rig_edit.textChanged.connect(lambda: self.config_changed.emit())

        self._browse_rig_btn = QPushButton("Browse...")
        self._browse_rig_btn.clicked.connect(self._browse_rig)

        rig_row = QHBoxLayout()
        rig_row.addWidget(self._rig_edit, 1)
        rig_row.addWidget(self._browse_rig_btn)
        layout.addLayout(rig_row, 2, 1)

        # Expression & Head Gains
        self._lbl_gains = QLabel("Motion Gains:")
        layout.addWidget(self._lbl_gains, 3, 0)

        gains_widget = QWidget()
        g_layout = QVBoxLayout(gains_widget)
        g_layout.setContentsMargins(0, 0, 0, 0)
        g_layout.setSpacing(4)

        # Expression Gain
        exp_row = QHBoxLayout()
        exp_row.addWidget(QLabel("Expression:"), 0)
        self._exp_slider = QSlider(Qt.Horizontal)
        self._exp_slider.setRange(0, 300)
        self._exp_slider.setValue(100)
        self._exp_val_lbl = QLabel("1.00x")
        self._exp_slider.valueChanged.connect(self._on_exp_changed)
        exp_row.addWidget(self._exp_slider, 1)
        exp_row.addWidget(self._exp_val_lbl)
        g_layout.addLayout(exp_row)

        # Head Motion Gain
        head_row = QHBoxLayout()
        head_row.addWidget(QLabel("Head Motion:"), 0)
        self._head_slider = QSlider(Qt.Horizontal)
        self._head_slider.setRange(0, 300)
        self._head_slider.setValue(100)
        self._head_val_lbl = QLabel("1.00x")
        self._head_slider.valueChanged.connect(self._on_head_changed)
        head_row.addWidget(self._head_slider, 1)
        head_row.addWidget(self._head_val_lbl)
        g_layout.addLayout(head_row)

        layout.addWidget(gains_widget, 3, 1)

        # Studio Link Button
        self._studio_btn = QPushButton("Open Character && Rig Studio →")
        self._studio_btn.clicked.connect(lambda: self.open_character_workspace.emit())
        layout.addWidget(self._studio_btn, 4, 1)

        self._update_visibility()

    def _on_exp_changed(self, val: int) -> None:
        self._exp_val_lbl.setText(f"{val / 100.0:.2f}x")
        self.config_changed.emit()

    def _on_head_changed(self, val: int) -> None:
        self._head_val_lbl.setText(f"{val / 100.0:.2f}x")
        self.config_changed.emit()

    def _on_renderer_changed(self) -> None:
        self._update_visibility()
        self.config_changed.emit()

    def _update_visibility(self) -> None:
        is_rig = (self._renderer_combo.currentIndex() == 1)
        self._lbl_char.setVisible(is_rig)
        self._char_edit.setVisible(is_rig)
        self._browse_char_btn.setVisible(is_rig)
        self._lbl_rig.setVisible(is_rig)
        self._rig_edit.setVisible(is_rig)
        self._browse_rig_btn.setVisible(is_rig)
        self._lbl_gains.setVisible(is_rig)
        self._exp_slider.setVisible(is_rig)
        self._exp_val_lbl.setVisible(is_rig)
        self._head_slider.setVisible(is_rig)
        self._head_val_lbl.setVisible(is_rig)
        self._studio_btn.setVisible(is_rig)

    def _browse_character(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Character Reference Image",
            os.path.expanduser("~"),
            "Image Files (*.png *.jpg *.jpeg *.webp);;All Files (*)",
        )
        if path:
            self._char_edit.setText(path)

    def _browse_rig(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Character Rig Sidecar",
            os.path.expanduser("~"),
            "Rig Files (*.rig.json);;All Files (*)",
        )
        if path:
            self._rig_edit.setText(path)

    def apply_to_config(self, cfg: SessionConfig) -> None:
        if self._renderer_combo.currentIndex() == 1:
            cfg.renderer_type = "rig"
            char_str = self._char_edit.text().strip()
            cfg.character_path = Path(char_str) if char_str else None
            rig_str = self._rig_edit.text().strip()
            cfg.rig_path = Path(rig_str) if rig_str else None
            cfg.expression_gain = self._exp_slider.value() / 100.0
            cfg.head_gain = self._head_slider.value() / 100.0
        else:
            cfg.renderer_type = "passthrough"
            cfg.character_path = None
            cfg.rig_path = None
            cfg.expression_gain = 1.0
            cfg.head_gain = 1.0

    def load_from_config(self, cfg: SessionConfig) -> None:
        if cfg.renderer_type == "rig":
            self._renderer_combo.setCurrentIndex(1)
            self._char_edit.setText(str(cfg.character_path) if cfg.character_path else "")
            self._rig_edit.setText(str(cfg.rig_path) if cfg.rig_path else "")
            self._exp_slider.setValue(int(cfg.expression_gain * 100))
            self._head_slider.setValue(int(cfg.head_gain * 100))
        else:
            self._renderer_combo.setCurrentIndex(0)
        self._update_visibility()


class OutputsPanel(QGroupBox):
    """Configuration panel for Live Output destinations (Take recording, MP4, OBS Virtual Camera)."""

    config_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Output Routing", parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(10)

        # 1. Performance Take Recording (.cpc)
        self._cpc_checkbox = QCheckBox("Record Performance Take (.cpc)")
        self._cpc_checkbox.stateChanged.connect(self._on_cpc_toggled)
        layout.addWidget(self._cpc_checkbox)

        self._cpc_widget = QWidget()
        cpc_row = QHBoxLayout(self._cpc_widget)
        cpc_row.setContentsMargins(0, 0, 0, 0)
        self._cpc_edit = QLineEdit()
        self._cpc_edit.setPlaceholderText("Destination file path (e.g. takes/take_01.cpc)...")
        self._cpc_edit.textChanged.connect(lambda: self.config_changed.emit())
        self._cpc_browse_btn = QPushButton("Browse...")
        self._cpc_browse_btn.clicked.connect(self._browse_cpc)
        cpc_row.addWidget(self._cpc_edit, 1)
        cpc_row.addWidget(self._cpc_browse_btn)
        self._cpc_widget.setVisible(False)
        layout.addWidget(self._cpc_widget)

        # 2. Rendered MP4 Recording
        self._mp4_checkbox = QCheckBox("Record Rendered Preview Video (.mp4)")
        self._mp4_checkbox.stateChanged.connect(self._on_mp4_toggled)
        layout.addWidget(self._mp4_checkbox)

        self._mp4_widget = QWidget()
        mp4_row = QHBoxLayout(self._mp4_widget)
        mp4_row.setContentsMargins(0, 0, 0, 0)
        self._mp4_edit = QLineEdit()
        self._mp4_edit.setPlaceholderText("Destination file path (e.g. captures/render_01.mp4)...")
        self._mp4_edit.textChanged.connect(lambda: self.config_changed.emit())
        self._mp4_browse_btn = QPushButton("Browse...")
        self._mp4_browse_btn.clicked.connect(self._browse_mp4)
        mp4_row.addWidget(self._mp4_edit, 1)
        mp4_row.addWidget(self._mp4_browse_btn)
        self._mp4_widget.setVisible(False)
        layout.addWidget(self._mp4_widget)

        # 3. Virtual Camera Sink (OBS / Zoom / Discord)
        self._vcam_checkbox = QCheckBox("Publish to Virtual Camera (OBS)")
        self._vcam_checkbox.stateChanged.connect(self._on_vcam_toggled)
        layout.addWidget(self._vcam_checkbox)

        self._vcam_widget = QWidget()
        vcam_row = QHBoxLayout(self._vcam_widget)
        vcam_row.setContentsMargins(0, 0, 0, 0)
        vcam_row.addWidget(QLabel("Output Resolution:"), 0)
        self._vcam_size_combo = QComboBox()
        self._vcam_size_combo.addItems(["1280x720 (720p - OBS Default)", "1920x1080 (1080p)", "640x480 (VGA)"])
        self._vcam_size_combo.currentIndexChanged.connect(lambda: self.config_changed.emit())
        vcam_row.addWidget(self._vcam_size_combo, 1)
        self._vcam_widget.setVisible(False)
        layout.addWidget(self._vcam_widget)

    def _on_cpc_toggled(self, state: int) -> None:
        self._cpc_widget.setVisible(state == Qt.Checked)
        self.config_changed.emit()

    def _on_mp4_toggled(self, state: int) -> None:
        self._mp4_widget.setVisible(state == Qt.Checked)
        self.config_changed.emit()

    def _on_vcam_toggled(self, state: int) -> None:
        self._vcam_widget.setVisible(state == Qt.Checked)
        self.config_changed.emit()

    def _browse_cpc(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Performance Capture Take",
            os.path.expanduser("~"),
            "CPC Captures (*.cpc);;All Files (*)",
        )
        if path:
            if not path.endswith(".cpc"):
                path += ".cpc"
            self._cpc_edit.setText(path)

    def _browse_mp4(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Rendered Video",
            os.path.expanduser("~"),
            "MP4 Video (*.mp4);;All Files (*)",
        )
        if path:
            if not path.endswith(".mp4"):
                path += ".mp4"
            self._mp4_edit.setText(path)

    def apply_to_config(self, cfg: SessionConfig) -> None:
        if self._cpc_checkbox.isChecked():
            cpc_str = self._cpc_edit.text().strip()
            cfg.record_performance_path = Path(cpc_str) if cpc_str else None
        else:
            cfg.record_performance_path = None

        if self._mp4_checkbox.isChecked():
            mp4_str = self._mp4_edit.text().strip()
            cfg.record_video_path = Path(mp4_str) if mp4_str else None
        else:
            cfg.record_video_path = None

        cfg.virtual_camera = self._vcam_checkbox.isChecked()
        size_str = self._vcam_size_combo.currentText().split(" ")[0]
        try:
            parts = size_str.lower().split("x", 1)
            cfg.vcam_size = (int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            cfg.vcam_size = (1280, 720)

    def load_from_config(self, cfg: SessionConfig) -> None:
        if cfg.record_performance_path is not None:
            self._cpc_checkbox.setChecked(True)
            self._cpc_widget.setVisible(True)
            self._cpc_edit.setText(str(cfg.record_performance_path))
        else:
            self._cpc_checkbox.setChecked(False)
            self._cpc_widget.setVisible(False)

        if cfg.record_video_path is not None:
            self._mp4_checkbox.setChecked(True)
            self._mp4_widget.setVisible(True)
            self._mp4_edit.setText(str(cfg.record_video_path))
        else:
            self._mp4_checkbox.setChecked(False)
            self._mp4_widget.setVisible(False)

        self._vcam_checkbox.setChecked(cfg.virtual_camera)
        self._vcam_widget.setVisible(cfg.virtual_camera)

        w, h = cfg.vcam_size
        if w == 1920 and h == 1080:
            self._vcam_size_combo.setCurrentIndex(1)
        elif w == 640 and h == 480:
            self._vcam_size_combo.setCurrentIndex(2)
        else:
            self._vcam_size_combo.setCurrentIndex(0)


class AdvancedPanel(QGroupBox):
    """Configuration panel for Advanced capture controls and execution boundaries."""

    config_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Session Limits && Display", parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(8)

        # Stop After Frame Limit
        layout.addWidget(QLabel("Stop After:"), 0, 0)
        self._frames_combo = QComboBox()
        self._frames_combo.addItems([
            "Unlimited (Stop manually)",
            "60 frames (~2 sec)",
            "120 frames (~4 sec)",
            "300 frames (~10 sec)",
            "900 frames (~30 sec)",
            "Custom Frame Count...",
        ])
        self._frames_combo.currentIndexChanged.connect(self._on_frames_changed)
        layout.addWidget(self._frames_combo, 0, 1)

        self._custom_frames_spin = QSpinBox()
        self._custom_frames_spin.setRange(1, 1000000)
        self._custom_frames_spin.setValue(150)
        self._custom_frames_spin.valueChanged.connect(lambda: self.config_changed.emit())
        self._custom_frames_spin.setVisible(False)
        layout.addWidget(self._custom_frames_spin, 1, 1)

        # Live Preview Display Toggle
        self._preview_checkbox = QCheckBox("Show Live Character Preview Window")
        self._preview_checkbox.setChecked(True)
        self._preview_checkbox.stateChanged.connect(lambda: self.config_changed.emit())
        layout.addWidget(self._preview_checkbox, 2, 0, 1, 2)

    def _on_frames_changed(self, idx: int) -> None:
        self._custom_frames_spin.setVisible(idx == 5)
        self.config_changed.emit()

    def apply_to_config(self, cfg: SessionConfig) -> None:
        idx = self._frames_combo.currentIndex()
        if idx == 0:
            cfg.frames = 0
        elif idx == 1:
            cfg.frames = 60
        elif idx == 2:
            cfg.frames = 120
        elif idx == 3:
            cfg.frames = 300
        elif idx == 4:
            cfg.frames = 900
        elif idx == 5:
            cfg.frames = self._custom_frames_spin.value()

        cfg.no_window = not self._preview_checkbox.isChecked()

    def load_from_config(self, cfg: SessionConfig) -> None:
        if cfg.frames == 0:
            self._frames_combo.setCurrentIndex(0)
        elif cfg.frames == 60:
            self._frames_combo.setCurrentIndex(1)
        elif cfg.frames == 120:
            self._frames_combo.setCurrentIndex(2)
        elif cfg.frames == 300:
            self._frames_combo.setCurrentIndex(3)
        elif cfg.frames == 900:
            self._frames_combo.setCurrentIndex(4)
        else:
            self._frames_combo.setCurrentIndex(5)
            self._custom_frames_spin.setValue(cfg.frames)

        self._preview_checkbox.setChecked(not cfg.no_window)
