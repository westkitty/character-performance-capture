from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QImage, QPixmap
from PySide6.QtWidgets import (
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
from cpc.ui.worker import DeriveRigWorker


class CharacterWorkspace(QWidget):
    """Dedicated Character & Rig derivation and inspection studio."""

    character_selected = Signal(Path, Path)  # (character_path, rig_path)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_rig: CharacterRig | None = None
        self._character_img: np.ndarray | None = None
        self._worker: DeriveRigWorker | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        splitter = QSplitter(Qt.Horizontal)

        # -------------------------------------------------------------
        # Left Panel: Steps & Controls
        # -------------------------------------------------------------
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        setup_group = QGroupBox("Character & Rig Configuration")
        grid = QGridLayout(setup_group)
        grid.setContentsMargins(12, 16, 12, 12)
        grid.setSpacing(8)

        # Step 1: Character Reference Image
        grid.addWidget(QLabel("1. Character Image:"), 0, 0)
        self._char_edit = QLineEdit()
        self._char_edit.setPlaceholderText("Select character reference image...")
        self._char_edit.textChanged.connect(self._on_character_path_changed)
        grid.addWidget(self._char_edit, 0, 1)

        self._char_browse_btn = QPushButton("Browse...")
        self._char_browse_btn.clicked.connect(self._browse_character)
        grid.addWidget(self._char_browse_btn, 0, 2)

        # Step 2: Face Landmarker Model
        grid.addWidget(QLabel("2. Tracker Model:"), 1, 0)
        self._model_edit = QLineEdit()
        self._model_edit.setPlaceholderText("Select face_landmarker.task model...")
        grid.addWidget(self._model_edit, 1, 1)

        self._model_browse_btn = QPushButton("Browse...")
        self._model_browse_btn.clicked.connect(self._browse_model)
        grid.addWidget(self._model_browse_btn, 1, 2)

        # Step 3: Delegate
        grid.addWidget(QLabel("3. Inference Delegate:"), 2, 0)
        self._delegate_combo = QComboBox()
        self._delegate_combo.addItem("CPU (Validated Default)", "cpu")
        self._delegate_combo.addItem("GPU (Experimental)", "gpu")
        grid.addWidget(self._delegate_combo, 2, 1, 1, 2)

        # Step 4: Output Rig Path
        grid.addWidget(QLabel("4. Destination Rig Sidecar:"), 3, 0)
        self._rig_edit = QLineEdit()
        self._rig_edit.setPlaceholderText("Default: <character>.rig.json")
        grid.addWidget(self._rig_edit, 3, 1)

        self._rig_browse_btn = QPushButton("Browse...")
        self._rig_browse_btn.clicked.connect(self._browse_rig_dest)
        grid.addWidget(self._rig_browse_btn, 3, 2)

        left_layout.addWidget(setup_group)

        # Action Buttons
        self._derive_btn = QPushButton("⚡  Derive Character Rig")
        self._derive_btn.setProperty("primary", True)
        self._derive_btn.setMinimumHeight(38)
        font = QFont(self._derive_btn.font())
        font.setPointSize(13)
        font.setBold(True)
        self._derive_btn.setFont(font)
        self._derive_btn.clicked.connect(self.derive_rig)
        left_layout.addWidget(self._derive_btn)

        self._use_char_btn = QPushButton("✔  Use Character in Live Studio")
        self._use_char_btn.setMinimumHeight(34)
        self._use_char_btn.setEnabled(False)
        self._use_char_btn.clicked.connect(self._use_in_live_studio)
        left_layout.addWidget(self._use_char_btn)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        left_layout.addWidget(self._progress)

        # Rig Metadata Summary
        summary_group = QGroupBox("Rig Verification Status")
        sum_layout = QGridLayout(summary_group)
        sum_layout.setContentsMargins(10, 14, 10, 10)
        sum_layout.setSpacing(6)

        self._lbl_status = QLabel("Pending selection")
        self._lbl_status.setStyleSheet("color: #a1a1aa; font-weight: bold;")
        sum_layout.addWidget(QLabel("Status:"), 0, 0)
        sum_layout.addWidget(self._lbl_status, 0, 1)

        self._lbl_points = QLabel("--")
        sum_layout.addWidget(QLabel("Landmark Points:"), 1, 0)
        sum_layout.addWidget(self._lbl_points, 1, 1)

        self._lbl_dimensions = QLabel("--")
        sum_layout.addWidget(QLabel("Rig Dimensions:"), 2, 0)
        sum_layout.addWidget(self._lbl_dimensions, 2, 1)

        self._lbl_triangles = QLabel("--")
        sum_layout.addWidget(QLabel("Triangles:"), 3, 0)
        sum_layout.addWidget(self._lbl_triangles, 3, 1)

        left_layout.addWidget(summary_group)

        # Technical Details / Log
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setPlaceholderText("Rig derivation and validation log...")
        self._log_view.setMaximumHeight(160)
        left_layout.addWidget(self._log_view)

        left_layout.addStretch(1)
        splitter.addWidget(left_widget)

        # -------------------------------------------------------------
        # Right Panel: Character & Mesh Triangulation Preview
        # -------------------------------------------------------------
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self._preview_lbl = QLabel("No character loaded")
        self._preview_lbl.setAlignment(Qt.AlignCenter)
        self._preview_lbl.setStyleSheet("background-color: #18181b; border: 1px solid #27272a; border-radius: 6px;")
        self._preview_lbl.setMinimumSize(480, 480)
        right_layout.addWidget(self._preview_lbl, 1)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

    def _browse_character(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Character Reference Image",
            str(Path.home()),
            "Image Files (*.png *.jpg *.jpeg *.webp);;All Files (*)",
        )
        if file_path:
            self._char_edit.setText(file_path)

    def _browse_model(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Face Landmarker Model",
            str(Path.home()),
            "MediaPipe Task (*.task);;All Files (*)",
        )
        if file_path:
            self._model_edit.setText(file_path)

    def _browse_rig_dest(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Rig Destination",
            str(Path.home() / "character.rig.json"),
            "JSON Rig Files (*.json);;All Files (*)",
        )
        if file_path:
            self._rig_edit.setText(file_path)

    def _on_character_path_changed(self) -> None:
        char_str = self._char_edit.text().strip()
        if not char_str or not Path(char_str).is_file():
            self._preview_lbl.setText("No character loaded")
            self._character_img = None
            self._current_rig = None
            self._use_char_btn.setEnabled(False)
            return

        char_path = Path(char_str)
        img = cv2.imread(str(char_path))
        if img is None:
            self._preview_lbl.setText("Failed to read image")
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
        model_str = self._model_edit.text().strip()

        if not char_str or not Path(char_str).is_file():
            QMessageBox.warning(self, "Missing Character", "Please select a valid character reference image.")
            return
        if not model_str or not Path(model_str).is_file():
            QMessageBox.warning(self, "Missing Model", "Please select a valid face_landmarker.task model file.")
            return

        char_path = Path(char_str)
        model_path = Path(model_str)
        rig_str = self._rig_edit.text().strip()
        rig_dest = Path(rig_str) if rig_str else default_rig_path(char_path)

        if rig_dest.is_file():
            reply = QMessageBox.question(
                self,
                "Overwrite Rig Sidecar?",
                f"Rig sidecar already exists at:\n{rig_dest}\n\nDo you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        self._derive_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._log_view.append(f"Starting rig derivation for {char_path.name}...")

        delegate = self._delegate_combo.currentData()
        self._worker = DeriveRigWorker(char_path, model_path, rig_dest, delegate=delegate, parent=self)
        self._worker.rig_derived.connect(self._on_rig_derived)
        self._worker.error_occurred.connect(self._on_rig_error)
        self._worker.start()

    def _on_rig_derived(self, rig: CharacterRig, path_str: str) -> None:
        self._derive_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._worker = None

        self._display_rig(rig, Path(path_str))
        self._log_view.append(f"Successfully derived rig: {rig.point_count} points, {len(rig.triangles)} triangles.")
        QMessageBox.information(
            self,
            "Rig Derivation Complete",
            f"Successfully derived character rig!\n\nWritten to: {path_str}\nPoints: {rig.point_count}\nTriangles: {len(rig.triangles)}",
        )

    def _on_rig_error(self, user_msg: str, tech_details: str) -> None:
        self._derive_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._worker = None
        self._log_view.append(f"ERROR: {user_msg}\n{tech_details}")
        QMessageBox.critical(self, "Derivation Error", f"{user_msg}\n\nTechnical details:\n{tech_details}")

    def _display_rig(self, rig: CharacterRig, path: Path) -> None:
        self._current_rig = rig
        self._lbl_status.setText("Verified & Ready")
        self._lbl_status.setStyleSheet("color: #10b981; font-weight: bold;")
        self._lbl_points.setText(f"{rig.point_count} landmarks")
        self._lbl_dimensions.setText(f"{rig.width} x {rig.height} px")
        self._lbl_triangles.setText(str(rig.topology))
        self._use_char_btn.setEnabled(True)

        if self._character_img is not None:
            self._render_rig_overlay(self._character_img, rig)

    def _render_character_preview(self, img: np.ndarray) -> None:
        h, w = img.shape[:2]
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)
        scaled = pix.scaled(self._preview_lbl.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._preview_lbl.setPixmap(scaled)

    def _render_rig_overlay(self, img: np.ndarray, rig: CharacterRig) -> None:
        overlay = img.copy()
        pts = rig.points.astype(int)

        # Draw landmark points
        for pt in pts:
            cv2.circle(overlay, tuple(pt), 2, (0, 255, 255), -1, cv2.LINE_AA)

        # Draw convex hull outline
        if len(pts) >= 3:
            hull = cv2.convexHull(pts)
            cv2.polylines(overlay, [hull], True, (0, 255, 0), 1, cv2.LINE_AA)

        # Blend with original
        blended = cv2.addWeighted(overlay, 0.75, img, 0.25, 0)
        self._render_character_preview(blended)

    def _use_in_live_studio(self) -> None:
        char_str = self._char_edit.text().strip()
        rig_str = self._rig_edit.text().strip()
        if char_str and Path(char_str).is_file():
            char_p = Path(char_str)
            rig_p = Path(rig_str) if rig_str and Path(rig_str).is_file() else default_rig_path(char_p)
            self.character_selected.emit(char_p, rig_p)

    def set_selected_character(self, character_path: Path, model_path: Path | None = None) -> None:
        self._char_edit.setText(str(character_path))
        if model_path:
            self._model_edit.setText(str(model_path))
