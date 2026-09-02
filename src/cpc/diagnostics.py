from __future__ import annotations

import math
import platform
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Protocol

import cv2

from .capture import CameraConfig, CameraInfo, CameraSource, Frame
from .tracking import PerformanceTracker


class CameraProbeSource(Protocol):
    def open(self) -> None: ...

    def info(self) -> CameraInfo: ...

    def read(self) -> Frame: ...

    def close(self) -> None: ...


CameraFactory = Callable[[CameraConfig], CameraProbeSource]


def _installed_version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def _timing_summary(samples_s: list[float]) -> dict[str, float | int]:
    if not samples_s:
        return {
            "samples": 0,
            "total_s": 0.0,
            "average_ms": 0.0,
            "p95_ms": 0.0,
            "effective_fps": 0.0,
        }

    ordered = sorted(samples_s)
    p95_index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    total = sum(samples_s)
    return {
        "samples": len(samples_s),
        "total_s": total,
        "average_ms": (total / len(samples_s)) * 1000.0,
        "p95_ms": ordered[p95_index] * 1000.0,
        "effective_fps": (len(samples_s) / total) if total > 0 else 0.0,
    }


def _system_report() -> dict[str, str | None]:
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "macos_version": platform.mac_ver()[0] or None,
        "python": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "opencv": cv2.__version__,
        "mediapipe": _installed_version("mediapipe"),
    }


def probe_runtime(
    source: CameraConfig | CameraProbeSource,
    *,
    tracker: PerformanceTracker,
    sample_frames: int = 60,
    camera_factory: CameraFactory = CameraSource,
) -> dict[str, Any]:
    """Measure the real local capture/tracker path without persisting camera pixels.

    ``source`` may be a :class:`CameraConfig` (built via ``camera_factory``) or
    any already-constructed frame source (camera or video file).
    """

    if sample_frames < 1:
        raise ValueError("sample_frames must be at least 1")

    if isinstance(source, CameraConfig):
        config = source
        camera = camera_factory(config)
    else:
        config = None
        camera = source
    read_times: list[float] = []
    tracker_times: list[float] = []
    tracked_frames = 0
    observed_width = 0
    observed_height = 0
    observed_channels = 0
    camera_info: CameraInfo | None = None
    elapsed_s = 0.0

    try:
        camera.open()
        camera_info = camera.info()
        tracker.start()
        session_start = time.perf_counter()

        for frame_index in range(sample_frames):
            read_start = time.perf_counter()
            frame = camera.read()
            read_times.append(time.perf_counter() - read_start)

            if frame_index == 0:
                observed_height = int(frame.shape[0])
                observed_width = int(frame.shape[1])
                observed_channels = int(frame.shape[2]) if frame.ndim >= 3 else 1

            tracker_start = time.perf_counter()
            performance = tracker.track(
                frame,
                frame_index=frame_index,
                timestamp_s=time.perf_counter() - session_start,
            )
            tracker_times.append(time.perf_counter() - tracker_start)
            tracked_frames += int(performance.tracked)

        elapsed_s = time.perf_counter() - session_start
    finally:
        tracker.close()
        camera.close()

    if camera_info is None:
        raise RuntimeError("camera probe did not produce camera information")

    requested = (
        {"width": config.width, "height": config.height, "fps": config.fps}
        if config is not None
        else {"width": None, "height": None, "fps": None}
    )
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "system": _system_report(),
        "privacy": {
            "camera_pixels_persisted": False,
            "network_required": False,
            "model_downloaded": False,
        },
        "camera": {
            "index": config.index if config is not None else None,
            "kind": type(camera).__name__,
            "backend": camera_info.backend,
            "requested": requested,
            "reported": {
                "width": camera_info.width,
                "height": camera_info.height,
                "fps": camera_info.fps,
            },
            "observed_frame": {
                "width": observed_width,
                "height": observed_height,
                "channels": observed_channels,
            },
            "sample_frames": sample_frames,
            "elapsed_s": elapsed_s,
            "overall_fps": (sample_frames / elapsed_s) if elapsed_s > 0 else 0.0,
            "read_timing": _timing_summary(read_times),
        },
        "tracker": {
            "name": tracker.name,
            "profile": tracker.profile,
            "sample_frames": sample_frames,
            "tracked_frames": tracked_frames,
            "tracking_rate": tracked_frames / sample_frames,
            "processing_timing": _timing_summary(tracker_times),
        },
    }
