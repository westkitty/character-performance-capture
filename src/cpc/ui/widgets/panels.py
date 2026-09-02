from __future__ import annotations

from pathlib import Path

import cv2
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from cpc.rig import default_rig_path
from cpc.session import SessionConfig


class SourcePanel(QGroupBox):
    """Configuration panel for camera capture or local video playback source."""

    config_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Frame Source", parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(10)

        # Source type selector
        type_layout = QHBoxLayout()
        self._radio_camera = QRadioButton("Physical Camera")
        self._radio_video = QRadioButton("Local Video File")
        self._radio_camera.setChecked(True)

        self._source_group = QButtonGroup(self)
        self._source_group.addButton(self._radio_camera)
        self._source_group.addButton(self._radio_video)
        self._source_group.buttonToggled.connect(self._on_source_type_toggled)

        type_layout.addWidget(self._radio_camera)
        type_layout.addWidget(self._radio_video)
        type_layout.addStretch(1)
        layout.addLayout(type_layout)

        # Camera settings container
        self._camera_container = QWidget()
        cam_layout = QGridLayout(self._camera_container)
        cam_layout.setContentsMargins(0, 0, 0, 0)
        cam_layout.setSpacing(6)

        cam_layout.addWidget(QLabel("Camera Index:"), 0, 0)
        self._camera_spin = QSpinBox()
        self._camera_spin.setRange(0, 32)
        self._camera_spin.setValue(0)
        self._camera_spin.valueChanged.connect(lambda: self.config_changed.emit())
        cam_layout.addWidget(self._camera_spin, 0, 1)

        self._rescan_btn = QPushButton("Rescan")
        self._rescan_btn.setToolTip("Scan local system for available video capture devices")
        self._rescan_btn.clicked.connect(self._rescan_cameras)
        cam_layout.addWidget(self._rescan_btn, 0, 2)

        # Width / Height / FPS
        cam_layout.addWidget(QLabel("Requested Size:"), 1, 0)
        dims_layout = QHBoxLayout()
        self._width_spin = QSpinBox()
        self._width_spin.setRange(0, 7680)
        self._width_spin.setSpecialValueText("Auto")
        self._width_spin.setValue(0)
        self._width_spin.valueChanged.connect(lambda: self.config_changed.emit())

        self._height_spin = QSpinBox()
        self._height_spin.setRange(0, 4320)
        self._height_spin.setSpecialValueText("Auto")
        self._height_spin.setValue(0)
        self._height_spin.valueChanged.connect(lambda: self.config_changed.emit())

        dims_layout.addWidget(self._width_spin)
        dims_layout.addWidget(QLabel("x"))
        dims_layout.addWidget(self._height_spin)
        cam_layout.addLayout(dims_layout, 1, 1, 1, 2)

        cam_layout.addWidget(QLabel("Requested FPS:"), 2, 0)
        self._fps_spin = QDoubleSpinBox()
        self._fps_spin.setRange(0.0, 240.0)
        self._fps_spin.setDecimals(1)
        self._fps_spin.setSpecialValueText("Auto")
        self._fps_spin.setValue(0.0)
        self._fps_spin.valueChanged.connect(lambda: self.config_changed.emit())
        cam_layout.addWidget(self._fps_spin, 2, 1, 1, 2)

        # Mirror checkbox
        self._mirror_check = QCheckBox("Mirror source horizontally")
        self._mirror_check.toggled.connect(lambda: self.config_changed.emit())
        cam_layout.addWidget(self._mirror_check, 3, 0, 1, 3)

        # macOS Camera Note
        self._tcc_note = QLabel(
            "macOS permission: If video is black/blocked, verify Camera access in\n"
            "System Settings → Privacy & Security → Camera."
        )
        self._tcc_note.setProperty("secondary", True)
        self._tcc_note.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        cam_layout.addWidget(self._tcc_note, 4, 0, 1, 3)

        layout.addWidget(self._camera_container)

        # Video settings container
        self._video_container = QWidget()
        vid_layout = QGridLayout(self._video_container)
        vid_layout.setContentsMargins(0, 0, 0, 0)
        vid_layout.setSpacing(6)

        vid_layout.addWidget(QLabel("Video File:"), 0, 0)
        self._video_edit = QLineEdit()
        self._video_edit.setPlaceholderText("Select or drop local MP4/MOV clip...")
        self._video_edit.textChanged.connect(lambda: self.config_changed.emit())
        vid_layout.addWidget(self._video_edit, 0, 1)

        self._video_browse_btn = QPushButton("Browse...")
        self._video_browse_btn.clicked.connect(self._browse_video)
        vid_layout.addWidget(self._video_browse_btn, 0, 2)

        self._loop_check = QCheckBox("Loop video at end of stream")
        self._loop_check.toggled.connect(lambda: self.config_changed.emit())
        vid_layout.addWidget(self._loop_check, 1, 0, 1, 3)

        self._video_container.setVisible(False)
        layout.addWidget(self._video_container)

    def _on_source_type_toggled(self) -> None:
        is_cam = self._radio_camera.isChecked()
        self._camera_container.setVisible(is_cam)
        self._video_container.setVisible(not is_cam)
        self.config_changed.emit()

    def _browse_video(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Source Video",
            str(Path.home()),
            "Video Files (*.mp4 *.mov *.avi *.mkv);;All Files (*)",
        )
        if file_path:
            self._video_edit.setText(file_path)

    def _rescan_cameras(self) -> None:
        # Check standard low camera indices
        available = []
        for idx in range(4):
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                available.append(idx)
                cap.release()
        if available:
            self._rescan_btn.setToolTip(f"Found camera indices: {available}")
        else:
            self._rescan_btn.setToolTip("No camera devices opened")

    def apply_to_config(self, cfg: SessionConfig) -> None:
        cfg.source_type = "camera" if self._radio_camera.isChecked() else "video"
        cfg.camera_index = self._camera_spin.value()
        cfg.requested_width = self._width_spin.value() if self._width_spin.value() > 0 else None
        cfg.requested_height = self._height_spin.value() if self._height_spin.value() > 0 else None
        cfg.requested_fps = self._fps_spin.value() if self._fps_spin.value() > 0 else None
        cfg.mirror = self._mirror_check.isChecked()

        v_path = self._video_edit.text().strip()
        cfg.video_path = Path(v_path) if v_path else None
        cfg.loop_video = self._loop_check.isChecked()

    def load_from_config(self, cfg: SessionConfig) -> None:
        if cfg.source_type == "video":
            self._radio_video.setChecked(True)
        else:
            self._radio_camera.setChecked(True)
        self._camera_spin.setValue(cfg.camera_index)
        self._width_spin.setValue(cfg.requested_width or 0)
        self._height_spin.setValue(cfg.requested_height or 0)
        self._fps_spin.setValue(cfg.requested_fps or 0.0)
        self._mirror_check.setChecked(cfg.mirror)
        self._video_edit.setText(str(cfg.video_path) if cfg.video_path else "")
        self._loop_check.setChecked(cfg.loop_video)


class TrackerPanel(QGroupBox):
    """Configuration panel for facial landmark tracker and model delegate."""

    config_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Performance Tracker", parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(6)

        # Tracker Type
        layout.addWidget(QLabel("Backend:"), 0, 0)
        self._tracker_combo = QComboBox()
        self._tracker_combo.addItem("No Tracking (Passthrough)", "null")
        self._tracker_combo.addItem("MediaPipe Face Landmarker", "mediapipe")
        self._tracker_combo.currentIndexChanged.connect(self._on_tracker_changed)
        layout.addWidget(self._tracker_combo, 0, 1, 1, 2)

        # Model Path
        self._lbl_model = QLabel("Model Asset (.task):")
        layout.addWidget(self._lbl_model, 1, 0)

        self._model_edit = QLineEdit()
        self._model_edit.setPlaceholderText("Select face_landmarker.task model...")
        self._model_edit.textChanged.connect(self._on_model_text_changed)
        layout.addWidget(self._model_edit, 1, 1)

        self._model_browse_btn = QPushButton("Browse...")
        self._model_browse_btn.clicked.connect(self._browse_model)
        layout.addWidget(self._model_browse_btn, 1, 2)

        # Model status indicator
        self._model_status_lbl = QLabel("")
        self._model_status_lbl.setProperty("secondary", True)
        layout.addWidget(self._model_status_lbl, 2, 1, 1, 2)

        # Delegate
        self._lbl_delegate = QLabel("Delegate:")
        layout.addWidget(self._lbl_delegate, 3, 0)

        self._delegate_combo = QComboBox()
        self._delegate_combo.addItem("CPU (Validated macOS Default)", "cpu")
        self._delegate_combo.addItem("GPU (Experimental)", "gpu")
        self._delegate_combo.currentIndexChanged.connect(self._on_delegate_changed)
        layout.addWidget(self._delegate_combo, 3, 1, 1, 2)

        # GPU Warning Note
        self._gpu_warning = QLabel(
            "Warning: GPU delegate can be unstable on some macOS/headless MediaPipe configurations. "
            "CPU is the validated CPC default."
        )
        self._gpu_warning.setStyleSheet("color: #f59e0b; font-size: 11px;")
        self._gpu_warning.setWordWrap(True)
        self._gpu_warning.setVisible(False)
        layout.addWidget(self._gpu_warning, 4, 0, 1, 3)

        self._on_tracker_changed()

    def _on_tracker_changed(self) -> None:
        is_mp = self._tracker_combo.currentData() == "mediapipe"
        self._lbl_model.setEnabled(is_mp)
        self._model_edit.setEnabled(is_mp)
        self._model_browse_btn.setEnabled(is_mp)
        self._lbl_delegate.setEnabled(is_mp)
        self._delegate_combo.setEnabled(is_mp)
        self._check_model_status()
        self.config_changed.emit()

    def _on_delegate_changed(self) -> None:
        is_gpu = self._delegate_combo.currentData() == "gpu"
        self._gpu_warning.setVisible(is_gpu)
        self.config_changed.emit()

    def _on_model_text_changed(self) -> None:
        self._check_model_status()
        self.config_changed.emit()

    def _check_model_status(self) -> None:
        path_str = self._model_edit.text().strip()
        if not path_str:
            self._model_status_lbl.setText("Required for MediaPipe tracking")
            self._model_status_lbl.setStyleSheet("color: #a1a1aa;")
            return
        if Path(path_str).is_file():
            self._model_status_lbl.setText("Model file verified")
            self._model_status_lbl.setStyleSheet("color: #10b981;")
        else:
            self._model_status_lbl.setText("File not found")
            self._model_status_lbl.setStyleSheet("color: #ef4444;")

    def _browse_model(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Face Landmarker Model",
            str(Path.home()),
            "MediaPipe Task (*.task);;All Files (*)",
        )
        if file_path:
            self._model_edit.setText(file_path)

    def apply_to_config(self, cfg: SessionConfig) -> None:
        cfg.tracker_type = self._tracker_combo.currentData()
        m_str = self._model_edit.text().strip()
        cfg.model_path = Path(m_str) if m_str else None
        cfg.tracker_delegate = self._delegate_combo.currentData()

    def load_from_config(self, cfg: SessionConfig) -> None:
        idx = self._tracker_combo.findData(cfg.tracker_type)
        if idx >= 0:
            self._tracker_combo.setCurrentIndex(idx)
        self._model_edit.setText(str(cfg.model_path) if cfg.model_path else "")
        d_idx = self._delegate_combo.findData(cfg.tracker_delegate)
        if d_idx >= 0:
            self._delegate_combo.setCurrentIndex(d_idx)


class RendererPanel(QGroupBox):
    """Configuration panel for character reference image, rig sidecar, and deformation gains."""

    config_changed = Signal()
    open_character_workspace = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Character & Renderer", parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(6)

        # Renderer Type
        layout.addWidget(QLabel("Renderer:"), 0, 0)
        self._renderer_combo = QComboBox()
        self._renderer_combo.addItem("Passthrough (Camera Frames)", "passthrough")
        self._renderer_combo.addItem("Rig-Warp Character", "rig")
        self._renderer_combo.currentIndexChanged.connect(self._on_renderer_changed)
        layout.addWidget(self._renderer_combo, 0, 1, 1, 2)

        # Character Image
        self._lbl_char = QLabel("Character Image:")
        layout.addWidget(self._lbl_char, 1, 0)

        self._char_edit = QLineEdit()
        self._char_edit.setPlaceholderText("Select character PNG reference...")
        self._char_edit.textChanged.connect(self._on_character_changed)
        layout.addWidget(self._char_edit, 1, 1)

        self._char_browse_btn = QPushButton("Browse...")
        self._char_browse_btn.clicked.connect(self._browse_character)
        layout.addWidget(self._char_browse_btn, 1, 2)

        # Resolved Rig Label
        self._lbl_rig_status = QLabel("Rig sidecar: Not loaded")
        self._lbl_rig_status.setProperty("secondary", True)
        layout.addWidget(self._lbl_rig_status, 2, 1, 1, 2)

        # Optional Explicit Rig File
        self._lbl_rig = QLabel("Explicit Rig:")
        layout.addWidget(self._lbl_rig, 3, 0)

        self._rig_edit = QLineEdit()
        self._rig_edit.setPlaceholderText("Optional: custom .rig.json path")
        self._rig_edit.textChanged.connect(lambda: self.config_changed.emit())
        layout.addWidget(self._rig_edit, 3, 1)

        self._rig_browse_btn = QPushButton("Browse...")
        self._rig_browse_btn.clicked.connect(self._browse_rig)
        layout.addWidget(self._rig_browse_btn, 3, 2)

        # Expression Gain
        layout.addWidget(QLabel("Expression Gain:"), 4, 0)
        exp_layout = QHBoxLayout()
        self._exp_slider = QSlider(Qt.Horizontal)
        self._exp_slider.setRange(0, 500)
        self._exp_slider.setValue(100)

        self._exp_spin = QDoubleSpinBox()
        self._exp_spin.setRange(0.0, 5.0)
        self._exp_spin.setSingleStep(0.1)
        self._exp_spin.setValue(1.0)

        self._exp_slider.valueChanged.connect(lambda val: self._exp_spin.setValue(val / 100.0))
        self._exp_spin.valueChanged.connect(lambda val: self._exp_slider.setValue(round(val * 100)))
        self._exp_spin.valueChanged.connect(lambda: self.config_changed.emit())

        exp_layout.addWidget(self._exp_slider, 1)
        exp_layout.addWidget(self._exp_spin)
        layout.addLayout(exp_layout, 4, 1, 1, 2)

        # Head Gain
        layout.addWidget(QLabel("Head Gain:"), 5, 0)
        head_layout = QHBoxLayout()
        self._head_slider = QSlider(Qt.Horizontal)
        self._head_slider.setRange(0, 500)
        self._head_slider.setValue(100)

        self._head_spin = QDoubleSpinBox()
        self._head_spin.setRange(0.0, 5.0)
        self._head_spin.setSingleStep(0.1)
        self._head_spin.setValue(1.0)

        self._head_slider.valueChanged.connect(lambda val: self._head_spin.setValue(val / 100.0))
        self._head_spin.valueChanged.connect(lambda val: self._head_slider.setValue(round(val * 100)))
        self._head_spin.valueChanged.connect(lambda: self.config_changed.emit())

        head_layout.addWidget(self._head_slider, 1)
        head_layout.addWidget(self._head_spin)
        layout.addLayout(head_layout, 5, 1, 1, 2)

        # Actions row (Reset Gains & Derive Rig Studio)
        btn_layout = QHBoxLayout()
        self._reset_gains_btn = QPushButton("Reset Gains")
        self._reset_gains_btn.clicked.connect(self._reset_gains)
        btn_layout.addWidget(self._reset_gains_btn)

        self._derive_studio_btn = QPushButton("Character & Rig Studio →")
        self._derive_studio_btn.clicked.connect(lambda: self.open_character_workspace.emit())
        btn_layout.addWidget(self._derive_studio_btn)
        layout.addLayout(btn_layout, 6, 1, 1, 2)

        self._on_renderer_changed()

    def _on_renderer_changed(self) -> None:
        is_rig = self._renderer_combo.currentData() == "rig"
        self._lbl_char.setEnabled(is_rig)
        self._char_edit.setEnabled(is_rig)
        self._char_browse_btn.setEnabled(is_rig)
        self._lbl_rig.setEnabled(is_rig)
        self._rig_edit.setEnabled(is_rig)
        self._rig_browse_btn.setEnabled(is_rig)
        self._exp_slider.setEnabled(is_rig)
        self._exp_spin.setEnabled(is_rig)
        self._head_slider.setEnabled(is_rig)
        self._head_spin.setEnabled(is_rig)
        self._reset_gains_btn.setEnabled(is_rig)
        self._derive_studio_btn.setEnabled(is_rig)
        self._on_character_changed()
        self.config_changed.emit()

    def _on_character_changed(self) -> None:
        char_str = self._char_edit.text().strip()
        if not char_str:
            self._lbl_rig_status.setText("Rig sidecar: Not selected")
            self._lbl_rig_status.setStyleSheet("color: #a1a1aa;")
            return

        char_path = Path(char_str)
        if not char_path.is_file():
            self._lbl_rig_status.setText("Character image not found")
            self._lbl_rig_status.setStyleSheet("color: #ef4444;")
            return

        def_rig = default_rig_path(char_path)
        if def_rig.is_file():
            self._lbl_rig_status.setText(f"Using default rig: {def_rig.name}")
            self._lbl_rig_status.setStyleSheet("color: #10b981;")
        else:
            self._lbl_rig_status.setText(f"No rig found ({def_rig.name}). Derive in Studio.")
            self._lbl_rig_status.setStyleSheet("color: #f59e0b;")

        self.config_changed.emit()

    def _browse_character(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Character Reference Image",
            str(Path.home()),
            "Image Files (*.png *.jpg *.jpeg *.webp);;All Files (*)",
        )
        if file_path:
            self._char_edit.setText(file_path)

    def _browse_rig(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Rig Sidecar",
            str(Path.home()),
            "JSON Rig Files (*.json);;All Files (*)",
        )
        if file_path:
            self._rig_edit.setText(file_path)

    def _reset_gains(self) -> None:
        self._exp_spin.setValue(1.0)
        self._head_spin.setValue(1.0)

    def apply_to_config(self, cfg: SessionConfig) -> None:
        cfg.renderer_type = self._renderer_combo.currentData()
        c_str = self._char_edit.text().strip()
        cfg.character_path = Path(c_str) if c_str else None
        r_str = self._rig_edit.text().strip()
        cfg.rig_path = Path(r_str) if r_str else None
        cfg.expression_gain = self._exp_spin.value()
        cfg.head_gain = self._head_spin.value()

    def load_from_config(self, cfg: SessionConfig) -> None:
        idx = self._renderer_combo.findData(cfg.renderer_type)
        if idx >= 0:
            self._renderer_combo.setCurrentIndex(idx)
        self._char_edit.setText(str(cfg.character_path) if cfg.character_path else "")
        self._rig_edit.setText(str(cfg.rig_path) if cfg.rig_path else "")
        self._exp_spin.setValue(cfg.expression_gain)
        self._head_spin.setValue(cfg.head_gain)


class OutputsPanel(QGroupBox):
    """Configuration panel for portable .cpc takes, rendered MP4 video, and Virtual Camera."""

    config_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Output Routing", parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(6)

        # 1. Performance Recording (.cpc)
        self._rec_cpc_check = QCheckBox("Record Performance Take (.cpc)")
        self._rec_cpc_check.toggled.connect(self._on_cpc_toggled)
        layout.addWidget(self._rec_cpc_check, 0, 0, 1, 3)

        self._cpc_path_edit = QLineEdit()
        self._cpc_path_edit.setPlaceholderText("Destination file path (e.g. takes/take_01.cpc)")
        self._cpc_path_edit.setEnabled(False)
        self._cpc_path_edit.textChanged.connect(lambda: self.config_changed.emit())
        layout.addWidget(self._cpc_path_edit, 1, 0, 1, 2)

        self._cpc_browse_btn = QPushButton("Browse...")
        self._cpc_browse_btn.setEnabled(False)
        self._cpc_browse_btn.clicked.connect(self._browse_cpc)
        layout.addWidget(self._cpc_browse_btn, 1, 2)

        self._cpc_hint = QLabel("Performance captures store facial landmarks & blendshapes, not camera pixels.")
        self._cpc_hint.setProperty("secondary", True)
        self._cpc_hint.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        layout.addWidget(self._cpc_hint, 2, 0, 1, 3)

        # Separator line
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet("color: #27272a;")
        layout.addWidget(sep1, 3, 0, 1, 3)

        # 2. Rendered Video Recording (.mp4)
        self._rec_video_check = QCheckBox("Record Rendered Preview (.mp4)")
        self._rec_video_check.toggled.connect(self._on_video_toggled)
        layout.addWidget(self._rec_video_check, 4, 0, 1, 3)

        self._video_path_edit = QLineEdit()
        self._video_path_edit.setPlaceholderText("Destination file path (e.g. captures/render.mp4)")
        self._video_path_edit.setEnabled(False)
        self._video_path_edit.textChanged.connect(lambda: self.config_changed.emit())
        layout.addWidget(self._video_path_edit, 5, 0, 1, 2)

        self._video_browse_btn = QPushButton("Browse...")
        self._video_browse_btn.setEnabled(False)
        self._video_browse_btn.clicked.connect(self._browse_mp4)
        layout.addWidget(self._video_browse_btn, 5, 2)

        # Separator line
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("color: #27272a;")
        layout.addWidget(sep2, 6, 0, 1, 3)

        # 3. Virtual Camera
        self._vcam_check = QCheckBox("Publish to Virtual Camera (OBS)")
        self._vcam_check.toggled.connect(self._on_vcam_toggled)
        layout.addWidget(self._vcam_check, 7, 0)

        self._vcam_size_combo = QComboBox()
        self._vcam_size_combo.addItem("1280x720 (HD Standard)", "1280x720")
        self._vcam_size_combo.addItem("1920x1080 (Full HD)", "1920x1080")
        self._vcam_size_combo.addItem("640x480 (SD 4:3)", "640x480")
        self._vcam_size_combo.addItem("1280x960 (HD 4:3)", "1280x960")
        self._vcam_size_combo.setEnabled(False)
        self._vcam_size_combo.currentIndexChanged.connect(lambda: self.config_changed.emit())
        layout.addWidget(self._vcam_size_combo, 7, 1, 1, 2)

        self._vcam_hint = QLabel("Broadcasts rendered character frames to Discord, Zoom, or OBS via virtual cam.")
        self._vcam_hint.setProperty("secondary", True)
        self._vcam_hint.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        layout.addWidget(self._vcam_hint, 8, 0, 1, 3)

    def _on_cpc_toggled(self, checked: bool) -> None:
        self._cpc_path_edit.setEnabled(checked)
        self._cpc_browse_btn.setEnabled(checked)
        self.config_changed.emit()

    def _on_video_toggled(self, checked: bool) -> None:
        self._video_path_edit.setEnabled(checked)
        self._video_browse_btn.setEnabled(checked)
        self.config_changed.emit()

    def _on_vcam_toggled(self, checked: bool) -> None:
        self._vcam_size_combo.setEnabled(checked)
        self.config_changed.emit()

    def _browse_cpc(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Choose Performance Capture Destination",
            str(Path.home() / "take.cpc"),
            "CPC Takes (*.cpc);;All Files (*)",
        )
        if file_path:
            if not file_path.endswith(".cpc"):
                file_path += ".cpc"
            self._cpc_path_edit.setText(file_path)

    def _browse_mp4(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Choose Rendered Video Destination",
            str(Path.home() / "output.mp4"),
            "MP4 Video (*.mp4);;All Files (*)",
        )
        if file_path:
            if not file_path.endswith(".mp4"):
                file_path += ".mp4"
            self._video_path_edit.setText(file_path)

    def apply_to_config(self, cfg: SessionConfig) -> None:
        if self._rec_cpc_check.isChecked() and self._cpc_path_edit.text().strip():
            cfg.record_performance_path = Path(self._cpc_path_edit.text().strip())
        else:
            cfg.record_performance_path = None

        if self._rec_video_check.isChecked() and self._video_path_edit.text().strip():
            cfg.record_video_path = Path(self._video_path_edit.text().strip())
        else:
            cfg.record_video_path = None

        cfg.virtual_camera = self._vcam_check.isChecked()
        size_str = self._vcam_size_combo.currentData() or "1280x720"
        try:
            parts = size_str.lower().split("x", 1)
            cfg.vcam_size = (int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            cfg.vcam_size = (1280, 720)

    def load_from_config(self, cfg: SessionConfig) -> None:
        has_cpc = cfg.record_performance_path is not None
        self._rec_cpc_check.setChecked(has_cpc)
        self._cpc_path_edit.setText(str(cfg.record_performance_path) if has_cpc else "")

        has_vid = cfg.record_video_path is not None
        self._rec_video_check.setChecked(has_vid)
        self._video_path_edit.setText(str(cfg.record_video_path) if has_vid else "")

        self._vcam_check.setChecked(cfg.virtual_camera)
        v_size_str = f"{cfg.vcam_size[0]}x{cfg.vcam_size[1]}"
        idx = self._vcam_size_combo.findData(v_size_str)
        if idx >= 0:
            self._vcam_size_combo.setCurrentIndex(idx)


class AdvancedPanel(QGroupBox):
    """Collapsible panel for advanced session options."""

    config_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Advanced Controls", parent)
        self.setCheckable(True)
        self.setChecked(False)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(6)

        layout.addWidget(QLabel("Stop after N frames:"), 0, 0)
        self._frames_spin = QSpinBox()
        self._frames_spin.setRange(0, 1_000_000)
        self._frames_spin.setSpecialValueText("Unlimited (0)")
        self._frames_spin.setValue(0)
        self._frames_spin.valueChanged.connect(lambda: self.config_changed.emit())
        layout.addWidget(self._frames_spin, 0, 1)

        self._preview_check = QCheckBox("Show Live Preview Stream")
        self._preview_check.setChecked(True)
        self._preview_check.toggled.connect(lambda: self.config_changed.emit())
        layout.addWidget(self._preview_check, 1, 0, 1, 2)

    def apply_to_config(self, cfg: SessionConfig) -> None:
        cfg.frames = self._frames_spin.value()
        cfg.no_window = not self._preview_check.isChecked()

    def load_from_config(self, cfg: SessionConfig) -> None:
        self._frames_spin.setValue(cfg.frames)
        self._preview_check.setChecked(not cfg.no_window)
