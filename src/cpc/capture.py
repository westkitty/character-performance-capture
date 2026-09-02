from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Self

import cv2
import numpy as np

Frame = np.ndarray


@dataclass(frozen=True)
class CameraConfig:
    index: int = 0
    width: int | None = None
    height: int | None = None
    fps: float | None = None


@dataclass(frozen=True)
class CameraInfo:
    backend: str
    width: int
    height: int
    fps: float


def _camera_dimension(value: float) -> int:
    if not math.isfinite(value) or value <= 0:
        return 0
    return max(0, round(value))


def _camera_rate(value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        return 0.0
    return float(value)


class CameraSource:
    """Small OpenCV camera wrapper with explicit lifecycle."""

    def __init__(self, config: CameraConfig) -> None:
        self.config = config
        self._capture: cv2.VideoCapture | None = None

    def open(self) -> None:
        if self._capture is not None:
            return
        capture = cv2.VideoCapture(self.config.index)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"Could not open camera index {self.config.index}")

        if self.config.width:
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        if self.config.height:
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        if self.config.fps:
            capture.set(cv2.CAP_PROP_FPS, self.config.fps)

        self._capture = capture

    def info(self) -> CameraInfo:
        if self._capture is None:
            self.open()
        assert self._capture is not None
        try:
            backend = self._capture.getBackendName()
        except cv2.error:
            backend = "unknown"
        return CameraInfo(
            backend=backend,
            width=_camera_dimension(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=_camera_dimension(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            fps=_camera_rate(self._capture.get(cv2.CAP_PROP_FPS)),
        )

    def read(self) -> Frame:
        if self._capture is None:
            self.open()
        assert self._capture is not None
        ok, frame = self._capture.read()
        if not ok or frame is None:
            raise RuntimeError("Camera frame read failed")
        return frame

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self) -> Self:
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
