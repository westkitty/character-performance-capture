import numpy as np
import pytest

from cpc.performance import Landmark, PerformanceFrame
from cpc.renderer import RigWarpRenderer
from cpc.rig import CharacterRig


def _face_mesh(n_side: int = 7) -> np.ndarray:
    xs, ys = np.meshgrid(
        np.linspace(60, 260, n_side), np.linspace(60, 320, n_side)
    )
    return np.column_stack([xs.ravel(), ys.ravel()]).astype(np.float32)


def _rig() -> CharacterRig:
    return CharacterRig(width=320, height=384, points=_face_mesh(), topology="grid-49")


def _character() -> np.ndarray:
    rng = np.random.default_rng(7)
    img = rng.integers(30, 220, size=(384, 320, 3), dtype=np.uint8)
    return img


def _perf(
    points: np.ndarray,
    *,
    tracked=True,
    confidence=None,
    index=0,
    ts=0.0,
    head_rotation_deg=None,
) -> PerformanceFrame:
    return PerformanceFrame(
        frame_index=index,
        timestamp_s=ts,
        tracked=tracked,
        tracker="fake",
        profile="grid-49",
        tracking_confidence=confidence,
        head_rotation_deg=head_rotation_deg,
        landmarks=tuple(Landmark(float(x), float(y)) for x, y in points),
    )


def _normalized_from_rig(rig: CharacterRig, jitter: np.ndarray | None = None) -> np.ndarray:
    pts = rig.points.copy()
    if jitter is not None:
        pts = pts + jitter
    pts = pts / np.array([rig.width, rig.height], dtype=np.float32)
    return pts


def test_untracked_frame_returns_character_reference_unchanged():
    rig, char = _rig(), _character()
    r = RigWarpRenderer(rig, char)
    r.start()
    out = r.render(np.zeros((10, 10, 3), np.uint8), _perf(np.zeros((49, 2)), tracked=False))
    assert out.shape == char.shape and out.dtype == np.uint8
    assert np.array_equal(out, char)
    r.close()


def test_first_tracked_frame_calibrates_and_returns_reference():
    rig, char = _rig(), _character()
    r = RigWarpRenderer(rig, char)
    r.start()
    norm = _normalized_from_rig(rig)
    out = r.render(char, _perf(norm))
    assert np.array_equal(out, char)
    r.close()


def test_second_tracked_frame_reacts_but_stays_valid():
    rig, char = _rig(), _character()
    r = RigWarpRenderer(rig, char)
    r.start()
    r.render(char, _perf(_normalized_from_rig(rig), index=0, ts=0.0))

    jitter = np.zeros_like(rig.points)
    jitter[20:30] += np.array([9.0, -6.0], dtype=np.float32)  # local "expression"
    out = r.render(char, _perf(_normalized_from_rig(rig, jitter), index=1, ts=0.033))

    assert out.shape == char.shape and out.dtype == np.uint8
    assert np.isfinite(out).all()
    assert not np.array_equal(out, char)
    r.close()


def test_low_confidence_frame_is_safe_passthrough():
    rig, char = _rig(), _character()
    r = RigWarpRenderer(rig, char, confidence_threshold=0.5)
    r.start()
    r.render(char, _perf(_normalized_from_rig(rig)))
    out = r.render(char, _perf(_normalized_from_rig(rig), confidence=0.1, index=1, ts=0.1))
    assert np.array_equal(out, char)
    r.close()


def test_landmark_count_mismatch_is_safe_passthrough():
    rig, char = _rig(), _character()
    r = RigWarpRenderer(rig, char)
    r.start()
    short = _normalized_from_rig(rig)[:10]
    out = r.render(char, _perf(short))
    assert np.array_equal(out, char)
    r.close()


def test_pathological_landmarks_are_clamped_to_a_valid_image():
    # The schema guarantees finite landmarks, so the renderer only has to defend
    # against wildly out-of-range (but finite) geometry.
    rig, char = _rig(), _character()
    r = RigWarpRenderer(rig, char)
    r.start()
    r.render(char, _perf(_normalized_from_rig(rig), index=0, ts=0.0))

    wild = _normalized_from_rig(rig)
    wild[5] = [1e6, -1e6]
    wild[6] = [-4.0e5, 8.0e5]
    out = r.render(char, _perf(wild, index=1, ts=0.033))
    assert out.shape == char.shape and out.dtype == np.uint8
    assert np.isfinite(out).all()
    r.close()


def test_head_rotation_is_applied_relative_to_calibrated_neutral():
    rig, char = _rig(), _character()
    r = RigWarpRenderer(rig, char, head_gain=1.0)
    r.start()
    norm = _normalized_from_rig(rig)

    # calibrate at a non-zero resting head pose
    r.render(char, _perf(norm, index=0, ts=0.0, head_rotation_deg=(6.0, -3.0, 28.0)))

    # a frame at the SAME head pose must not add any head transform -> reference
    same = r.render(char, _perf(norm, index=1, ts=0.03, head_rotation_deg=(6.0, -3.0, 28.0)))
    assert np.array_equal(same, char)

    # a real head turn away from neutral changes the output
    turned = r.render(char, _perf(norm, index=2, ts=0.06, head_rotation_deg=(6.0, 22.0, 28.0)))
    assert turned.shape == char.shape and np.isfinite(turned).all()
    assert not np.array_equal(turned, char)
    r.close()


def test_constructor_rejects_bad_character_image():
    rig = _rig()
    with pytest.raises(ValueError):
        RigWarpRenderer(rig, np.zeros((10, 10), np.uint8))
    with pytest.raises(ValueError):
        RigWarpRenderer(rig, np.zeros((100, 100, 3), np.uint8))  # wrong dims vs rig


def test_close_is_idempotent_and_restartable():
    rig, char = _rig(), _character()
    r = RigWarpRenderer(rig, char)
    r.start()
    r.close()
    r.close()
    r.start()
    out = r.render(char, _perf(_normalized_from_rig(rig), tracked=False))
    assert np.array_equal(out, char)
    r.close()
