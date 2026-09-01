import pytest

from cpc.performance import Landmark, PerformanceFrame


def test_performance_frame_round_trip_preserves_portable_state():
    frame = PerformanceFrame(
        frame_index=7,
        timestamp_s=0.25,
        tracked=True,
        tracker="fake-tracker",
        profile="arkit-compatible",
        tracking_confidence=0.9,
        blendshapes={"eyeBlinkLeft": 0.2, "jawOpen": 0.75},
        head_rotation_deg=(3.0, -5.0, 1.5),
        gaze_left=(0.1, -0.2),
        gaze_right=(0.12, -0.18),
        face_transform=tuple(float(index) for index in range(16)),
        landmarks=(Landmark(0.25, 0.5, -0.1),),
        metadata={"subject": "test"},
    )

    restored = PerformanceFrame.from_dict(frame.to_dict())

    assert restored == frame


def test_performance_frame_rejects_non_normalized_blendshape():
    with pytest.raises(ValueError, match="between 0 and 1"):
        PerformanceFrame(
            frame_index=0,
            timestamp_s=0.0,
            tracked=True,
            tracker="fake",
            blendshapes={"jawOpen": 1.2},
        )


def test_face_transform_must_be_four_by_four_flattened():
    with pytest.raises(ValueError, match="exactly 16"):
        PerformanceFrame(
            frame_index=0,
            timestamp_s=0.0,
            tracked=True,
            tracker="fake",
            face_transform=(1.0, 2.0),
        )
