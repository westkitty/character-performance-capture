import numpy as np
import pytest

import cpc.capture as capture_module
from cpc.capture import CameraConfig, CameraInfo, CameraSource
from cpc.diagnostics import probe_runtime
from cpc.performance import PerformanceFrame


class FakeCamera:
    def __init__(self, config: CameraConfig) -> None:
        self.config = config
        self.opened = False
        self.closed = False

    def open(self) -> None:
        self.opened = True

    def info(self) -> CameraInfo:
        return CameraInfo(backend="FAKE", width=640, height=480, fps=30.0)

    def read(self) -> np.ndarray:
        return np.zeros((480, 640, 3), dtype=np.uint8)

    def close(self) -> None:
        self.closed = True


class FakeTracker:
    name = "fake-tracker"
    profile = "fake-profile"

    def __init__(self) -> None:
        self.started = False
        self.closed = False

    def start(self) -> None:
        self.started = True

    def track(
        self,
        frame: np.ndarray,
        *,
        frame_index: int,
        timestamp_s: float,
    ) -> PerformanceFrame:
        del frame
        return PerformanceFrame(
            frame_index=frame_index,
            timestamp_s=timestamp_s,
            tracked=True,
            tracker=self.name,
            profile=self.profile,
        )

    def close(self) -> None:
        self.closed = True


def test_runtime_probe_reports_camera_tracker_and_privacy_state():
    cameras: list[FakeCamera] = []

    def factory(config: CameraConfig) -> FakeCamera:
        camera = FakeCamera(config)
        cameras.append(camera)
        return camera

    tracker = FakeTracker()
    report = probe_runtime(
        CameraConfig(index=2, width=1280, height=720, fps=60.0),
        tracker=tracker,
        sample_frames=3,
        camera_factory=factory,
    )

    assert report["schema_version"] == 1
    assert report["camera"]["index"] == 2
    assert report["camera"]["backend"] == "FAKE"
    assert report["camera"]["reported"] == {"width": 640, "height": 480, "fps": 30.0}
    assert report["camera"]["observed_frame"] == {"width": 640, "height": 480, "channels": 3}
    assert report["camera"]["sample_frames"] == 3
    assert report["tracker"]["name"] == "fake-tracker"
    assert report["tracker"]["tracked_frames"] == 3
    assert report["tracker"]["tracking_rate"] == 1.0
    assert report["privacy"] == {
        "camera_pixels_persisted": False,
        "network_required": False,
        "model_downloaded": False,
    }
    assert tracker.started is True
    assert tracker.closed is True
    assert cameras[0].opened is True
    assert cameras[0].closed is True


def test_runtime_probe_closes_camera_and_tracker_when_tracking_fails():
    cameras: list[FakeCamera] = []

    def factory(config: CameraConfig) -> FakeCamera:
        camera = FakeCamera(config)
        cameras.append(camera)
        return camera

    class BrokenTracker(FakeTracker):
        def track(
            self,
            frame: np.ndarray,
            *,
            frame_index: int,
            timestamp_s: float,
        ) -> PerformanceFrame:
            del frame, frame_index, timestamp_s
            raise RuntimeError("tracker failed")

    tracker = BrokenTracker()
    with pytest.raises(RuntimeError, match="tracker failed"):
        probe_runtime(
            CameraConfig(),
            tracker=tracker,
            sample_frames=2,
            camera_factory=factory,
        )

    assert tracker.closed is True
    assert cameras[0].closed is True


def test_runtime_probe_rejects_empty_sample():
    with pytest.raises(ValueError, match="sample_frames must be at least 1"):
        probe_runtime(CameraConfig(), tracker=FakeTracker(), sample_frames=0)


def test_camera_source_info_reports_backend_and_negotiated_properties(monkeypatch):
    class FakeVideoCapture:
        def __init__(self, index: int) -> None:
            self.index = index
            self.released = False

        def isOpened(self) -> bool:
            return True

        def set(self, prop: int, value: float) -> bool:
            del prop, value
            return True

        def get(self, prop: int) -> float:
            values = {
                capture_module.cv2.CAP_PROP_FRAME_WIDTH: 1920.0,
                capture_module.cv2.CAP_PROP_FRAME_HEIGHT: 1080.0,
                capture_module.cv2.CAP_PROP_FPS: 29.97,
            }
            return values[prop]

        def getBackendName(self) -> str:
            return "AVFOUNDATION"

        def release(self) -> None:
            self.released = True

    fake = FakeVideoCapture(4)
    monkeypatch.setattr(capture_module.cv2, "VideoCapture", lambda index: fake)

    source = CameraSource(CameraConfig(index=4))
    source.open()
    info = source.info()
    source.close()

    assert fake.index == 4
    assert info == CameraInfo(
        backend="AVFOUNDATION",
        width=1920,
        height=1080,
        fps=29.97,
    )
    assert fake.released is True
