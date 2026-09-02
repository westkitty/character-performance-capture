import numpy as np
import pytest

from cpc.geometry import (
    apply_affine,
    boundary_points,
    clamp_displacement,
    clamp_points,
    delaunay_triangles,
    matrix_to_euler_deg,
    similarity_transform,
    warp_image,
)


def _euler_matrix(pitch_deg, yaw_deg, roll_deg):
    px, py, pz = np.deg2rad([pitch_deg, yaw_deg, roll_deg])
    rx = np.array([[1, 0, 0], [0, np.cos(px), -np.sin(px)], [0, np.sin(px), np.cos(px)]])
    ry = np.array([[np.cos(py), 0, np.sin(py)], [0, 1, 0], [-np.sin(py), 0, np.cos(py)]])
    rz = np.array([[np.cos(pz), -np.sin(pz), 0], [np.sin(pz), np.cos(pz), 0], [0, 0, 1]])
    return rz @ ry @ rx


def _grid(n: int = 6, step: float = 20.0) -> np.ndarray:
    xs, ys = np.meshgrid(np.arange(n) * step + 10.0, np.arange(n) * step + 10.0)
    return np.column_stack([xs.ravel(), ys.ravel()]).astype(np.float32)


def test_similarity_transform_recovers_known_scale_rotation_translation():
    src = _grid()
    theta = np.deg2rad(25.0)
    rot = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    dst = (1.7 * src @ rot.T) + np.array([40.0, -15.0])

    matrix = similarity_transform(src, dst)
    recovered = apply_affine(src, matrix)

    assert np.allclose(recovered, dst, atol=1e-3)
    scale = np.sqrt(np.linalg.det(matrix[:, :2]))
    assert scale == pytest.approx(1.7, rel=1e-3)


def test_similarity_transform_handles_degenerate_source():
    src = np.zeros((5, 2), dtype=np.float32)
    dst = np.tile([3.0, 4.0], (5, 1)).astype(np.float32)
    matrix = similarity_transform(src, dst)
    moved = apply_affine(src, matrix)
    assert np.allclose(moved, dst, atol=1e-6)


def test_clamp_points_bounds_pathological_input():
    points = np.array(
        [[np.inf, 0.0], [-1e30, 5e29], [np.nan, np.nan], [50.0, 50.0]], dtype=np.float64
    )
    clamped = clamp_points(points, 100, 80, margin=0.5)
    assert np.isfinite(clamped).all()
    assert (clamped[:, 0] >= -50.0).all() and (clamped[:, 0] <= 150.0).all()
    assert (clamped[:, 1] >= -40.0).all() and (clamped[:, 1] <= 120.0).all()


def test_clamp_displacement_limits_travel_distance():
    base = _grid()
    target = base + 500.0  # far beyond any sane shift
    limited = clamp_displacement(base, target, max_shift=12.0)
    travelled = np.linalg.norm(limited - base, axis=1)
    assert travelled.max() <= 12.0 + 1e-4
    # a small move is left untouched
    small = base.copy()
    small[0] += [3.0, 4.0]
    kept = clamp_displacement(base, small, max_shift=12.0)
    assert np.linalg.norm(kept[0] - base[0]) == pytest.approx(5.0, abs=1e-4)


def test_clamp_displacement_scrubs_non_finite_delta():
    base = _grid()
    target = base.copy()
    target[3] = [np.nan, np.inf]
    out = clamp_displacement(base, target, max_shift=10.0)
    assert np.isfinite(out).all()
    assert np.allclose(out[3], base[3])


def test_delaunay_triangles_are_valid_indices():
    points = np.vstack([_grid(4), boundary_points(120, 120)]).astype(np.float32)
    tris = delaunay_triangles(points, 120, 120)
    assert tris.ndim == 2 and tris.shape[1] == 3
    assert tris.min() >= 0 and tris.max() < len(points)
    # every triangle references three distinct points
    assert all(len(set(row)) == 3 for row in tris)


def test_warp_image_identity_when_source_equals_destination():
    rng = np.random.default_rng(0)
    image = rng.integers(0, 255, size=(120, 120, 3), dtype=np.uint8)
    points = np.vstack([_grid(5, 22.0), boundary_points(120, 120)]).astype(np.float32)
    tris = delaunay_triangles(points, 120, 120)
    out = warp_image(image, points, points, tris, (120, 120))

    assert out.shape == image.shape and out.dtype == image.dtype
    covered = out.any(axis=2)
    # identity warp reproduces the covered interior faithfully
    assert np.array_equal(out[covered], image[covered])


@pytest.mark.parametrize(
    "pitch,yaw,roll",
    [(0, 0, 0), (12, 0, 0), (0, -20, 0), (0, 0, 30), (10, -15, 25), (-8, 33, -12)],
)
def test_matrix_to_euler_deg_recovers_known_rotation(pitch, yaw, roll):
    rot = _euler_matrix(pitch, yaw, roll)
    transform = np.eye(4)
    transform[:3, :3] = rot * np.array([1.3, 0.7, 2.1])  # arbitrary per-column scale
    transform[:3, 3] = [11.0, -4.0, 30.0]
    got = matrix_to_euler_deg(transform.reshape(-1).tolist())
    assert got == pytest.approx((pitch, yaw, roll), abs=1e-4)


def test_matrix_to_euler_deg_accepts_3x3_and_rejects_bad_size():
    assert matrix_to_euler_deg(_euler_matrix(0, 0, 0).reshape(-1)) == pytest.approx((0, 0, 0))
    with pytest.raises(ValueError):
        matrix_to_euler_deg([1.0, 2.0, 3.0, 4.0])


def test_warp_image_reacts_to_destination_change():
    rng = np.random.default_rng(1)
    image = rng.integers(0, 255, size=(100, 100, 3), dtype=np.uint8)
    src = np.vstack([_grid(5, 18.0), boundary_points(100, 100)]).astype(np.float32)
    tris = delaunay_triangles(src, 100, 100)
    dst = src.copy()
    dst[: 25] += rng.normal(0.0, 4.0, size=(25, 2)).astype(np.float32)
    out = warp_image(image, src, dst, tris, (100, 100))
    assert out.shape == image.shape
    assert not np.array_equal(out, warp_image(image, src, src, tris, (100, 100)))
