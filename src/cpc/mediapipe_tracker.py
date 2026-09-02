from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .geometry import matrix_to_euler_deg
from .performance import Landmark, PerformanceFrame
from .pipeline import Frame

_DELEGATES = ("cpu", "gpu")


def _resolve_delegate(mp_python: Any, delegate: str) -> Any:
    key = delegate.lower().strip()
    if key not in _DELEGATES:
        raise ValueError(f"tracker delegate must be one of {_DELEGATES}, got {delegate!r}")
    return getattr(mp_python.BaseOptions.Delegate, key.upper())


def create_face_landmarker(
    model_path: str | Path,
    *,
    delegate: str = "cpu",
    running_mode: str = "VIDEO",
    num_faces: int = 1,
    min_face_detection_confidence: float = 0.5,
    min_face_presence_confidence: float = 0.5,
    min_tracking_confidence: float = 0.5,
) -> Any:
    """Build a configured MediaPipe FaceLandmarker from a local model asset.

    The default ``cpu`` delegate is deliberate: the GPU delegate aborts the
    process on headless macOS builds without a usable Metal/GL context.
    """

    model_path = Path(model_path)
    if not model_path.is_file():
        raise FileNotFoundError(f"MediaPipe model not found: {model_path}")

    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise RuntimeError(
            "MediaPipe tracker requested but mediapipe is not installed. "
            "Install character-performance-capture[tracker-mediapipe]."
        ) from exc

    vision = mp.tasks.vision
    mode = getattr(vision.RunningMode, running_mode.upper(), None)
    if mode is None:
        raise ValueError(f"unknown MediaPipe running mode: {running_mode!r}")

    options = vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(
            model_asset_path=str(model_path),
            delegate=_resolve_delegate(mp_python, delegate),
        ),
        running_mode=mode,
        num_faces=num_faces,
        min_face_detection_confidence=min_face_detection_confidence,
        min_face_presence_confidence=min_face_presence_confidence,
        min_tracking_confidence=min_tracking_confidence,
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=True,
    )
    return vision.FaceLandmarker.create_from_options(options)


def _to_mp_image(frame: Frame) -> Any:
    import mediapipe as mp

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb = np.ascontiguousarray(rgb)
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)


def landmarker_points(
    landmarker: Any,
    frame: Frame,
    *,
    timestamp_ms: int | None,
) -> np.ndarray | None:
    """Run one detection and return normalized ``(N, 2)`` landmarks, or ``None``."""

    mp_image = _to_mp_image(frame)
    if timestamp_ms is None:
        result = landmarker.detect(mp_image)
    else:
        result = landmarker.detect_for_video(mp_image, timestamp_ms)
    if not result.face_landmarks:
        return None
    face = result.face_landmarks[0]
    return np.array([[float(p.x), float(p.y)] for p in face], dtype=np.float32)


class MediaPipeFaceTracker:
    """Optional MediaPipe Face Landmarker adapter.

    The adapter never downloads or bundles a model. Callers must provide a local
    Face Landmarker model asset they are authorized to use.
    """

    name = "mediapipe-face-landmarker"
    profile = "mediapipe-52"

    def __init__(
        self,
        model_path: str | Path,
        *,
        delegate: str = "cpu",
        min_face_detection_confidence: float = 0.5,
        min_face_presence_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        self.model_path = Path(model_path)
        self.delegate = delegate
        self.min_face_detection_confidence = min_face_detection_confidence
        self.min_face_presence_confidence = min_face_presence_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self._landmarker: Any = None
        self._last_timestamp_ms = -1

    def start(self) -> None:
        if self._landmarker is not None:
            return
        self._landmarker = create_face_landmarker(
            self.model_path,
            delegate=self.delegate,
            running_mode="VIDEO",
            min_face_detection_confidence=self.min_face_detection_confidence,
            min_face_presence_confidence=self.min_face_presence_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
        )
        self._last_timestamp_ms = -1

    def track(
        self,
        frame: Frame,
        *,
        frame_index: int,
        timestamp_s: float,
    ) -> PerformanceFrame:
        if self._landmarker is None:
            self.start()

        mp_image = _to_mp_image(frame)
        timestamp_ms = round(timestamp_s * 1000.0)
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms

        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        if not result.face_landmarks:
            return PerformanceFrame(
                frame_index=frame_index,
                timestamp_s=timestamp_s,
                tracked=False,
                tracker=self.name,
                profile=self.profile,
            )

        face_landmarks = result.face_landmarks[0]
        landmarks = tuple(
            Landmark(
                x=float(point.x),
                y=float(point.y),
                z=float(point.z),
                visibility=(
                    float(point.visibility)
                    if getattr(point, "visibility", None) is not None
                    else None
                ),
            )
            for point in face_landmarks
        )

        blendshapes: dict[str, float] = {}
        if result.face_blendshapes:
            for category in result.face_blendshapes[0]:
                name = getattr(category, "category_name", None)
                if name:
                    score = max(0.0, min(1.0, float(category.score)))
                    blendshapes[str(name)] = score

        face_transform = None
        head_rotation_deg = None
        if result.facial_transformation_matrixes:
            matrix = np.asarray(result.facial_transformation_matrixes[0], dtype=float)
            if matrix.size == 16:
                face_transform = tuple(float(value) for value in matrix.reshape(-1))
                head_rotation_deg = matrix_to_euler_deg(face_transform)

        return PerformanceFrame(
            frame_index=frame_index,
            timestamp_s=timestamp_s,
            tracked=True,
            tracker=self.name,
            profile=self.profile,
            blendshapes=blendshapes,
            head_rotation_deg=head_rotation_deg,
            face_transform=face_transform,
            landmarks=landmarks,
        )

    def close(self) -> None:
        if self._landmarker is None:
            return
        self._landmarker.close()
        self._landmarker = None
        self._last_timestamp_ms = -1
