from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

from .performance import JsonScalar, PerformanceFrame


FORMAT_NAME = "cpc-performance-capture"
FORMAT_VERSION = 1


class CaptureFormatError(ValueError):
    """Raised when a capture file violates the CPC format contract."""


@dataclass(frozen=True)
class CaptureHeader:
    tracker: str
    profile: str
    started_at_utc: str
    metadata: dict[str, JsonScalar]
    format_name: str = FORMAT_NAME
    version: int = FORMAT_VERSION


@dataclass(frozen=True)
class CaptureData:
    header: CaptureHeader
    frames: tuple[PerformanceFrame, ...]
    complete: bool
    frame_count: int
    duration_s: float


class PerformanceRecorder:
    """Crash-tolerant JSONL recorder for portable performance data only."""

    def __init__(
        self,
        path: str | Path,
        *,
        tracker: str,
        profile: str,
        metadata: dict[str, JsonScalar] | None = None,
    ) -> None:
        self.path = Path(path)
        self.partial_path = Path(f"{self.path}.partial")
        self.tracker = tracker
        self.profile = profile
        self.metadata = dict(metadata or {})
        self._file = None
        self._frame_count = 0
        self._first_timestamp: float | None = None
        self._last_timestamp: float | None = None
        self._last_frame_index: int | None = None

    def start(self) -> None:
        if self._file is not None:
            return
        if self.path.exists():
            raise FileExistsError(f"capture already exists: {self.path}")
        if self.partial_path.exists():
            raise FileExistsError(f"partial capture already exists: {self.partial_path}")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.partial_path.open("x", encoding="utf-8", newline="\n")
        self._write_record(
            {
                "record_type": "header",
                "format": FORMAT_NAME,
                "version": FORMAT_VERSION,
                "tracker": self.tracker,
                "profile": self.profile,
                "started_at_utc": datetime.now(UTC).isoformat(),
                "metadata": self.metadata,
            }
        )

    def write(self, frame: PerformanceFrame) -> None:
        if self._file is None:
            self.start()

        if self._last_frame_index is not None and frame.frame_index <= self._last_frame_index:
            raise ValueError("capture frame_index values must be strictly increasing")
        if self._last_timestamp is not None and frame.timestamp_s < self._last_timestamp:
            raise ValueError("capture timestamps must be monotonically increasing")

        self._write_record({"record_type": "frame", "frame": frame.to_dict()})
        self._last_frame_index = frame.frame_index
        self._last_timestamp = frame.timestamp_s
        if self._first_timestamp is None:
            self._first_timestamp = frame.timestamp_s
        self._frame_count += 1

    def close(self, *, commit: bool = True) -> None:
        if self._file is None:
            return

        if commit:
            duration_s = 0.0
            if self._first_timestamp is not None and self._last_timestamp is not None:
                duration_s = max(0.0, self._last_timestamp - self._first_timestamp)
            self._write_record(
                {
                    "record_type": "end",
                    "frame_count": self._frame_count,
                    "duration_s": duration_s,
                }
            )

        self._file.flush()
        os.fsync(self._file.fileno())
        self._file.close()
        self._file = None

        if commit:
            os.replace(self.partial_path, self.path)

    def _write_record(self, payload: dict[str, Any]) -> None:
        assert self._file is not None
        self._file.write(json.dumps(payload, separators=(",", ":"), allow_nan=False))
        self._file.write("\n")

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close(commit=exc_type is None)


class PerformanceReplay:
    """Replay source for captured performer state without requiring captured video."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def frames(self, *, realtime: bool = False, speed: float = 1.0) -> Iterator[PerformanceFrame]:
        if speed <= 0:
            raise ValueError("replay speed must be greater than zero")

        previous_timestamp: float | None = None
        for frame in iter_capture_frames(self.path):
            if realtime and previous_timestamp is not None:
                delay = max(0.0, frame.timestamp_s - previous_timestamp) / speed
                if delay:
                    time.sleep(delay)
            previous_timestamp = frame.timestamp_s
            yield frame


def _parse_header(payload: dict[str, Any]) -> CaptureHeader:
    if payload.get("record_type") != "header":
        raise CaptureFormatError("first record must be a header")
    if payload.get("format") != FORMAT_NAME:
        raise CaptureFormatError("unsupported capture format")
    if payload.get("version") != FORMAT_VERSION:
        raise CaptureFormatError(f"unsupported capture version: {payload.get('version')}")
    return CaptureHeader(
        tracker=str(payload["tracker"]),
        profile=str(payload["profile"]),
        started_at_utc=str(payload["started_at_utc"]),
        metadata=dict(payload.get("metadata", {})),
    )


def _records(path: str | Path) -> Iterator[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CaptureFormatError(f"invalid JSON on line {line_number}") from exc
            if not isinstance(payload, dict):
                raise CaptureFormatError(f"record on line {line_number} must be an object")
            yield payload


def iter_capture_frames(path: str | Path) -> Iterator[PerformanceFrame]:
    records = _records(path)
    try:
        _parse_header(next(records))
    except StopIteration as exc:
        raise CaptureFormatError("capture is empty") from exc

    last_index: int | None = None
    last_timestamp: float | None = None
    for payload in records:
        record_type = payload.get("record_type")
        if record_type == "end":
            break
        if record_type != "frame":
            raise CaptureFormatError(f"unknown record type: {record_type!r}")
        frame = PerformanceFrame.from_dict(payload["frame"])
        if last_index is not None and frame.frame_index <= last_index:
            raise CaptureFormatError("frame_index values are not strictly increasing")
        if last_timestamp is not None and frame.timestamp_s < last_timestamp:
            raise CaptureFormatError("timestamps are not monotonically increasing")
        last_index = frame.frame_index
        last_timestamp = frame.timestamp_s
        yield frame


def read_capture(path: str | Path) -> CaptureData:
    records = _records(path)
    try:
        header = _parse_header(next(records))
    except StopIteration as exc:
        raise CaptureFormatError("capture is empty") from exc

    frames: list[PerformanceFrame] = []
    footer: dict[str, Any] | None = None
    last_index: int | None = None
    last_timestamp: float | None = None

    for payload in records:
        record_type = payload.get("record_type")
        if record_type == "frame":
            if footer is not None:
                raise CaptureFormatError("frame record appears after end record")
            frame = PerformanceFrame.from_dict(payload["frame"])
            if last_index is not None and frame.frame_index <= last_index:
                raise CaptureFormatError("frame_index values are not strictly increasing")
            if last_timestamp is not None and frame.timestamp_s < last_timestamp:
                raise CaptureFormatError("timestamps are not monotonically increasing")
            last_index = frame.frame_index
            last_timestamp = frame.timestamp_s
            frames.append(frame)
        elif record_type == "end":
            if footer is not None:
                raise CaptureFormatError("capture contains multiple end records")
            footer = payload
        else:
            raise CaptureFormatError(f"unknown record type: {record_type!r}")

    complete = footer is not None
    if footer is not None:
        declared_count = int(footer.get("frame_count", -1))
        if declared_count != len(frames):
            raise CaptureFormatError(
                f"end record declares {declared_count} frames but file contains {len(frames)}"
            )
        duration_s = float(footer.get("duration_s", 0.0))
    elif len(frames) >= 2:
        duration_s = max(0.0, frames[-1].timestamp_s - frames[0].timestamp_s)
    else:
        duration_s = 0.0

    return CaptureData(
        header=header,
        frames=tuple(frames),
        complete=complete,
        frame_count=len(frames),
        duration_s=duration_s,
    )
