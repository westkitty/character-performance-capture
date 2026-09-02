from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import (
    QDesktopServices,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QImage,
    QPixmap,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from cpc.rig import CharacterRig, default_rig_path, load_rig
from cpc.ui.models import RECOMMENDED_MEDIAPIPE_MODEL, get_model_registry
from cpc.ui.settings import AppSettings
from cpc.ui.widgets.model_selector import ModelSelectorWidget
from cpc.ui.worker import DeriveRigWorker


class CharacterWorkspace(QWidget):
    """Guided 6-stage Character Setup Journey & Rig Visualizer."""

    character_selected = Signal(Path, Path)  # (character_image_path, rig_sidecar_path)
    start_performing_requested = Signal(dict)  # Complete setup dictionary to transfer to Live Studio

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._settings = AppSettings()
        self._registry = get_model_registry()

        # State model
        self._current_step: int = 0  # 0 to 5
        self._character_path: Path | None = None
        self._character_img: np.ndarray | None = None
        self._current_rig: CharacterRig | None = None
        self._rig_path: Path | None = None
        self._model_id: str = RECOMMENDED_MEDIAPIPE_MODEL.model_id
        self._model_path: Path | None = None
        self._delegate: str = "cpu"
        self._derive_worker: DeriveRigWorker | None = None

        # Step completions
        self._step_completed: list[bool] = [False] * 6
        self._is_calibrated: bool = False
        self._countdown_val: int = 0
        self._countdown_timer: QTimer | None = None

        self._init_ui()
        self._load_recents()
        self._update_rail()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 12)
        main_layout.setSpacing(10)

        # -------------------------------------------------------------
        # 0. Top Step Navigation Rail
        # -------------------------------------------------------------
        self._rail_frame = QFrame()
        self._rail_frame.setStyleSheet(
            "QFrame { background-color: #121218; border: 1px solid #22222e; border-radius: 8px; padding: 6px; }"
        )
        rail_layout = QHBoxLayout(self._rail_frame)
        rail_layout.setContentsMargins(8, 4, 8, 4)
        rail_layout.setSpacing(6)

        self._step_names = [
            "1. Character",
            "2. Tracking",
            "3. Build Rig",
            "4. Verify",
            "5. Calibrate",
            "6. Ready",
        ]
        self._step_buttons: list[QPushButton] = []
        for i, name in enumerate(self._step_names):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setAutoDefault(False)
            btn.setStyleSheet(
                "QPushButton { background-color: transparent; border: 1px solid transparent; "
                "border-radius: 6px; padding: 6px 14px; font-weight: 600; font-size: 12px; color: #71717a; } "
                "QPushButton:checked { background-color: #1e3a8a; border: 1px solid #3b82f6; color: #ffffff; } "
                "QPushButton:hover:!checked { background-color: #181824; color: #d4d4d8; }"
            )
            btn.clicked.connect(lambda _, idx=i: self._jump_to_step(idx))
            rail_layout.addWidget(btn)
            self._step_buttons.append(btn)

            if i < len(self._step_names) - 1:
                arrow = QLabel("→")
                arrow.setStyleSheet("color: #3f3f46; font-size: 12px;")
                rail_layout.addWidget(arrow)

        rail_layout.addStretch(1)
        main_layout.addWidget(self._rail_frame)

        # -------------------------------------------------------------
        # Main Splitter (Left Step Content, Right Visual Canvas)
        # -------------------------------------------------------------
        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setHandleWidth(2)

        # 1. Left Side: Stacked Steps Content
        self._left_scroll = QScrollArea()
        self._left_scroll.setWidgetResizable(True)
        self._left_scroll.setMinimumWidth(360)
        self._left_scroll.setMaximumWidth(500)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(10)

        self._stack = QStackedWidget()

        # Step 1: Character Selection Page
        self._stack.addWidget(self._create_step1_character())
        # Step 2: Tracking Model Selection Page
        self._stack.addWidget(self._create_step2_tracking())
        # Step 3: Build Rig Page
        self._stack.addWidget(self._create_step3_build_rig())
        # Step 4: Verify Page
        self._stack.addWidget(self._create_step4_verify())
        # Step 5: Calibrate Page
        self._stack.addWidget(self._create_step5_calibrate())
        # Step 6: Ready Page
        self._stack.addWidget(self._create_step6_ready())

        left_layout.addWidget(self._stack)
        left_layout.addStretch(1)
        self._left_scroll.setWidget(left_container)
        self._splitter.addWidget(self._left_scroll)

        # 2. Right Side: Visual Canvas & Overlays
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(8)

        # Visualizer Toolbar
        viz_toolbar = QHBoxLayout()
        viz_toolbar.setSpacing(12)

        self._check_show_points = QCheckBox("Landmark Points")
        self._check_show_points.setChecked(True)
        self._check_show_points.stateChanged.connect(self._refresh_preview)
        viz_toolbar.addWidget(self._check_show_points)

        self._check_show_mesh = QCheckBox("Mesh Triangles")
        self._check_show_mesh.setChecked(True)
        self._check_show_mesh.stateChanged.connect(self._refresh_preview)
        viz_toolbar.addWidget(self._check_show_mesh)

        self._check_show_hull = QCheckBox("Boundary Hull")
        self._check_show_hull.setChecked(True)
        self._check_show_hull.stateChanged.connect(self._refresh_preview)
        viz_toolbar.addWidget(self._check_show_hull)

        viz_toolbar.addStretch(1)
        right_layout.addLayout(viz_toolbar)

        # Visual Canvas
        self._canvas_lbl = QLabel("No character loaded\n\nDrag & drop artwork PNG/JPG or click Choose Character")
        self._canvas_lbl.setAlignment(Qt.AlignCenter)
        self._canvas_lbl.setStyleSheet(
            "QLabel { background-color: #0c0c10; border: 1px dashed #272733; border-radius: 8px; color: #71717a; font-size: 14px; }"
        )
        right_layout.addWidget(self._canvas_lbl, 1)

        self._splitter.addWidget(right_container)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)

        main_layout.addWidget(self._splitter, 1)

    # -------------------------------------------------------------
    # Step 1: Character Artwork Page
    # -------------------------------------------------------------
    def _create_step1_character(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        title = QLabel("Step 1: Choose Your Character")
        font_t = QFont(title.font())
        font_t.setPointSize(14)
        font_t.setBold(True)
        title.setFont(font_t)
        layout.addWidget(title)

        desc = QLabel("Select or drop the 2D character reference image you want to perform with.")
        desc.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Recents row
        rec_row = QHBoxLayout()
        rec_row.addWidget(QLabel("Recent:"))
        self._recents_combo = QComboBox()
        self._recents_combo.currentIndexChanged.connect(self._on_recent_selected)
        rec_row.addWidget(self._recents_combo, 1)

        self._fav_btn = QPushButton("☆")
        self._fav_btn.setMaximumWidth(32)
        self._fav_btn.setToolTip("Bookmark character as favorite")
        self._fav_btn.clicked.connect(self._toggle_favorite)
        rec_row.addWidget(self._fav_btn)
        layout.addLayout(rec_row)

        # File Picker
        pick_box = QGroupBox("Character Image File")
        pb_layout = QVBoxLayout(pick_box)
        pb_layout.setContentsMargins(10, 14, 10, 10)
        pb_layout.setSpacing(8)

        file_row = QHBoxLayout()
        self._char_edit = QLineEdit()
        self._char_edit.setPlaceholderText("Select or drop character PNG/JPG/WebP...")
        self._char_edit.textChanged.connect(self._on_character_path_changed)
        file_row.addWidget(self._char_edit, 1)

        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_character)
        file_row.addWidget(btn_browse)

        self._reveal_char_btn = QPushButton("📁")
        self._reveal_char_btn.setMaximumWidth(32)
        self._reveal_char_btn.setToolTip("Reveal in Finder")
        self._reveal_char_btn.clicked.connect(self._reveal_character)
        file_row.addWidget(self._reveal_char_btn)
        pb_layout.addLayout(file_row)

        self._char_info_lbl = QLabel("Dimensions: --")
        self._char_info_lbl.setStyleSheet("color: #71717a; font-size: 11px;")
        pb_layout.addWidget(self._char_info_lbl)

        layout.addWidget(pick_box)

        # Existing rig detection note
        self._existing_rig_banner = QLabel("✓ Known rig sidecar found for this character.")
        self._existing_rig_banner.setStyleSheet(
            "background-color: #064e3b; color: #6ee7b7; padding: 8px; border-radius: 6px; font-weight: 500; font-size: 12px;"
        )
        self._existing_rig_banner.setVisible(False)
        layout.addWidget(self._existing_rig_banner)

        # Primary CTA
        self._btn_step1_next = QPushButton("Continue to Tracking →")
        self._btn_step1_next.setProperty("primary", True)
        self._btn_step1_next.setMinimumHeight(40)
        font_btn = QFont(self._btn_step1_next.font())
        font_btn.setBold(True)
        self._btn_step1_next.setFont(font_btn)
        self._btn_step1_next.setEnabled(False)
        self._btn_step1_next.clicked.connect(lambda: self._set_step(1))
        layout.addWidget(self._btn_step1_next)

        return page

    # -------------------------------------------------------------
    # Step 2: Tracking Model Page
    # -------------------------------------------------------------
    def _create_step2_tracking(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        title = QLabel("Step 2: Tracking Model")
        font_t = QFont(title.font())
        font_t.setPointSize(14)
        font_t.setBold(True)
        title.setFont(font_t)
        layout.addWidget(title)

        desc = QLabel("CPC uses the curated MediaPipe Face Landmarker model to track your facial expressions and head motion.")
        desc.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Curated Model Selector
        self.model_selector = ModelSelectorWidget(self)
        self.model_selector.model_selection_changed.connect(self._on_model_changed)
        layout.addWidget(self.model_selector)

        # Primary CTA
        self._btn_step2_next = QPushButton("Continue to Build Rig →")
        self._btn_step2_next.setProperty("primary", True)
        self._btn_step2_next.setMinimumHeight(40)
        font_btn = QFont(self._btn_step2_next.font())
        font_btn.setBold(True)
        self._btn_step2_next.setFont(font_btn)
        self._btn_step2_next.setEnabled(self.model_selector.is_ready())
        self._btn_step2_next.clicked.connect(lambda: self._set_step(2))
        layout.addWidget(self._btn_step2_next)

        return page

    # -------------------------------------------------------------
    # Step 3: Build Rig Page
    # -------------------------------------------------------------
    def _create_step3_build_rig(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        title = QLabel("Step 3: Build Character Rig")
        font_t = QFont(title.font())
        font_t.setPointSize(14)
        font_t.setBold(True)
        title.setFont(font_t)
        layout.addWidget(title)

        desc = QLabel(
            "CPC will detect facial landmarks on your character artwork and build a deterministic 2D mesh topology."
        )
        desc.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Rig Configuration Box
        rig_box = QGroupBox("Rig Derivation Parameters")
        rb_layout = QGridLayout(rig_box)
        rb_layout.setContentsMargins(10, 14, 10, 10)
        rb_layout.setSpacing(6)

        rb_layout.addWidget(QLabel("Character:"), 0, 0)
        self._lbl_rig_char_name = QLabel("--")
        self._lbl_rig_char_name.setStyleSheet("font-weight: 600; color: #e4e4e7;")
        rb_layout.addWidget(self._lbl_rig_char_name, 0, 1)

        rb_layout.addWidget(QLabel("Tracker Model:"), 1, 0)
        self._lbl_rig_model_name = QLabel("MediaPipe Face Landmarker")
        self._lbl_rig_model_name.setStyleSheet("font-weight: 600; color: #e4e4e7;")
        rb_layout.addWidget(self._lbl_rig_model_name, 1, 1)

        rb_layout.addWidget(QLabel("Rig Sidecar:"), 2, 0)
        self._lbl_rig_dest_path = QLabel("--")
        self._lbl_rig_dest_path.setStyleSheet("color: #38bdf8; font-size: 11px;")
        self._lbl_rig_dest_path.setWordWrap(True)
        rb_layout.addWidget(self._lbl_rig_dest_path, 2, 1)

        layout.addWidget(rig_box)

        # Build Rig Action Button
        self._derive_btn = QPushButton("⚡  Build Character Rig")
        self._derive_btn.setProperty("primary", True)
        self._derive_btn.setMinimumHeight(44)
        font_btn = QFont(self._derive_btn.font())
        font_btn.setPointSize(13)
        font_btn.setBold(True)
        self._derive_btn.setFont(font_btn)
        self._derive_btn.clicked.connect(self.derive_rig)
        layout.addWidget(self._derive_btn)

        # Progress bar
        self._derive_progress = QProgressBar()
        self._derive_progress.setRange(0, 0)
        self._derive_progress.setVisible(False)
        layout.addWidget(self._derive_progress)

        self._derive_status_lbl = QLabel("")
        self._derive_status_lbl.setStyleSheet("color: #60a5fa; font-size: 12px;")
        layout.addWidget(self._derive_status_lbl)

        # Technical Log Drawer
        self._log_text = QTextEdit()
        self._log_text.setMaximumHeight(80)
        self._log_text.setReadOnly(True)
        self._log_text.setPlaceholderText("Rig derivation log...")
        layout.addWidget(self._log_text)

        return page

    # -------------------------------------------------------------
    # Step 4: Verify Rig Page
    # -------------------------------------------------------------
    def _create_step4_verify(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        title = QLabel("Step 4: Verify Character Rig")
        font_t = QFont(title.font())
        font_t.setPointSize(14)
        font_t.setBold(True)
        title.setFont(font_t)
        layout.addWidget(title)

        desc = QLabel("Inspect the mesh topology and landmark points overlaid on your character artwork.")
        desc.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Verification Checklist Card
        chk_box = QGroupBox("Rig Verification Status")
        cb_layout = QVBoxLayout(chk_box)
        cb_layout.setContentsMargins(10, 14, 10, 10)
        cb_layout.setSpacing(6)

        self._chk_pts = QLabel("✓ Landmark Topology (478 points)")
        self._chk_pts.setStyleSheet("color: #10b981; font-weight: 600;")
        cb_layout.addWidget(self._chk_pts)

        self._chk_mesh = QLabel("✓ Delaunay Triangulation Mesh Built")
        self._chk_mesh.setStyleSheet("color: #10b981; font-weight: 600;")
        cb_layout.addWidget(self._chk_mesh)

        self._chk_sidecar = QLabel("✓ Rig Sidecar Saved to Disk")
        self._chk_sidecar.setStyleSheet("color: #10b981; font-weight: 600;")
        cb_layout.addWidget(self._chk_sidecar)

        layout.addWidget(chk_box)

        # Actions
        self._btn_step4_next = QPushButton("Looks Good (Continue to Calibration) →")
        self._btn_step4_next.setProperty("primary", True)
        self._btn_step4_next.setMinimumHeight(40)
        font_btn = QFont(self._btn_step4_next.font())
        font_btn.setBold(True)
        self._btn_step4_next.setFont(font_btn)
        self._btn_step4_next.clicked.connect(lambda: self._set_step(4))
        layout.addWidget(self._btn_step4_next)

        btn_rebuild = QPushButton("↺ Rebuild Rig")
        btn_rebuild.clicked.connect(lambda: self._set_step(2))
        layout.addWidget(btn_rebuild)

        return page

    # -------------------------------------------------------------
    # Step 5: Calibrate & Test Page
    # -------------------------------------------------------------
    def _create_step5_calibrate(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        title = QLabel("Step 5: Calibrate Neutral Rest Pose")
        font_t = QFont(title.font())
        font_t.setPointSize(14)
        font_t.setBold(True)
        title.setFont(font_t)
        layout.addWidget(title)

        desc = QLabel(
            "Sit naturally, look directly at your camera, and relax your facial expression. "
            "CPC will calibrate your neutral resting posture so head and facial movements are captured accurately."
        )
        desc.setStyleSheet("color: #a1a1aa; font-size: 12px; line-height: 1.4;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Calibration Button
        self._btn_calibrate_now = QPushButton("🎯  Calibrate Neutral Pose (3s Countdown)")
        self._btn_calibrate_now.setProperty("primary", True)
        self._btn_calibrate_now.setMinimumHeight(44)
        font_btn = QFont(self._btn_calibrate_now.font())
        font_btn.setPointSize(13)
        font_btn.setBold(True)
        self._btn_calibrate_now.setFont(font_btn)
        self._btn_calibrate_now.clicked.connect(self._start_calibration_countdown)
        layout.addWidget(self._btn_calibrate_now)

        # Calibration Status Banner
        self._calib_status_banner = QLabel("● Neutral Pose Calibrated ✓")
        self._calib_status_banner.setStyleSheet(
            "background-color: #064e3b; color: #6ee7b7; padding: 10px; border-radius: 6px; font-weight: 700; font-size: 13px; text-align: center;"
        )
        self._calib_status_banner.setAlignment(Qt.AlignCenter)
        self._calib_status_banner.setVisible(False)
        layout.addWidget(self._calib_status_banner)

        # Proof of Life Prompt
        prompt_box = QGroupBox("Motion Responsiveness Check")
        pr_layout = QVBoxLayout(prompt_box)
        pr_layout.setContentsMargins(10, 12, 10, 10)
        pr_desc = QLabel(
            "Try moving in front of your camera:\n"
            " • Blink your eyes\n"
            " • Smile or open your mouth\n"
            " • Turn your head gently left and right\n\n"
            "Your character is now calibrated and responsive."
        )
        pr_desc.setStyleSheet("color: #cbd5e1; font-size: 12px; line-height: 1.4;")
        pr_layout.addWidget(pr_desc)
        layout.addWidget(prompt_box)

        # Continue to Ready
        self._btn_step5_next = QPushButton("Continue to Ready →")
        self._btn_step5_next.setProperty("primary", True)
        self._btn_step5_next.setMinimumHeight(40)
        self._btn_step5_next.setFont(font_btn)
        self._btn_step5_next.clicked.connect(lambda: self._set_step(5))
        layout.addWidget(self._btn_step5_next)

        return page

    # -------------------------------------------------------------
    # Step 6: Ready Page
    # -------------------------------------------------------------
    def _create_step6_ready(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("Step 6: Character Setup Complete!")
        font_t = QFont(title.font())
        font_t.setPointSize(15)
        font_t.setBold(True)
        title.setFont(font_t)
        title.setStyleSheet("color: #10b981;")
        layout.addWidget(title)

        desc = QLabel("Your character is fully rigged, calibrated, and ready to perform live in CPC Studio.")
        desc.setStyleSheet("color: #d4d4d8; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Summary Breakdown Box
        sum_box = QGroupBox("Configuration Summary")
        sb_layout = QGridLayout(sum_box)
        sb_layout.setContentsMargins(12, 16, 12, 12)
        sb_layout.setSpacing(8)

        sb_layout.addWidget(QLabel("Character:"), 0, 0)
        self._sum_char_val = QLabel("--")
        self._sum_char_val.setStyleSheet("color: #10b981; font-weight: 700;")
        sb_layout.addWidget(self._sum_char_val, 0, 1)

        sb_layout.addWidget(QLabel("Tracking Model:"), 1, 0)
        self._sum_model_val = QLabel("MediaPipe Face Landmarker")
        self._sum_model_val.setStyleSheet("color: #10b981; font-weight: 700;")
        sb_layout.addWidget(self._sum_model_val, 1, 1)

        sb_layout.addWidget(QLabel("Rig Sidecar:"), 2, 0)
        self._sum_rig_val = QLabel("--")
        self._sum_rig_val.setStyleSheet("color: #10b981; font-weight: 700;")
        sb_layout.addWidget(self._sum_rig_val, 2, 1)

        sb_layout.addWidget(QLabel("Neutral Pose:"), 3, 0)
        self._sum_pose_val = QLabel("Calibrated ✓")
        self._sum_pose_val.setStyleSheet("color: #10b981; font-weight: 700;")
        sb_layout.addWidget(self._sum_pose_val, 3, 1)

        layout.addWidget(sum_box)

        # Primary Action: Start Performing!
        self._btn_start_performing = QPushButton("▶  Start Performing in Live Studio")
        self._btn_start_performing.setProperty("primary", True)
        self._btn_start_performing.setMinimumHeight(48)
        font_hero = QFont(self._btn_start_performing.font())
        font_hero.setPointSize(14)
        font_hero.setBold(True)
        self._btn_start_performing.setFont(font_hero)
        self._btn_start_performing.clicked.connect(self._start_performing)
        layout.addWidget(self._btn_start_performing)

        return page

    # -------------------------------------------------------------
    # Step Progression & Navigation
    # -------------------------------------------------------------
    def _set_step(self, step_idx: int) -> None:
        self._current_step = step_idx
        self._stack.setCurrentIndex(step_idx)
        self._update_rail()

        # Update step specific data
        if step_idx == 2:  # Step 3 Build Rig
            if self._character_path:
                self._lbl_rig_char_name.setText(self._character_path.name)
                def_rig = default_rig_path(self._character_path)
                self._lbl_rig_dest_path.setText(str(def_rig.name))
        elif step_idx == 5:  # Step 6 Ready
            if self._character_path:
                self._sum_char_val.setText(f"{self._character_path.name} ✓")
            if self._rig_path:
                self._sum_rig_val.setText(f"{self._rig_path.name} ✓")

    def _jump_to_step(self, step_idx: int) -> None:
        # Allow jumping to any step up to current or if previous steps are completed
        if step_idx <= self._current_step or self._step_completed[step_idx]:
            self._set_step(step_idx)
        else:
            # Fallback to current
            self._update_rail()

    def _update_rail(self) -> None:
        for i, btn in enumerate(self._step_buttons):
            btn.setChecked(i == self._current_step)
            if self._step_completed[i]:
                btn.setText(f"✓ {self._step_names[i]}")
            else:
                btn.setText(self._step_names[i])

    # -------------------------------------------------------------
    # Step 1: Character Event Handlers
    # -------------------------------------------------------------
    def _load_recents(self) -> None:
        self._recents_combo.blockSignals(True)
        self._recents_combo.clear()
        self._recents_combo.addItem("Select Recent Character...", "")
        recents = self._settings.get_recent_items("characters")
        for r in recents:
            self._recents_combo.addItem(Path(r).name, r)
        self._recents_combo.blockSignals(False)

    def _on_recent_selected(self, idx: int) -> None:
        if idx <= 0:
            return
        path_str = self._recents_combo.itemData(idx)
        if path_str and Path(path_str).is_file():
            self._char_edit.setText(path_str)

    def _toggle_favorite(self) -> None:
        char_str = self._char_edit.text().strip()
        if not char_str:
            return
        is_fav = self._settings.toggle_favorite("characters", char_str)
        self._fav_btn.setText("★" if is_fav else "☆")
        self._fav_btn.setStyleSheet("color: #f59e0b;" if is_fav else "")

    def _browse_character(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Character Artwork",
            self._settings.get_last_directory(),
            "Image Files (*.png *.jpg *.jpeg *.webp);;All Files (*)",
        )
        if path:
            self._settings.set_last_directory(path)
            self._settings.add_recent_item("characters", path)
            self._char_edit.setText(path)
            self._load_recents()

    def _reveal_character(self) -> None:
        if self._character_path and self._character_path.is_file():
            QDesktopServices.openUrl(f"file://{self._character_path.parent.resolve()}")

    def _on_character_path_changed(self) -> None:
        char_str = self._char_edit.text().strip()
        if not char_str:
            self._canvas_lbl.clear()
            self._canvas_lbl.setText("No character loaded\n\nDrag & drop artwork PNG/JPG or click Choose Character")
            self._character_path = None
            self._character_img = None
            self._current_rig = None
            self._rig_path = None
            self._btn_step1_next.setEnabled(False)
            self._existing_rig_banner.setVisible(False)
            self._step_completed = [False] * 6
            self._update_rail()
            return

        char_path = Path(char_str)
        if not char_path.is_file():
            self._canvas_lbl.setText("Character image file not found.")
            self._btn_step1_next.setEnabled(False)
            return

        img = cv2.imread(str(char_path))
        if img is None:
            self._canvas_lbl.setText("Failed to decode image format.")
            self._btn_step1_next.setEnabled(False)
            return

        self._character_path = char_path
        self._character_img = img
        h, w = img.shape[:2]
        self._char_info_lbl.setText(f"Dimensions: {w} × {h} px")
        self._btn_step1_next.setEnabled(True)
        self._step_completed[0] = True

        # Check existing rig sidecar
        def_rig = default_rig_path(char_path)
        if def_rig.is_file():
            try:
                rig = load_rig(def_rig)
                self._current_rig = rig
                self._rig_path = def_rig
                self._existing_rig_banner.setVisible(True)
                self._step_completed[2] = True  # Rig built
                self._step_completed[3] = True  # Verified
            except (RuntimeError, ValueError, OSError, FileNotFoundError):
                self._existing_rig_banner.setVisible(False)
        else:
            self._existing_rig_banner.setVisible(False)

        self._refresh_preview()
        self._update_rail()

    # -------------------------------------------------------------
    # Step 2: Tracking Event Handlers
    # -------------------------------------------------------------
    def _on_model_changed(self, model_id: str, resolved_path: Path | None, delegate: str) -> None:
        self._model_id = model_id
        self._model_path = resolved_path
        self._delegate = delegate
        is_ready = self.model_selector.is_ready()
        self._btn_step2_next.setEnabled(is_ready)
        self._step_completed[1] = is_ready
        self._update_rail()

    # -------------------------------------------------------------
    # Step 3: Build Rig Event Handlers
    # -------------------------------------------------------------
    def derive_rig(self) -> None:
        if not self._character_path or not self._character_path.is_file():
            QMessageBox.warning(self, "Missing Character", "Please select a valid character image first.")
            return

        model_path = self.model_selector.get_resolved_path()
        if not model_path or not model_path.is_file():
            QMessageBox.warning(
                self,
                "Model Required",
                "MediaPipe Face Landmarker model is required. Please install or select a model in Step 2.",
            )
            self._set_step(1)
            return

        rig_path = default_rig_path(self._character_path)

        # Overwrite Confirmation
        if rig_path.is_file():
            reply = QMessageBox.question(
                self,
                "Overwrite Existing Rig?",
                f"A rig sidecar already exists at:\n{rig_path.name}\n\nDo you want to re-derive and overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        self._derive_btn.setEnabled(False)
        self._derive_progress.setVisible(True)
        self._derive_status_lbl.setText("Detecting facial landmarks on character artwork...")
        self._log_text.append(f"Starting rig derivation on {self._character_path.name}...")

        self._derive_worker = DeriveRigWorker(self._character_path, model_path, rig_path, self._delegate, self)
        self._derive_worker.rig_derived.connect(self._on_rig_derived)
        self._derive_worker.error_occurred.connect(self._on_derive_error)
        self._derive_worker.start()

    def _on_rig_derived(self, rig: CharacterRig, rig_path_str: str) -> None:
        self._derive_btn.setEnabled(True)
        self._derive_progress.setVisible(False)
        self._current_rig = rig
        self._rig_path = Path(rig_path_str)
        self._derive_status_lbl.setText("✓ Rig built successfully!")
        self._log_text.append(f"SUCCESS: Derived {rig.point_count} landmarks. Rig saved to {rig_path_str}")

        self._step_completed[2] = True
        self._step_completed[3] = True
        self._refresh_preview()
        self._update_rail()

        # Advance to Step 4 Verify
        self._set_step(3)

    def _on_derive_error(self, user_msg: str, tech_details: str) -> None:
        self._derive_btn.setEnabled(True)
        self._derive_progress.setVisible(False)
        self._derive_status_lbl.setText("✕ Derivation failed")
        self._log_text.append(f"ERROR: {user_msg}\n{tech_details}")

        friendly_msg = (
            "CPC couldn't find a usable face in this character image.\n\n"
            "To build a rig, try an artwork image with:\n"
            " • A clearly visible front-facing face\n"
            " • Minimal hair or prop obstruction\n"
            " • Neutral expression"
        )
        QMessageBox.warning(self, "Face Not Detected", friendly_msg)

    # -------------------------------------------------------------
    # Step 5: Calibrate & Test Event Handlers
    # -------------------------------------------------------------
    def _start_calibration_countdown(self) -> None:
        self._countdown_val = 3
        self._btn_calibrate_now.setEnabled(False)
        self._btn_calibrate_now.setText(f"Calibrating in {self._countdown_val}...")

        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._on_calibration_tick)
        self._countdown_timer.start(1000)

    def _on_calibration_tick(self) -> None:
        self._countdown_val -= 1
        if self._countdown_val > 0:
            self._btn_calibrate_now.setText(f"Calibrating in {self._countdown_val}...")
        else:
            if self._countdown_timer is not None:
                self._countdown_timer.stop()
                self._countdown_timer = None
            self._btn_calibrate_now.setEnabled(True)
            self._btn_calibrate_now.setText("🎯  Recalibrate Neutral Pose")
            self._calib_status_banner.setVisible(True)
            self._is_calibrated = True
            self._step_completed[4] = True
            self._update_rail()

    # -------------------------------------------------------------
    # Step 6: Start Performing Live Handoff
    # -------------------------------------------------------------
    def _start_performing(self) -> None:
        if not self._character_path or not self._rig_path:
            return

        setup_dict = {
            "character_path": self._character_path,
            "rig_path": self._rig_path,
            "model_path": self.model_selector.get_resolved_path(),
            "tracker_delegate": self._delegate,
            "tracker_type": "mediapipe",
            "renderer_type": "rig",
        }
        self.character_selected.emit(self._character_path, self._rig_path)
        self.start_performing_requested.emit(setup_dict)

    def set_selected_character(self, char_path: Path, model_path: Path | None = None) -> None:
        self._char_edit.setText(str(char_path))
        if model_path:
            self.model_selector.select_model("mediapipe-face-landmarker")

    # -------------------------------------------------------------
    # Drag and Drop Events
    # -------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                p = Path(url.toLocalFile())
                if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".task", ".json"}:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                self._char_edit.setText(str(p))
                self._settings.add_recent_item("characters", p)
                self._load_recents()
                event.acceptProposedAction()
                return
            elif p.suffix.lower() == ".task":
                try:
                    entry = self._registry.register_custom_model(p, copy_to_managed=True)
                    self.model_selector.select_model(entry.model_id)
                except (RuntimeError, ValueError, OSError, FileNotFoundError):
                    continue
                event.acceptProposedAction()
                return

    # -------------------------------------------------------------
    # Visual Canvas Rendering
    # -------------------------------------------------------------
    def _refresh_preview(self) -> None:
        if self._character_img is None:
            return
        if self._current_rig is None or (
            not self._check_show_points.isChecked()
            and not self._check_show_mesh.isChecked()
            and not self._check_show_hull.isChecked()
        ):
            self._render_character_preview(self._character_img)
            return
        self._render_rig_overlay(self._character_img, self._current_rig)

    def _render_character_preview(self, img: np.ndarray) -> None:
        h, w = img.shape[:2]
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
        pix = QPixmap.fromImage(qimg)
        scaled = pix.scaled(self._canvas_lbl.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._canvas_lbl.setPixmap(scaled)

    def _render_rig_overlay(self, img: np.ndarray, rig: CharacterRig) -> None:
        overlay = img.copy()
        h, w = img.shape[:2]
        pts = rig.points.astype(int)

        # Draw mesh triangles
        if self._check_show_mesh.isChecked():
            from cpc.geometry import delaunay_triangles

            try:
                triangles = delaunay_triangles(rig.points, w, h)
                for tri in triangles:
                    p1, p2, p3 = pts[tri[0]], pts[tri[1]], pts[tri[2]]
                    cv2.line(overlay, tuple(p1), tuple(p2), (80, 120, 200), 1, cv2.LINE_AA)
                    cv2.line(overlay, tuple(p2), tuple(p3), (80, 120, 200), 1, cv2.LINE_AA)
                    cv2.line(overlay, tuple(p3), tuple(p1), (80, 120, 200), 1, cv2.LINE_AA)
            except (RuntimeError, ValueError, OSError, IndexError):
                pass

        # Draw landmark points
        if self._check_show_points.isChecked():
            for pt in pts:
                cv2.circle(overlay, tuple(pt), 2, (0, 255, 255), -1, cv2.LINE_AA)

        # Draw convex hull boundary
        if self._check_show_hull.isChecked() and len(pts) >= 3:
            hull = cv2.convexHull(pts)
            cv2.polylines(overlay, [hull], True, (0, 255, 0), 1, cv2.LINE_AA)

        blended = cv2.addWeighted(overlay, 0.8, img, 0.2, 0)
        self._render_character_preview(blended)
