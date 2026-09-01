from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .performance import Landmark, PerformanceFrame
from .pipeline import Frame


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
        min_face_detection_confidence: float = 0.5,
        min_face_presence_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        self.model_path = Path(model_path)
        self.min_face_detection_confidence = min_face_detection_confidence
        self.min_face_presence_confidence = min_face_presence_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self._mp: Any = None
        self._landmarker: Any = None
        self._last_timestamp_ms = -1

    def start(self) -> None:
        if self._landmarker is not None:
            return
        if not self.model_path.is_file():
            raise FileNotFoundError(f"MediaPipe model not found: {self.model_path}")

        try:
            import mediapipe as mp
        except ImportError as exc:
            raise RuntimeError(
                "MediaPipe tracker requested but mediapipe is not installed. "
                "Install character-performance-capture[tracker-mediapipe]."
            ) from exc

        vision = mp.tasks.vision
        options = vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(self.model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=self.min_face_detection_confidence,
            min_face_presence_confidence=self.min_face_presence_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
        )
        self._mp = mp
        self._landmarker = vision.FaceLandmarker.create_from_options(options)
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

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb)
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)

        timestamp_ms = int(round(timestamp_s * 1000.0))
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
        if result.facial_transformation_matrixes:
            matrix = np.asarray(result.facial_transformation_matrixes[0], dtype=float)
            if matrix.size == 16:
                face_transform = tuple(float(value) for value in matrix.reshape(-1))

        return PerformanceFrame(
            frame_index=frame_index,
            timestamp_s=timestamp_s,
            tracked=True,
            tracker=self.name,
            profile=self.profile,
            blendshapes=blendshapes,
            face_transform=face_transform,
            landmarks=landmarks,
        )

    def close(self) -> None:
        if self._landmarker is None:
            return
        self._landmarker.close()
        self._landmarker = None
        self._mp = None
        self._last_timestamp_ms = -1
