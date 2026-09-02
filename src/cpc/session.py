from __future__ import annotations

import argparse
import shlex
from dataclasses import dataclass, field
from pathlib import Path

import cv2

from .capture import CameraConfig, CameraSource, FrameSource, VideoFileSource
from .mediapipe_tracker import MediaPipeFaceTracker
from .processors import PassthroughRenderer
from .rig import CharacterRig, default_rig_path, derive_rig_from_image, load_rig, save_rig
from .tracking import NullTracker, PerformanceTracker


@dataclass
class SessionConfig:
    """Unified session configuration supporting both CLI and GUI interfaces."""

    source_type: str = "camera"  # "camera" or "video"
    camera_index: int = 0
    video_path: Path | None = None
    loop_video: bool = False
    requested_width: int | None = None
    requested_height: int | None = None
    requested_fps: float | None = None
    mirror: bool = False

    tracker_type: str = "null"  # "null" or "mediapipe"
    model_path: Path | None = None
    tracker_delegate: str = "cpu"  # "cpu" or "gpu"

    renderer_type: str = "passthrough"  # "passthrough" or "rig"
    character_path: Path | None = None
    rig_path: Path | None = None
    expression_gain: float = 1.0
    head_gain: float = 1.0

    record_performance_path: Path | None = None
    record_video_path: Path | None = None
    virtual_camera: bool = False
    vcam_size: tuple[int, int] = (1280, 720)
    no_window: bool = False
    frames: int = 0

    extra_metadata: dict = field(default_factory=dict)

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> SessionConfig:
        """Construct a SessionConfig from parsed argparse arguments."""
        source_type = "video" if getattr(args, "video", None) is not None else "camera"
        vcam_w, vcam_h = 1280, 720
        vcam_size_raw = getattr(args, "vcam_size", "1280x720")
        if isinstance(vcam_size_raw, tuple):
            vcam_w, vcam_h = vcam_size_raw
        elif isinstance(vcam_size_raw, str):
            try:
                parts = vcam_size_raw.lower().split("x", 1)
                vcam_w, vcam_h = int(parts[0]), int(parts[1])
            except (ValueError, IndexError):
                pass

        return cls(
            source_type=source_type,
            camera_index=int(getattr(args, "camera", 0) or 0),
            video_path=Path(args.video) if getattr(args, "video", None) else None,
            loop_video=bool(getattr(args, "loop", False)),
            requested_width=getattr(args, "width", None),
            requested_height=getattr(args, "height", None),
            requested_fps=getattr(args, "fps", None),
            mirror=bool(getattr(args, "mirror", False)),
            tracker_type=getattr(args, "tracker", "null"),
            model_path=Path(args.model) if getattr(args, "model", None) else None,
            tracker_delegate=getattr(args, "tracker_delegate", "cpu"),
            renderer_type=getattr(args, "render", "passthrough"),
            character_path=Path(args.character) if getattr(args, "character", None) else None,
            rig_path=Path(args.rig) if getattr(args, "rig", None) else None,
            expression_gain=float(getattr(args, "expression_gain", 1.0)),
            head_gain=float(getattr(args, "head_gain", 1.0)),
            record_performance_path=(
                Path(args.record_performance)
                if getattr(args, "record_performance", None)
                else None
            ),
            record_video_path=(
                Path(args.record_video) if getattr(args, "record_video", None) else None
            ),
            virtual_camera=bool(getattr(args, "virtual_camera", False)),
            vcam_size=(vcam_w, vcam_h),
            no_window=bool(getattr(args, "no_window", False)),
            frames=int(getattr(args, "frames", 0) or 0),
        )

    def to_cli_args(self) -> list[str]:
        """Convert this configuration to a list of CLI argument tokens."""
        args: list[str] = []

        if self.source_type == "video" and self.video_path is not None:
            args.extend(["--video", str(self.video_path)])
            if self.loop_video:
                args.append("--loop")
        else:
            if self.camera_index != 0:
                args.extend(["--camera", str(self.camera_index)])

        if self.requested_width is not None:
            args.extend(["--width", str(self.requested_width)])
        if self.requested_height is not None:
            args.extend(["--height", str(self.requested_height)])
        if self.requested_fps is not None:
            args.extend(["--fps", str(self.requested_fps)])
        if self.mirror:
            args.append("--mirror")

        if self.tracker_type != "null":
            args.extend(["--tracker", self.tracker_type])
        if self.model_path is not None:
            args.extend(["--model", str(self.model_path)])
        if self.tracker_delegate != "cpu":
            args.extend(["--tracker-delegate", self.tracker_delegate])

        if self.renderer_type != "passthrough":
            args.extend(["--render", self.renderer_type])
        if self.character_path is not None:
            args.extend(["--character", str(self.character_path)])
        if self.rig_path is not None:
            args.extend(["--rig", str(self.rig_path)])
        if self.expression_gain != 1.0:
            args.extend(["--expression-gain", f"{self.expression_gain:.2f}"])
        if self.head_gain != 1.0:
            args.extend(["--head-gain", f"{self.head_gain:.2f}"])

        if self.record_performance_path is not None:
            args.extend(["--record-performance", str(self.record_performance_path)])
        if self.record_video_path is not None:
            args.extend(["--record-video", str(self.record_video_path)])
        if self.virtual_camera:
            args.append("--virtual-camera")
            if self.vcam_size != (1280, 720):
                args.extend(["--vcam-size", f"{self.vcam_size[0]}x{self.vcam_size[1]}"])

        if self.no_window:
            args.append("--no-window")
        if self.frames > 0:
            args.extend(["--frames", str(self.frames)])

        return args

    def to_command_string(self) -> str:
        """Format as a shell command for display and troubleshooting."""
        tokens = ["cpc"] + [shlex.quote(arg) for arg in self.to_cli_args()]
        return " ".join(tokens)

    def validate(self) -> list[str]:
        """Validate configuration sanity and return a list of actionable error strings."""
        errors: list[str] = []

        if self.source_type == "camera":
            if self.camera_index < 0:
                errors.append("Camera index must be non-negative.")
        elif self.source_type == "video":
            if self.video_path is None or str(self.video_path).strip() == "":
                errors.append("Video source selected, but no video file was provided.")
            elif not Path(self.video_path).is_file():
                errors.append(f"Video file does not exist: {self.video_path}")
        else:
            errors.append(f"Unknown source type: {self.source_type}")

        if self.requested_width is not None and self.requested_width <= 0:
            errors.append("Requested width must be greater than 0.")
        if self.requested_height is not None and self.requested_height <= 0:
            errors.append("Requested height must be greater than 0.")
        if self.requested_fps is not None and self.requested_fps <= 0:
            errors.append("Requested FPS must be greater than 0.")

        if self.tracker_type == "mediapipe":
            if self.model_path is None or str(self.model_path).strip() == "":
                errors.append("MediaPipe tracker requires a Face Landmarker .task model path.")
            elif not Path(self.model_path).is_file():
                errors.append(f"Model file does not exist: {self.model_path}")
            if self.tracker_delegate not in ("cpu", "gpu"):
                errors.append(f"Invalid tracker delegate: {self.tracker_delegate}")
        elif self.tracker_type != "null":
            errors.append(f"Unknown tracker type: {self.tracker_type}")

        if self.renderer_type == "rig":
            if self.character_path is None or str(self.character_path).strip() == "":
                errors.append("Rig-Warp renderer requires a character reference image.")
            elif not Path(self.character_path).is_file():
                errors.append(f"Character image does not exist: {self.character_path}")
            else:
                # Check rig availability
                rig_target = self.rig_path or default_rig_path(Path(self.character_path))
                if not rig_target.is_file() and (
                    self.model_path is None or not Path(self.model_path).is_file()
                ):
                    errors.append(
                        f"No rig sidecar found at '{rig_target}'. Provide an explicit rig "
                        "or specify a Face Landmarker model to derive one."
                    )
        elif self.renderer_type != "passthrough":
            errors.append(f"Unknown renderer type: {self.renderer_type}")

        if self.record_performance_path is not None:
            rec_path = Path(self.record_performance_path)
            if rec_path.is_file():
                errors.append(
                    f"Performance capture destination already exists: {rec_path} "
                    "(CPC never overwrites existing captures)."
                )

        if self.virtual_camera:
            w, h = self.vcam_size
            if w <= 0 or h <= 0:
                errors.append(f"Invalid virtual camera resolution: {w}x{h}")

        if self.frames < 0:
            errors.append("Frame limit cannot be negative.")

        return errors


def build_frame_source_from_config(config: SessionConfig) -> FrameSource:
    if config.source_type == "video":
        if config.video_path is None:
            raise ValueError("video path required for video source")
        return VideoFileSource(config.video_path, loop=config.loop_video)
    return CameraSource(
        CameraConfig(
            index=config.camera_index,
            width=config.requested_width,
            height=config.requested_height,
            fps=config.requested_fps,
        )
    )


def build_tracker_from_config(config: SessionConfig) -> PerformanceTracker:
    if config.tracker_type == "null":
        return NullTracker()
    if config.tracker_type == "mediapipe":
        if config.model_path is None:
            raise ValueError("--model is required when --tracker mediapipe is selected")
        return MediaPipeFaceTracker(config.model_path, delegate=config.tracker_delegate)
    raise ValueError(f"unknown tracker: {config.tracker_type}")


def resolve_rig_from_config(config: SessionConfig, character: Path) -> CharacterRig:
    rig_path = config.rig_path or default_rig_path(character)
    if rig_path.is_file():
        return load_rig(rig_path)
    if config.model_path is not None and config.model_path.is_file():
        rig = derive_rig_from_image(
            character, config.model_path, delegate=config.tracker_delegate
        )
        save_rig(rig, rig_path)
        return rig
    raise ValueError(
        f"no rig found at {rig_path}; pass an explicit rig, or pass a model to derive one."
    )


def build_renderer_from_config(config: SessionConfig):
    if config.renderer_type == "passthrough":
        return PassthroughRenderer()
    if config.renderer_type == "rig":
        if config.character_path is None:
            raise ValueError("character image is required when rig renderer is selected")
        image = cv2.imread(str(config.character_path))
        if image is None:
            raise ValueError(f"could not read character reference image: {config.character_path}")
        rig = resolve_rig_from_config(config, config.character_path)
        if image.shape[1] != rig.width or image.shape[0] != rig.height:
            image = cv2.resize(image, (rig.width, rig.height), interpolation=cv2.INTER_AREA)
        from .renderer import RigWarpRenderer

        return RigWarpRenderer(
            rig,
            image,
            expression_gain=config.expression_gain,
            head_gain=config.head_gain,
        )
    raise ValueError(f"unknown renderer: {config.renderer_type}")
