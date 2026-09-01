from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Protocol

from .performance import PerformanceFrame
from .pipeline import Frame, FrameMetrics
from .tracking import NullTracker, PerformanceTracker


class CharacterRenderer(Protocol):
    """Renderer contract: performer state in, rendered frame out."""

    name: str

    def start(self) -> None: ...

    def render(self, frame: Frame, performance: PerformanceFrame) -> Frame: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class PerformanceResult:
    frame: Frame
    performance: PerformanceFrame
    metrics: FrameMetrics


class PerformancePipeline:
    """Tracker -> renderer pipeline with portable performance state between them."""

    def __init__(
        self,
        renderer: CharacterRenderer,
        tracker: PerformanceTracker | None = None,
    ) -> None:
        self.tracker = tracker or NullTracker()
        self.renderer = renderer
        self._started = False
        self._started_at: float | None = None
        self._last_frame_time: float | None = None
        self._frame_index = 0

    def start(self) -> None:
        if self._started:
            return

        self.tracker.start()
        try:
            self.renderer.start()
        except Exception:
            self.tracker.close()
            raise

        self._started_at = time.perf_counter()
        self._started = True

    def process(
        self,
        frame: Frame,
        *,
        timestamp_s: float | None = None,
    ) -> PerformanceResult:
        if not self._started:
            self.start()

        assert self._started_at is not None
        started = time.perf_counter()
        performance_timestamp = (
            timestamp_s if timestamp_s is not None else started - self._started_at
        )

        performance = self.tracker.track(
            frame,
            frame_index=self._frame_index,
            timestamp_s=performance_timestamp,
        )
        rendered = self.renderer.render(frame, performance)

        now = time.perf_counter()
        processing_ms = (now - started) * 1000.0
        if self._last_frame_time is None:
            fps = 0.0
        else:
            delta = now - self._last_frame_time
            fps = 1.0 / delta if delta > 0 else 0.0
        self._last_frame_time = now

        metrics = FrameMetrics(
            frame_index=self._frame_index,
            processing_ms=processing_ms,
            fps=fps,
        )
        self._frame_index += 1
        return PerformanceResult(rendered, performance, metrics)

    def close(self) -> None:
        if not self._started:
            return

        try:
            self.renderer.close()
        finally:
            self.tracker.close()
            self._started = False

    def __enter__(self) -> "PerformancePipeline":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
