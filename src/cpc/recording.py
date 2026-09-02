from __future__ import annotations

import json
import math
import os
import time
from collections.abc import Iterator
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from numbers import Real
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


def _validate_json_object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CaptureFormatError(f"{field_name} must be an object")
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise CaptureFormatError(f"{field_name} must contain JSON-safe finite values") from exc
    return dict(value)


def _require_nonempty_string(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise CaptureFormatError(f"{field_name} must be a non-empty string")
    return value


def _expected_duration(
    frame_count: int,
    first_timestamp: float | None,
    last_timestamp: float | None,
) -> float:
    if frame_count < 2 or first_timestamp is None or last_timestamp is None:
        return 0.0
    return max(0.0, last_timestamp - first_timestamp)


def _validate_footer(
    payload: dict[str, Any],
    *,
    frame_count: int,
    first_timestamp: float | None,
    last_timestamp: float | None,
) -> float:
    declared_count = payload.get("frame_count")
    if type(declared_count) is not int or declared_count < 0:
        raise CaptureFormatError("end record frame_count must be a non-negative integer")
    if declared_count != frame_count:
        raise CaptureFormatError(
            f"end record declares {declared_count} frames but file contains {frame_count}"
        )

    raw_duration = payload.get("duration_s")
    if isinstance(raw_duration, bool) or not isinstance(raw_duration, Real):
        raise CaptureFormatError("end record duration_s must be a finite non-negative number")
    duration_s = float(raw_duration)
    if not math.isfinite(duration_s) or duration_s < 0.0:
        raise CaptureFormatError("end record duration_s must be a finite non-negative number")

    expected = _expected_duration(frame_count, first_timestamp, last_timestamp)
    if not math.isclose(duration_s, expected, rel_tol=1e-9, abs_tol=1e-9):
        raise CaptureFormatError(
            f"end record duration_s {duration_s} does not match frame timestamps {expected}"
        )
    return duration_s


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
        if not isinstance(tracker, str) or not tracker.strip():
            raise ValueError("tracker must be a non-empty string")
        if not isinstance(profile, str) or not profile.strip():
            raise ValueError("profile must be a non-empty string")
        self.tracker = tracker
        self.profile = profile
        self.metadata = dict(metadata or {})
        try:
            json.dumps(self.metadata, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("metadata must contain JSON-safe finite values") from exc
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
        try:
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
        except Exception:
            self._file.close()
            self._file = None
            raise

    def write(self, frame: PerformanceFrame) -> None:
        try:
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
        except Exception:
            with suppress(Exception):
                self.close(commit=False)
            raise

    def close(self, *, commit: bool = True) -> None:
        if self._file is None:
            return

        if commit:
            duration_s = _expected_duration(
                self._frame_count,
                self._first_timestamp,
                self._last_timestamp,
            )
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
            try:
                os.link(self.partial_path, self.path)
            except FileExistsError as exc:
                raise FileExistsError(f"capture appeared before commit: {self.path}") from exc
            self.partial_path.unlink()

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
    if type(payload.get("version")) is not int or payload.get("version") != FORMAT_VERSION:
        raise CaptureFormatError(f"unsupported capture version: {payload.get('version')}")

    tracker = _require_nonempty_string(payload, "tracker")
    profile = _require_nonempty_string(payload, "profile")
    started_at_utc = _require_nonempty_string(payload, "started_at_utc")
    metadata = _validate_json_object(payload.get("metadata", {}), "header metadata")

    return CaptureHeader(
        tracker=tracker,
        profile=profile,
        started_at_utc=started_at_utc,
        metadata=metadata,
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
    first_timestamp: float | None = None
    last_timestamp: float | None = None
    frame_count = 0
    footer_seen = False

    for payload in records:
        if footer_seen:
            raise CaptureFormatError("record appears after end record")

        record_type = payload.get("record_type")
        if record_type == "frame":
            frame_payload = payload.get("frame")
            if not isinstance(frame_payload, dict):
                raise CaptureFormatError("frame record must contain a frame object")
            frame = PerformanceFrame.from_dict(frame_payload)
            if last_index is not None and frame.frame_index <= last_index:
                raise CaptureFormatError("frame_index values are not strictly increasing")
            if last_timestamp is not None and frame.timestamp_s < last_timestamp:
                raise CaptureFormatError("timestamps are not monotonically increasing")
            last_index = frame.frame_index
            last_timestamp = frame.timestamp_s
            if first_timestamp is None:
                first_timestamp = frame.timestamp_s
            frame_count += 1
            yield frame
        elif record_type == "end":
            _validate_footer(
                payload,
                frame_count=frame_count,
                first_timestamp=first_timestamp,
                last_timestamp=last_timestamp,
            )
            footer_seen = True
        else:
            raise CaptureFormatError(f"unknown record type: {record_type!r}")


def read_capture(path: str | Path) -> CaptureData:
    records = _records(path)
    try:
        header = _parse_header(next(records))
    except StopIteration as exc:
        raise CaptureFormatError("capture is empty") from exc

    frames: list[PerformanceFrame] = []
    footer: dict[str, Any] | None = None
    first_timestamp: float | None = None
    last_index: int | None = None
    last_timestamp: float | None = None

    for payload in records:
        if footer is not None:
            raise CaptureFormatError("record appears after end record")

        record_type = payload.get("record_type")
        if record_type == "frame":
            frame_payload = payload.get("frame")
            if not isinstance(frame_payload, dict):
                raise CaptureFormatError("frame record must contain a frame object")
            frame = PerformanceFrame.from_dict(frame_payload)
            if last_index is not None and frame.frame_index <= last_index:
                raise CaptureFormatError("frame_index values are not strictly increasing")
            if last_timestamp is not None and frame.timestamp_s < last_timestamp:
                raise CaptureFormatError("timestamps are not monotonically increasing")
            last_index = frame.frame_index
            last_timestamp = frame.timestamp_s
            if first_timestamp is None:
                first_timestamp = frame.timestamp_s
            frames.append(frame)
        elif record_type == "end":
            footer = payload
        else:
            raise CaptureFormatError(f"unknown record type: {record_type!r}")

    complete = footer is not None
    if footer is not None:
        duration_s = _validate_footer(
            footer,
            frame_count=len(frames),
            first_timestamp=first_timestamp,
            last_timestamp=last_timestamp,
        )
    else:
        duration_s = _expected_duration(len(frames), first_timestamp, last_timestamp)

    return CaptureData(
        header=header,
        frames=tuple(frames),
        complete=complete,
        frame_count=len(frames),
        duration_s=duration_s,
    )
