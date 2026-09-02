from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from numbers import Real
from typing import Any

JsonScalar = str | int | float | bool | None


def _finite(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a finite number")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"{field_name} must be finite")
    return normalized


def _finite_tuple(
    values: tuple[float, ...] | list[float] | None,
    length: int,
    field_name: str,
) -> tuple[float, ...] | None:
    if values is None:
        return None
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{field_name} must be a sequence")
    if len(values) != length:
        raise ValueError(f"{field_name} must contain exactly {length} values")
    return tuple(_finite(value, field_name) for value in values)


@dataclass(frozen=True)
class Landmark:
    """Tracker-neutral normalized facial landmark."""

    x: float
    y: float
    z: float = 0.0
    visibility: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _finite(self.x, "landmark.x"))
        object.__setattr__(self, "y", _finite(self.y, "landmark.y"))
        object.__setattr__(self, "z", _finite(self.z, "landmark.z"))
        if self.visibility is not None:
            visibility = _finite(self.visibility, "landmark.visibility")
            if not 0.0 <= visibility <= 1.0:
                raise ValueError("landmark.visibility must be between 0 and 1")
            object.__setattr__(self, "visibility", visibility)

    def to_dict(self) -> dict[str, float | None]:
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "visibility": self.visibility,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Landmark:
        if not isinstance(payload, dict):
            raise TypeError("landmark must be an object")
        return cls(
            x=payload["x"],
            y=payload["y"],
            z=payload.get("z", 0.0),
            visibility=payload.get("visibility"),
        )


@dataclass(frozen=True)
class PerformanceFrame:
    """One portable frame of performer state, independent of any renderer."""

    frame_index: int
    timestamp_s: float
    tracked: bool
    tracker: str
    profile: str = "generic"
    tracking_confidence: float | None = None
    blendshapes: dict[str, float] = field(default_factory=dict)
    head_rotation_deg: tuple[float, float, float] | None = None
    gaze_left: tuple[float, float] | None = None
    gaze_right: tuple[float, float] | None = None
    face_transform: tuple[float, ...] | None = None
    landmarks: tuple[Landmark, ...] = ()
    metadata: dict[str, JsonScalar] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if type(self.frame_index) is not int:
            raise TypeError("frame_index must be an integer")
        if self.frame_index < 0:
            raise ValueError("frame_index must be non-negative")
        if type(self.tracked) is not bool:
            raise TypeError("tracked must be a boolean")
        if not isinstance(self.tracker, str):
            raise TypeError("tracker must be a string")
        if not self.tracker.strip():
            raise ValueError("tracker must not be empty")
        if not isinstance(self.profile, str):
            raise TypeError("profile must be a string")
        if not self.profile.strip():
            raise ValueError("profile must not be empty")

        timestamp_s = _finite(self.timestamp_s, "timestamp_s")
        if timestamp_s < 0.0:
            raise ValueError("timestamp_s must be non-negative")
        object.__setattr__(self, "timestamp_s", timestamp_s)

        if self.tracking_confidence is not None:
            confidence = _finite(self.tracking_confidence, "tracking_confidence")
            if not 0.0 <= confidence <= 1.0:
                raise ValueError("tracking_confidence must be between 0 and 1")
            object.__setattr__(self, "tracking_confidence", confidence)

        if not isinstance(self.blendshapes, dict):
            raise TypeError("blendshapes must be an object")
        normalized_blendshapes: dict[str, float] = {}
        for name, raw_value in self.blendshapes.items():
            if not isinstance(name, str):
                raise TypeError("blendshape names must be strings")
            if not name.strip():
                raise ValueError("blendshape names must not be empty")
            value = _finite(raw_value, f"blendshape:{name}")
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"blendshape {name!r} must be between 0 and 1")
            normalized_blendshapes[name] = value
        object.__setattr__(self, "blendshapes", normalized_blendshapes)

        head_rotation = _finite_tuple(self.head_rotation_deg, 3, "head_rotation_deg")
        gaze_left = _finite_tuple(self.gaze_left, 2, "gaze_left")
        gaze_right = _finite_tuple(self.gaze_right, 2, "gaze_right")
        face_transform = _finite_tuple(self.face_transform, 16, "face_transform")

        if not isinstance(self.landmarks, (tuple, list)):
            raise TypeError("landmarks must be a sequence")
        landmarks = tuple(self.landmarks)
        if any(not isinstance(item, Landmark) for item in landmarks):
            raise TypeError("landmarks must contain Landmark objects")

        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be an object")
        metadata = dict(self.metadata)

        object.__setattr__(self, "head_rotation_deg", head_rotation)
        object.__setattr__(self, "gaze_left", gaze_left)
        object.__setattr__(self, "gaze_right", gaze_right)
        object.__setattr__(self, "face_transform", face_transform)
        object.__setattr__(self, "landmarks", landmarks)
        object.__setattr__(self, "metadata", metadata)

        try:
            json.dumps(metadata, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("metadata must contain JSON-serializable finite values") from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "timestamp_s": self.timestamp_s,
            "tracked": self.tracked,
            "tracker": self.tracker,
            "profile": self.profile,
            "tracking_confidence": self.tracking_confidence,
            "blendshapes": dict(self.blendshapes),
            "head_rotation_deg": list(self.head_rotation_deg) if self.head_rotation_deg else None,
            "gaze_left": list(self.gaze_left) if self.gaze_left else None,
            "gaze_right": list(self.gaze_right) if self.gaze_right else None,
            "face_transform": list(self.face_transform) if self.face_transform else None,
            "landmarks": [landmark.to_dict() for landmark in self.landmarks],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> PerformanceFrame:
        if not isinstance(payload, dict):
            raise TypeError("performance frame must be an object")

        landmarks_payload = payload.get("landmarks", [])
        if not isinstance(landmarks_payload, list):
            raise TypeError("landmarks must be an array")

        return cls(
            frame_index=payload["frame_index"],
            timestamp_s=payload["timestamp_s"],
            tracked=payload["tracked"],
            tracker=payload["tracker"],
            profile=payload.get("profile", "generic"),
            tracking_confidence=payload.get("tracking_confidence"),
            blendshapes=payload.get("blendshapes", {}),
            head_rotation_deg=payload.get("head_rotation_deg"),
            gaze_left=payload.get("gaze_left"),
            gaze_right=payload.get("gaze_right"),
            face_transform=payload.get("face_transform"),
            landmarks=tuple(Landmark.from_dict(item) for item in landmarks_payload),
            metadata=payload.get("metadata", {}),
        )
