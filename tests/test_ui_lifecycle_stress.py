from __future__ import annotations

import cv2
import numpy as np
import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from cpc.session import SessionConfig
from cpc.ui.widgets.preview_widget import PreviewWidget
from cpc.ui.workspaces.live_workspace import LiveWorkspace


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def test_preview_widget_memory_safety_and_modes(qapp):
    widget = PreviewWidget()
    widget.resize(640, 480)
    widget.show()

    # Pass ephemeral NumPy buffer
    raw_frame = np.zeros((240, 320, 3), dtype=np.uint8)
    raw_frame[50:100, 50:100] = [0, 255, 0]  # Green square
    widget.update_frame(raw_frame)

    assert widget._pixmap is not None
    assert not widget._pixmap.isNull()
    assert widget._frame_count == 1

    # Overwrite original NumPy buffer to prove QPixmap owns its memory independently
    raw_frame.fill(255)
    assert widget._pixmap is not None

    # Performance Mode HUD
    widget.set_performance_mode(True)
    assert widget._performance_mode is True
    widget.set_performance_mode(False)
    assert widget._performance_mode is False

    widget.clear_frame()
    assert widget._pixmap is None
    widget.close()


def test_live_workspace_multi_session_lifecycle(qapp, tmp_path):
    # Prepare dummy video
    vid_path = tmp_path / "lifecycle_clip.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(vid_path), fourcc, 30.0, (160, 120))
    for _ in range(30):
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        out.write(frame)
    out.release()

    workspace = LiveWorkspace()
    workspace.resize(1100, 700)
    workspace.show()

    cfg = SessionConfig(
        source_type="video",
        video_path=vid_path,
        loop_video=True,
        tracker_type="null",
        renderer_type="passthrough",
    )
    workspace.set_session_config(cfg)

    # Session 1: Start -> Stop
    workspace.start_session()
    assert workspace.is_running()
    workspace.stop_session()
    if workspace._worker is not None:
        assert workspace._worker.wait(4000)
    assert not workspace.is_running()

    # Session 2: Start -> Stop
    workspace.start_session()
    assert workspace.is_running()
    workspace.stop_session()
    if workspace._worker is not None:
        assert workspace._worker.wait(4000)
    assert not workspace.is_running()

    # Performance Mode
    workspace.toggle_performance_mode()
    assert workspace._performance_mode is True
    workspace.toggle_performance_mode()
    assert workspace._performance_mode is False

    workspace.close()
