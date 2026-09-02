from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from cpc.recording import read_capture


class TakesWorkspace(QWidget):
    """Graphical Capture Inspector for .cpc and partial takes."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Header banner
        header_banner = QFrame()
        header_banner.setStyleSheet("background-color: #1e1e24; border: 1px solid #27272a; border-radius: 6px; padding: 12px;")
        h_layout = QVBoxLayout(header_banner)
        h_layout.setContentsMargins(8, 8, 8, 8)
        h_layout.setSpacing(4)

        title = QLabel("Performance Take Inspector (.cpc)")
        font = QFont(title.font())
        font.setPointSize(15)
        font.setBold(True)
        title.setFont(font)
        h_layout.addWidget(title)

        privacy_notice = QLabel(
            "Privacy Note: CPC performance captures store facial landmark coordinates, head rotation matrices, "
            "and 52 blendshape coefficients. Camera pixels are never recorded or stored in .cpc files."
        )
        privacy_notice.setStyleSheet("color: #38bdf8; font-size: 12px;")
        privacy_notice.setWordWrap(True)
        h_layout.addWidget(privacy_notice)

        layout.addWidget(header_banner)

        # File picker bar
        picker_bar = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Select .cpc or .partial capture file to inspect...")
        self._path_edit.returnPressed.connect(self._inspect_current_path)
        picker_bar.addWidget(self._path_edit, 1)

        self._browse_btn = QPushButton("Open Take...")
        self._browse_btn.setProperty("primary", True)
        self._browse_btn.clicked.connect(self._browse_take)
        picker_bar.addWidget(self._browse_btn)

        self._inspect_btn = QPushButton("Inspect")
        self._inspect_btn.clicked.connect(self._inspect_current_path)
        picker_bar.addWidget(self._inspect_btn)

        layout.addLayout(picker_bar)

        # Inspection results grid
        results_group = QGroupBox("Capture Metadata & Integrity")
        grid = QGridLayout(results_group)
        grid.setContentsMargins(14, 18, 14, 14)
        grid.setSpacing(10)

        self._lbl_status = self._add_field(grid, 0, 0, "Capture Status:", "No take opened")
        self._lbl_frames = self._add_field(grid, 0, 1, "Recorded Frames:", "--")
        self._lbl_duration = self._add_field(grid, 1, 0, "Take Duration:", "--")
        self._lbl_fps = self._add_field(grid, 1, 1, "Average Frame Rate:", "--")
        self._lbl_tracker = self._add_field(grid, 2, 0, "Tracker Backend:", "--")
        self._lbl_profile = self._add_field(grid, 2, 1, "Performance Profile:", "--")
        self._lbl_created = self._add_field(grid, 3, 0, "Created Timestamp (UTC):", "--")
        self._lbl_filesize = self._add_field(grid, 3, 1, "File Size:", "--")

        layout.addWidget(results_group)

        # Raw Header / Metadata Viewer
        viewer_group = QGroupBox("Inspection Report (JSON)")
        v_layout = QVBoxLayout(viewer_group)
        v_layout.setContentsMargins(10, 14, 10, 10)

        self._json_view = QTextEdit()
        self._json_view.setReadOnly(True)
        self._json_view.setPlaceholderText("Inspection summary output...")
        v_layout.addWidget(self._json_view)

        layout.addWidget(viewer_group, 1)

    def _add_field(self, layout: QGridLayout, row: int, col: int, label: str, default: str) -> QLabel:
        col_idx = col * 2
        lbl_title = QLabel(label)
        lbl_title.setProperty("secondary", True)

        lbl_val = QLabel(default)
        font = QFont(lbl_val.font())
        font.setBold(True)
        lbl_val.setFont(font)

        layout.addWidget(lbl_title, row, col_idx)
        layout.addWidget(lbl_val, row, col_idx + 1)
        return lbl_val

    def _browse_take(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Performance Capture Take",
            str(Path.home()),
            "CPC Takes (*.cpc *.partial);;All Files (*)",
        )
        if file_path:
            self._path_edit.setText(file_path)
            self._inspect_file(Path(file_path))

    def _inspect_current_path(self) -> None:
        path_str = self._path_edit.text().strip()
        if not path_str:
            return
        p = Path(path_str)
        if not p.is_file():
            QMessageBox.warning(self, "File Not Found", f"Could not find take at:\n{p}")
            return
        self._inspect_file(p)

    def _inspect_file(self, path: Path) -> None:
        try:
            capture = read_capture(path)
        except (ValueError, RuntimeError, OSError, KeyError) as exc:
            QMessageBox.critical(self, "Inspection Error", f"Failed to inspect take: {exc}")
            return

        status_text = "COMPLETE TAKE" if capture.complete else "PARTIAL / RECOVERABLE"
        color = "#10b981" if capture.complete else "#f59e0b"
        self._lbl_status.setText(status_text)
        self._lbl_status.setStyleSheet(f"color: {color}; font-weight: bold;")

        self._lbl_frames.setText(f"{capture.frame_count:,} frames")
        self._lbl_duration.setText(f"{capture.duration_s:.3f} s")
        fps = (capture.frame_count / capture.duration_s) if capture.duration_s > 0 else 0.0
        self._lbl_fps.setText(f"{fps:.1f} FPS" if fps > 0 else "--")

        self._lbl_tracker.setText(str(capture.header.tracker))
        self._lbl_profile.setText(str(capture.header.profile))
        self._lbl_created.setText(str(capture.header.started_at_utc))

        size_kb = path.stat().st_size / 1024.0
        if size_kb > 1024:
            self._lbl_filesize.setText(f"{size_kb / 1024.0:.2f} MB")
        else:
            self._lbl_filesize.setText(f"{size_kb:.1f} KB")

        report_dict = {
            "path": str(path),
            "status": "complete" if capture.complete else "partial/recoverable",
            "format_name": capture.header.format_name,
            "version": capture.header.version,
            "started_at_utc": capture.header.started_at_utc,
            "tracker": capture.header.tracker,
            "profile": capture.header.profile,
            "frame_count": capture.frame_count,
            "duration_s": capture.duration_s,
            "effective_fps": fps,
            "file_size_bytes": path.stat().st_size,
        }
        self._json_view.setText(json.dumps(report_dict, indent=2))

    def inspect_path(self, path: Path) -> None:
        self._path_edit.setText(str(path))
        self._inspect_file(path)
