from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Literal

AdapterKind = Literal["tracker", "renderer"]
Readiness = Literal["ready", "missing-dependency", "missing-model", "unavailable"]


@dataclass(frozen=True)
class AdapterCapability:
    adapter_id: str
    kind: AdapterKind
    display_name: str
    dependency: str | None
    model_required: bool
    model_path_required: bool
    channels: tuple[str, ...]
    local_offline: bool
    provenance: str
    hardware: str
    readiness: Readiness
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def default_adapter_registry(*, mediapipe_model: str | Path | None = None) -> tuple[AdapterCapability, ...]:
    mp_available = find_spec("mediapipe") is not None
    model_ok = bool(mediapipe_model and Path(mediapipe_model).is_file())
    if not mp_available:
        mp_state: Readiness = "missing-dependency"
        mp_detail = "Install the optional tracker-mediapipe extra."
    elif not model_ok:
        mp_state = "missing-model"
        mp_detail = "A user-supplied Face Landmarker .task model is required."
    else:
        mp_state = "ready"
        mp_detail = "Local package and user-supplied model are available."

    return (
        AdapterCapability(
            adapter_id="tracker.null",
            kind="tracker",
            display_name="No Tracking",
            dependency=None,
            model_required=False,
            model_path_required=False,
            channels=(),
            local_offline=True,
            provenance="CPC clean-room core",
            hardware="CPU",
            readiness="ready",
        ),
        AdapterCapability(
            adapter_id="tracker.mediapipe-face-landmarker",
            kind="tracker",
            display_name="MediaPipe Face Landmarker",
            dependency="mediapipe>=0.10.35,<0.11",
            model_required=True,
            model_path_required=True,
            channels=("blendshapes", "landmarks", "head_rotation", "face_transform"),
            local_offline=True,
            provenance="Google MediaPipe runtime; model rights are separate",
            hardware="CPU default; GPU optional and environment-sensitive",
            readiness=mp_state,
            detail=mp_detail,
        ),
        AdapterCapability(
            adapter_id="renderer.passthrough",
            kind="renderer",
            display_name="Passthrough",
            dependency=None,
            model_required=False,
            model_path_required=False,
            channels=(),
            local_offline=True,
            provenance="CPC clean-room core",
            hardware="CPU",
            readiness="ready",
        ),
        AdapterCapability(
            adapter_id="renderer.rig-warp",
            kind="renderer",
            display_name="RigWarp",
            dependency="opencv-python, numpy",
            model_required=False,
            model_path_required=False,
            channels=("landmarks", "head_rotation"),
            local_offline=True,
            provenance="CPC deterministic OpenCV/NumPy renderer",
            hardware="CPU",
            readiness="ready",
        ),
        AdapterCapability(
            adapter_id="reference.synthetic",
            kind="tracker",
            display_name="Synthetic Reference Adapter",
            dependency=None,
            model_required=False,
            model_path_required=False,
            channels=("blendshapes", "head_rotation", "confidence"),
            local_offline=True,
            provenance="CPC test/reference adapter; not a production tracker",
            hardware="None",
            readiness="ready",
            detail="Deterministic fixture only. No production model backend is claimed.",
        ),
    )
