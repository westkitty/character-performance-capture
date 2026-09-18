from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Protocol, Self

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
    tracking_ms: float = 0.0
    render_ms: float = 0.0
    queue_depth: int = 0
    coalesced_preview_frames: int = 0


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
        self._last_frame_time = None
        self._frame_index = 0
        self._started = True

    def process(self, frame: Frame, *, timestamp_s: float | None = None) -> PerformanceResult:
        if not self._started:
            self.start()
        assert self._started_at is not None
        started = time.perf_counter()
        performance_timestamp = timestamp_s if timestamp_s is not None else started - self._started_at

        track_started = time.perf_counter()
        performance = self.tracker.track(
            frame,
            frame_index=self._frame_index,
            timestamp_s=performance_timestamp,
        )
        tracked_at = time.perf_counter()
        rendered = self.renderer.render(frame, performance)
        now = time.perf_counter()

        processing_ms = (now - started) * 1000.0
        fps = 0.0
        if self._last_frame_time is not None:
            delta = now - self._last_frame_time
            fps = 1.0 / delta if delta > 0 else 0.0
        self._last_frame_time = now
        metrics = FrameMetrics(self._frame_index, processing_ms, fps)
        self._frame_index += 1
        return PerformanceResult(
            rendered,
            performance,
            metrics,
            tracking_ms=(tracked_at - track_started) * 1000.0,
            render_ms=(now - tracked_at) * 1000.0,
        )

    def close(self) -> None:
        if not self._started:
            return
        try:
            self.renderer.close()
        finally:
            self.tracker.close()
            self._started = False
            self._started_at = None
            self._last_frame_time = None

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


@dataclass(frozen=True)
class _WorkItem:
    frame_index: int
    timestamp_s: float
    frame: Frame


@dataclass(frozen=True)
class _WorkerFailure:
    error: Exception


class ThreadedPerformancePipeline:
    """Bounded ordered tracker/render worker for live capture.

    Canonical performer state is never dropped. Producers block on the bounded
    input queue; callers may coalesce presentation after receiving ordered
    results. Worker exceptions are re-raised on the consumer thread.
    """

    def __init__(
        self,
        renderer: CharacterRenderer,
        tracker: PerformanceTracker | None = None,
        *,
        queue_size: int = 3,
    ) -> None:
        if queue_size < 1:
            raise ValueError("queue_size must be at least 1")
        self.tracker = tracker or NullTracker()
        self.renderer = renderer
        self.queue_size = int(queue_size)
        self._input: queue.Queue[_WorkItem | None] = queue.Queue(maxsize=self.queue_size)
        self._output: queue.Queue[PerformanceResult | _WorkerFailure] = queue.Queue(
            maxsize=self.queue_size
        )
        self._thread: threading.Thread | None = None
        self._started_at: float | None = None
        self._next_index = 0
        self._last_result_time: float | None = None
        self._closed = True

    @property
    def queue_depth(self) -> int:
        return self._input.qsize()

    @property
    def worker_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.worker_alive:
            return
        self.tracker.start()
        try:
            self.renderer.start()
        except Exception:
            self.tracker.close()
            raise
        self._input = queue.Queue(maxsize=self.queue_size)
        self._output = queue.Queue(maxsize=self.queue_size)
        self._started_at = time.perf_counter()
        self._next_index = 0
        self._last_result_time = None
        self._closed = False
        self._thread = threading.Thread(target=self._worker, name="cpc-performance", daemon=False)
        self._thread.start()

    def submit(self, frame: Frame, *, timestamp_s: float | None = None) -> int:
        if not self.worker_alive:
            self.start()
        assert self._started_at is not None
        index = self._next_index
        self._next_index += 1
        ts = timestamp_s if timestamp_s is not None else time.perf_counter() - self._started_at
        self._input.put(_WorkItem(index, ts, frame))
        return index

    def receive(self, *, timeout: float | None = None) -> PerformanceResult:
        item = self._output.get(timeout=timeout)
        if isinstance(item, _WorkerFailure):
            raise RuntimeError("threaded performance worker failed") from item.error  # noqa: TRY004
        return item

    def process(self, frame: Frame, *, timestamp_s: float | None = None) -> PerformanceResult:
        self.submit(frame, timestamp_s=timestamp_s)
        return self.receive()

    def _worker(self) -> None:
        try:
            while True:
                item = self._input.get()
                if item is None:
                    break
                started = time.perf_counter()
                track_started = started
                performance = self.tracker.track(
                    item.frame,
                    frame_index=item.frame_index,
                    timestamp_s=item.timestamp_s,
                )
                tracked_at = time.perf_counter()
                rendered = self.renderer.render(item.frame, performance)
                now = time.perf_counter()
                fps = 0.0
                if self._last_result_time is not None:
                    delta = now - self._last_result_time
                    fps = 1.0 / delta if delta > 0 else 0.0
                self._last_result_time = now
                result = PerformanceResult(
                    rendered,
                    performance,
                    FrameMetrics(item.frame_index, (now - started) * 1000.0, fps),
                    tracking_ms=(tracked_at - track_started) * 1000.0,
                    render_ms=(now - tracked_at) * 1000.0,
                    queue_depth=self._input.qsize(),
                )
                self._output.put(result)
        except Exception as exc:  # noqa: BLE001
            self._output.put(_WorkerFailure(exc))

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._thread and self._thread.is_alive():
            self._input.put(None)
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                raise RuntimeError("performance worker did not shut down")
        try:
            self.renderer.close()
        finally:
            self.tracker.close()
            self._thread = None
            self._started_at = None

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
