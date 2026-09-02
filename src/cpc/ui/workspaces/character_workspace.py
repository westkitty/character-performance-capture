from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from cpc.rig import CharacterRig, default_rig_path, load_rig
from cpc.ui.settings import AppSettings
from cpc.ui.worker import DeriveRigWorker


class CharacterWorkspace(QWidget):
    """Character Reference Artwork & Rig Derivation Studio."""

    character_selected = Signal(Path, Path)  # (character_image_path, rig_sidecar_path)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._derive_worker: DeriveRigWorker | None = None
        self._current_rig: CharacterRig | None = None
        self._character_img: np.ndarray | None = None
        self._settings = AppSettings()
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)

        # -------------------------------------------------------------
        # 1. Left Column: Character Configuration & Derivation Controls
        # -------------------------------------------------------------
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        config_group = QGroupBox("Character && Rig Setup")
        grid = QGridLayout(config_group)
        grid.setContentsMargins(12, 16, 12, 12)
        grid.setSpacing(8)

        # 1. Character Image
        grid.addWidget(QLabel("1. Character Image:"), 0, 0)
        self._char_edit = QLineEdit()
        self._char_edit.setPlaceholderText("Select character reference PNG/JPG...")
        self._char_edit.textChanged.connect(self._on_character_path_changed)

        self._browse_char_btn = QPushButton("Browse...")
        self._browse_char_btn.clicked.connect(self._browse_character)

        char_row = QHBoxLayout()
        char_row.addWidget(self._char_edit, 1)
        char_row.addWidget(self._browse_char_btn)
        grid.addLayout(char_row, 0, 1)

        # 2. Tracker Model
        grid.addWidget(QLabel("2. Tracker Model:"), 1, 0)
        self._model_edit = QLineEdit()
        self._model_edit.setPlaceholderText("Path to face_landmarker.task...")

        self._browse_model_btn = QPushButton("Browse...")
        self._browse_model_btn.clicked.connect(self._browse_model)

        model_row = QHBoxLayout()
        model_row.addWidget(self._model_edit, 1)
        model_row.addWidget(self._browse_model_btn)
        grid.addLayout(model_row, 1, 1)

        # 3. Execution Delegate
        grid.addWidget(QLabel("3. Compute Delegate:"), 2, 0)
        self._delegate_combo = QComboBox()
        self._delegate_combo.addItems([
            "CPU (Validated Default)",
            "GPU (Experimental on macOS)",
        ])
        grid.addWidget(self._delegate_combo, 2, 1)

        # 4. Target Rig Sidecar
        grid.addWidget(QLabel("4. Rig Output:"), 3, 0)
        self._rig_edit = QLineEdit()
        self._rig_edit.setPlaceholderText("Default: <character>.rig.json")

        self._browse_rig_btn = QPushButton("Browse...")
        self._browse_rig_btn.clicked.connect(self._browse_rig)

        rig_row = QHBoxLayout()
        rig_row.addWidget(self._rig_edit, 1)
        rig_row.addWidget(self._browse_rig_btn)
        grid.addLayout(rig_row, 3, 1)

        left_layout.addWidget(config_group)

        # Action Buttons
        self._derive_btn = QPushButton("⚡ Derive Character Rig")
        self._derive_btn.setProperty("primary", True)
        self._derive_btn.setMinimumHeight(38)
        font = QFont(self._derive_btn.font())
        font.setBold(True)
        self._derive_btn.setFont(font)
        self._derive_btn.clicked.connect(self.derive_rig)
        left_layout.addWidget(self._derive_btn)

        self._use_char_btn = QPushButton("✓ Use Character in Live Studio")
        self._use_char_btn.setMinimumHeight(34)
        self._use_char_btn.setEnabled(False)
        self._use_char_btn.clicked.connect(self._use_in_studio)
        left_layout.addWidget(self._use_char_btn)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # Indeterminate
        self._progress.setVisible(False)
        left_layout.addWidget(self._progress)

        # Rig Status Card
        status_group = QGroupBox("Rig Verification Status")
        s_grid = QGridLayout(status_group)
        s_grid.setContentsMargins(12, 16, 12, 12)
        s_grid.setSpacing(6)

        self._lbl_status = self._add_stat_row(s_grid, 0, "Status:", "Pending selection", "#71717a")
        self._lbl_points = self._add_stat_row(s_grid, 1, "Landmark Points:", "--", "#e4e4e7")
        self._lbl_dimensions = self._add_stat_row(s_grid, 2, "Dimensions:", "--", "#e4e4e7")
        self._lbl_triangles = self._add_stat_row(s_grid, 3, "Topology:", "--", "#e4e4e7")

        left_layout.addWidget(status_group)

        # Derivation Log
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setPlaceholderText("Rig derivation and validation log...")
        left_layout.addWidget(self._log_text, 1)

        splitter.addWidget(left_widget)

        # -------------------------------------------------------------
        # 2. Right Column: Character Visualizer & Mesh Overlay
        # -------------------------------------------------------------
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # Visualizer Toolbar
        viz_toolbar = QHBoxLayout()
        viz_toolbar.setSpacing(12)

        self._check_show_points = QCheckBox("Show Landmarks (Points)")
        self._check_show_points.setChecked(True)
        self._check_show_points.stateChanged.connect(self._refresh_preview)
        viz_toolbar.addWidget(self._check_show_points)

        self._check_show_hull = QCheckBox("Show Boundary Hull")
        self._check_show_hull.setChecked(True)
        self._check_show_hull.stateChanged.connect(self._refresh_preview)
        viz_toolbar.addWidget(self._check_show_hull)

        viz_toolbar.addStretch(1)
        right_layout.addLayout(viz_toolbar)

        # Character Preview Canvas
        self._preview_lbl = QLabel("No character loaded")
        self._preview_lbl.setAlignment(Qt.AlignCenter)
        self._preview_lbl.setStyleSheet("background-color: #0e0e11; border: 1px solid #22222a; border-radius: 8px; color: #71717a; font-size: 14px;")
        right_layout.addWidget(self._preview_lbl, 1)

        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)

    def _add_stat_row(self, grid: QGridLayout, row: int, label: str, val: str, color: str) -> QLabel:
        lbl_title = QLabel(label)
        lbl_title.setProperty("secondary", True)
        lbl_val = QLabel(val)
        lbl_val.setStyleSheet(f"color: {color};")
        font = QFont(lbl_val.font())
        font.setBold(True)
        lbl_val.setFont(font)
        grid.addWidget(lbl_title, row, 0)
        grid.addWidget(lbl_val, row, 1)
        return lbl_val

    def _browse_character(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Character Artwork",
            os.path.expanduser("~"),
            "Image Files (*.png *.jpg *.jpeg *.webp);;All Files (*)",
        )
        if path:
            self._char_edit.setText(path)

    def _browse_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select MediaPipe Task Model",
            os.path.expanduser("~"),
            "Task Models (*.task);;All Files (*)",
        )
        if path:
            self._model_edit.setText(path)

    def _browse_rig(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Target Character Rig Sidecar",
            os.path.expanduser("~"),
            "Rig Files (*.rig.json);;All Files (*)",
        )
        if path:
            if not path.endswith(".rig.json"):
                path += ".rig.json"
            self._rig_edit.setText(path)

    def _on_character_path_changed(self) -> None:
        char_str = self._char_edit.text().strip()
        if not char_str:
            self._preview_lbl.clear()
            self._preview_lbl.setText("No character loaded")
            self._current_rig = None
            self._character_img = None
            self._use_char_btn.setEnabled(False)
            return

        char_path = Path(char_str)
        if not char_path.is_file():
            self._preview_lbl.setText("Character image file not found")
            return

        img = cv2.imread(str(char_path))
        if img is None:
            self._preview_lbl.setText("Failed to decode image format")
            return

        self._character_img = img
        def_rig = default_rig_path(char_path)
        self._rig_edit.setPlaceholderText(f"Default: {def_rig.name}")

        # Check if default rig already exists
        if def_rig.is_file():
            try:
                rig = load_rig(def_rig)
                self._display_rig(rig, def_rig)
                return
            except (ValueError, OSError, KeyError):
                pass

        self._render_character_preview(img)
        self._lbl_status.setText("Image loaded — Ready to derive rig")
        self._lbl_status.setStyleSheet("color: #38bdf8;")
        self._lbl_dimensions.setText(f"{img.shape[1]} x {img.shape[0]} px")
        self._lbl_points.setText("--")
        self._lbl_triangles.setText("--")

    def derive_rig(self) -> None:
        char_str = self._char_edit.text().strip()
        if not char_str or not Path(char_str).is_file():
            QMessageBox.warning(self, "Missing Character", "Please select a valid character reference image first.")
            return

        model_str = self._model_edit.text().strip()
        if not model_str or not Path(model_str).is_file():
            QMessageBox.warning(self, "Missing Task Model", "Please select a valid MediaPipe face_landmarker.task model file.")
            return

        char_path = Path(char_str)
        model_path = Path(model_str)
        rig_str = self._rig_edit.text().strip()
        rig_path = Path(rig_str) if rig_str else default_rig_path(char_path)

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

        delegate = "gpu" if self._delegate_combo.currentIndex() == 1 else "cpu"

        self._set_ui_locked(True)
        self._progress.setVisible(True)
        self._log_text.append(f"Starting rig derivation on {char_path.name} using {delegate.upper()} delegate...")

        self._derive_worker = DeriveRigWorker(char_path, model_path, rig_path, delegate, self)
        self._derive_worker.rig_derived.connect(self._on_rig_derived)
        self._derive_worker.error_occurred.connect(self._on_derive_error)
        self._derive_worker.start()

    def _on_rig_derived(self, rig: CharacterRig, rig_path_str: str) -> None:
        self._set_ui_locked(False)
        self._progress.setVisible(False)
        self._log_text.append(f"SUCCESS: Derived {rig.point_count} landmarks. Rig saved to {rig_path_str}")
        self._display_rig(rig, Path(rig_path_str))

    def _on_derive_error(self, user_msg: str, tech_details: str) -> None:
        self._set_ui_locked(False)
        self._progress.setVisible(False)
        self._log_text.append(f"ERROR: {user_msg}\n{tech_details}")
        QMessageBox.critical(self, "Derivation Error", f"{user_msg}\n\nEnsure character image has a clear, visible neutral face.")

    def _display_rig(self, rig: CharacterRig, path: Path) -> None:
        self._current_rig = rig
        self._lbl_status.setText("Verified & Ready")
        self._lbl_status.setStyleSheet("color: #10b981; font-weight: bold;")
        self._lbl_points.setText(f"{rig.point_count} landmarks")
        self._lbl_dimensions.setText(f"{rig.width} x {rig.height} px")
        self._lbl_triangles.setText(str(rig.topology))
        self._use_char_btn.setEnabled(True)

        self._refresh_preview()

    def _refresh_preview(self) -> None:
        if self._character_img is None:
            return
        if self._current_rig is None or (not self._check_show_points.isChecked() and not self._check_show_hull.isChecked()):
            self._render_character_preview(self._character_img)
            return
        self._render_rig_overlay(self._character_img, self._current_rig)

    def _render_character_preview(self, img: np.ndarray) -> None:
        h, w = img.shape[:2]
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
        pix = QPixmap.fromImage(qimg)
        scaled = pix.scaled(self._preview_lbl.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._preview_lbl.setPixmap(scaled)

    def _render_rig_overlay(self, img: np.ndarray, rig: CharacterRig) -> None:
        overlay = img.copy()
        pts = rig.points.astype(int)

        # Draw landmark points
        if self._check_show_points.isChecked():
            for pt in pts:
                cv2.circle(overlay, tuple(pt), 2, (0, 255, 255), -1, cv2.LINE_AA)

        # Draw convex hull boundary
        if self._check_show_hull.isChecked() and len(pts) >= 3:
            hull = cv2.convexHull(pts)
            cv2.polylines(overlay, [hull], True, (0, 255, 0), 1, cv2.LINE_AA)

        # Blend overlay with original
        blended = cv2.addWeighted(overlay, 0.75, img, 0.25, 0)
        self._render_character_preview(blended)

    def _use_in_studio(self) -> None:
        char_str = self._char_edit.text().strip()
        if not char_str or not Path(char_str).is_file():
            return
        char_path = Path(char_str)
        rig_str = self._rig_edit.text().strip()
        rig_path = Path(rig_str) if rig_str else default_rig_path(char_path)

        self.character_selected.emit(char_path, rig_path)

    def set_selected_character(self, char_path: Path, model_path: Path | None = None) -> None:
        self._char_edit.setText(str(char_path))
        if model_path:
            self._model_edit.setText(str(model_path))

    def _set_ui_locked(self, locked: bool) -> None:
        self._derive_btn.setEnabled(not locked)
        self._browse_char_btn.setEnabled(not locked)
        self._browse_model_btn.setEnabled(not locked)
        self._browse_rig_btn.setEnabled(not locked)
        self._char_edit.setEnabled(not locked)
        self._model_edit.setEnabled(not locked)
        self._rig_edit.setEnabled(not locked)
        self._delegate_combo.setEnabled(not locked)
