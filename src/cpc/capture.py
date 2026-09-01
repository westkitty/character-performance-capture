from __future__ import annotations

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
