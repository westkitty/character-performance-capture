import numpy as np
import pytest

from cpc.virtualcam import VirtualCameraSink


class FakeCamera:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.width = kwargs["width"]
        self.height = kwargs["height"]
        self.fps = kwargs["fps"]
        self.backend = "fake"
        self.device = "Fake Camera"
        self.sent: list[np.ndarray] = []
        self.closed = False

    def send(self, frame):
        assert frame.dtype == np.uint8
        assert frame.shape == (self.height, self.width, 3)
        self.sent.append(frame.copy())

    def sleep_until_next_frame(self):
        pass

    def close(self):
        self.closed = True


def test_sink_negotiates_size_and_sends_rgb():
    made: list[FakeCamera] = []

    def factory(**kwargs):
        cam = FakeCamera(**kwargs)
        made.append(cam)
        return cam

    sink = VirtualCameraSink(32, 24, 30.0, camera_factory=factory)
    sink.start()
    assert sink.device == "Fake Camera"

    bgr = np.zeros((24, 32, 3), dtype=np.uint8)
    bgr[..., 0] = 255  # blue channel in BGR
    sink.send(bgr)
    sent = made[0].sent[0]
    assert sent[0, 0, 2] == 255 and sent[0, 0, 0] == 0  # became RGB

    sink.close()
    sink.close()
    assert made[0].closed is True


def test_sink_resizes_mismatched_frames():
    made: list[FakeCamera] = []
    sink = VirtualCameraSink(16, 16, 30.0, camera_factory=lambda **k: made.append(FakeCamera(**k)) or made[-1])
    sink.start()
    sink.send(np.zeros((40, 50, 3), dtype=np.uint8))
    assert made[0].sent[0].shape == (16, 16, 3)
    sink.close()


def test_sink_rejects_bad_dimensions():
    with pytest.raises(ValueError):
        VirtualCameraSink(0, 10, 30.0)
    with pytest.raises(ValueError):
        VirtualCameraSink(10, 10, 0.0)


def test_missing_backend_raises_actionable_error(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pyvirtualcam":
            raise ImportError("no module named pyvirtualcam")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    sink = VirtualCameraSink(32, 24, 30.0)
    with pytest.raises(RuntimeError, match="pyvirtualcam is not installed"):
        sink.start()
