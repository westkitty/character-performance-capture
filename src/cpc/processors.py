from __future__ import annotations

import cv2
import numpy as np

from .pipeline import Frame, FrameMetrics


class PassthroughRenderer:
    """No-op renderer used to prove capture and lifecycle before model integration."""

    name = "passthrough"

    def start(self) -> None:
        return None

    def process(self, frame: Frame) -> Frame:
        return frame

    def close(self) -> None:
        return None


def draw_metrics(frame: Frame, metrics: FrameMetrics) -> np.ndarray:
    output = frame.copy()
    label = f"CPC  fps {metrics.fps:5.1f}  process {metrics.processing_ms:5.1f} ms"
    cv2.rectangle(output, (12, 12), (430, 48), (0, 0, 0), -1)
    cv2.putText(
        output,
        label,
        (22, 38),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    return output
