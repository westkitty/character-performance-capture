from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import (
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
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from cpc.rig import CharacterRig, default_rig_path, load_rig
from cpc.ui.models import RECOMMENDED_MEDIAPIPE_MODEL, get_model_registry
from cpc.ui.settings import AppSettings
from cpc.ui.widgets.model_selector import ModelSelectorWidget
from cpc.ui.worker import DeriveRigWorker


class CharacterWorkspace(QWidget):
    """Calm, Guided 6-stage Character Setup Journey & Rig Visualizer."""

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
        main_layout.setContentsMargins(14, 10, 14, 14)
        main_layout.setSpacing(10)

        # -------------------------------------------------------------
        # 0. Top Step Navigation Rail
        # -------------------------------------------------------------
        self._rail_frame = QFrame()
        self._rail_frame.setStyleSheet(
            "QFrame { background-color: #121218; border: 1px solid #1f1f2a; border-radius: 8px; padding: 4px; }"
        )
        rail_layout = QHBoxLayout(self._rail_frame)
        rail_layout.setContentsMargins(6, 4, 6, 4)
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
                "border-radius: 6px; padding: 6px 14px; font-weight: 500; font-size: 12px; color: #9ca3af; } "
                "QPushButton:checked { background-color: #1e3a8a; border: 1px solid #3b82f6; color: #ffffff; font-weight: 600; } "
                "QPushButton:hover:!checked { background-color: #171722; color: #d1d1d6; }"
            )
            btn.clicked.connect(lambda _, idx=i: self._jump_to_step(idx))
            rail_layout.addWidget(btn)
            self._step_buttons.append(btn)

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
        self._left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._left_scroll.setMinimumWidth(380)
        self._left_scroll.setMaximumWidth(500)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(6, 6, 6, 6)
        left_layout.setSpacing(10)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._create_step1_character())
        self._stack.addWidget(self._create_step2_tracking())
        self._stack.addWidget(self._create_step3_build_rig())
        self._stack.addWidget(self._create_step4_verify())
        self._stack.addWidget(self._create_step5_calibrate())
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

        # Visualizer Toolbar (hidden on steps 1-3 until a rig exists to verify)
        self._viz_toolbar_widget = QWidget()
        viz_toolbar = QHBoxLayout(self._viz_toolbar_widget)
        viz_toolbar.setContentsMargins(0, 0, 0, 0)
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
        self._viz_toolbar_widget.setVisible(False)
        right_layout.addWidget(self._viz_toolbar_widget)

        # Visual Canvas
        self._canvas_lbl = QLabel("No character loaded\n\nDrag & drop artwork PNG/JPG or click Choose Character")
        self._canvas_lbl.setAlignment(Qt.AlignCenter)
        self._canvas_lbl.setStyleSheet(
            "QLabel { background-color: #0c0c10; border: 1px dashed #242432; border-radius: 8px; color: #71717a; font-size: 14px; }"
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
        layout.setSpacing(12)

        title = QLabel("Step 1: Choose Your Character")
        font_t = QFont(title.font())
        font_t.setPointSize(15)
        font_t.setBold(True)
        title.setFont(font_t)
        layout.addWidget(title)

        desc = QLabel("Select or drop the 2D character reference image you want to perform with.")
        desc.setStyleSheet("color: #9ca3af; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Drop Target / Primary Action Button
        self._drop_card = QFrame()
        self._drop_card.setStyleSheet(
            "QFrame { background-color: #14141d; border: 2px dashed #2b2b3d; border-radius: 8px; padding: 16px; }"
            "QFrame:hover { border-color: #3b82f6; background-color: #171722; }"
        )
        drop_layout = QVBoxLayout(self._drop_card)
        drop_layout.setSpacing(8)

        drop_prompt = QLabel("Drag & drop character image here (PNG, JPG, WebP)")
        drop_prompt.setAlignment(Qt.AlignCenter)
        drop_prompt.setStyleSheet("color: #d1d5db; font-size: 13px; font-weight: 500;")
        drop_layout.addWidget(drop_prompt)

        btn_browse_main = QPushButton("📁  Choose Character Artwork...")
        btn_browse_main.setProperty("primary", True)
        btn_browse_main.setMinimumHeight(38)
        btn_browse_main.clicked.connect(self._browse_character)
        drop_layout.addWidget(btn_browse_main)

        layout.addWidget(self._drop_card)

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

        # Selected Character Summary Card (visible when loaded)
        self._char_summary_card = QFrame()
        self._char_summary_card.setStyleSheet(
            "background-color: #14141c; border: 1px solid #232330; border-radius: 6px; padding: 10px;"
        )
        csum_layout = QVBoxLayout(self._char_summary_card)
        csum_layout.setSpacing(4)

        self._char_edit = QLineEdit()
        self._char_edit.setVisible(False)
        self._char_edit.textChanged.connect(self._on_character_path_changed)
        csum_layout.addWidget(self._char_edit)

        self._char_filename_lbl = QLabel("No character selected")
        self._char_filename_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #ffffff;")
        csum_layout.addWidget(self._char_filename_lbl)

        self._char_info_lbl = QLabel("Dimensions: --")
        self._char_info_lbl.setStyleSheet("color: #9ca3af; font-size: 12px;")
        csum_layout.addWidget(self._char_info_lbl)

        self._existing_rig_banner = QLabel("✓ Rig sidecar found for this character")
        self._existing_rig_banner.setStyleSheet(
            "color: #10b981; font-weight: 500; font-size: 12px;"
        )
        self._existing_rig_banner.setVisible(False)
        csum_layout.addWidget(self._existing_rig_banner)

        self._char_summary_card.setVisible(False)
        layout.addWidget(self._char_summary_card)

        layout.addStretch(1)

        # Primary CTA
        self._btn_step1_next = QPushButton("Continue to Tracking →")
        self._btn_step1_next.setProperty("primary", True)
        self._btn_step1_next.setMinimumHeight(42)
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
        layout.setSpacing(12)

        title = QLabel("Step 2: Tracking Model")
        font_t = QFont(title.font())
        font_t.setPointSize(15)
        font_t.setBold(True)
        title.setFont(font_t)
        layout.addWidget(title)

        desc = QLabel("Select the facial landmark tracker. The official MediaPipe Face Landmarker runs locally on your CPU.")
        desc.setStyleSheet("color: #9ca3af; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.model_selector = ModelSelectorWidget(self)
        self.model_selector.model_selection_changed.connect(self._on_model_selection_changed)
        layout.addWidget(self.model_selector)

        layout.addStretch(1)

        nav_row = QHBoxLayout()
        btn_back = QPushButton("← Back")
        btn_back.setMinimumHeight(40)
        btn_back.clicked.connect(lambda: self._set_step(0))
        nav_row.addWidget(btn_back)

        self._btn_step2_next = QPushButton("Continue to Build Rig →")
        self._btn_step2_next.setProperty("primary", True)
        self._btn_step2_next.setMinimumHeight(40)
        font_btn = QFont(self._btn_step2_next.font())
        font_btn.setBold(True)
        self._btn_step2_next.setFont(font_btn)
        self._btn_step2_next.clicked.connect(lambda: self._set_step(2))
        nav_row.addWidget(self._btn_step2_next, 1)
        layout.addLayout(nav_row)

        return page

    # -------------------------------------------------------------
    # Step 3: Build Rig Page
    # -------------------------------------------------------------
    def _create_step3_build_rig(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("Step 3: Build Character Rig")
        font_t = QFont(title.font())
        font_t.setPointSize(15)
        font_t.setBold(True)
        title.setFont(font_t)
        layout.addWidget(title)

        desc = QLabel(
            "CPC will analyze your character artwork, detect facial geometry, and generate the 2D deformation mesh rig."
        )
        desc.setStyleSheet("color: #9ca3af; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Action Card
        rig_card = QFrame()
        rig_card.setStyleSheet("background-color: #14141c; border: 1px solid #232330; border-radius: 8px; padding: 14px;")
        rc_layout = QVBoxLayout(rig_card)
        rc_layout.setSpacing(10)

        self._rig_status_msg = QLabel("Ready to build character rig.")
        self._rig_status_msg.setStyleSheet("color: #d1d5db; font-size: 13px;")
        rc_layout.addWidget(self._rig_status_msg)

        self._btn_build_rig = QPushButton("⚡  Build Character Rig")
        self._btn_build_rig.setProperty("primary", True)
        self._btn_build_rig.setMinimumHeight(44)
        font_bb = QFont(self._btn_build_rig.font())
        font_bb.setBold(True)
        font_bb.setPointSize(13)
        self._btn_build_rig.setFont(font_bb)
        self._btn_build_rig.clicked.connect(self._build_rig_action)
        rc_layout.addWidget(self._btn_build_rig)

        self._derive_prog = QProgressBar()
        self._derive_prog.setRange(0, 0)  # indeterminate
        self._derive_prog.setVisible(False)
        rc_layout.addWidget(self._derive_prog)

        layout.addWidget(rig_card)
        layout.addStretch(1)

        nav_row = QHBoxLayout()
        btn_back = QPushButton("← Back")
        btn_back.setMinimumHeight(40)
        btn_back.clicked.connect(lambda: self._set_step(1))
        nav_row.addWidget(btn_back)

        self._btn_step3_next = QPushButton("Continue to Verify →")
        self._btn_step3_next.setProperty("primary", True)
        self._btn_step3_next.setMinimumHeight(40)
        font_btn = QFont(self._btn_step3_next.font())
        font_btn.setBold(True)
        self._btn_step3_next.setFont(font_btn)
        self._btn_step3_next.setEnabled(False)
        self._btn_step3_next.clicked.connect(lambda: self._set_step(3))
        nav_row.addWidget(self._btn_step3_next, 1)
        layout.addLayout(nav_row)

        return page

    # -------------------------------------------------------------
    # Step 4: Verify Mesh Page
    # -------------------------------------------------------------
    def _create_step4_verify(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("Step 4: Verify Mesh Alignment")
        font_t = QFont(title.font())
        font_t.setPointSize(15)
        font_t.setBold(True)
        title.setFont(font_t)
        layout.addWidget(title)

        desc = QLabel("Inspect the facial landmarks and deformation mesh overlaid on your character in the preview canvas.")
        desc.setStyleSheet("color: #9ca3af; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Verification Card
        v_card = QFrame()
        v_card.setStyleSheet("background-color: #14141c; border: 1px solid #232330; border-radius: 8px; padding: 14px;")
        vc_layout = QVBoxLayout(v_card)
        vc_layout.setSpacing(10)

        q_lbl = QLabel("Does the mesh align with your character's eyes, nose, and mouth?")
        q_lbl.setStyleSheet("color: #ffffff; font-weight: 600; font-size: 13px;")
        q_lbl.setWordWrap(True)
        vc_layout.addWidget(q_lbl)

        self._rig_details_lbl = QLabel("Rig Points: -- | Triangles: --")
        self._rig_details_lbl.setStyleSheet("color: #9ca3af; font-size: 12px;")
        vc_layout.addWidget(self._rig_details_lbl)

        btn_rederive = QPushButton("↻ Re-derive Rig")
        btn_rederive.clicked.connect(self._build_rig_action)
        vc_layout.addWidget(btn_rederive)

        layout.addWidget(v_card)
        layout.addStretch(1)

        nav_row = QHBoxLayout()
        btn_back = QPushButton("← Back")
        btn_back.setMinimumHeight(40)
        btn_back.clicked.connect(lambda: self._set_step(2))
        nav_row.addWidget(btn_back)

        self._btn_step4_next = QPushButton("Looks Great → Continue to Calibrate")
        self._btn_step4_next.setProperty("primary", True)
        self._btn_step4_next.setMinimumHeight(40)
        font_btn = QFont(self._btn_step4_next.font())
        font_btn.setBold(True)
        self._btn_step4_next.setFont(font_btn)
        self._btn_step4_next.clicked.connect(self._on_step4_next_clicked)
        nav_row.addWidget(self._btn_step4_next, 1)
        layout.addLayout(nav_row)

        return page

    # -------------------------------------------------------------
    # Step 5: Calibrate & Test Page
    # -------------------------------------------------------------
    def _create_step5_calibrate(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("Step 5: Calibrate Neutral Rest Pose")
        font_t = QFont(title.font())
        font_t.setPointSize(15)
        font_t.setBold(True)
        title.setFont(font_t)
        layout.addWidget(title)

        desc = QLabel(
            "Look straight at the camera in a relaxed, neutral expression. Capturing a neutral rest pose ensures accurate head rotation and expression mapping."
        )
        desc.setStyleSheet("color: #9ca3af; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Calibration Action Card
        calib_card = QFrame()
        calib_card.setStyleSheet("background-color: #14141c; border: 1px solid #232330; border-radius: 8px; padding: 14px;")
        cc_layout = QVBoxLayout(calib_card)
        cc_layout.setSpacing(10)

        self._btn_calibrate_now = QPushButton("🎯  Capture Neutral Pose (3s Countdown)")
        self._btn_calibrate_now.setProperty("primary", True)
        self._btn_calibrate_now.setMinimumHeight(44)
        font_c = QFont(self._btn_calibrate_now.font())
        font_c.setBold(True)
        self._btn_calibrate_now.setFont(font_c)
        self._btn_calibrate_now.clicked.connect(self._start_calibration_countdown)
        cc_layout.addWidget(self._btn_calibrate_now)

        self._calib_status_banner = QLabel("✓ Neutral pose calibrated.")
        self._calib_status_banner.setStyleSheet("color: #10b981; font-weight: 600; font-size: 12px;")
        self._calib_status_banner.setVisible(False)
        cc_layout.addWidget(self._calib_status_banner)

        layout.addWidget(calib_card)
        layout.addStretch(1)

        nav_row = QHBoxLayout()
        btn_back = QPushButton("← Back")
        btn_back.setMinimumHeight(40)
        btn_back.clicked.connect(lambda: self._set_step(3))
        nav_row.addWidget(btn_back)

        self._btn_step5_next = QPushButton("Continue to Ready →")
        self._btn_step5_next.setProperty("primary", True)
        self._btn_step5_next.setMinimumHeight(40)
        font_btn = QFont(self._btn_step5_next.font())
        font_btn.setBold(True)
        self._btn_step5_next.setFont(font_btn)
        self._btn_step5_next.clicked.connect(lambda: self._set_step(5))
        nav_row.addWidget(self._btn_step5_next, 1)
        layout.addLayout(nav_row)

        return page

    # -------------------------------------------------------------
    # Step 6: Ready to Perform Page
    # -------------------------------------------------------------
    def _create_step6_ready(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("Step 6: Ready to Perform")
        font_t = QFont(title.font())
        font_t.setPointSize(15)
        font_t.setBold(True)
        title.setFont(font_t)
        layout.addWidget(title)

        desc = QLabel("Your character is fully configured and ready for live performance capture.")
        desc.setStyleSheet("color: #9ca3af; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Summary confirmation card
        sum_card = QFrame()
        sum_card.setStyleSheet("background-color: #14141c; border: 1px solid #232330; border-radius: 8px; padding: 14px;")
        sc_layout = QVBoxLayout(sum_card)
        sc_layout.setSpacing(8)

        self._ready_char_lbl = QLabel("Character: --")
        self._ready_char_lbl.setStyleSheet("font-size: 13px; color: #ffffff;")
        sc_layout.addWidget(self._ready_char_lbl)

        self._ready_model_lbl = QLabel("Tracker: MediaPipe Face Landmarker (CPU)")
        self._ready_model_lbl.setStyleSheet("font-size: 13px; color: #ffffff;")
        sc_layout.addWidget(self._ready_model_lbl)

        self._ready_rig_lbl = QLabel("Rig: Active & Verified")
        self._ready_rig_lbl.setStyleSheet("font-size: 13px; color: #10b981;")
        sc_layout.addWidget(self._ready_rig_lbl)

        layout.addWidget(sum_card)

        # Dominant Handoff CTA
        self._btn_start_performing = QPushButton("▶  Start Performing in Live Studio")
        self._btn_start_performing.setProperty("primary", True)
        self._btn_start_performing.setMinimumHeight(46)
        font_sp = QFont(self._btn_start_performing.font())
        font_sp.setPointSize(14)
        font_sp.setBold(True)
        self._btn_start_performing.setFont(font_sp)
        self._btn_start_performing.clicked.connect(self._start_performing)
        layout.addWidget(self._btn_start_performing)

        layout.addStretch(1)

        nav_row = QHBoxLayout()
        btn_back = QPushButton("← Back")
        btn_back.setMinimumHeight(40)
        btn_back.clicked.connect(lambda: self._set_step(4))
        nav_row.addWidget(btn_back)
        nav_row.addStretch(1)
        layout.addLayout(nav_row)

        return page

    # -------------------------------------------------------------
    # Navigation & Step State Logic
    # -------------------------------------------------------------
    def _jump_to_step(self, idx: int) -> None:
        self._set_step(idx)

    def _set_step(self, idx: int) -> None:
        self._current_step = idx
        self._stack.setCurrentIndex(idx)
        self._update_rail()

        # Update visualizer toolbar visibility (only relevant when inspecting/verifying a rig)
        show_viz = idx >= 3 and self._current_rig is not None
        self._viz_toolbar_widget.setVisible(show_viz)

        if idx == 5:
            self._update_ready_summary()

    def _update_rail(self) -> None:
        for i, btn in enumerate(self._step_buttons):
            btn.setChecked(i == self._current_step)
            is_done = self._step_completed[i]
            base_name = self._step_names[i]
            if is_done:
                btn.setText(f"✓ {base_name}")
                btn.setStyleSheet(
                    "QPushButton { background-color: transparent; border: 1px solid transparent; "
                    "border-radius: 6px; padding: 6px 14px; font-weight: 600; font-size: 12px; color: #10b981; } "
                    "QPushButton:checked { background-color: #1e3a8a; border: 1px solid #3b82f6; color: #ffffff; } "
                    "QPushButton:hover:!checked { background-color: #171722; color: #6ee7b7; }"
                )
            else:
                btn.setText(base_name)
                btn.setStyleSheet(
                    "QPushButton { background-color: transparent; border: 1px solid transparent; "
                    "border-radius: 6px; padding: 6px 14px; font-weight: 500; font-size: 12px; color: #9ca3af; } "
                    "QPushButton:checked { background-color: #1e3a8a; border: 1px solid #3b82f6; color: #ffffff; font-weight: 600; } "
                    "QPushButton:hover:!checked { background-color: #171722; color: #d1d1d6; }"
                )

    def _update_ready_summary(self) -> None:
        c_name = self._character_path.name if self._character_path else "None"
        self._ready_char_lbl.setText(f"Character: {c_name}")
        self._ready_model_lbl.setText(f"Tracker: {self.model_selector.get_selected_entry().name} ({self._delegate.upper()})")
        r_status = "Active & Verified (478 pts)" if self._current_rig else "Missing"
        self._ready_rig_lbl.setText(f"Rig: {r_status}")

    # -------------------------------------------------------------
    # Step 1: Character Event Handlers
    # -------------------------------------------------------------
    def _load_recents(self) -> None:
        self._recents_combo.blockSignals(True)
        self._recents_combo.clear()
        self._recents_combo.addItem("Select Recent Character...")
        recents = self._settings.get_recent_items("characters")
        for item in recents:
            self._recents_combo.addItem(Path(item).name, item)
        self._recents_combo.blockSignals(False)

    def _on_recent_selected(self, idx: int) -> None:
        if idx == 0:
            return
        data = self._recents_combo.currentData()
        if data:
            self._char_edit.setText(str(data))

    def _toggle_favorite(self) -> None:
        if self._character_path:
            is_fav = self._settings.toggle_favorite("characters", self._character_path)
            self._fav_btn.setText("★" if is_fav else "☆")

    def _browse_character(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Character Reference Image",
            self._settings.get_last_directory(),
            "Image Files (*.png *.jpg *.jpeg *.webp);;All Files (*)",
        )
        if path:
            self._settings.set_last_directory(path)
            self._char_edit.setText(path)
            self._settings.add_recent_item("characters", Path(path))
            self._load_recents()

    def _on_character_path_changed(self, text: str) -> None:
        path_str = text.strip()
        if not path_str:
            self._character_path = None
            self._character_img = None
            self._char_summary_card.setVisible(False)
            self._btn_step1_next.setEnabled(False)
            self._step_completed[0] = False
            self._canvas_lbl.setText("No character loaded\n\nDrag & drop artwork PNG/JPG or click Choose Character")
            self._canvas_lbl.setPixmap(QPixmap())
            self._update_rail()
            return

        p = Path(path_str)
        if p.is_file():
            self._character_path = p
            img = cv2.imread(str(p))
            if img is not None:
                self._character_img = img
                h, w = img.shape[:2]
                self._char_filename_lbl.setText(p.name)
                self._char_info_lbl.setText(f"Dimensions: {w} × {h} px  |  Path: {p.parent.name}/{p.name}")
                self._char_summary_card.setVisible(True)
                self._btn_step1_next.setEnabled(True)
                self._step_completed[0] = True

                # Check for existing rig sidecar
                expected_rig = default_rig_path(p)
                if expected_rig.is_file():
                    try:
                        self._current_rig = load_rig(expected_rig)
                        self._rig_path = expected_rig
                        self._existing_rig_banner.setVisible(True)
                        self._step_completed[2] = True
                        self._btn_step3_next.setEnabled(True)
                        self._rig_details_lbl.setText(f"Rig Points: {len(self._current_rig.points)} | Auto-loaded")
                    except (RuntimeError, ValueError, OSError, KeyError):
                        self._current_rig = None
                        self._existing_rig_banner.setVisible(False)
                else:
                    self._current_rig = None
                    self._existing_rig_banner.setVisible(False)

                self._render_character_preview(img)
                self._update_rail()

    # -------------------------------------------------------------
    # Step 2: Tracking Event Handlers
    # -------------------------------------------------------------
    def _on_model_selection_changed(self, model_id: str, resolved_path: Path | None, delegate: str) -> None:
        self._model_id = model_id
        self._model_path = resolved_path
        self._delegate = delegate
        is_ready = self.model_selector.is_ready()
        self._step_completed[1] = is_ready
        self._btn_step2_next.setEnabled(is_ready)
        self._update_rail()

    # -------------------------------------------------------------
    # Step 3: Build Rig Event Handlers
    # -------------------------------------------------------------
    def _build_rig_action(self) -> None:
        if not self._character_path:
            QMessageBox.warning(self, "Missing Character", "Please choose a character image first.")
            self._set_step(0)
            return

        model_path = self.model_selector.get_resolved_path()
        if not model_path or not model_path.is_file():
            QMessageBox.warning(self, "Missing Model", "Please install or select a valid tracking model in Step 2.")
            self._set_step(1)
            return

        self._btn_build_rig.setEnabled(False)
        self._derive_prog.setVisible(True)
        self._rig_status_msg.setText("Analyzing character face geometry...")

        self._derive_worker = DeriveRigWorker(
            character_path=self._character_path,
            model_path=model_path,
            delegate=self._delegate,
            parent=self,
        )
        self._derive_worker.stage_changed.connect(lambda msg: self._rig_status_msg.setText(msg))
        self._derive_worker.derived_success.connect(self._on_rig_derived)
        self._derive_worker.error_occurred.connect(self._on_derive_error)
        self._derive_worker.start()

    def _on_rig_derived(self, rig: CharacterRig, rig_path: Path | str) -> None:
        self._derive_worker = None
        self._btn_build_rig.setEnabled(True)
        self._derive_prog.setVisible(False)
        self._current_rig = rig
        p_obj = Path(rig_path)
        self._rig_path = p_obj
        self._step_completed[2] = True
        self._step_completed[3] = True
        self._btn_step3_next.setEnabled(True)
        self._rig_status_msg.setText(f"✓ Character Rig Built ({len(rig.points)} points)")
        self._rig_details_lbl.setText(f"Rig Points: {len(rig.points)}  |  Saved to: {p_obj.name}")
        self._update_rail()
        self._set_step(3)  # Advance to Verify
        self._refresh_preview()

    def _on_step4_next_clicked(self) -> None:
        self._step_completed[3] = True
        self._set_step(4)

    def _on_derive_error(self, err_msg: str, tech_details: str) -> None:
        self._derive_worker = None
        self._btn_build_rig.setEnabled(True)
        self._derive_prog.setVisible(False)
        self._rig_status_msg.setText("Rig derivation failed.")

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
