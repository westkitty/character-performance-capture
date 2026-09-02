from __future__ import annotations

import numpy as np

from .geometry import (
    apply_affine,
    boundary_points,
    clamp_displacement,
    clamp_points,
    delaunay_triangles,
    rotation_affine,
    similarity_transform,
    warp_image,
)
from .performance import PerformanceFrame
from .pipeline import Frame
from .rig import CharacterRig

# A curated control subset of the MediaPipe 478 mesh (face oval, brows, eyes,
# lips, nose, iris centres, cheek/jaw anchors). Warping a ~110-point control
# mesh instead of all 478 points is both much faster and less prone to
# triangle-flip artefacts, while still tracking every expressive region.
_MP_CONTROL_INDICES = tuple(
    sorted(
        {
            # face oval
            10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365,
            379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93,
            234, 127, 162, 21, 54, 103, 67, 109,
            # right eye + brow
            33, 7, 163, 144, 145, 153, 154, 155, 133, 246, 161, 160, 159, 158,
            157, 173, 46, 53, 52, 65, 55, 70, 63, 105, 66, 107,
            # left eye + brow
            263, 249, 390, 373, 374, 380, 381, 382, 362, 466, 388, 387, 386,
            385, 384, 398, 276, 283, 282, 295, 285, 300, 293, 334, 296, 336,
            # lips (outer + inner)
            61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269,
            267, 0, 37, 39, 40, 185, 78, 95, 88, 178, 87, 14, 317, 402, 318,
            324, 308, 415, 310, 311, 312, 13, 82, 81, 42, 183, 80, 191,
            # nose + midline + cheek/jaw anchors
            1, 2, 98, 327, 168, 6, 197, 195, 5, 4, 19, 94, 45, 275, 220, 440,
            50, 280, 137, 366, 213, 433, 138, 367,
            # iris centres (478-point mesh only)
            468, 473,
        }
    )
)
# Indices *within the control subset* that stay roughly rigid under expression.
_CONTROL_RIGID = tuple(
    _MP_CONTROL_INDICES.index(i) for i in (33, 263, 168, 6, 10, 234, 454)
)
_CONTROL_LEFT_EYE = _MP_CONTROL_INDICES.index(33)
_CONTROL_RIGHT_EYE = _MP_CONTROL_INDICES.index(263)


class RigWarpRenderer:
    """Landmark-driven 2D character renderer.

    The character reference image is warped from its neutral rig mesh toward a
    target mesh built by transferring the performer's *relative* expression and
    head motion onto the character's own geometry. The character's pixels are
    never replaced by the performer's face, so identity is preserved.
    """

    name = "rig-warp"

    def __init__(
        self,
        rig: CharacterRig,
        character_image: np.ndarray,
        *,
        confidence_threshold: float = 0.15,
        expression_gain: float = 1.0,
        head_gain: float = 1.0,
        max_shift_frac: float = 0.45,
        work_max_edge: int = 640,
        out_size: tuple[int, int] | None = None,
    ) -> None:
        if not isinstance(character_image, np.ndarray) or character_image.ndim != 3:
            raise ValueError("character_image must be an (H, W, 3) array")
        if character_image.shape[2] != 3:
            raise ValueError("character_image must have 3 colour channels")
        if character_image.shape[0] != rig.height or character_image.shape[1] != rig.width:
            raise ValueError("character_image dimensions must match the rig width/height")
        if not np.isfinite(expression_gain) or not np.isfinite(head_gain):
            raise ValueError("gains must be finite")

        self.rig = rig
        self.character_image = np.ascontiguousarray(character_image.astype(np.uint8))
        self.confidence_threshold = float(confidence_threshold)
        self.expression_gain = float(expression_gain)
        self.head_gain = float(head_gain)
        self.max_shift_frac = float(max_shift_frac)

        # Warp at a bounded working resolution: cost scales with pixel count and a
        # 640px long edge keeps a full-mesh warp interactive on CPU-only Macs.
        long_edge = max(rig.width, rig.height)
        self._work_scale = min(1.0, float(work_max_edge) / long_edge) if work_max_edge else 1.0
        self._work_w = max(1, round(rig.width * self._work_scale))
        self._work_h = max(1, round(rig.height * self._work_scale))
        self.out_size = out_size or (self._work_w, self._work_h)

        # When a full MediaPipe mesh is available, warp a curated control subset;
        # otherwise (small authored rigs, tests) use every rig point.
        self._expected_landmarks = rig.point_count
        if rig.point_count > max(_MP_CONTROL_INDICES):
            self._control = np.array(_MP_CONTROL_INDICES, dtype=np.int64)
            self._rigid_indices = np.array(_CONTROL_RIGID, dtype=np.int64)
            self._eye_pair: tuple[int, int] | None = (_CONTROL_LEFT_EYE, _CONTROL_RIGHT_EYE)
        else:
            self._control = np.arange(rig.point_count, dtype=np.int64)
            self._rigid_indices = np.arange(rig.point_count, dtype=np.int64)
            self._eye_pair = None
        self._rig_control_full = rig.points[self._control].astype(np.float32)
        self._rig_control = self._rig_control_full
        self._n_control = int(self._control.shape[0])

        self._src_points: np.ndarray | None = None
        self._triangles: np.ndarray | None = None
        self._neutral_perf: np.ndarray | None = None
        self._last_render: np.ndarray | None = None
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        import cv2

        w, h = self._work_w, self._work_h
        if self._work_scale != 1.0:
            self._work_image = cv2.resize(
                self.character_image, (w, h), interpolation=cv2.INTER_AREA
            )
            control = self._rig_control_full * self._work_scale
        else:
            self._work_image = self.character_image
            control = self._rig_control_full
        self._rig_control = clamp_points(control, w, h, margin=0.0).astype(np.float32)
        anchors = boundary_points(w, h)
        self._src_points = np.vstack([self._rig_control, anchors]).astype(np.float32)
        self._triangles = delaunay_triangles(self._src_points, w, h)
        if self._triangles.size == 0:
            raise RuntimeError("rig produced no usable triangulation")
        self._neutral_perf = None
        self._last_render = None
        self._started = True

    # -- helpers ---------------------------------------------------------------

    def _interocular(self, points: np.ndarray) -> float:
        if self._eye_pair is not None:
            left, right = self._eye_pair
            span = np.linalg.norm(points[left] - points[right])
        else:
            span = float(np.linalg.norm(points.max(axis=0) - points.min(axis=0)))
        return float(span) if np.isfinite(span) and span > 1e-6 else 1.0

    def _fallback(self) -> np.ndarray:
        if self._last_render is not None:
            return self._last_render
        return self._resized_reference()

    def _resized_reference(self) -> np.ndarray:
        import cv2

        base = getattr(self, "_work_image", self.character_image)
        if self.out_size == (base.shape[1], base.shape[0]):
            return base.copy()
        return cv2.resize(self.character_image, self.out_size, interpolation=cv2.INTER_AREA)

    def _performer_matrix(self, performance: PerformanceFrame) -> np.ndarray | None:
        if len(performance.landmarks) < self._expected_landmarks:
            return None
        pts = np.array(
            [[lm.x, lm.y] for lm in performance.landmarks], dtype=np.float64
        )[self._control]
        if not np.isfinite(pts).all():
            return None
        # Work in a stable pixel-like space rather than raw [0, 1] normals.
        return (pts * 1000.0).astype(np.float32)

    # -- main entry point ----------------------------------------------------

    def render(self, frame: Frame, performance: PerformanceFrame) -> Frame:
        del frame  # a character renderer does not show performer pixels
        if not self._started:
            self.start()
        assert self._src_points is not None and self._triangles is not None

        if not performance.tracked:
            return self._fallback()
        if (
            performance.tracking_confidence is not None
            and performance.tracking_confidence < self.confidence_threshold
        ):
            return self._fallback()

        perf = self._performer_matrix(performance)
        if perf is None:
            return self._fallback()

        if self._neutral_perf is None:
            self._neutral_perf = perf
            render = self._resized_reference()
            self._last_render = render
            return render

        rigid = self._rigid_indices
        matrix = similarity_transform(self._neutral_perf[rigid], perf[rigid])
        aligned_neutral = apply_affine(self._neutral_perf, matrix)
        expr_delta = (perf - aligned_neutral) * self.expression_gain

        perf_scale = self._interocular(self._neutral_perf)
        char_scale = self._interocular(self._rig_control)
        expr_delta *= char_scale / perf_scale

        target = self._rig_control + expr_delta.astype(np.float32)

        roll, yaw, pitch = self._head_angles(performance, matrix)
        centroid = self._rig_control.mean(axis=0)
        head_affine = rotation_affine(centroid, roll_deg=roll, yaw_deg=yaw, pitch_deg=pitch)
        target = apply_affine(target, head_affine)

        max_shift = self.max_shift_frac * char_scale
        target = clamp_displacement(self._rig_control, target, max_shift=max_shift)
        target = clamp_points(target, self._work_w, self._work_h, margin=0.35)

        dst_points = np.vstack(
            [target, boundary_points(self._work_w, self._work_h)]
        ).astype(np.float32)

        render = warp_image(
            self._work_image,
            self._src_points,
            dst_points,
            self._triangles,
            self.out_size,
        )
        self._last_render = render
        return render

    def _head_angles(
        self, performance: PerformanceFrame, align_matrix: np.ndarray
    ) -> tuple[float, float, float]:
        if performance.head_rotation_deg is not None:
            pitch, yaw, roll = performance.head_rotation_deg
            return (
                float(roll) * self.head_gain,
                float(yaw) * self.head_gain,
                float(pitch) * self.head_gain,
            )
        # Derive roll only, from the alignment rotation of the rigid points.
        roll = np.degrees(np.arctan2(align_matrix[1, 0], align_matrix[0, 0]))
        return (float(roll) * self.head_gain, 0.0, 0.0)

    def close(self) -> None:
        self._src_points = None
        self._triangles = None
        self._neutral_perf = None
        self._last_render = None
        self._work_image = None
        self._started = False
