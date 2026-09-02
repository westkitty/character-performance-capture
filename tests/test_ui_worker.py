from __future__ import annotations

import time

import cv2
import numpy as np
import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from cpc.session import SessionConfig
from cpc.ui.worker import DeriveRigWorker, DiagnosticsWorker, SessionWorker


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def test_session_worker_lifecycle(qapp, tmp_path):
    # Create a small dummy video file
    vid_path = tmp_path / "dummy.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(vid_path), fourcc, 30.0, (160, 120))
    for _ in range(10):
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        out.write(frame)
    out.release()

    cfg = SessionConfig(
        source_type="video",
        video_path=vid_path,
        tracker_type="null",
        renderer_type="passthrough",
        frames=5,
    )

    worker = SessionWorker(cfg)
    frames_received = []
    states_received = []
    telemetry_received = []
    finished = []

    worker.frame_ready.connect(lambda f, p, m: frames_received.append(f))
    worker.state_changed.connect(lambda s: states_received.append(s))
    worker.telemetry_updated.connect(lambda t: telemetry_received.append(t))
    worker.session_finished.connect(lambda: finished.append(True))

    worker.start()
    assert worker.wait(5000)
    qapp.processEvents()

    assert len(finished) == 1
    assert len(frames_received) >= 5
    assert "initializing" in states_received
    assert "running" in states_received
    assert len(telemetry_received) >= 1
    assert telemetry_received[-1]["processed_frames"] >= 5


def test_session_worker_stop_signal(qapp, tmp_path):
    vid_path = tmp_path / "loop_dummy.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(vid_path), fourcc, 30.0, (160, 120))
    for _ in range(30):
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        out.write(frame)
    out.release()

    cfg = SessionConfig(
        source_type="video",
        video_path=vid_path,
        loop_video=True,
        tracker_type="null",
        renderer_type="passthrough",
    )

    worker = SessionWorker(cfg)
    worker.start()
    # Wait until running
    for _ in range(20):
        if worker.isRunning():
            break
        time.sleep(0.05)

    worker.stop()
    assert worker.wait(4000)
    qapp.processEvents()
    assert not worker.isRunning()


def test_session_worker_initialization_error(qapp, tmp_path):
    # Non-existent video path
    cfg = SessionConfig(
        source_type="video",
        video_path=tmp_path / "does_not_exist.mp4",
    )

    worker = SessionWorker(cfg)
    errors = []
    worker.error_occurred.connect(lambda msg, tech: errors.append(msg))
    worker.start()
    assert worker.wait(4000)
    qapp.processEvents()

    assert len(errors) == 1
    assert "video file not found" in errors[0]


def test_diagnostics_worker(qapp, tmp_path):
    vid_path = tmp_path / "diag_dummy.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(vid_path), fourcc, 30.0, (160, 120))
    for _ in range(15):
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        out.write(frame)
    out.release()

    cfg = SessionConfig(
        source_type="video",
        video_path=vid_path,
        tracker_type="null",
    )

    worker = DiagnosticsWorker(cfg, sample_frames=5)
    reports = []
    worker.probe_finished.connect(lambda r: reports.append(r))
    worker.start()
    assert worker.wait(5000)
    qapp.processEvents()

    assert len(reports) == 1
    report = reports[0]
    assert report["schema_version"] == 1
    assert report["privacy"]["camera_pixels_persisted"] is False
    assert report["camera"]["sample_frames"] == 5


def test_derive_rig_worker_error(qapp, tmp_path):
    worker = DeriveRigWorker(
        character_path=tmp_path / "non_existent.png",
        model_path=tmp_path / "non_existent.task",
    )
    errors = []
    worker.error_occurred.connect(lambda msg, tech: errors.append(msg))
    worker.start()
    assert worker.wait(4000)
    qapp.processEvents()

    assert len(errors) == 1
    assert "Failed to derive" in errors[0]
