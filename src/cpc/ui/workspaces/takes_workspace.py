from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent, QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from cpc.recording import read_capture
from cpc.ui.settings import AppSettings


class TakesWorkspace(QWidget):
    """Graphical Capture Inspector for .cpc and partial takes with batch inspection, drag/drop, and recents."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._current_take_path: Path | None = None
        self._settings = AppSettings()
        self._init_ui()
        self._load_recents()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Header banner
        header_banner = QFrame()
        header_banner.setStyleSheet("background-color: #16161d; border: 1px solid #23232c; border-radius: 8px; padding: 10px;")
        h_layout = QVBoxLayout(header_banner)
        h_layout.setContentsMargins(8, 6, 8, 6)
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
        privacy_notice.setStyleSheet("color: #60a5fa; font-size: 12px;")
        privacy_notice.setWordWrap(True)
        h_layout.addWidget(privacy_notice)

        layout.addWidget(header_banner)

        # Recents & Single/Batch file picker bar
        picker_bar = QHBoxLayout()
        picker_bar.setSpacing(8)

        self._recents_combo = QComboBox()
        self._recents_combo.setMinimumWidth(180)
        self._recents_combo.currentIndexChanged.connect(self._on_recent_selected)
        picker_bar.addWidget(self._recents_combo)

        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Select or drop .cpc / .partial file...")
        self._path_edit.returnPressed.connect(self._inspect_current_path)
        picker_bar.addWidget(self._path_edit, 1)

        self._browse_btn = QPushButton("Open Take...")
        self._browse_btn.setProperty("primary", True)
        self._browse_btn.clicked.connect(self._browse_take)
        picker_bar.addWidget(self._browse_btn)

        self._browse_batch_btn = QPushButton("Batch Inspect...")
        self._browse_batch_btn.setToolTip("Select multiple .cpc takes for batch inspection")
        self._browse_batch_btn.clicked.connect(self._browse_batch_takes)
        picker_bar.addWidget(self._browse_batch_btn)

        layout.addLayout(picker_bar)

        # Tabs: Single Take Inspection vs Batch Table
        self._tabs = QTabWidget()

        # Tab 1: Single Take Details
        single_tab = QWidget()
        s_layout = QVBoxLayout(single_tab)
        s_layout.setContentsMargins(0, 8, 0, 0)
        s_layout.setSpacing(10)

        # Inspection results grid
        results_group = QGroupBox("Capture Metadata && Integrity")
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

        s_layout.addWidget(results_group)

        # Report viewer
        viewer_group = QGroupBox("Inspection Report (JSON)")
        v_layout = QVBoxLayout(viewer_group)
        v_layout.setContentsMargins(10, 14, 10, 10)

        self._json_view = QTextEdit()
        self._json_view.setReadOnly(True)
        self._json_view.setPlaceholderText("Inspection summary output...")
        v_layout.addWidget(self._json_view)

        btn_row = QHBoxLayout()
        self._copy_btn = QPushButton("Copy JSON")
        self._copy_btn.clicked.connect(self._copy_report_json)
        self._export_json_btn = QPushButton("Export JSON...")
        self._export_json_btn.clicked.connect(self._export_report_json)
        self._reveal_btn = QPushButton("Reveal in Finder")
        self._reveal_btn.clicked.connect(self._reveal_in_finder)
        btn_row.addWidget(self._copy_btn)
        btn_row.addWidget(self._export_json_btn)
        btn_row.addWidget(self._reveal_btn)
        btn_row.addStretch(1)
        v_layout.addLayout(btn_row)

        s_layout.addWidget(viewer_group, 1)
        self._tabs.addTab(single_tab, "Take Details")

        # Tab 2: Batch Multi-Take Inspector Table
        batch_tab = QWidget()
        b_layout = QVBoxLayout(batch_tab)
        b_layout.setContentsMargins(0, 8, 0, 0)
        b_layout.setSpacing(8)

        self._batch_table = QTableWidget()
        self._batch_table.setColumnCount(6)
        self._batch_table.setHorizontalHeaderLabels([
            "File Name",
            "Status",
            "Frames",
            "Duration (s)",
            "FPS",
            "Tracker",
        ])
        self._batch_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._batch_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        b_layout.addWidget(self._batch_table)

        self._tabs.addTab(batch_tab, "Batch Inspection")
        layout.addWidget(self._tabs, 1)

    def _load_recents(self) -> None:
        self._recents_combo.blockSignals(True)
        self._recents_combo.clear()
        self._recents_combo.addItem("Select Recent Take...", "")
        recents = self._settings.get_recent_items("takes")
        for r in recents:
            self._recents_combo.addItem(Path(r).name, r)
        self._recents_combo.blockSignals(False)

    def _on_recent_selected(self, idx: int) -> None:
        if idx <= 0:
            return
        path_str = self._recents_combo.itemData(idx)
        if path_str and Path(path_str).is_file():
            self.inspect_path(Path(path_str))

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
            self._settings.get_last_directory(),
            "CPC Takes (*.cpc *.partial);;All Files (*)",
        )
        if file_path:
            self._settings.set_last_directory(file_path)
            self._settings.add_recent_item("takes", file_path)
            self.inspect_path(Path(file_path))
            self._load_recents()

    def _browse_batch_takes(self) -> None:
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Takes for Batch Inspection",
            self._settings.get_last_directory(),
            "CPC Takes (*.cpc *.partial);;All Files (*)",
        )
        if file_paths:
            self._batch_inspect([Path(p) for p in file_paths])
            self._tabs.setCurrentIndex(1)

    def _batch_inspect(self, paths: list[Path]) -> None:
        self._batch_table.setRowCount(0)
        for i, p in enumerate(paths):
            self._batch_table.insertRow(i)
            self._batch_table.setItem(i, 0, QTableWidgetItem(p.name))
            try:
                cap = read_capture(p)
                status = "Complete" if cap.complete else "Partial"
                fps = (cap.frame_count / cap.duration_s) if cap.duration_s > 0 else 0.0
                
                item_stat = QTableWidgetItem(status)
                item_stat.setForeground(Qt.green if cap.complete else Qt.yellow)
                self._batch_table.setItem(i, 1, item_stat)
                self._batch_table.setItem(i, 2, QTableWidgetItem(f"{cap.frame_count:,}"))
                self._batch_table.setItem(i, 3, QTableWidgetItem(f"{cap.duration_s:.2f}"))
                self._batch_table.setItem(i, 4, QTableWidgetItem(f"{fps:.1f}"))
                self._batch_table.setItem(i, 5, QTableWidgetItem(str(cap.header.tracker)))
            except (ValueError, RuntimeError, OSError, KeyError) as exc:
                item_err = QTableWidgetItem(f"Error: {exc}")
                item_err.setForeground(Qt.red)
                self._batch_table.setItem(i, 1, item_err)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                p = Path(url.toLocalFile())
                if p.suffix.lower() in {".cpc", ".partial"}:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.suffix.lower() in {".cpc", ".partial"}:
                self._settings.add_recent_item("takes", p)
                self.inspect_path(p)
                self._load_recents()
                event.acceptProposedAction()
                return

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

        self._current_take_path = path
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
        self._tabs.setCurrentIndex(0)

    def _copy_report_json(self) -> None:
        text = self._json_view.toPlainText().strip()
        if text:
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "Copied", "Report JSON copied to clipboard.")

    def _export_report_json(self) -> None:
        text = self._json_view.toPlainText().strip()
        if not text:
            return
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Export Take Metadata JSON",
            self._settings.get_last_directory(),
            "JSON Files (*.json);;All Files (*)",
        )
        if dest:
            Path(dest).write_text(text, encoding="utf-8")
            QMessageBox.information(self, "Export Complete", f"Metadata saved to:\n{dest}")

    def _reveal_in_finder(self) -> None:
        if self._current_take_path and self._current_take_path.is_file():
            QDesktopServices.openUrl(f"file://{self._current_take_path.parent.resolve()}")

    def inspect_path(self, path: Path) -> None:
        self._path_edit.setText(str(path))
        self._inspect_file(path)
