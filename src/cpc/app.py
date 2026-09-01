from __future__ import annotations

import argparse

import cv2

from .capture import CameraConfig, CameraSource
from .pipeline import Pipeline
from .processors import PassthroughRenderer, draw_metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Character Performance Capture")
    parser.add_argument("--camera", type=int, default=0, help="OpenCV camera index")
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--fps", type=float, default=None)
    parser.add_argument("--mirror", action="store_true", help="Mirror preview horizontally")
    return parser


def run_preview(config: CameraConfig, mirror: bool = False) -> None:
    pipeline = Pipeline([PassthroughRenderer()])
    window_name = "Character Performance Capture"

    try:
        with CameraSource(config) as camera, pipeline:
            while True:
                frame = camera.read()
                if mirror:
                    frame = cv2.flip(frame, 1)

                rendered, metrics = pipeline.process(frame)
                preview = draw_metrics(rendered, metrics)
                cv2.imshow(window_name, preview)

                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    break
    finally:
        pipeline.close()
        cv2.destroyAllWindows()


def main() -> None:
    args = build_parser().parse_args()
    config = CameraConfig(
        index=args.camera,
        width=args.width,
        height=args.height,
        fps=args.fps,
    )
    run_preview(config, mirror=args.mirror)


if __name__ == "__main__":
    main()
