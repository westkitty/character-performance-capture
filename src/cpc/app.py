from __future__ import annotations

import argparse
import json
import sys
from contextlib import ExitStack
from pathlib import Path

import cv2

from .capture import CameraConfig, CameraSource, FrameSource, VideoFileSource
from .diagnostics import probe_runtime
from .mediapipe_tracker import MediaPipeFaceTracker
from .performance_pipeline import PerformancePipeline
from .processors import PassthroughRenderer, draw_metrics, draw_tracking_status
from .recording import PerformanceRecorder, read_capture
from .rig import CharacterRig, default_rig_path, derive_rig_from_image, load_rig, save_rig
from .tracking import NullTracker, PerformanceTracker

_WORKFLOW = """\
core live route:
  webcam / video  ->  tracker  ->  PerformanceFrame  ->  character renderer  ->  preview
                                        |                                          |
                                        +-> optional .cpc recording               +-> optional virtual camera

examples:
  cpc --camera 0 --mirror
  cpc --doctor --camera 0 --doctor-frames 120
  cpc --video clip.mp4 --tracker mediapipe --model face_landmarker.task \\
      --render rig --character char.png --record-performance takes/take.cpc
  cpc --inspect-performance takes/take.cpc
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cpc",
        description="Character Performance Capture: local-first webcam-driven character rendering.",
        epilog=_WORKFLOW,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    source = parser.add_argument_group("frame source")
    source.add_argument("--camera", type=int, default=0, help="OpenCV camera index (default: 0)")
    source.add_argument(
        "--video",
        type=Path,
        default=None,
        metavar="PATH",
        help="Read frames from a local video file instead of a camera",
    )
    source.add_argument("--loop", action="store_true", help="Loop the --video source at EOF")
    source.add_argument("--width", type=int, default=None)
    source.add_argument("--height", type=int, default=None)
    source.add_argument("--fps", type=float, default=None)
    source.add_argument("--mirror", action="store_true", help="Mirror the source horizontally")

    track = parser.add_argument_group("tracker")
    track.add_argument(
        "--tracker",
        choices=("null", "mediapipe"),
        default="null",
        help="Performance tracker backend (default: null)",
    )
    track.add_argument(
        "--model",
        type=Path,
        default=None,
        help="Local Face Landmarker .task asset; required for --tracker mediapipe",
    )
    track.add_argument(
        "--tracker-delegate",
        choices=("cpu", "gpu"),
        default="cpu",
        help="MediaPipe inference delegate (default: cpu; gpu can abort headless macOS)",
    )

    render = parser.add_argument_group("character renderer")
    render.add_argument(
        "--render",
        choices=("passthrough", "rig"),
        default="passthrough",
        help="Renderer behind the PerformanceFrame seam (default: passthrough)",
    )
    render.add_argument(
        "--character",
        type=Path,
        default=None,
        metavar="IMAGE",
        help="Authorized local character reference image; required for --render rig",
    )
    render.add_argument(
        "--rig",
        type=Path,
        default=None,
        metavar="RIG.json",
        help="Explicit rig sidecar (default: <character>.rig.json)",
    )
    render.add_argument(
        "--derive-rig",
        action="store_true",
        help="Detect a neutral rig on --character with --model, write the sidecar, and exit",
    )
    render.add_argument("--expression-gain", type=float, default=1.0)
    render.add_argument("--head-gain", type=float, default=1.0)

    out = parser.add_argument_group("output")
    out.add_argument(
        "--record-performance",
        type=Path,
        default=None,
        metavar="CAPTURE.cpc",
        help="Record portable performance data; never records camera pixels",
    )
    out.add_argument(
        "--record-video",
        type=Path,
        default=None,
        metavar="OUT.mp4",
        help="Write the rendered preview frames to a video file",
    )
    out.add_argument(
        "--virtual-camera",
        action="store_true",
        help="Publish rendered frames to a virtual camera (needs the output-virtualcam extra)",
    )
    out.add_argument(
        "--vcam-size",
        default="1280x720",
        metavar="WxH",
        help="Virtual camera resolution; must be one the backend accepts (default: 1280x720)",
    )
    out.add_argument("--no-window", action="store_true", help="Do not open a preview window")
    out.add_argument(
        "--frames",
        type=int,
        default=0,
        metavar="N",
        help="Stop after N frames (0 = run until quit / end of stream)",
    )

    inspect = parser.add_argument_group("offline / diagnostics")
    inspect.add_argument(
        "--inspect-performance",
        type=Path,
        default=None,
        metavar="CAPTURE.cpc",
        help="Validate a capture and print a summary instead of opening a source",
    )
    inspect.add_argument(
        "--doctor",
        action="store_true",
        help="Probe the local source/tracker path and print a JSON diagnostics report",
    )
    inspect.add_argument("--doctor-frames", type=int, default=60, metavar="N")
    return parser


def build_tracker(name: str, model_path: Path | None, *, delegate: str = "cpu") -> PerformanceTracker:
    if name == "null":
        return NullTracker()
    if name == "mediapipe":
        if model_path is None:
            raise ValueError("--model is required when --tracker mediapipe is selected")
        return MediaPipeFaceTracker(model_path, delegate=delegate)
    raise ValueError(f"unknown tracker: {name}")


def build_frame_source(args: argparse.Namespace) -> FrameSource:
    if args.video is not None:
        return VideoFileSource(args.video, loop=args.loop)
    return CameraSource(
        CameraConfig(index=args.camera, width=args.width, height=args.height, fps=args.fps)
    )


def _resolve_rig(args: argparse.Namespace, character: Path) -> CharacterRig:
    rig_path = args.rig or default_rig_path(character)
    if rig_path.is_file():
        return load_rig(rig_path)
    if args.model is not None:
        rig = derive_rig_from_image(character, args.model, delegate=args.tracker_delegate)
        save_rig(rig, rig_path)
        return rig
    raise ValueError(
        f"no rig found at {rig_path}; pass --rig, or pass --model to derive one, "
        "or run --derive-rig first"
    )


def build_renderer(args: argparse.Namespace):
    if args.render == "passthrough":
        return PassthroughRenderer()
    if args.render == "rig":
        if args.character is None:
            raise ValueError("--character IMAGE is required when --render rig is selected")
        image = cv2.imread(str(args.character))
        if image is None:
            raise ValueError(f"could not read character reference image: {args.character}")
        rig = _resolve_rig(args, args.character)
        if image.shape[1] != rig.width or image.shape[0] != rig.height:
            image = cv2.resize(image, (rig.width, rig.height), interpolation=cv2.INTER_AREA)
        from .renderer import RigWarpRenderer

        return RigWarpRenderer(
            rig,
            image,
            expression_gain=args.expression_gain,
            head_gain=args.head_gain,
        )
    raise ValueError(f"unknown renderer: {args.render}")


def run_preview(
    source: FrameSource,
    *,
    tracker: PerformanceTracker,
    renderer,
    mirror: bool = False,
    record_path: Path | None = None,
    record_video: Path | None = None,
    virtual_camera: bool = False,
    vcam_size: tuple[int, int] = (1280, 720),
    show_window: bool = True,
    frame_limit: int = 0,
) -> None:
    pipeline = PerformancePipeline(renderer, tracker=tracker)
    window_name = "Character Performance Capture"
    writer: cv2.VideoWriter | None = None

    # On macOS the HighGUI window must exist before the MediaPipe graph builds
    # its GL/Metal context, otherwise the first cv2.imshow disturbs that context
    # and the face detector silently stops returning landmarks.
    if show_window:
        with _suppress_cv2():
            cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
            for _ in range(3):
                cv2.waitKey(1)

    try:
        with ExitStack() as stack:
            stack.enter_context(source)
            stack.enter_context(pipeline)

            recorder = None
            if record_path is not None:
                recorder = stack.enter_context(
                    PerformanceRecorder(
                        record_path, tracker=tracker.name, profile=tracker.profile
                    )
                )

            sink = None
            if virtual_camera:
                from .virtualcam import VirtualCameraSink

                info = source.info()
                vcam_w, vcam_h = vcam_size
                sink = stack.enter_context(
                    VirtualCameraSink(vcam_w, vcam_h, info.fps or 30.0)
                )
                print(f"virtual camera: {sink.device} ({sink.backend}) {vcam_w}x{vcam_h}")

            count = 0
            while True:
                frame = source.read()
                if mirror:
                    frame = cv2.flip(frame, 1)

                result = pipeline.process(frame)
                if recorder is not None:
                    recorder.write(result.performance)

                preview = draw_metrics(result.frame, result.metrics)
                preview = draw_tracking_status(preview, result.performance)

                if record_video is not None:
                    if writer is None:
                        h, w = preview.shape[:2]
                        writer = cv2.VideoWriter(
                            str(record_video),
                            cv2.VideoWriter_fourcc(*"mp4v"),
                            30.0,
                            (w, h),
                        )
                    writer.write(preview)
                if sink is not None:
                    sink.send(result.frame)
                if show_window:
                    cv2.imshow(window_name, preview)
                    key = cv2.waitKey(1) & 0xFF
                    if key in (27, ord("q")):
                        break

                count += 1
                if frame_limit and count >= frame_limit:
                    break
    except (RuntimeError, KeyboardInterrupt) as exc:
        if not isinstance(exc, KeyboardInterrupt) and "end of video stream" not in str(exc):
            raise
    finally:
        if writer is not None:
            writer.release()
        with _suppress_cv2():
            cv2.destroyAllWindows()


class _suppress_cv2:
    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type, exc, tb) -> bool:
        return exc_type is not None and issubclass(exc_type, cv2.error)


def inspect_performance(path: Path) -> None:
    capture = read_capture(path)
    status = "complete" if capture.complete else "partial/recoverable"
    print(f"capture: {path}")
    print(f"status: {status}")
    print(f"tracker: {capture.header.tracker}")
    print(f"profile: {capture.header.profile}")
    print(f"frames: {capture.frame_count}")
    print(f"duration_s: {capture.duration_s:.3f}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.inspect_performance is not None:
        inspect_performance(args.inspect_performance)
        return

    if args.derive_rig:
        if args.character is None or args.model is None:
            parser.error("--derive-rig requires --character IMAGE and --model face_landmarker.task")
        rig = derive_rig_from_image(args.character, args.model, delegate=args.tracker_delegate)
        rig_path = args.rig or default_rig_path(args.character)
        save_rig(rig, rig_path)
        print(f"wrote rig: {rig_path} ({rig.point_count} points, {rig.width}x{rig.height})")
        return

    try:
        tracker = build_tracker(args.tracker, args.model, delegate=args.tracker_delegate)
        renderer = build_renderer(args)
    except ValueError as exc:
        parser.error(str(exc))

    if args.doctor:
        source = build_frame_source(args)
        try:
            report = probe_runtime(
                source, tracker=tracker, sample_frames=args.doctor_frames
            )
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            parser.exit(2, f"cpc doctor failed: {exc}\n")
        print(json.dumps(report, indent=2, sort_keys=True))
        return

    try:
        vw, vh = (int(part) for part in str(args.vcam_size).lower().split("x", 1))
        vcam_size = (vw, vh)
    except ValueError:
        parser.error("--vcam-size must look like 1280x720")

    run_preview(
        build_frame_source(args),
        tracker=tracker,
        renderer=renderer,
        mirror=args.mirror,
        record_path=args.record_performance,
        record_video=args.record_video,
        virtual_camera=args.virtual_camera,
        vcam_size=vcam_size,
        show_window=not args.no_window,
        frame_limit=max(0, args.frames),
    )


if __name__ == "__main__":
    sys.exit(main())
