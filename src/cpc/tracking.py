from __future__ import annotations

from typing import Protocol

from .performance import PerformanceFrame
from .pipeline import Frame


class PerformanceTracker(Protocol):
    """Contract implemented by any live performer tracker."""

    name: str
    profile: str

    def start(self) -> None: ...

    def track(
        self,
        frame: Frame,
        *,
        frame_index: int,
        timestamp_s: float,
    ) -> PerformanceFrame: ...

    def close(self) -> None: ...


class NullTracker:
    """Zero-dependency tracker used to prove pipeline behavior without a model."""

    name = "null"
    profile = "none"

    def start(self) -> None:
        return None

    def track(
        self,
        frame: Frame,
        *,
        frame_index: int,
        timestamp_s: float,
    ) -> PerformanceFrame:
        del frame
        return PerformanceFrame(
            frame_index=frame_index,
            timestamp_s=timestamp_s,
            tracked=False,
            tracker=self.name,
            profile=self.profile,
        )

    def close(self) -> None:
        return None
