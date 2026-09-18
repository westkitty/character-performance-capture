from pathlib import Path

import pytest

from cpc.calibration import CalibrationProfile, build_calibration_profile
from cpc.performance import PerformanceFrame


def _frame(index: int, jaw: float, yaw: float) -> PerformanceFrame:
    return PerformanceFrame(
        frame_index=index,
        timestamp_s=index / 30,
        tracked=True,
        tracker="test",
        blendshapes={"jawOpen": jaw},
        head_rotation_deg=(0.0, yaw, 0.0),
    )


def test_calibration_round_trip_and_no_media(tmp_path: Path):
    profile = build_calibration_profile([_frame(0, 0.1, -10), _frame(1, 0.5, 0), _frame(2, 1.0, 15)])
    path = tmp_path / "profile.json"
    profile.save(path)
    loaded = CalibrationProfile.load(path)
    assert loaded == profile
    text = path.read_text()
    assert "pixels" not in text
    assert "image" not in text


def test_calibration_unsupported_and_normalization():
    profile = build_calibration_profile([_frame(0, 0.1, 0), _frame(1, 0.5, 10), _frame(2, 0.9, 20)])
    assert "gaze_left_x" in profile.unavailable
    jaw = profile.channels["blendshape:jawOpen"]
    assert jaw.normalize(jaw.neutral) == 0
    assert jaw.normalize(jaw.maximum) == 1


def test_apply_calibration_preserves_original_portable_frame():
    from cpc.calibration import CalibrationProfile, ChannelRange, apply_calibration

    profile = CalibrationProfile(
        channels={
            "blendshape:jawOpen": ChannelRange(0.1, 0.1, 0.9),
            "head_yaw": ChannelRange(10.0, -20.0, 40.0),
        }
    )
    original = PerformanceFrame(
        frame_index=0,
        timestamp_s=0.0,
        tracked=True,
        tracker="test",
        blendshapes={"jawOpen": 0.5},
        head_rotation_deg=(0.0, 15.0, 0.0),
    )
    calibrated = apply_calibration(original, profile)
    assert calibrated.blendshapes["jawOpen"] == 0.5
    assert calibrated.head_rotation_deg == (0.0, 5.0, 0.0)
    assert original.head_rotation_deg == (0.0, 15.0, 0.0)
    assert original.metadata == {}


def test_calibrated_renderer_applies_loaded_profile_and_can_reset():
    from cpc.calibration import CalibratedRenderer, CalibrationProfile, ChannelRange

    seen = []

    class Renderer:
        name = "capture"
        def start(self): return None
        def render(self, frame, performance):
            seen.append(performance)
            return frame
        def close(self): return None

    wrapper = CalibratedRenderer(
        Renderer(),
        CalibrationProfile(
            channels={"blendshape:jawOpen": ChannelRange(0.2, 0.2, 1.0)}
        ),
    )
    frame = PerformanceFrame(
        0,
        0.0,
        True,
        "test",
        blendshapes={"jawOpen": 0.6},
    )
    wrapper.start()
    wrapper.render(None, frame)
    wrapper.set_profile(None)
    wrapper.render(None, frame)
    wrapper.close()
    assert seen[0].blendshapes["jawOpen"] == pytest.approx(0.5)
    assert seen[1] is frame
