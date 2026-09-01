from __future__ import annotations

import cv2
import numpy as np

from .performance import PerformanceFrame
from .pipeline import Frame, FrameMetrics


class PassthroughRenderer:
    """No-op renderer used to prove capture and lifecycle before model integration."""

    name = "passthrough"

    def start(self) -> None:
        return None

    def process(self, frame: Frame) -> Frame:
        """Compatibility path for the original frame-only Pipeline."""
        return frame

    def render(self, frame: Frame, performance: PerformanceFrame) -> Frame:
        del performance
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


def draw_tracking_status(frame: Frame, performance: PerformanceFrame) -> np.ndarray:
    output = frame.copy()
    state = "TRACKED" if performance.tracked else "NO TRACK"
    label = f"{performance.tracker}  {state}  {len(performance.blendshapes)} coeffs"
    cv2.rectangle(output, (12, 54), (430, 90), (0, 0, 0), -1)
    cv2.putText(
        output,
        label,
        (22, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    return output
