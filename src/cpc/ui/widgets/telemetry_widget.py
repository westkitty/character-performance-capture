from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QVBoxLayout, QWidget


class TelemetryWidget(QWidget):
    """Compact real-time telemetry panel displaying session, source, tracker, and output metrics."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(240)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(12)

        # 1. Session Group
        session_group = QGroupBox("Session")
        sg_layout = QGridLayout(session_group)
        sg_layout.setContentsMargins(10, 14, 10, 10)
        sg_layout.setSpacing(6)

        self._lbl_state = self._add_row(sg_layout, 0, "State:", "Idle")
        self._lbl_fps = self._add_row(sg_layout, 1, "Pipeline FPS:", "--")
        self._lbl_frames = self._add_row(sg_layout, 2, "Frames:", "0")
        self._lbl_elapsed = self._add_row(sg_layout, 3, "Elapsed:", "00:00.0")
        layout.addWidget(session_group)

        # 2. Source Group
        source_group = QGroupBox("Source Ingest")
        src_layout = QGridLayout(source_group)
        src_layout.setContentsMargins(10, 14, 10, 10)
        src_layout.setSpacing(6)

        self._lbl_src_backend = self._add_row(src_layout, 0, "Backend:", "--")
        self._lbl_src_res = self._add_row(src_layout, 1, "Resolution:", "--")
        self._lbl_src_fps = self._add_row(src_layout, 2, "Device FPS:", "--")
        layout.addWidget(source_group)

        # 3. Tracker Group
        tracker_group = QGroupBox("Tracker & Performance")
        trk_layout = QGridLayout(tracker_group)
        trk_layout.setContentsMargins(10, 14, 10, 10)
        trk_layout.setSpacing(6)

        self._lbl_tracker = self._add_row(trk_layout, 0, "Tracker:", "--")
        self._lbl_trk_status = self._add_row(trk_layout, 1, "Tracking:", "--")
        self._lbl_trk_rate = self._add_row(trk_layout, 2, "Track Rate:", "--")
        self._lbl_trk_latency = self._add_row(trk_layout, 3, "Tracker Latency:", "--")
        self._lbl_render_latency = self._add_row(trk_layout, 4, "Render Latency:", "--")
        self._lbl_landmarks = self._add_row(trk_layout, 5, "Landmarks:", "--")
        self._lbl_blendshapes = self._add_row(trk_layout, 6, "Blendshapes:", "--")
        layout.addWidget(tracker_group)

        # 4. Outputs Group
        outputs_group = QGroupBox("Active Outputs")
        out_layout = QGridLayout(outputs_group)
        out_layout.setContentsMargins(10, 14, 10, 10)
        out_layout.setSpacing(6)

        self._lbl_out_cpc = self._add_row(out_layout, 0, ".CPC Take:", "Inactive")
        self._lbl_out_video = self._add_row(out_layout, 1, "Rendered MP4:", "Inactive")
        self._lbl_out_vcam = self._add_row(out_layout, 2, "Virtual Camera:", "Inactive")
        layout.addWidget(outputs_group)

        layout.addStretch(1)

    def _add_row(self, layout: QGridLayout, row: int, label_text: str, default_val: str) -> QLabel:
        lbl_title = QLabel(label_text)
        lbl_title.setProperty("secondary", True)
        lbl_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        lbl_val = QLabel(default_val)
        lbl_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        font = QFont(lbl_val.font())
        font.setBold(True)
        lbl_val.setFont(font)

        layout.addWidget(lbl_title, row, 0)
        layout.addWidget(lbl_val, row, 1)
        return lbl_val

    def update_telemetry(self, data: dict[str, Any]) -> None:
        """Update display labels from the background worker telemetry payload."""
        state = data.get("state", "idle")
        if state == "tracking":
            self._lbl_state.setText("Tracking")
            self._lbl_state.setStyleSheet("color: #10b981;")
            self._lbl_trk_status.setText("TRACKED")
            self._lbl_trk_status.setStyleSheet("color: #10b981;")
        elif state == "tracking_lost":
            self._lbl_state.setText("Tracking Lost")
            self._lbl_state.setStyleSheet("color: #f59e0b;")
            self._lbl_trk_status.setText("LOST")
            self._lbl_trk_status.setStyleSheet("color: #f59e0b;")
        else:
            self._lbl_state.setText(state.capitalize())
            self._lbl_state.setStyleSheet("color: #e4e4e7;")
            self._lbl_trk_status.setText("--")
            self._lbl_trk_status.setStyleSheet("color: #a1a1aa;")

        fps = data.get("current_fps", 0.0)
        self._lbl_fps.setText(f"{fps:.1f} FPS" if fps > 0 else "--")

        frames = data.get("processed_frames", 0)
        self._lbl_frames.setText(f"{frames:,}")

        elapsed_s = data.get("elapsed_s", 0.0)
        mins = int(elapsed_s // 60)
        secs = elapsed_s % 60
        self._lbl_elapsed.setText(f"{mins:02d}:{secs:04.1f}")

        # Source
        backend = data.get("source_backend", "--")
        self._lbl_src_backend.setText(str(backend))

        w = data.get("source_width", 0)
        h = data.get("source_height", 0)
        self._lbl_src_res.setText(f"{w}x{h}" if w and h else "--")

        src_fps = data.get("source_reported_fps", 0.0)
        self._lbl_src_fps.setText(f"{src_fps:.1f} FPS" if src_fps > 0 else "--")

        # Tracker
        self._lbl_tracker.setText(str(data.get("tracker_name", "--")))
        rate = data.get("tracking_rate", 0.0) * 100.0
        self._lbl_trk_rate.setText(f"{rate:.1f}%")

        trk_lat = data.get("tracker_latency_ms", 0.0)
        self._lbl_trk_latency.setText(f"{trk_lat:.1f} ms" if trk_lat > 0 else "--")

        rnd_lat = data.get("render_latency_ms", 0.0)
        self._lbl_render_latency.setText(f"{rnd_lat:.1f} ms" if rnd_lat > 0 else "--")

        lm_count = data.get("landmark_count", 0)
        self._lbl_landmarks.setText(str(lm_count) if lm_count > 0 else "--")

        bs_count = data.get("blendshape_count", 0)
        self._lbl_blendshapes.setText(str(bs_count) if bs_count > 0 else "--")

        # Outputs
        if data.get("recording_cpc", False):
            self._lbl_out_cpc.setText("RECORDING")
            self._lbl_out_cpc.setStyleSheet("color: #ef4444;")
        else:
            self._lbl_out_cpc.setText("Inactive")
            self._lbl_out_cpc.setStyleSheet("color: #71717a;")

        if data.get("recording_video", False):
            self._lbl_out_video.setText("RECORDING")
            self._lbl_out_video.setStyleSheet("color: #ef4444;")
        else:
            self._lbl_out_video.setText("Inactive")
            self._lbl_out_video.setStyleSheet("color: #71717a;")

        if data.get("virtual_camera", False):
            v_dev = data.get("vcam_device") or "Active"
            self._lbl_out_vcam.setText(f"Active ({v_dev})")
            self._lbl_out_vcam.setStyleSheet("color: #8b5cf6;")
        else:
            self._lbl_out_vcam.setText("Inactive")
            self._lbl_out_vcam.setStyleSheet("color: #71717a;")

    def reset(self) -> None:
        """Clear metrics back to idle state."""
        self._lbl_state.setText("Idle")
        self._lbl_state.setStyleSheet("color: #e4e4e7;")
        self._lbl_fps.setText("--")
        self._lbl_frames.setText("0")
        self._lbl_elapsed.setText("00:00.0")
        self._lbl_src_backend.setText("--")
        self._lbl_src_res.setText("--")
        self._lbl_src_fps.setText("--")
        self._lbl_tracker.setText("--")
        self._lbl_trk_status.setText("--")
        self._lbl_trk_status.setStyleSheet("color: #a1a1aa;")
        self._lbl_trk_rate.setText("--")
        self._lbl_trk_latency.setText("--")
        self._lbl_render_latency.setText("--")
        self._lbl_landmarks.setText("--")
        self._lbl_blendshapes.setText("--")
        self._lbl_out_cpc.setText("Inactive")
        self._lbl_out_cpc.setStyleSheet("color: #71717a;")
        self._lbl_out_video.setText("Inactive")
        self._lbl_out_video.setStyleSheet("color: #71717a;")
        self._lbl_out_vcam.setText("Inactive")
        self._lbl_out_vcam.setStyleSheet("color: #71717a;")
