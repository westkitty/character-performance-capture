from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .geometry import as_points

RIG_SUFFIX = ".rig.json"
DEFAULT_TOPOLOGY = "mediapipe-face-landmarker-478"


class RigFormatError(ValueError):
    """Raised when a character rig file violates the rig contract."""


@dataclass(frozen=True)
class CharacterRig:
    """Neutral control mesh for an authorized character reference image.

    ``points`` are pixel coordinates in the reference image, in the same
    ordering/topology a tracker emits (MediaPipe Face Landmarker by default).
    The rig is renderer input only; it never touches ``.cpc`` performance data.
    """

    width: int
    height: int
    points: np.ndarray  # (N, 2) float32, pixel coordinates
    topology: str = DEFAULT_TOPOLOGY
    name: str = "character"

    def __post_init__(self) -> None:
        if int(self.width) <= 0 or int(self.height) <= 0:
            raise RigFormatError("rig width and height must be positive integers")
        try:
            points = as_points(self.points, name="rig points")
        except ValueError as exc:
            raise RigFormatError(str(exc)) from exc
        if not isinstance(self.topology, str) or not self.topology.strip():
            raise RigFormatError("rig topology must be a non-empty string")
        if not isinstance(self.name, str) or not self.name.strip():
            raise RigFormatError("rig name must be a non-empty string")
        object.__setattr__(self, "width", int(self.width))
        object.__setattr__(self, "height", int(self.height))
        object.__setattr__(self, "points", points)

    @property
    def point_count(self) -> int:
        return int(self.points.shape[0])

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology": self.topology,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "points": [[float(x), float(y)] for x, y in self.points],
        }


def default_rig_path(character_path: str | Path) -> Path:
    """`<character>.png` -> `<character>.png.rig.json` beside the reference image."""

    return Path(f"{Path(character_path)}{RIG_SUFFIX}")


def load_rig(path: str | Path) -> CharacterRig:
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise RigFormatError(f"rig file is not readable JSON: {path}") from exc

    if not isinstance(raw, dict):
        raise RigFormatError("rig file must contain a JSON object")

    for key in ("width", "height", "points"):
        if key not in raw:
            raise RigFormatError(f"rig file is missing required key: {key!r}")

    width = raw["width"]
    height = raw["height"]
    if not isinstance(width, int) or isinstance(width, bool) or width <= 0:
        raise RigFormatError("rig width must be a positive integer")
    if not isinstance(height, int) or isinstance(height, bool) or height <= 0:
        raise RigFormatError("rig height must be a positive integer")

    points_payload = raw["points"]
    if not isinstance(points_payload, list) or not points_payload:
        raise RigFormatError("rig points must be a non-empty array")
    for row in points_payload:
        if (
            not isinstance(row, (list, tuple))
            or len(row) != 2
            or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in row)
        ):
            raise RigFormatError("each rig point must be a [x, y] pair of numbers")

    try:
        points = as_points(points_payload, name="rig points")
    except ValueError as exc:
        raise RigFormatError(str(exc)) from exc

    topology = raw.get("topology", DEFAULT_TOPOLOGY)
    name = raw.get("name", path.stem)
    try:
        return CharacterRig(
            width=width, height=height, points=points, topology=topology, name=name
        )
    except RigFormatError:
        raise
    except ValueError as exc:
        raise RigFormatError(str(exc)) from exc


def save_rig(rig: CharacterRig, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rig.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


def derive_rig_from_image(
    image_path: str | Path,
    model_path: str | Path,
    *,
    delegate: str = "cpu",
    name: str | None = None,
) -> CharacterRig:
    """One-time: detect a neutral landmark mesh on a character reference image.

    This is the only rig path that imports MediaPipe. The model asset is never
    downloaded or bundled; the caller supplies a local authorized ``.task`` file.
    """

    import cv2

    from .mediapipe_tracker import create_face_landmarker, landmarker_points

    image_path = Path(image_path)
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"character reference image not found: {image_path}")
    height, width = image.shape[:2]

    landmarker = create_face_landmarker(model_path, delegate=delegate, running_mode="IMAGE")
    try:
        normalized = landmarker_points(landmarker, image, timestamp_ms=None)
    finally:
        landmarker.close()
    if normalized is None:
        raise RuntimeError(
            "no face detected in character reference; supply a rig sidecar JSON instead"
        )

    points = normalized.copy()
    points[:, 0] *= width
    points[:, 1] *= height
    return CharacterRig(
        width=width,
        height=height,
        points=points,
        name=name or image_path.stem,
    )
