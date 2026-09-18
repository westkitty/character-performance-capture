from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent, QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from cpc.recording import read_capture
from cpc.takes import TakeAnnotations, TakeMarker, TakeTimeline
from cpc.ui.settings import AppSettings


class TakesWorkspace(QWidget):
    """Calm, Library-First Capture Inspector for .cpc takes with instant metadata and batch inspection."""

    open_live_studio = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._current_take_path: Path | None = None
        self._settings = AppSettings()
        self._timeline: TakeTimeline | None = None
        self._annotations: TakeAnnotations | None = None
        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._playback_tick)
        self._init_ui()
        self.refresh_library()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # -------------------------------------------------------------
        # 0. Header Bar with Calm Privacy Note
        # -------------------------------------------------------------
        header_bar = QWidget()
        h_layout = QHBoxLayout(header_bar)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(12)

        title_col = QVBoxLayout()
        title = QLabel("Takes Library & Inspector (.cpc)")
        font = QFont(title.font())
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        title_col.addWidget(title)

        privacy_notice = QLabel(
            "🔒 Local Performance Data Only — .cpc files store facial landmark coordinates, head rotation matrices, "
            "and 52 blendshapes; camera pixels are never recorded."
        )
        privacy_notice.setStyleSheet("color: #9ca3af; font-size: 12px;")
        privacy_notice.setWordWrap(True)
        title_col.addWidget(privacy_notice)
        h_layout.addLayout(title_col, 1)

        # Quick Actions
        self._browse_btn = QPushButton("📂  Open Take...")
        self._browse_btn.setProperty("primary", True)
        self._browse_btn.setMinimumHeight(36)
        self._browse_btn.clicked.connect(self._browse_take)
        h_layout.addWidget(self._browse_btn)

        self._browse_batch_btn = QPushButton("📊  Batch Inspect...")
        self._browse_batch_btn.setMinimumHeight(36)
        self._browse_batch_btn.clicked.connect(self._browse_batch_takes)
        h_layout.addWidget(self._browse_batch_btn)

        layout.addWidget(header_bar)

        # -------------------------------------------------------------
        # 1. Main View Tabs (Takes Library vs Batch Table)
        # -------------------------------------------------------------
        self._tabs = QTabWidget()

        # Tab 1: Library & Single Take Inspector Splitter
        lib_tab = QWidget()
        lt_layout = QHBoxLayout(lib_tab)
        lt_layout.setContentsMargins(0, 8, 0, 0)
        lt_layout.setSpacing(0)

        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setHandleWidth(2)

        # Left Column: Recent Takes List / Table
        left_box = QWidget()
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(8)

        list_head = QHBoxLayout()
        list_lbl = QLabel("Recent Recordings")
        list_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #ffffff;")
        list_head.addWidget(list_lbl, 1)

        btn_rescan = QPushButton("↻ Refresh")
        btn_rescan.setMaximumWidth(80)
        btn_rescan.clicked.connect(self.refresh_library)
        list_head.addWidget(btn_rescan)
        left_layout.addLayout(list_head)

        self._takes_table = QTableWidget()
        self._takes_table.setColumnCount(4)
        self._takes_table.setHorizontalHeaderLabels(["Take Name", "Status", "Duration", "Frames"])
        self._takes_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._takes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._takes_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._takes_table.setSelectionMode(QTableWidget.SingleSelection)
        self._takes_table.itemSelectionChanged.connect(self._on_table_selection_changed)
        left_layout.addWidget(self._takes_table, 1)

        self._empty_lib_lbl = QLabel("No recordings found in takes folder.\n\nCapture a performance in Studio to see takes here.")
        self._empty_lib_lbl.setAlignment(Qt.AlignCenter)
        self._empty_lib_lbl.setStyleSheet(
            "QLabel { background-color: #121218; border: 1px dashed #22222e; border-radius: 8px; color: #71717a; font-size: 13px; padding: 20px; }"
        )
        self._empty_lib_lbl.setVisible(False)
        left_layout.addWidget(self._empty_lib_lbl)

        self._splitter.addWidget(left_box)

        # Right Column: Take Inspection Details Card
        right_box = QWidget()
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(10)

        self._details_card = QFrame()
        self._details_card.setStyleSheet("background-color: #14141c; border: 1px solid #232330; border-radius: 8px; padding: 14px;")
        dc_layout = QVBoxLayout(self._details_card)
        dc_layout.setSpacing(12)

        # Header with status pill
        dh_row = QHBoxLayout()
        self._take_title_lbl = QLabel("No Take Selected")
        d_font = QFont(self._take_title_lbl.font())
        d_font.setPointSize(14)
        d_font.setBold(True)
        self._take_title_lbl.setFont(d_font)
        dh_row.addWidget(self._take_title_lbl, 1)

        self._lbl_status = QLabel("● Ready")
        self._lbl_status.setStyleSheet("font-weight: 700; font-size: 12px; color: #10b981;")
        dh_row.addWidget(self._lbl_status)
        dc_layout.addLayout(dh_row)

        # Metadata Grid
        grid = QGridLayout()
        grid.setSpacing(10)
        self._lbl_frames = self._add_field(grid, 0, 0, "Frames:", "--")
        self._lbl_duration = self._add_field(grid, 0, 1, "Duration:", "--")
        self._lbl_fps = self._add_field(grid, 1, 0, "Frame Rate:", "--")
        self._lbl_filesize = self._add_field(grid, 1, 1, "File Size:", "--")
        self._lbl_tracker = self._add_field(grid, 2, 0, "Tracker Backend:", "--")
        self._lbl_profile = self._add_field(grid, 2, 1, "Performance Profile:", "--")
        self._lbl_created = self._add_field(grid, 3, 0, "Created (UTC):", "--")
        dc_layout.addLayout(grid)

        timeline_box = QFrame()
        timeline_box.setStyleSheet("background-color: #101016; border: 1px solid #252532; border-radius: 6px; padding: 8px;")
        tl = QVBoxLayout(timeline_box)
        tl.setSpacing(6)
        tl.addWidget(QLabel("Performance Timeline"))
        self._timeline_slider = QSlider(Qt.Horizontal)
        self._timeline_slider.setRange(0, 0)
        self._timeline_slider.valueChanged.connect(self._on_timeline_changed)
        tl.addWidget(self._timeline_slider)
        self._frame_detail_lbl = QLabel("No frame selected")
        self._frame_detail_lbl.setWordWrap(True)
        self._frame_detail_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        tl.addWidget(self._frame_detail_lbl)

        transport = QHBoxLayout()
        self._step_back_btn = QPushButton("◀ Frame")
        self._step_back_btn.clicked.connect(lambda: self._step_frame(-1))
        transport.addWidget(self._step_back_btn)
        self._play_btn = QPushButton("▶ Play")
        self._play_btn.clicked.connect(self._toggle_playback)
        transport.addWidget(self._play_btn)
        self._step_forward_btn = QPushButton("Frame ▶")
        self._step_forward_btn.clicked.connect(lambda: self._step_frame(1))
        transport.addWidget(self._step_forward_btn)
        transport.addWidget(QLabel("Speed:"))
        self._speed_combo = QComboBox()
        self._speed_combo.addItems(["0.25x", "0.5x", "1.0x", "1.5x", "2.0x"])
        self._speed_combo.setCurrentText("1.0x")
        transport.addWidget(self._speed_combo)
        tl.addLayout(transport)

        loop_row = QHBoxLayout()
        loop_row.addWidget(QLabel("Loop frames:"))
        self._loop_start = QSpinBox()
        self._loop_end = QSpinBox()
        self._loop_start.setRange(0, 0)
        self._loop_end.setRange(0, 0)
        loop_row.addWidget(self._loop_start)
        loop_row.addWidget(QLabel("to"))
        loop_row.addWidget(self._loop_end)
        self._loop_btn = QPushButton("Set Loop")
        self._loop_btn.clicked.connect(self._toggle_loop)
        loop_row.addWidget(self._loop_btn)
        tl.addLayout(loop_row)

        note_row = QHBoxLayout()
        self._marker_edit = QLineEdit()
        self._marker_edit.setPlaceholderText("Marker / note for current frame")
        note_row.addWidget(self._marker_edit, 1)
        self._marker_btn = QPushButton("Add Marker")
        self._marker_btn.clicked.connect(self._add_marker)
        note_row.addWidget(self._marker_btn)
        self._compare_btn = QPushButton("A/B Compare...")
        self._compare_btn.clicked.connect(self._compare_take)
        note_row.addWidget(self._compare_btn)
        tl.addLayout(note_row)
        self._comparison_lbl = QLabel("")
        self._comparison_lbl.setWordWrap(True)
        self._comparison_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        tl.addWidget(self._comparison_lbl)
        dc_layout.addWidget(timeline_box)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._reveal_btn = QPushButton("📁  Reveal in Finder")
        self._reveal_btn.setEnabled(False)
        self._reveal_btn.clicked.connect(self._reveal_in_finder)
        btn_row.addWidget(self._reveal_btn)

        self._copy_path_btn = QPushButton("📋  Copy Path")
        self._copy_path_btn.setEnabled(False)
        self._copy_path_btn.clicked.connect(self._copy_path)
        btn_row.addWidget(self._copy_path_btn)

        self._export_json_btn = QPushButton("📄  Export JSON...")
        self._export_json_btn.setEnabled(False)
        self._export_json_btn.clicked.connect(self._export_report_json)
        btn_row.addWidget(self._export_json_btn)
        btn_row.addStretch(1)
        dc_layout.addLayout(btn_row)

        # Collapsible JSON details
        self._toggle_json_btn = QPushButton("▸ Technical JSON Metadata")
        self._toggle_json_btn.setStyleSheet("text-align: left; background: transparent; border: none; color: #9ca3af; font-size: 12px;")
        self._toggle_json_btn.clicked.connect(self._toggle_json_view)
        dc_layout.addWidget(self._toggle_json_btn)

        self._json_view = QTextEdit()
        self._json_view.setReadOnly(True)
        self._json_view.setMaximumHeight(160)
        self._json_view.setVisible(False)
        dc_layout.addWidget(self._json_view)

        right_layout.addWidget(self._details_card)
        right_layout.addStretch(1)

        self._splitter.addWidget(right_box)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 1)

        lt_layout.addWidget(self._splitter)
        self._tabs.addTab(lib_tab, "Takes Library")

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

    def _toggle_json_view(self) -> None:
        vis = not self._json_view.isVisible()
        self._json_view.setVisible(vis)
        self._toggle_json_btn.setText("▾ Technical JSON Metadata" if vis else "▸ Technical JSON Metadata")

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

    def refresh_library(self) -> None:
        """Scan takes folder and recent takes into the library table."""
        takes_dir = Path(self._settings.get_default_output_directory())
        found_takes: list[Path] = []

        if takes_dir.is_dir():
            found_takes.extend(sorted(takes_dir.glob("*.cpc"), reverse=True))
            found_takes.extend(sorted(takes_dir.glob("*.partial"), reverse=True))

        # Include recents
        recents = self._settings.get_recent_items("takes")
        for r in recents:
            rp = Path(r)
            if rp.is_file() and rp not in found_takes:
                found_takes.append(rp)

        self._takes_table.setRowCount(0)
        if not found_takes:
            self._takes_table.setVisible(False)
            self._empty_lib_lbl.setVisible(True)
            return

        self._takes_table.setVisible(True)
        self._empty_lib_lbl.setVisible(False)

        for i, p in enumerate(found_takes):
            self._takes_table.insertRow(i)
            name_item = QTableWidgetItem(p.name)
            name_item.setData(Qt.UserRole, str(p))
            self._takes_table.setItem(i, 0, name_item)

            try:
                cap = read_capture(p)
                status = "Complete" if cap.complete else "Partial"

                item_stat = QTableWidgetItem(status)
                item_stat.setForeground(Qt.green if cap.complete else Qt.yellow)
                self._takes_table.setItem(i, 1, item_stat)
                self._takes_table.setItem(i, 2, QTableWidgetItem(f"{cap.duration_s:.1f}s"))
                self._takes_table.setItem(i, 3, QTableWidgetItem(f"{cap.frame_count:,}"))
            except (RuntimeError, ValueError, OSError, KeyError):
                self._takes_table.setItem(i, 1, QTableWidgetItem("Corrupt / Unknown"))
                self._takes_table.setItem(i, 2, QTableWidgetItem("--"))
                self._takes_table.setItem(i, 3, QTableWidgetItem("--"))

        if self._takes_table.rowCount() > 0:
            self._takes_table.selectRow(0)

    def _on_table_selection_changed(self) -> None:
        selected_rows = self._takes_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        item = self._takes_table.item(row, 0)
        if item:
            path_str = item.data(Qt.UserRole)
            if path_str:
                self.inspect_path(Path(path_str))

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
            self.refresh_library()

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
                self.refresh_library()
                event.acceptProposedAction()
                return

    def inspect_path(self, path: Path) -> None:
        try:
            capture = read_capture(path)
        except (ValueError, RuntimeError, OSError, KeyError) as exc:
            QMessageBox.critical(self, "Inspection Error", f"Failed to inspect take: {exc}")
            return

        self._current_take_path = path
        self._timeline = TakeTimeline(capture)
        self._annotations = TakeAnnotations.load(path)
        max_index = max(0, capture.frame_count - 1)
        self._timeline_slider.setRange(0, max_index)
        self._timeline_slider.setValue(0)
        self._loop_start.setRange(0, max_index)
        self._loop_end.setRange(0, max_index)
        self._loop_end.setValue(max_index)
        self._play_timer.stop()
        self._play_btn.setText("▶ Play")
        self._update_frame_detail()
        self._take_title_lbl.setText(path.name)
        status_text = "● COMPLETE TAKE" if capture.complete else "▲ PARTIAL / RECOVERABLE"
        color = "#10b981" if capture.complete else "#f59e0b"
        self._lbl_status.setText(status_text)
        self._lbl_status.setStyleSheet(f"color: {color}; font-weight: bold;")

        self._lbl_frames.setText(f"{capture.frame_count:,} frames")
        self._lbl_duration.setText(f"{capture.duration_s:.2f} s")
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

        self._reveal_btn.setEnabled(True)
        self._copy_path_btn.setEnabled(True)
        self._export_json_btn.setEnabled(True)

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


    def _on_timeline_changed(self, value: int) -> None:
        if self._timeline is None or not self._timeline.frames:
            return
        self._timeline.position = max(0, min(value, len(self._timeline.frames) - 1))
        self._update_frame_detail()

    def _update_frame_detail(self) -> None:
        if self._timeline is None or not self._timeline.frames:
            self._frame_detail_lbl.setText("No performance frames")
            return
        frame = self._timeline.current()
        confidence = "—" if frame.tracking_confidence is None else f"{frame.tracking_confidence:.2f}"
        head = "—" if frame.head_rotation_deg is None else ", ".join(f"{v:.1f}°" for v in frame.head_rotation_deg)
        major_names = ("jawOpen", "mouthSmileLeft", "mouthSmileRight", "eyeBlinkLeft", "eyeBlinkRight", "browInnerUp")
        major = ", ".join(
            f"{name}={frame.blendshapes[name]:.2f}"
            for name in major_names
            if name in frame.blendshapes
        ) or "no major expression channels"
        self._frame_detail_lbl.setText(
            f"Frame {frame.frame_index} • {frame.timestamp_s:.3f}s • "
            f"tracked={frame.tracked} • confidence={confidence} • head=({head}) • {major}"
        )

    def _step_frame(self, delta: int) -> None:
        if self._timeline is None or not self._timeline.frames:
            return
        frame = self._timeline.step(delta)
        self._timeline_slider.setValue(self._timeline.position)
        self._update_frame_detail()
        if frame is None:
            return

    def _toggle_playback(self) -> None:
        if self._timeline is None or not self._timeline.frames:
            return
        if self._play_timer.isActive():
            self._play_timer.stop()
            self._play_btn.setText("▶ Play")
            return
        speed = float(self._speed_combo.currentText().removesuffix("x"))
        self._play_timer.start(max(8, round(33 / speed)))
        self._play_btn.setText("⏸ Pause")

    def _playback_tick(self) -> None:
        if self._timeline is None or not self._timeline.frames:
            self._play_timer.stop()
            return
        old = self._timeline.position
        self._timeline.step(1)
        if self._timeline.loop is None and self._timeline.position == old:
            self._play_timer.stop()
            self._play_btn.setText("▶ Play")
        self._timeline_slider.setValue(self._timeline.position)

    def _toggle_loop(self) -> None:
        if self._timeline is None or not self._timeline.frames:
            return
        if self._timeline.loop is not None:
            self._timeline.clear_loop()
            self._loop_btn.setText("Set Loop")
            return
        try:
            self._timeline.set_loop(self._loop_start.value(), self._loop_end.value())
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Loop", str(exc))
            return
        self._loop_btn.setText("Clear Loop")

    def _add_marker(self) -> None:
        if self._timeline is None or self._annotations is None:
            return
        note = self._marker_edit.text().strip()
        if not note:
            return
        frame = self._timeline.current()
        self._annotations.add(TakeMarker(frame.frame_index, note))
        self._annotations.save()
        self._marker_edit.clear()
        self._comparison_lbl.setText(
            f"Saved {len(self._annotations.markers)} marker(s) in sidecar metadata; original take unchanged."
        )

    def _compare_take(self) -> None:
        if self._timeline is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Compare Against Take",
            self._settings.get_last_directory(),
            "CPC Takes (*.cpc *.partial);;All Files (*)",
        )
        if not path:
            return
        try:
            other = read_capture(Path(path))
        except (ValueError, RuntimeError, OSError, KeyError) as exc:
            QMessageBox.warning(self, "Comparison Error", str(exc))
            return
        current = self._timeline.capture
        current_tracked = sum(1 for frame in current.frames if frame.tracked)
        other_tracked = sum(1 for frame in other.frames if frame.tracked)
        current_rate = current_tracked / current.frame_count if current.frame_count else 0.0
        other_rate = other_tracked / other.frame_count if other.frame_count else 0.0
        self._comparison_lbl.setText(
            f"A/B: current {current.frame_count} frames / {current.duration_s:.2f}s / "
            f"{current_rate:.0%} tracked; {Path(path).name} {other.frame_count} frames / "
            f"{other.duration_s:.2f}s / {other_rate:.0%} tracked."
        )

    def _copy_path(self) -> None:
        if self._current_take_path:
            QApplication.clipboard().setText(str(self._current_take_path.resolve()))
            QMessageBox.information(self, "Copied", "Take path copied to clipboard.")

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
