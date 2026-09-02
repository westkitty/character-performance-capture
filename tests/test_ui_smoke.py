from __future__ import annotations

import cv2
import numpy as np
import pytest

pytest.importorskip("PySide6")
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication

from cpc.session import SessionConfig
from cpc.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def test_main_window_construction_and_tab_navigation(qapp):
    window = MainWindow()
    assert "Character Performance Capture" in window.windowTitle()
    assert window.minimumWidth() >= 1024
    assert window.minimumHeight() >= 680

    # Verify all 5 workspaces exist
    assert window._tabs.count() == 5
    assert window._tabs.tabText(0) == "Studio (Live)"
    assert "Character" in window._tabs.tabText(1)
    assert window._tabs.tabText(2) == "Takes"
    assert window._tabs.tabText(3) == "Diagnostics"
    assert "Settings" in window._tabs.tabText(4)

    # Switch across tabs
    for idx in range(5):
        window._tabs.setCurrentIndex(idx)
        assert window._tabs.currentIndex() == idx

    window.close()


def test_main_window_session_run_and_close(qapp, tmp_path):
    # Prepare dummy video
    vid_path = tmp_path / "smoke_clip.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(vid_path), fourcc, 30.0, (160, 120))
    for _ in range(20):
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        out.write(frame)
    out.release()

    window = MainWindow()
    cfg = SessionConfig(
        source_type="video",
        video_path=vid_path,
        loop_video=True,
        tracker_type="null",
        renderer_type="passthrough",
    )
    window.live_workspace.set_session_config(cfg)

    # Start session
    window.live_workspace.start_session()
    assert window.live_workspace.is_running()
    assert not window.live_workspace.start_btn.isEnabled()
    assert window.live_workspace.stop_btn.isEnabled()

    # Stop session
    window.live_workspace.stop_session()
    if window.live_workspace._worker is not None:
        assert window.live_workspace._worker.wait(4000)

    assert not window.live_workspace.is_running()

    # Trigger closeEvent
    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted()
