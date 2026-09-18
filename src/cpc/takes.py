from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .performance import PerformanceFrame
from .recording import CaptureData, read_capture


@dataclass(frozen=True)
class TakeMarker:
    frame_index: int
    note: str

    def __post_init__(self) -> None:
        if type(self.frame_index) is not int or self.frame_index < 0:
            raise ValueError("marker frame_index must be a non-negative integer")
        if not isinstance(self.note, str):
            raise TypeError("marker note must be a string")


class TakeTimeline:
    """Deterministic in-memory timeline over an immutable .cpc capture."""

    def __init__(self, capture: CaptureData) -> None:
        self.capture = capture
        self.frames = capture.frames
        self.position = 0
        self.loop: tuple[int, int] | None = None

    @classmethod
    def open(cls, path: str | Path) -> TakeTimeline:
        return cls(read_capture(path))

    def seek_frame(self, frame_index: int) -> PerformanceFrame:
        if not self.frames:
            raise IndexError("take has no frames")
        for index, frame in enumerate(self.frames):
            if frame.frame_index >= frame_index:
                self.position = index
                return frame
        self.position = len(self.frames) - 1
        return self.frames[self.position]

    def seek_time(self, timestamp_s: float) -> PerformanceFrame:
        if timestamp_s < 0:
            raise ValueError("timestamp must be non-negative")
        if not self.frames:
            raise IndexError("take has no frames")
        for index, frame in enumerate(self.frames):
            if frame.timestamp_s >= timestamp_s:
                self.position = index
                return frame
        self.position = len(self.frames) - 1
        return self.frames[self.position]

    def current(self) -> PerformanceFrame:
        if not self.frames:
            raise IndexError("take has no frames")
        return self.frames[self.position]

    def step(self, delta: int = 1) -> PerformanceFrame:
        if not self.frames:
            raise IndexError("take has no frames")
        lower, upper = (0, len(self.frames) - 1)
        if self.loop is not None:
            lower, upper = self.loop
        target = self.position + int(delta)
        if self.loop is not None and target > upper:
            target = lower
        elif self.loop is not None and target < lower:
            target = upper
        self.position = max(lower, min(upper, target))
        return self.frames[self.position]

    def set_loop(self, start: int, end: int) -> None:
        if not self.frames:
            raise IndexError("take has no frames")
        if not (0 <= start <= end < len(self.frames)):
            raise ValueError("invalid loop bounds")
        self.loop = (start, end)
        self.position = max(start, min(end, self.position))

    def clear_loop(self) -> None:
        self.loop = None

    def iter_playback(self, *, start: int | None = None, end: int | None = None) -> Iterator[PerformanceFrame]:
        if not self.frames:
            return
        lo = self.position if start is None else start
        hi = len(self.frames) - 1 if end is None else end
        if not (0 <= lo <= hi < len(self.frames)):
            raise ValueError("invalid playback bounds")
        for index in range(lo, hi + 1):
            self.position = index
            yield self.frames[index]


class TakeAnnotations:
    """Versioned sidecar notes; never mutates the canonical .cpc take."""

    FORMAT = "cpc-take-annotations"
    VERSION = 1

    def __init__(self, take_path: str | Path, markers: tuple[TakeMarker, ...] = ()) -> None:
        self.take_path = Path(take_path)
        self.markers = list(markers)

    @property
    def path(self) -> Path:
        return Path(f"{self.take_path}.annotations.json")

    def add(self, marker: TakeMarker) -> None:
        self.markers.append(marker)

    def save(self) -> None:
        payload = {
            "format": self.FORMAT,
            "version": self.VERSION,
            "take": self.take_path.name,
            "markers": [{"frame_index": m.frame_index, "note": m.note} for m in self.markers],
        }
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, take_path: str | Path) -> TakeAnnotations:
        obj = cls(take_path)
        if not obj.path.exists():
            return obj
        payload = json.loads(obj.path.read_text(encoding="utf-8"))
        if payload.get("format") != cls.FORMAT or payload.get("version") != cls.VERSION:
            raise ValueError("unsupported take annotation format")
        obj.markers = [
            TakeMarker(int(item["frame_index"]), str(item["note"]))
            for item in payload.get("markers", [])
        ]
        return obj


def replay_through_renderer(
    path: str | Path,
    renderer,
    *,
    source_frame: np.ndarray,
) -> list[np.ndarray]:
    """Drive a recorded take through the normal CharacterRenderer contract without camera access."""
    timeline = TakeTimeline.open(path)
    rendered: list[np.ndarray] = []
    renderer.start()
    try:
        for performance in timeline.iter_playback(start=0):
            rendered.append(renderer.render(source_frame, performance))
    finally:
        renderer.close()
    return rendered
