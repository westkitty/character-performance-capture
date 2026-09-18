from pathlib import Path

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
