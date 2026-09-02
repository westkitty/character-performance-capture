from __future__ import annotations

import shutil
from pathlib import Path

import cv2
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
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
from cpc.ui.settings import AppSettings, generate_timestamped_filename


class SourcePanel(QGroupBox):
    """Configuration panel for Camera vs Video frame source with drag/drop and camera scan."""

    config_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Frame Ingest Source", parent)
        self.setAcceptDrops(True)
        self._settings = AppSettings()
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(10)

        # Source Kind Selector
        type_row = QHBoxLayout()
        type_row.setSpacing(12)
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

        cam_layout.addWidget(QLabel("Camera Device:"), 0, 0)
        self._cam_combo = QComboBox()
        self._cam_combo.addItem("Camera 0 (Default)", 0)
        self._cam_combo.currentIndexChanged.connect(lambda: self.config_changed.emit())

        self._rescan_btn = QPushButton("↻ Rescan")
        self._rescan_btn.setToolTip("Probe connected camera devices")
        self._rescan_btn.clicked.connect(self._rescan_cameras)

        cam_row = QHBoxLayout()
        cam_row.addWidget(self._cam_combo, 1)
        cam_row.addWidget(self._rescan_btn)
        cam_layout.addLayout(cam_row, 0, 1)

        # Resolution & FPS Negotiation
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

        vid_layout.addWidget(QLabel("Video File:"), 0, 0)
        self._video_edit = QLineEdit()
        self._video_edit.setPlaceholderText("Select or drop performer video (.mp4, .mov)...")
        self._video_edit.textChanged.connect(lambda: self.config_changed.emit())

        self._browse_vid_btn = QPushButton("Browse...")
        self._browse_vid_btn.clicked.connect(self._browse_video)

        self._clear_vid_btn = QPushButton("✕")
        self._clear_vid_btn.setMaximumWidth(28)
        self._clear_vid_btn.setToolTip("Clear video source and return to camera")
        self._clear_vid_btn.clicked.connect(self._clear_video)

        vid_path_row = QHBoxLayout()
        vid_path_row.addWidget(self._video_edit, 1)
        vid_path_row.addWidget(self._browse_vid_btn)
        vid_path_row.addWidget(self._clear_vid_btn)
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
        """Scan available camera indices 0..3."""
        curr_val = self._cam_combo.currentData()
        self._cam_combo.blockSignals(True)
        self._cam_combo.clear()
        
        found = 0
        for i in range(4):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                self._cam_combo.addItem(f"Camera {i}", i)
                cap.release()
                found += 1

        if found == 0:
            self._cam_combo.addItem("Camera 0 (Default)", 0)

        # Restore index if found
        idx = self._cam_combo.findData(curr_val)
        if idx >= 0:
            self._cam_combo.setCurrentIndex(idx)
        else:
            self._cam_combo.setCurrentIndex(0)
        self._cam_combo.blockSignals(False)
        self.config_changed.emit()

    def _browse_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Performer Video",
            self._settings.get_last_directory(),
            "Video Files (*.mp4 *.mov *.avi *.mkv);;All Files (*)",
        )
        if path:
            self._settings.set_last_directory(path)
            self._settings.add_recent_item("videos", path)
            self._video_edit.setText(path)

    def _clear_video(self) -> None:
        self._video_edit.clear()
        self._combo_source_type.setCurrentIndex(0)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                p = Path(url.toLocalFile())
                if p.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"}:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"}:
                self._combo_source_type.setCurrentIndex(1)
                self._video_edit.setText(str(p))
                self._settings.add_recent_item("videos", p)
                event.acceptProposedAction()
                return

    def apply_to_config(self, cfg: SessionConfig) -> None:
        if self._combo_source_type.currentIndex() == 0:
            cfg.source_type = "camera"
            cam_idx = self._cam_combo.currentData()
            cfg.camera_index = int(cam_idx) if cam_idx is not None else 0
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
            idx = self._cam_combo.findData(cfg.camera_index)
            if idx >= 0:
                self._cam_combo.setCurrentIndex(idx)
            else:
                self._cam_combo.addItem(f"Camera {cfg.camera_index}", cfg.camera_index)
                self._cam_combo.setCurrentIndex(self._cam_combo.count() - 1)

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
    """Configuration panel for Performance Tracker selection with Curated Model Library."""

    config_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Performance Tracker", parent)
        self.setAcceptDrops(True)
        self._settings = AppSettings()
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(6)

        from cpc.ui.widgets.model_selector import ModelSelectorWidget

        self.model_selector = ModelSelectorWidget(self)
        self.model_selector.model_selection_changed.connect(lambda *_: self.config_changed.emit())
        layout.addWidget(self.model_selector)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                p = Path(url.toLocalFile())
                if p.suffix.lower() == ".task":
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.suffix.lower() == ".task":
                from cpc.ui.models import get_model_registry

                reg = get_model_registry()
                try:
                    entry = reg.register_custom_model(p, copy_to_managed=True)
                    self.model_selector.select_model(entry.model_id)
                    event.acceptProposedAction()
                    return
                except (RuntimeError, ValueError, OSError, FileNotFoundError):
                    continue

    def apply_to_config(self, cfg: SessionConfig) -> None:
        mid = self.model_selector.get_selected_model_id()
        if mid == "null-tracker":
            cfg.tracker_type = "null"
            cfg.model_path = None
            cfg.tracker_delegate = "cpu"
        else:
            cfg.tracker_type = "mediapipe"
            cfg.model_path = self.model_selector.get_resolved_path()
            cfg.tracker_delegate = self.model_selector.get_selected_delegate()

    def load_from_config(self, cfg: SessionConfig) -> None:
        if cfg.tracker_type == "null":
            self.model_selector.select_model("null-tracker")
        else:
            self.model_selector.set_delegate(cfg.tracker_delegate)
            if cfg.model_path and cfg.model_path.is_file():
                # Check if it matches default resolved path
                resolved = self.model_selector.get_resolved_path()
                if resolved != cfg.model_path:
                    from cpc.ui.models import get_model_registry

                    reg = get_model_registry()
                    try:
                        entry = reg.register_custom_model(cfg.model_path, copy_to_managed=False)
                        self.model_selector.select_model(entry.model_id)
                    except (RuntimeError, ValueError, OSError, FileNotFoundError):
                        self.model_selector.select_model("mediapipe-face-landmarker")
                else:
                    self.model_selector.select_model("mediapipe-face-landmarker")
            else:
                self.model_selector.select_model("mediapipe-face-landmarker")
        self.model_selector.refresh_state()


class RendererPanel(QGroupBox):
    """Configuration panel for Character Artwork and 2D Mesh-Warp Renderer with Live Gains."""

    config_changed = Signal()
    open_character_workspace = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Character && Renderer", parent)
        self.setAcceptDrops(True)
        self._settings = AppSettings()
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
        self._char_edit.setPlaceholderText("Select or drop character PNG/JPG...")
        self._char_edit.textChanged.connect(self._on_char_path_changed)

        self._browse_char_btn = QPushButton("Browse...")
        self._browse_char_btn.clicked.connect(self._browse_character)

        self._clear_char_btn = QPushButton("✕")
        self._clear_char_btn.setMaximumWidth(28)
        self._clear_char_btn.clicked.connect(self._char_edit.clear)

        char_row = QHBoxLayout()
        char_row.addWidget(self._char_edit, 1)
        char_row.addWidget(self._browse_char_btn)
        char_row.addWidget(self._clear_char_btn)
        layout.addLayout(char_row, 1, 1)

        # Rig Definition
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

        # Expression & Head Gains with precise DoubleSpinBoxes and Reset
        self._lbl_gains = QLabel("Motion Gains:")
        layout.addWidget(self._lbl_gains, 3, 0)

        gains_widget = QWidget()
        g_layout = QVBoxLayout(gains_widget)
        g_layout.setContentsMargins(0, 0, 0, 0)
        g_layout.setSpacing(6)

        # Expression Gain
        exp_row = QHBoxLayout()
        exp_row.addWidget(QLabel("Expression:"), 0)
        self._exp_slider = QSlider(Qt.Horizontal)
        self._exp_slider.setRange(0, 300)
        self._exp_slider.setValue(100)
        self._exp_slider.valueChanged.connect(self._on_exp_slider_changed)
        exp_row.addWidget(self._exp_slider, 1)

        self._exp_spin = QDoubleSpinBox()
        self._exp_spin.setRange(0.0, 3.0)
        self._exp_spin.setSingleStep(0.05)
        self._exp_spin.setValue(1.0)
        self._exp_spin.setSuffix("x")
        self._exp_spin.valueChanged.connect(self._on_exp_spin_changed)
        exp_row.addWidget(self._exp_spin)
        g_layout.addLayout(exp_row)

        # Head Motion Gain
        head_row = QHBoxLayout()
        head_row.addWidget(QLabel("Head Motion:"), 0)
        self._head_slider = QSlider(Qt.Horizontal)
        self._head_slider.setRange(0, 300)
        self._head_slider.setValue(100)
        self._head_slider.valueChanged.connect(self._on_head_slider_changed)
        head_row.addWidget(self._head_slider, 1)

        self._head_spin = QDoubleSpinBox()
        self._head_spin.setRange(0.0, 3.0)
        self._head_spin.setSingleStep(0.05)
        self._head_spin.setValue(1.0)
        self._head_spin.setSuffix("x")
        self._head_spin.valueChanged.connect(self._on_head_spin_changed)
        head_row.addWidget(self._head_spin)

        # Reset gains button
        self._reset_gains_btn = QPushButton("↺ Reset")
        self._reset_gains_btn.setMaximumWidth(60)
        self._reset_gains_btn.setToolTip("Reset gains to default 1.0x")
        self._reset_gains_btn.clicked.connect(self._reset_gains)
        head_row.addWidget(self._reset_gains_btn)

        g_layout.addLayout(head_row)
        layout.addWidget(gains_widget, 3, 1)

        # Studio Link Button
        self._studio_btn = QPushButton("Open Character && Rig Studio →")
        self._studio_btn.clicked.connect(lambda: self.open_character_workspace.emit())
        layout.addWidget(self._studio_btn, 4, 1)

        self._update_visibility()

    def _on_exp_slider_changed(self, val: int) -> None:
        self._exp_spin.blockSignals(True)
        self._exp_spin.setValue(val / 100.0)
        self._exp_spin.blockSignals(False)
        self.config_changed.emit()

    def _on_exp_spin_changed(self, val: float) -> None:
        self._exp_slider.blockSignals(True)
        self._exp_slider.setValue(int(val * 100))
        self._exp_slider.blockSignals(False)
        self.config_changed.emit()

    def _on_head_slider_changed(self, val: int) -> None:
        self._head_spin.blockSignals(True)
        self._head_spin.setValue(val / 100.0)
        self._head_spin.blockSignals(False)
        self.config_changed.emit()

    def _on_head_spin_changed(self, val: float) -> None:
        self._head_slider.blockSignals(True)
        self._head_slider.setValue(int(val * 100))
        self._head_slider.blockSignals(False)
        self.config_changed.emit()

    def _reset_gains(self) -> None:
        self._exp_slider.setValue(100)
        self._head_slider.setValue(100)

    def _on_char_path_changed(self, text: str) -> None:
        char_path_str = text.strip()
        if char_path_str and not self._rig_edit.text().strip():
            auto_rig = Path(char_path_str).with_suffix(Path(char_path_str).suffix + ".rig.json")
            if auto_rig.is_file():
                self._rig_edit.setText(str(auto_rig))

        # Check per-character memory
        if char_path_str:
            mem = self._settings.get_character_memory(char_path_str)
            if mem:
                if mem.get("rig_path") and Path(mem["rig_path"]).is_file():
                    self._rig_edit.setText(mem["rig_path"])
                if "expression_gain" in mem:
                    self._exp_spin.setValue(float(mem["expression_gain"]))
                if "head_gain" in mem:
                    self._head_spin.setValue(float(mem["head_gain"]))

        self.config_changed.emit()

    def _on_renderer_changed(self) -> None:
        self._update_visibility()
        self.config_changed.emit()

    def _update_visibility(self) -> None:
        is_rig = (self._renderer_combo.currentIndex() == 1)
        self._lbl_char.setVisible(is_rig)
        self._char_edit.setVisible(is_rig)
        self._browse_char_btn.setVisible(is_rig)
        self._clear_char_btn.setVisible(is_rig)
        self._lbl_rig.setVisible(is_rig)
        self._rig_edit.setVisible(is_rig)
        self._browse_rig_btn.setVisible(is_rig)
        self._lbl_gains.setVisible(is_rig)
        self._exp_slider.setVisible(is_rig)
        self._exp_spin.setVisible(is_rig)
        self._head_slider.setVisible(is_rig)
        self._head_spin.setVisible(is_rig)
        self._reset_gains_btn.setVisible(is_rig)
        self._studio_btn.setVisible(is_rig)

    def _browse_character(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Character Reference Image",
            self._settings.get_last_directory(),
            "Image Files (*.png *.jpg *.jpeg *.webp);;All Files (*)",
        )
        if path:
            self._settings.set_last_directory(path)
            self._settings.add_recent_item("characters", path)
            self._char_edit.setText(path)

    def _browse_rig(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Character Rig Sidecar",
            self._settings.get_last_directory(),
            "Rig Files (*.rig.json);;All Files (*)",
        )
        if path:
            self._settings.set_last_directory(path)
            self._rig_edit.setText(path)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                p = Path(url.toLocalFile())
                if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".json"}:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                self._renderer_combo.setCurrentIndex(1)
                self._char_edit.setText(str(p))
                self._settings.add_recent_item("characters", p)
                event.acceptProposedAction()
                return
            elif p.name.endswith(".rig.json"):
                self._renderer_combo.setCurrentIndex(1)
                self._rig_edit.setText(str(p))
                event.acceptProposedAction()
                return

    def apply_to_config(self, cfg: SessionConfig) -> None:
        if self._renderer_combo.currentIndex() == 1:
            cfg.renderer_type = "rig"
            char_str = self._char_edit.text().strip()
            cfg.character_path = Path(char_str) if char_str else None
            rig_str = self._rig_edit.text().strip()
            cfg.rig_path = Path(rig_str) if rig_str else None
            cfg.expression_gain = float(self._exp_spin.value())
            cfg.head_gain = float(self._head_spin.value())

            # Save per-character memory
            if cfg.character_path:
                self._settings.set_character_memory(
                    cfg.character_path,
                    cfg.rig_path,
                    cfg.expression_gain,
                    cfg.head_gain,
                )
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
            self._exp_spin.setValue(cfg.expression_gain)
            self._head_spin.setValue(cfg.head_gain)
        else:
            self._renderer_combo.setCurrentIndex(0)
        self._update_visibility()


class OutputsPanel(QGroupBox):
    """Configuration panel for Live Output destinations with timestamp generators and disk space safety."""

    config_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Output Routing", parent)
        self._settings = AppSettings()
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
        cpc_row.setSpacing(6)
        self._cpc_edit = QLineEdit()
        self._cpc_edit.setPlaceholderText("Destination file path (e.g. takes/take_01.cpc)...")
        self._cpc_edit.textChanged.connect(lambda: self.config_changed.emit())

        self._cpc_gen_btn = QPushButton("⚡ Auto Name")
        self._cpc_gen_btn.setToolTip("Generate collision-safe timestamped take name")
        self._cpc_gen_btn.clicked.connect(self._generate_cpc_filename)

        self._cpc_browse_btn = QPushButton("Browse...")
        self._cpc_browse_btn.clicked.connect(self._browse_cpc)

        cpc_row.addWidget(self._cpc_edit, 1)
        cpc_row.addWidget(self._cpc_gen_btn)
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
        mp4_row.setSpacing(6)
        self._mp4_edit = QLineEdit()
        self._mp4_edit.setPlaceholderText("Destination file path (e.g. captures/render_01.mp4)...")
        self._mp4_edit.textChanged.connect(lambda: self.config_changed.emit())

        self._mp4_gen_btn = QPushButton("⚡ Auto Name")
        self._mp4_gen_btn.setToolTip("Generate collision-safe timestamped render name")
        self._mp4_gen_btn.clicked.connect(self._generate_mp4_filename)

        self._mp4_browse_btn = QPushButton("Browse...")
        self._mp4_browse_btn.clicked.connect(self._browse_mp4)

        mp4_row.addWidget(self._mp4_edit, 1)
        mp4_row.addWidget(self._mp4_gen_btn)
        mp4_row.addWidget(self._mp4_browse_btn)
        self._mp4_widget.setVisible(False)
        layout.addWidget(self._mp4_widget)

        # 3. Virtual Camera Sink
        self._vcam_checkbox = QCheckBox("Publish to Virtual Camera (OBS)")
        self._vcam_checkbox.stateChanged.connect(self._on_vcam_toggled)
        layout.addWidget(self._vcam_checkbox)

        self._vcam_widget = QWidget()
        vcam_row = QHBoxLayout(self._vcam_widget)
        vcam_row.setContentsMargins(0, 0, 0, 0)
        vcam_row.addWidget(QLabel("Resolution:"), 0)
        self._vcam_size_combo = QComboBox()
        self._vcam_size_combo.addItems(["1280x720 (720p - OBS Default)", "1920x1080 (1080p)", "640x480 (VGA)"])
        self._vcam_size_combo.currentIndexChanged.connect(lambda: self.config_changed.emit())
        vcam_row.addWidget(self._vcam_size_combo, 1)
        self._vcam_widget.setVisible(False)
        layout.addWidget(self._vcam_widget)

        # Output folder tools & disk space info
        tools_row = QHBoxLayout()
        self._reveal_takes_btn = QPushButton("📁 Reveal Output Folder")
        self._reveal_takes_btn.clicked.connect(self._reveal_output_folder)
        tools_row.addWidget(self._reveal_takes_btn)

        self._lbl_disk = QLabel(self._get_disk_space_str())
        self._lbl_disk.setStyleSheet("color: #94a3b8; font-size: 11px;")
        tools_row.addWidget(self._lbl_disk, 1, Qt.AlignRight)
        layout.addLayout(tools_row)

    def _get_disk_space_str(self) -> str:
        try:
            _, _, free = shutil.disk_usage(Path.cwd())
            free_gb = free / (1024.0 ** 3)
            return f"Free Disk Space: {free_gb:.1f} GB"
        except (OSError, ValueError):
            return ""

    def _generate_cpc_filename(self) -> None:
        target_dir = Path(self._settings.get_default_output_directory())
        p = generate_timestamped_filename("take", "cpc", target_dir)
        self._cpc_edit.setText(str(p))

    def _generate_mp4_filename(self) -> None:
        target_dir = Path(self._settings.get_default_output_directory())
        p = generate_timestamped_filename("render", "mp4", target_dir)
        self._mp4_edit.setText(str(p))

    def _reveal_output_folder(self) -> None:
        folder = Path(self._settings.get_default_output_directory())
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(f"file://{folder.resolve()}")

    def _on_cpc_toggled(self, state: int) -> None:
        is_checked = (state == Qt.Checked)
        self._cpc_widget.setVisible(is_checked)
        if is_checked and not self._cpc_edit.text().strip():
            self._generate_cpc_filename()
        self.config_changed.emit()

    def _on_mp4_toggled(self, state: int) -> None:
        is_checked = (state == Qt.Checked)
        self._mp4_widget.setVisible(is_checked)
        if is_checked and not self._mp4_edit.text().strip():
            self._generate_mp4_filename()
        self.config_changed.emit()

    def _on_vcam_toggled(self, state: int) -> None:
        self._vcam_widget.setVisible(state == Qt.Checked)
        self.config_changed.emit()

    def _browse_cpc(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Performance Capture Take",
            self._settings.get_last_directory(),
            "CPC Captures (*.cpc);;All Files (*)",
        )
        if path:
            if not path.endswith(".cpc"):
                path += ".cpc"
            self._settings.set_last_directory(path)
            self._cpc_edit.setText(path)

    def _browse_mp4(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Rendered Video",
            self._settings.get_last_directory(),
            "MP4 Video (*.mp4);;All Files (*)",
        )
        if path:
            if not path.endswith(".mp4"):
                path += ".mp4"
            self._settings.set_last_directory(path)
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
    """Configuration panel for Advanced capture controls, countdowns, and session limits."""

    config_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("Session Limits && Options", parent)
        self._settings = AppSettings()
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(8)

        # Countdown Timer Option
        layout.addWidget(QLabel("Countdown:"), 0, 0)
        self._countdown_combo = QComboBox()
        self._countdown_combo.addItems(["Immediate (No countdown)", "3 Seconds Countdown", "5 Seconds Countdown"])
        self._countdown_combo.currentIndexChanged.connect(self._on_countdown_changed)
        layout.addWidget(self._countdown_combo, 0, 1)

        # Stop After Frame Limit
        layout.addWidget(QLabel("Stop After:"), 1, 0)
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
        layout.addWidget(self._frames_combo, 1, 1)

        self._custom_frames_spin = QSpinBox()
        self._custom_frames_spin.setRange(1, 1000000)
        self._custom_frames_spin.setValue(150)
        self._custom_frames_spin.valueChanged.connect(lambda: self.config_changed.emit())
        self._custom_frames_spin.setVisible(False)
        layout.addWidget(self._custom_frames_spin, 2, 1)

        # Live Preview Display Toggle
        self._preview_checkbox = QCheckBox("Show Live Character Preview Canvas")
        self._preview_checkbox.setChecked(True)
        self._preview_checkbox.stateChanged.connect(lambda: self.config_changed.emit())
        layout.addWidget(self._preview_checkbox, 3, 0, 1, 2)

        # Restore countdown setting
        cd = self._settings.get_countdown_seconds()
        if cd == 3:
            self._countdown_combo.setCurrentIndex(1)
        elif cd == 5:
            self._countdown_combo.setCurrentIndex(2)
        else:
            self._countdown_combo.setCurrentIndex(0)

    def _on_countdown_changed(self, idx: int) -> None:
        if idx == 1:
            self._settings.set_countdown_seconds(3)
        elif idx == 2:
            self._settings.set_countdown_seconds(5)
        else:
            self._settings.set_countdown_seconds(0)
        self.config_changed.emit()

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
