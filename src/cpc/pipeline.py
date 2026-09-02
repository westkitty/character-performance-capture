from __future__ import annotations

import time
from contextlib import suppress
from dataclasses import dataclass
from typing import Protocol, Self

import numpy as np

Frame = np.ndarray


class FrameProcessor(Protocol):
    """Minimal contract for any tracker/renderer stage."""

    name: str

    def start(self) -> None: ...

    def process(self, frame: Frame) -> Frame: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class FrameMetrics:
    frame_index: int
    processing_ms: float
    fps: float


class Pipeline:
    """Composable, camera-independent frame-processing core."""

    def __init__(self, processors: list[FrameProcessor] | None = None) -> None:
        self.processors = list(processors or [])
        self._started = False
        self._frame_index = 0
        self._last_frame_time: float | None = None

    def start(self) -> None:
        if self._started:
            return

        started_processors: list[FrameProcessor] = []
        try:
            for processor in self.processors:
                processor.start()
                started_processors.append(processor)
        except Exception:
            for processor in reversed(started_processors):
                with suppress(Exception):
                    processor.close()
            raise

        self._frame_index = 0
        self._last_frame_time = None
        self._started = True

    def process(self, frame: Frame) -> tuple[Frame, FrameMetrics]:
        if not self._started:
            self.start()

        started = time.perf_counter()
        output = frame
        for processor in self.processors:
            output = processor.process(output)

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
        return output, metrics

    def close(self) -> None:
        if not self._started:
            return
        for processor in reversed(self.processors):
            processor.close()
        self._started = False
        self._last_frame_time = None

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
