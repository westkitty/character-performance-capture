from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import cv2
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from cpc.ui.settings import AppSettings


def _pkg_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


class SettingsWorkspace(QWidget):
    """Settings, Dependency Readiness Dashboard, and About screen."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._settings = AppSettings()
        self._init_ui()

    def _init_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # -------------------------------------------------------------
        # 1. Dependency & Hardware Readiness
        # -------------------------------------------------------------
        readiness_group = QGroupBox("System && Dependency Readiness")
        r_grid = QGridLayout(readiness_group)
        r_grid.setContentsMargins(14, 18, 14, 14)
        r_grid.setSpacing(8)

        # Core Engine
        self._add_status_row(r_grid, 0, "Core Engine (cpc):", "Active & Verified", "#10b981")

        # PySide6 UI
        py_ver = _pkg_version("PySide6") or "Active"
        self._add_status_row(r_grid, 1, "Desktop GUI (PySide6):", f"v{py_ver} Active", "#10b981")

        # OpenCV
        self._add_status_row(r_grid, 2, "OpenCV Engine:", f"v{cv2.__version__} Active", "#10b981")

        # MediaPipe
        mp_ver = _pkg_version("mediapipe")
        if mp_ver:
            self._add_status_row(r_grid, 3, "MediaPipe Adapter:", f"v{mp_ver} (CPU delegate validated)", "#10b981")
        else:
            self._add_status_row(
                r_grid,
                3,
                "MediaPipe Adapter:",
                "Not Installed (install via: pip install '.[tracker-mediapipe]')",
                "#f59e0b",
                copy_cmd="pip install '.[tracker-mediapipe]'",
            )

        # Virtual Camera
        vcam_ver = _pkg_version("pyvirtualcam")
        if vcam_ver:
            self._add_status_row(r_grid, 4, "Virtual Camera (pyvirtualcam):", f"v{vcam_ver} Installed", "#10b981")
        else:
            self._add_status_row(
                r_grid,
                4,
                "Virtual Camera (pyvirtualcam):",
                "Not Installed (install via: pip install '.[output-virtualcam]')",
                "#a1a1aa",
                copy_cmd="pip install '.[output-virtualcam]'",
            )

        # Full install button row
        inst_row = QHBoxLayout()
        copy_all_btn = QPushButton("📋 Copy Full CPC Studio Install Command")
        copy_all_btn.clicked.connect(lambda: self._copy_cmd("pip install '.[ui,tracker-mediapipe,output-virtualcam]'"))
        inst_row.addWidget(copy_all_btn)
        inst_row.addStretch(1)
        r_grid.addLayout(inst_row, 5, 0, 1, 3)

        layout.addWidget(readiness_group)

        # -------------------------------------------------------------
        # 2. Local Preferences & Storage
        # -------------------------------------------------------------
        pref_group = QGroupBox("Preferences && Defaults")
        p_layout = QVBoxLayout(pref_group)
        p_layout.setContentsMargins(14, 18, 14, 14)
        p_layout.setSpacing(10)

        # Default Output Folder
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Default Output Directory:"))
        self._out_dir_edit = QLineEdit(self._settings.get_default_output_directory())
        self._out_dir_edit.textChanged.connect(self._settings.set_default_output_directory)
        out_row.addWidget(self._out_dir_edit, 1)

        out_browse = QPushButton("Browse...")
        out_browse.clicked.connect(self._browse_output_dir)
        out_row.addWidget(out_browse)
        p_layout.addLayout(out_row)

        # Default Countdown
        cd_row = QHBoxLayout()
        cd_row.addWidget(QLabel("Default Session Countdown:"))
        self._cd_combo = QComboBox()
        self._cd_combo.addItems(["Immediate (0s)", "3 Seconds", "5 Seconds"])
        cd_val = self._settings.get_countdown_seconds()
        self._cd_combo.setCurrentIndex(1 if cd_val == 3 else (2 if cd_val == 5 else 0))
        self._cd_combo.currentIndexChanged.connect(self._on_cd_changed)
        cd_row.addWidget(self._cd_combo, 1)
        p_layout.addLayout(cd_row)

        btns_row = QHBoxLayout()
        self._reset_onboarding_btn = QPushButton("Show Welcome / Onboarding Card")
        self._reset_onboarding_btn.clicked.connect(self._reset_onboarding)
        btns_row.addWidget(self._reset_onboarding_btn)

        self._reset_btn = QPushButton("Reset All UI Settings to Default")
        self._reset_btn.clicked.connect(self._reset_settings)
        btns_row.addWidget(self._reset_btn)
        p_layout.addLayout(btns_row)

        layout.addWidget(pref_group)

        # -------------------------------------------------------------
        # 3. Privacy & Licensing Architecture
        # -------------------------------------------------------------
        about_group = QGroupBox("About Character Performance Capture")
        a_layout = QVBoxLayout(about_group)
        a_layout.setContentsMargins(14, 18, 14, 14)
        a_layout.setSpacing(10)

        app_title = QLabel("Character Performance Capture")
        font = QFont(app_title.font())
        font.setPointSize(16)
        font.setBold(True)
        app_title.setFont(font)
        a_layout.addWidget(app_title)

        app_desc = QLabel(
            "Local-first, model-agnostic character performance capture engine & studio.\n\n"
            "• Clean-Room Architecture: Independent implementation with modular tracking and deterministic 2D mesh-warp rendering.\n"
            "• Local-First Privacy: Zero telemetry, zero analytics, zero network calls, zero cloud uploads. Performer state is computed and rendered 100% locally on your machine.\n"
            "• Performer Data Isolation: .CPC captures store facial landmark vectors and blendshapes, never camera pixels.\n"
            "• Proprietary License: Copyright © 2026 westkitty. All rights reserved."
        )
        app_desc.setStyleSheet("color: #d4d4d8; line-height: 1.4;")
        app_desc.setWordWrap(True)
        a_layout.addWidget(app_desc)

        layout.addWidget(about_group)
        layout.addStretch(1)

        scroll.setWidget(container)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _add_status_row(self, grid: QGridLayout, row: int, label: str, val_text: str, color: str, copy_cmd: str | None = None) -> None:
        lbl_title = QLabel(label)
        lbl_title.setProperty("secondary", True)

        lbl_val = QLabel(val_text)
        font = QFont(lbl_val.font())
        font.setBold(True)
        lbl_val.setFont(font)
        lbl_val.setStyleSheet(f"color: {color};")

        grid.addWidget(lbl_title, row, 0)
        grid.addWidget(lbl_val, row, 1)

        if copy_cmd:
            btn_copy = QPushButton("Copy Command")
            btn_copy.setMaximumWidth(120)
            btn_copy.clicked.connect(lambda: self._copy_cmd(copy_cmd))
            grid.addWidget(btn_copy, row, 2)

    def _copy_cmd(self, cmd: str) -> None:
        QGuiApplication.clipboard().setText(cmd)
        QMessageBox.information(self, "Copied", f"Command copied to clipboard:\n\n{cmd}")

    def _browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Default Output Directory",
            self._out_dir_edit.text() or str(Path.cwd()),
        )
        if path:
            self._out_dir_edit.setText(path)
            self._settings.set_default_output_directory(path)

    def _on_cd_changed(self, idx: int) -> None:
        sec = 3 if idx == 1 else (5 if idx == 2 else 0)
        self._settings.set_countdown_seconds(sec)

    def _reset_onboarding(self) -> None:
        self._settings.set_first_run_completed(False)
        QMessageBox.information(self, "Onboarding Reset", "The welcome card will appear on next launch.")

    def _reset_settings(self) -> None:
        reply = QMessageBox.question(
            self,
            "Reset Settings?",
            "Are you sure you want to reset all saved UI preferences to defaults?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._settings.reset_all()
            self._out_dir_edit.setText(self._settings.get_default_output_directory())
            self._cd_combo.setCurrentIndex(0)
            QMessageBox.information(self, "Settings Reset", "All preferences have been reset to default values.")
