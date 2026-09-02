from __future__ import annotations

import cv2
import numpy as np
import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from cpc.recording import PerformanceRecorder
from cpc.rig import CharacterRig, save_rig
from cpc.session import SessionConfig
from cpc.tracking import PerformanceFrame
from cpc.ui.widgets.clean_preview_window import CleanPreviewWindow
from cpc.ui.widgets.command_preview import CommandPreviewWidget
from cpc.ui.widgets.preview_widget import PreviewWidget
from cpc.ui.widgets.telemetry_widget import TelemetryWidget
from cpc.ui.workspaces.character_workspace import CharacterWorkspace
from cpc.ui.workspaces.diagnostics_workspace import DiagnosticsWorkspace
from cpc.ui.workspaces.live_workspace import LiveWorkspace
from cpc.ui.workspaces.settings_workspace import SettingsWorkspace
from cpc.ui.workspaces.takes_workspace import TakesWorkspace


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def test_preview_widget_rendering(qapp):
    widget = PreviewWidget()
    widget.resize(640, 480)
    widget.set_state("idle")
    assert widget._state == "idle"

    # Feed a dummy BGR frame
    dummy = np.zeros((240, 320, 3), dtype=np.uint8)
    dummy[50:100, 50:100] = (0, 255, 0)
    widget.update_frame(dummy)
    assert widget._pixmap is not None
    assert not widget._pixmap.isNull()

    widget.set_metrics(30.0, 15.0)
    assert widget._fps_text == "30.0 FPS"
    assert widget._latency_text == "15.0 ms"

    widget.set_countdown_number(3)
    assert widget._countdown_count == 3

    widget.set_calibration_toast("● Neutral Pose Calibrated")
    assert widget._calibrated_toast_text == "● Neutral Pose Calibrated"

    widget.clear_frame()
    assert widget._pixmap is None


def test_clean_preview_window(qapp):
    win = CleanPreviewWindow()
    win.resize(640, 480)
    win.show()

    dummy = np.zeros((240, 320, 3), dtype=np.uint8)
    win.update_frame(dummy)
    win.set_metrics(60.0, 16.6)
    win.set_state("tracking")

    # Toggle Always on Top
    win._toggle_always_on_top(True)
    win._toggle_always_on_top(False)

    # Change HUD Mode
    win._on_hud_changed(1)  # Minimal
    win._on_hud_changed(2)  # Hidden
    win._on_hud_changed(0)  # Full

    closed = []
    win.window_closed.connect(lambda: closed.append(True))
    win.close()
    assert len(closed) == 1


def test_telemetry_widget_update_and_reset(qapp):
    widget = TelemetryWidget()
    widget.update_telemetry({
        "state": "tracking",
        "current_fps": 29.8,
        "processed_frames": 150,
        "elapsed_s": 5.02,
        "tracking_rate": 0.95,
        "source_backend": "AVFOUNDATION",
        "source_width": 1280,
        "source_height": 720,
        "source_reported_fps": 30.0,
        "tracker_name": "mediapipe",
        "tracker_latency_ms": 14.5,
        "render_latency_ms": 2.1,
        "landmark_count": 478,
        "blendshape_count": 52,
        "recording_cpc": True,
        "recording_video": False,
        "virtual_camera": True,
        "vcam_device": "OBS Virtual Camera",
    })

    assert "Tracking" in widget._lbl_state.text()
    assert "29.8 FPS" in widget._lbl_fps.text()
    assert "150" in widget._lbl_frames.text()
    assert "RECORDING" in widget._lbl_out_cpc.text()
    assert "Active" in widget._lbl_out_vcam.text()

    widget.reset()
    assert widget._lbl_state.text() == "Idle"
    assert widget._lbl_fps.text() == "--"
    assert widget._lbl_out_cpc.text() == "Inactive"


def test_command_preview_widget(qapp, tmp_path):
    widget = CommandPreviewWidget()
    cfg = SessionConfig(
        source_type="camera",
        camera_index=1,
        mirror=True,
        tracker_type="null",
        renderer_type="passthrough",
    )
    widget.update_command(cfg)
    cmd = widget._cmd_edit.text()
    assert "cpc" in cmd
    assert "--camera 1" in cmd
    assert "--mirror" in cmd


def test_live_workspace_interaction(qapp, tmp_path):
    workspace = LiveWorkspace()
    workspace.resize(1000, 600)
    workspace.show()

    # By default, camera index 0 with null tracker is valid
    assert workspace.start_btn.isEnabled()

    # Change to video mode without file -> should disable start button
    workspace.source_panel._combo_source_type.setCurrentIndex(1)
    assert not workspace.start_btn.isEnabled()
    assert workspace._validation_banner_widget.isVisible()

    # Provide a valid video file
    vid_file = tmp_path / "sample.mp4"
    vid_file.touch()
    workspace.source_panel._video_edit.setText(str(vid_file))
    assert workspace.start_btn.isEnabled()
    assert not workspace._validation_banner_widget.isVisible()

    # Recenter / Neutral Calibration
    workspace.calibrate_neutral()

    # Open clean preview
    workspace.open_clean_preview()
    assert workspace._clean_preview_win is not None
    workspace._clean_preview_win.close()
    assert workspace._clean_preview_win is None

    cfg = workspace.get_session_config()
    assert cfg.source_type == "video"
    assert cfg.video_path == vid_file
    workspace.close()


def test_character_workspace_interaction(qapp, tmp_path):
    workspace = CharacterWorkspace()
    workspace.resize(900, 600)
    workspace.show()

    char_img = tmp_path / "test_char.png"
    img = np.zeros((100, 80, 3), dtype=np.uint8)
    cv2.imwrite(str(char_img), img)

    # Save a dummy rig sidecar
    pts = np.zeros((10, 2), dtype=np.float32)
    save_rig(CharacterRig(width=80, height=100, points=pts), tmp_path / "test_char.png.rig.json")

    workspace._char_edit.setText(str(char_img))
    assert workspace._existing_rig_banner.isVisible()
    assert workspace._btn_step1_next.isEnabled()

    # Toggle favorite
    workspace._toggle_favorite()
    assert workspace._settings.is_favorite("characters", str(char_img)) is True
    workspace._toggle_favorite()
    assert workspace._settings.is_favorite("characters", str(char_img)) is False

    workspace.close()


def test_takes_workspace_inspection_and_batch(qapp, tmp_path):
    workspace = TakesWorkspace()
    workspace.resize(800, 500)
    workspace.show()

    take_file1 = tmp_path / "sample_take1.cpc"
    with PerformanceRecorder(take_file1, tracker="test_tracker", profile="test_profile") as rec:
        rec.write(PerformanceFrame(tracker="test_tracker", frame_index=0, timestamp_s=0.0, tracked=True))
        rec.write(PerformanceFrame(tracker="test_tracker", frame_index=1, timestamp_s=0.033, tracked=True))

    take_file2 = tmp_path / "sample_take2.cpc"
    with PerformanceRecorder(take_file2, tracker="test_tracker_2", profile="test_profile_2") as rec:
        rec.write(PerformanceFrame(tracker="test_tracker_2", frame_index=0, timestamp_s=0.0, tracked=True))

    # Inspect single take
    workspace.inspect_path(take_file1)
    assert "COMPLETE TAKE" in workspace._lbl_status.text()
    assert "2 frames" in workspace._lbl_frames.text()
    assert "test_tracker" in workspace._lbl_tracker.text()

    # Batch inspect
    workspace._batch_inspect([take_file1, take_file2])
    assert workspace._batch_table.rowCount() == 2

    workspace.close()


def test_diagnostics_workspace(qapp):
    workspace = DiagnosticsWorkspace()
    workspace.resize(900, 600)

    assert workspace._run_btn.isEnabled()
    assert workspace._source_combo.count() == 2
    assert workspace._tracker_combo.count() == 2

    # Test populate from session config
    cfg = SessionConfig(
        source_type="camera",
        camera_index=3,
        tracker_type="mediapipe",
        tracker_delegate="gpu",
    )
    workspace.populate_from_session_config(cfg)
    assert workspace._cam_spin.value() == 3
    assert workspace._delegate_combo.currentIndex() == 1


def test_settings_workspace(qapp):
    workspace = SettingsWorkspace()
    workspace.resize(800, 500)
    assert workspace._reset_btn.isEnabled()
