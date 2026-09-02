from __future__ import annotations

import cv2
import numpy as np

Points = np.ndarray  # float32 array shaped (N, 2)


def as_points(values: object, *, name: str = "points") -> Points:
    """Coerce a sequence of coordinate pairs into a validated ``(N, 2)`` float array."""

    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] != 2:
        raise ValueError(f"{name} must be shaped (N, 2)")
    if array.shape[0] < 3:
        raise ValueError(f"{name} must contain at least 3 points")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must contain only finite values")
    return array.astype(np.float32, copy=False)


def similarity_transform(src: Points, dst: Points) -> np.ndarray:
    """Least-squares similarity (uniform scale + rotation + translation).

    Returns a ``(2, 3)`` affine matrix ``M`` such that ``M @ [x, y, 1]`` maps
    ``src`` onto ``dst`` as closely as possible without reflection or shear.
    """

    src = np.asarray(src, dtype=np.float64)
    dst = np.asarray(dst, dtype=np.float64)
    if src.shape != dst.shape or src.ndim != 2 or src.shape[1] != 2:
        raise ValueError("similarity_transform requires matching (N, 2) inputs")
    if src.shape[0] < 2:
        raise ValueError("similarity_transform requires at least 2 point pairs")

    src_mean = src.mean(axis=0)
    dst_mean = dst.mean(axis=0)
    src_centered = src - src_mean
    dst_centered = dst - dst_mean

    src_var = (src_centered**2).sum() / src.shape[0]
    if src_var < 1e-12:
        # Degenerate source (all points coincident): fall back to translation only.
        matrix = np.eye(2)
        translation = dst_mean - src_mean
        return np.hstack([matrix, translation.reshape(2, 1)]).astype(np.float64)

    cov = (dst_centered.T @ src_centered) / src.shape[0]
    u, s, vt = np.linalg.svd(cov)
    d = np.sign(np.linalg.det(u @ vt))
    correction = np.diag([1.0, d])
    rotation = u @ correction @ vt
    scale = (s * np.array([1.0, d])).sum() / src_var

    linear = scale * rotation
    translation = dst_mean - linear @ src_mean
    return np.hstack([linear, translation.reshape(2, 1)]).astype(np.float64)


def apply_affine(points: Points, matrix: np.ndarray) -> Points:
    """Apply a ``(2, 3)`` affine matrix to an ``(N, 2)`` point array."""

    points = np.asarray(points, dtype=np.float64)
    matrix = np.asarray(matrix, dtype=np.float64)
    if matrix.shape != (2, 3):
        raise ValueError("affine matrix must be shaped (2, 3)")
    homogeneous = np.hstack([points, np.ones((points.shape[0], 1))])
    return (homogeneous @ matrix.T).astype(np.float32)


def rotation_affine(center: np.ndarray, *, roll_deg: float, yaw_deg: float, pitch_deg: float) -> np.ndarray:
    """Cheap 2D stand-in for a head pose: roll rotates, yaw/pitch scale about ``center``."""

    roll = np.deg2rad(_clamp(roll_deg, -35.0, 35.0))
    yaw = _clamp(yaw_deg, -45.0, 45.0)
    pitch = _clamp(pitch_deg, -35.0, 35.0)

    cos_r, sin_r = np.cos(roll), np.sin(roll)
    rot = np.array([[cos_r, -sin_r], [sin_r, cos_r]])
    # Foreshortening: a turned head compresses horizontally, a nodding head vertically.
    scale = np.diag([np.cos(np.deg2rad(yaw)) ** 0.5, np.cos(np.deg2rad(pitch)) ** 0.5])
    linear = rot @ scale
    center = np.asarray(center, dtype=np.float64).reshape(2)
    translation = center - linear @ center
    return np.hstack([linear, translation.reshape(2, 1)]).astype(np.float64)


def _clamp(value: float, low: float, high: float) -> float:
    if not np.isfinite(value):
        return 0.0
    return float(min(high, max(low, value)))


def clamp_points(points: Points, width: int, height: int, *, margin: float = 0.5) -> Points:
    """Force every point inside an expanded image box and scrub non-finite values."""

    points = np.array(points, dtype=np.float32, copy=True)
    center = np.array([width / 2.0, height / 2.0], dtype=np.float32)
    bad = ~np.isfinite(points).all(axis=1)
    if bad.any():
        points[bad] = center
    lo = np.array([-margin * width, -margin * height], dtype=np.float32)
    hi = np.array([(1.0 + margin) * width, (1.0 + margin) * height], dtype=np.float32)
    return np.clip(points, lo, hi)


def clamp_displacement(base: Points, target: Points, *, max_shift: float) -> Points:
    """Limit how far any point may travel from ``base`` to keep the warp well-behaved."""

    base = np.asarray(base, dtype=np.float32)
    target = np.array(target, dtype=np.float32, copy=True)
    if base.shape != target.shape:
        raise ValueError("clamp_displacement requires matching shapes")
    if not np.isfinite(max_shift) or max_shift <= 0:
        return np.array(base, dtype=np.float32, copy=True)

    delta = target - base
    delta[~np.isfinite(delta)] = 0.0
    lengths = np.linalg.norm(delta, axis=1, keepdims=True)
    scale = np.ones_like(lengths)
    over = lengths.squeeze(-1) > max_shift
    scale[over] = (max_shift / lengths[over]).reshape(-1, 1)
    return (base + delta * scale).astype(np.float32)


def boundary_points(width: int, height: int) -> Points:
    """Eight fixed anchor points around the image frame so the warp keeps edges still."""

    w = float(width)
    h = float(height)
    return np.array(
        [
            [0.0, 0.0],
            [w / 2.0, 0.0],
            [w - 1.0, 0.0],
            [0.0, h / 2.0],
            [w - 1.0, h / 2.0],
            [0.0, h - 1.0],
            [w / 2.0, h - 1.0],
            [w - 1.0, h - 1.0],
        ],
        dtype=np.float32,
    )


def delaunay_triangles(points: Points, width: int, height: int) -> np.ndarray:
    """Delaunay triangulation as ``(T, 3)`` integer indices into ``points``.

    Points outside the image rectangle are ignored by ``Subdiv2D``; callers
    should pass points that have already been clamped into the frame.
    """

    points = np.asarray(points, dtype=np.float32)
    rect = (0, 0, width + 1, height + 1)
    subdiv = cv2.Subdiv2D(rect)
    lookup: dict[tuple[int, int], int] = {}
    for index, (x, y) in enumerate(points):
        key = (round(x * 16), round(y * 16))
        if key in lookup:
            continue
        if not (0 <= x <= width and 0 <= y <= height):
            continue
        lookup[key] = index
        subdiv.insert((float(x), float(y)))

    triangles: list[tuple[int, int, int]] = []
    for tri in subdiv.getTriangleList():
        idx = []
        for px, py in ((tri[0], tri[1]), (tri[2], tri[3]), (tri[4], tri[5])):
            key = (round(px * 16), round(py * 16))
            if key not in lookup:
                break
            idx.append(lookup[key])
        if len(idx) == 3 and len({*idx}) == 3:
            triangles.append(tuple(idx))
    return np.array(sorted(triangles), dtype=np.int32).reshape(-1, 3)


def warp_image(
    image: np.ndarray,
    src_points: Points,
    dst_points: Points,
    triangles: np.ndarray,
    out_size: tuple[int, int],
) -> np.ndarray:
    """Piecewise-affine warp: for each triangle, map ``src`` pixels onto ``dst``.

    ``out_size`` is ``(width, height)``. This is the standard OpenCV triangle
    morph; it is deterministic and performs no model inference.
    """

    src_points = np.asarray(src_points, dtype=np.float32)
    dst_points = np.asarray(dst_points, dtype=np.float32)
    out_w, out_h = int(out_size[0]), int(out_size[1])
    output = np.zeros((out_h, out_w, image.shape[2] if image.ndim == 3 else 1), dtype=image.dtype)
    if output.shape[2] == 1:
        output = output[:, :, 0]

    for tri in triangles.reshape(-1, 3):
        src_tri = src_points[tri]
        dst_tri = dst_points[tri]

        src_rect = cv2.boundingRect(src_tri.reshape(-1, 1, 2))
        dst_rect = cv2.boundingRect(dst_tri.reshape(-1, 1, 2))
        sx, sy, sw, sh = src_rect
        dx, dy, dw, dh = dst_rect
        if sw <= 0 or sh <= 0 or dw <= 0 or dh <= 0:
            continue
        sx = max(0, min(sx, image.shape[1] - 1))
        sy = max(0, min(sy, image.shape[0] - 1))
        sw = max(1, min(sw, image.shape[1] - sx))
        sh = max(1, min(sh, image.shape[0] - sy))
        dx = max(0, min(dx, out_w - 1))
        dy = max(0, min(dy, out_h - 1))
        dw = max(1, min(dw, out_w - dx))
        dh = max(1, min(dh, out_h - dy))

        src_local = src_tri - np.array([sx, sy], dtype=np.float32)
        dst_local = dst_tri - np.array([dx, dy], dtype=np.float32)

        patch = image[sy : sy + sh, sx : sx + sw]
        affine = cv2.getAffineTransform(src_local.astype(np.float32), dst_local.astype(np.float32))
        warped_patch = cv2.warpAffine(
            patch,
            affine,
            (dw, dh),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT_101,
        )

        mask = np.zeros((dh, dw), dtype=np.uint8)
        cv2.fillConvexPoly(mask, np.int32(dst_local), 255, cv2.LINE_AA)
        region = output[dy : dy + dh, dx : dx + dw]
        if region.ndim == 3 and warped_patch.ndim == 2:
            warped_patch = warped_patch[:, :, None].repeat(region.shape[2], axis=2)
        bool_mask = mask.astype(bool)
        region[bool_mask] = warped_patch[bool_mask]

    return output
