from __future__ import annotations

import json
import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .performance import PerformanceFrame

CALIBRATION_FORMAT = "cpc-calibration-profile"
CALIBRATION_VERSION = 1


def _finite(value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("calibration values must be finite")
    return value


@dataclass(frozen=True)
class ChannelRange:
    neutral: float
    minimum: float
    maximum: float

    def __post_init__(self) -> None:
        n, lo, hi = map(_finite, (self.neutral, self.minimum, self.maximum))
        if lo > hi:
            raise ValueError("calibration minimum cannot exceed maximum")
        object.__setattr__(self, "neutral", n)
        object.__setattr__(self, "minimum", lo)
        object.__setattr__(self, "maximum", hi)

    def normalize(self, value: float) -> float:
        value = _finite(value)
        if value >= self.neutral:
            span = self.maximum - self.neutral
            return 0.0 if span <= 0 else min(1.0, (value - self.neutral) / span)
        span = self.neutral - self.minimum
        return 0.0 if span <= 0 else max(-1.0, (value - self.neutral) / span)


@dataclass(frozen=True)
class CalibrationProfile:
    name: str = "session"
    channels: dict[str, ChannelRange] = field(default_factory=dict)
    unavailable: tuple[str, ...] = ()
    character_id: str | None = None
    version: int = CALIBRATION_VERSION

    def to_dict(self) -> dict:
        return {
            "format": CALIBRATION_FORMAT,
            "version": self.version,
            "name": self.name,
            "character_id": self.character_id,
            "unavailable": list(self.unavailable),
            "channels": {
                key: {"neutral": value.neutral, "minimum": value.minimum, "maximum": value.maximum}
                for key, value in sorted(self.channels.items())
            },
        }

    @classmethod
    def from_dict(cls, payload: dict) -> CalibrationProfile:
        if payload.get("format") != CALIBRATION_FORMAT:
            raise ValueError("unsupported calibration format")
        if payload.get("version") != CALIBRATION_VERSION:
            raise ValueError(f"unsupported calibration version: {payload.get('version')}")
        channels = {
            str(key): ChannelRange(**value)
            for key, value in dict(payload.get("channels", {})).items()
        }
        return cls(
            name=str(payload.get("name", "session")),
            channels=channels,
            unavailable=tuple(str(x) for x in payload.get("unavailable", [])),
            character_id=payload.get("character_id"),
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> CalibrationProfile:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def build_calibration_profile(
    frames: Iterable[PerformanceFrame],
    *,
    name: str = "session",
    character_id: str | None = None,
) -> CalibrationProfile:
    frames = tuple(frame for frame in frames if frame.tracked)
    channels: dict[str, list[float]] = {}
    for frame in frames:
        if frame.head_rotation_deg is not None:
            for label, value in zip(("head_pitch", "head_yaw", "head_roll"), frame.head_rotation_deg):
                channels.setdefault(label, []).append(float(value))
        for key, value in frame.blendshapes.items():
            channels.setdefault(f"blendshape:{key}", []).append(float(value))
        if frame.gaze_left is not None:
            channels.setdefault("gaze_left_x", []).append(frame.gaze_left[0])
            channels.setdefault("gaze_left_y", []).append(frame.gaze_left[1])
        if frame.gaze_right is not None:
            channels.setdefault("gaze_right_x", []).append(frame.gaze_right[0])
            channels.setdefault("gaze_right_y", []).append(frame.gaze_right[1])

    ranges: dict[str, ChannelRange] = {}
    for key, values in channels.items():
        ordered = sorted(values)
        neutral = ordered[len(ordered) // 2]
        ranges[key] = ChannelRange(neutral=neutral, minimum=min(values), maximum=max(values))

    requested = {
        "head_pitch", "head_yaw", "head_roll",
        "blendshape:jawOpen", "blendshape:mouthSmileLeft", "blendshape:mouthSmileRight",
        "blendshape:eyeBlinkLeft", "blendshape:eyeBlinkRight",
        "blendshape:browInnerUp", "gaze_left_x", "gaze_left_y", "gaze_right_x", "gaze_right_y",
    }
    return CalibrationProfile(
        name=name,
        channels=ranges,
        unavailable=tuple(sorted(requested - set(ranges))),
        character_id=character_id,
    )
