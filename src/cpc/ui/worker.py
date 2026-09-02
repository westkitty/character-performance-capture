from __future__ import annotations

import time
import traceback
from contextlib import ExitStack
from pathlib import Path

import cv2
from PySide6.QtCore import QThread, Signal

from cpc.capture import CameraInfo
from cpc.diagnostics import probe_runtime
from cpc.performance_pipeline import PerformancePipeline
from cpc.recording import PerformanceRecorder
from cpc.rig import default_rig_path, derive_rig_from_image, save_rig
from cpc.session import (
    SessionConfig,
    build_frame_source_from_config,
    build_renderer_from_config,
    build_tracker_from_config,
)


class SessionWorker(QThread):
    """Executes the live capture/tracker/renderer loop on a dedicated thread."""

    frame_ready = Signal(object, object, object)  # (bgr_frame: np.ndarray, performance_frame, metrics)
    telemetry_updated = Signal(dict)
    state_changed = Signal(str)
    error_occurred = Signal(str, str)  # (user_message, technical_details)
    session_finished = Signal()

    def __init__(self, config: SessionConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self._running = True

    def stop(self) -> None:
        """Signal the worker thread to stop cleanly."""
        self._running = False

    def run(self) -> None:
        self.state_changed.emit("initializing")
        writer: cv2.VideoWriter | None = None
        camera_info: CameraInfo | None = None

        try:
            tracker = build_tracker_from_config(self.config)
            renderer = build_renderer_from_config(self.config)
            source = build_frame_source_from_config(self.config)
            pipeline = PerformancePipeline(renderer, tracker=tracker)
        except (RuntimeError, ValueError, FileNotFoundError, OSError, TypeError, AttributeError) as exc:
            user_msg = f"Failed to initialize session components: {exc}"
            self.error_occurred.emit(user_msg, traceback.format_exc())
            self.state_changed.emit("error")
            self.session_finished.emit()
            return

        try:
            with ExitStack() as stack:
                stack.enter_context(source)
                try:
                    camera_info = source.info()
                except (RuntimeError, OSError):
                    camera_info = None

                stack.enter_context(pipeline)

                recorder = None
                if self.config.record_performance_path is not None:
                    recorder = stack.enter_context(
                        PerformanceRecorder(
                            self.config.record_performance_path,
                            tracker=tracker.name,
                            profile=tracker.profile,
                        )
                    )

                sink = None
                if self.config.virtual_camera:
                    from cpc.virtualcam import VirtualCameraSink

                    vcam_w, vcam_h = self.config.vcam_size
                    fps = (camera_info.fps if camera_info and camera_info.fps > 0 else 30.0)
                    sink = stack.enter_context(
                        VirtualCameraSink(vcam_w, vcam_h, fps)
                    )

                self.state_changed.emit("running")
                count = 0
                tracked_count = 0
                session_start = time.perf_counter()
                fps_window_start = session_start
                fps_window_frames = 0
                current_fps = 0.0

                while self._running:
                    try:
                        frame = source.read()
                    except RuntimeError as read_exc:
                        if "end of video stream" in str(read_exc).lower():
                            break
                        raise

                    if self.config.mirror:
                        frame = cv2.flip(frame, 1)

                    result = pipeline.process(frame)
                    count += 1
                    fps_window_frames += 1

                    if result.performance.tracked:
                        tracked_count += 1
                        self.state_changed.emit("tracking")
                    else:
                        self.state_changed.emit("tracking_lost")

                    if recorder is not None:
                        recorder.write(result.performance)

                    if sink is not None:
                        sink.send(result.frame)

                    if self.config.record_video_path is not None:
                        if writer is None:
                            h, w = result.frame.shape[:2]
                            writer = cv2.VideoWriter(
                                str(self.config.record_video_path),
                                cv2.VideoWriter_fourcc(*"mp4v"),
                                30.0,
                                (w, h),
                            )
                        writer.write(result.frame)

                    # Update FPS calculations periodically
                    now = time.perf_counter()
                    if now - fps_window_start >= 0.5:
                        current_fps = fps_window_frames / (now - fps_window_start)
                        fps_window_frames = 0
                        fps_window_start = now

                    # Emit telemetry data
                    elapsed_s = now - session_start
                    telemetry = {
                        "state": "tracking" if result.performance.tracked else "tracking_lost",
                        "elapsed_s": elapsed_s,
                        "processed_frames": count,
                        "current_fps": current_fps,
                        "tracking_rate": (tracked_count / count) if count > 0 else 0.0,
                        "source_backend": camera_info.backend if camera_info else "unknown",
                        "source_width": frame.shape[1],
                        "source_height": frame.shape[0],
                        "source_reported_fps": camera_info.fps if camera_info else 0.0,
                        "tracker_name": tracker.name,
                        "tracker_latency_ms": result.metrics.processing_ms,
                        "render_latency_ms": 0.0,
                        "total_latency_ms": result.metrics.processing_ms,
                        "landmark_count": len(result.performance.landmarks) if result.performance.landmarks is not None else 0,
                        "blendshape_count": len(result.performance.blendshapes) if result.performance.blendshapes is not None else 0,
                        "recording_cpc": recorder is not None,
                        "recording_video": writer is not None,
                        "virtual_camera": sink is not None,
                        "vcam_device": sink.device if sink else None,
                        "vcam_backend": sink.backend if sink else None,
                    }
                    self.telemetry_updated.emit(telemetry)

                    # Emit frame for UI display
                    if not self.config.no_window:
                        self.frame_ready.emit(result.frame, result.performance, result.metrics)

                    if self.config.frames > 0 and count >= self.config.frames:
                        break

        except (RuntimeError, ValueError, OSError, cv2.error, KeyError, AttributeError) as exc:
            if self._running:
                user_msg = f"Capture loop encountered an error: {exc}"
                self.error_occurred.emit(user_msg, traceback.format_exc())
                self.state_changed.emit("error")
        finally:
            self.state_changed.emit("stopping")
            if writer is not None:
                writer.release()
            self.state_changed.emit("stopped")
            self.session_finished.emit()


class DiagnosticsWorker(QThread):
    """Executes the probe_runtime diagnostic hardware benchmark asynchronously."""

    probe_finished = Signal(dict)
    error_occurred = Signal(str, str)

    def __init__(self, config: SessionConfig, sample_frames: int = 60, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.sample_frames = sample_frames

    def run(self) -> None:
        try:
            tracker = build_tracker_from_config(self.config)
            source = build_frame_source_from_config(self.config)
            report = probe_runtime(source, tracker=tracker, sample_frames=self.sample_frames)
            self.probe_finished.emit(report)
        except (RuntimeError, ValueError, FileNotFoundError, OSError, TypeError) as exc:
            user_msg = f"Diagnostics probe failed: {exc}"
            self.error_occurred.emit(user_msg, traceback.format_exc())


class DeriveRigWorker(QThread):
    """Executes facial landmark detection and rig triangulation on a character image."""

    rig_derived = Signal(object, str)  # (CharacterRig, rig_path_str)
    error_occurred = Signal(str, str)

    def __init__(
        self,
        character_path: Path,
        model_path: Path,
        rig_path: Path | None = None,
        delegate: str = "cpu",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.character_path = character_path
        self.model_path = model_path
        self.rig_path = rig_path or default_rig_path(character_path)
        self.delegate = delegate

    def run(self) -> None:
        try:
            rig = derive_rig_from_image(
                self.character_path, self.model_path, delegate=self.delegate
            )
            save_rig(rig, self.rig_path)
            self.rig_derived.emit(rig, str(self.rig_path))
        except (RuntimeError, ValueError, FileNotFoundError, OSError, TypeError) as exc:
            user_msg = f"Failed to derive character rig: {exc}"
            self.error_occurred.emit(user_msg, traceback.format_exc())
