from __future__ import annotations

import argparse
import json
from contextlib import ExitStack
from pathlib import Path

import cv2

from .capture import CameraConfig, CameraSource
from .diagnostics import probe_runtime
from .mediapipe_tracker import MediaPipeFaceTracker
from .performance_pipeline import PerformancePipeline
from .processors import PassthroughRenderer, draw_metrics, draw_tracking_status
from .recording import PerformanceRecorder, read_capture
from .tracking import NullTracker, PerformanceTracker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Character Performance Capture")
    parser.add_argument("--camera", type=int, default=0, help="OpenCV camera index")
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--fps", type=float, default=None)
    parser.add_argument("--mirror", action="store_true", help="Mirror preview horizontally")
    parser.add_argument(
        "--tracker",
        choices=("null", "mediapipe"),
        default="null",
        help="Performance tracker backend",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=None,
        help="Local tracker model asset; required for --tracker mediapipe",
    )
    parser.add_argument(
        "--record-performance",
        type=Path,
        default=None,
        metavar="CAPTURE.cpc",
        help="Record portable performance data; never records camera pixels",
    )
    parser.add_argument(
        "--inspect-performance",
        type=Path,
        default=None,
        metavar="CAPTURE.cpc",
        help="Validate a capture and print a compact summary instead of opening a camera",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Probe the local camera/tracker path and print a JSON diagnostics report",
    )
    parser.add_argument(
        "--doctor-frames",
        type=int,
        default=60,
        metavar="N",
        help="Number of frames to sample with --doctor (default: 60)",
    )
    return parser


def build_tracker(name: str, model_path: Path | None) -> PerformanceTracker:
    if name == "null":
        return NullTracker()
    if name == "mediapipe":
        if model_path is None:
            raise ValueError("--model is required when --tracker mediapipe is selected")
        return MediaPipeFaceTracker(model_path)
    raise ValueError(f"unknown tracker: {name}")


def run_preview(
    config: CameraConfig,
    *,
    tracker: PerformanceTracker,
    mirror: bool = False,
    record_path: Path | None = None,
) -> None:
    pipeline = PerformancePipeline(PassthroughRenderer(), tracker=tracker)
    window_name = "Character Performance Capture"

    try:
        with ExitStack() as stack:
            camera = stack.enter_context(CameraSource(config))
            stack.enter_context(pipeline)
            recorder = None
            if record_path is not None:
                recorder = stack.enter_context(
                    PerformanceRecorder(
                        record_path,
                        tracker=tracker.name,
                        profile=tracker.profile,
                    )
                )

            while True:
                frame = camera.read()
                if mirror:
                    frame = cv2.flip(frame, 1)

                result = pipeline.process(frame)
                if recorder is not None:
                    recorder.write(result.performance)

                preview = draw_metrics(result.frame, result.metrics)
                preview = draw_tracking_status(preview, result.performance)
                cv2.imshow(window_name, preview)

                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    break
    finally:
        pipeline.close()
        cv2.destroyAllWindows()


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

    try:
        tracker = build_tracker(args.tracker, args.model)
    except ValueError as exc:
        parser.error(str(exc))

    config = CameraConfig(
        index=args.camera,
        width=args.width,
        height=args.height,
        fps=args.fps,
    )

    if args.doctor:
        try:
            report = probe_runtime(
                config,
                tracker=tracker,
                sample_frames=args.doctor_frames,
            )
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            parser.exit(2, f"cpc doctor failed: {exc}\n")
        print(json.dumps(report, indent=2, sort_keys=True))
        return

    run_preview(
        config,
        tracker=tracker,
        mirror=args.mirror,
        record_path=args.record_performance,
    )


if __name__ == "__main__":
    main()
