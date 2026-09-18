from __future__ import annotations

import platform
import sys
import time
import traceback
from contextlib import ExitStack
from pathlib import Path

import cv2
from PySide6.QtCore import QThread, Signal

from cpc.calibration import build_calibration_profile
from cpc.capture import CameraInfo
from cpc.diagnostics import probe_runtime
from cpc.performance_pipeline import PerformancePipeline, ThreadedPerformancePipeline
from cpc.recording import PerformanceRecorder
from cpc.rig import default_rig_path, derive_rig_from_image, save_rig
from cpc.runtime_adapter import LoopbackJsonServer
from cpc.session import (
    SessionConfig,
    build_frame_source_from_config,
    build_renderer_from_config,
    build_tracker_from_config,
)


class SessionWorker(QThread):
    """Run capture while preserving ordered performer-state delivery."""

    frame_ready = Signal(object, object, object)
    telemetry_updated = Signal(dict)
    state_changed = Signal(str)
    calibration_updated = Signal(object, str)
    error_occurred = Signal(str, str)
    session_finished = Signal()

    def __init__(self, config: SessionConfig, session_token: int = 0, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.session_token = session_token
        self._running = True
        self._recenter_requested = False
        self._calibration_frames = None
        self._calibration_target = 60

    def stop(self) -> None:
        self._running = False

    def calibrate_neutral(self) -> None:
        """Reset renderer neutral and measure a fresh local calibration profile."""
        self._recenter_requested = True

    def _handle_result(
        self,
        result,
        *,
        recorder,
        sink,
        runtime,
        writer_holder,
        camera_info,
        source_frame,
        session_start: float,
        fps_state: dict,
    ) -> None:
        performance = result.performance
        if performance.tracked:
            fps_state["tracked"] += 1
            self.state_changed.emit("tracking")
        else:
            self.state_changed.emit("tracking_lost")

        if recorder is not None:
            recorder.write(performance)
        if runtime is not None:
            runtime.publish(performance)
        if sink is not None:
            sink.send(result.frame)

        writer = writer_holder[0]
        if self.config.record_video_path is not None:
            if writer is None:
                h, w = result.frame.shape[:2]
                writer = cv2.VideoWriter(
                    str(self.config.record_video_path),
                    cv2.VideoWriter_fourcc(*"mp4v"),
                    30.0,
                    (w, h),
                )
                writer_holder[0] = writer
            writer.write(result.frame)

        if self._calibration_frames is not None and performance.tracked:
            self._calibration_frames.append(performance)
            if len(self._calibration_frames) >= self._calibration_target:
                character_id = (
                    str(self.config.character_path.resolve())
                    if self.config.character_path is not None
                    else None
                )
                profile = build_calibration_profile(
                    self._calibration_frames,
                    name="session",
                    character_id=character_id,
                )
                if self.config.calibration_profile_path is not None:
                    profile.save(self.config.calibration_profile_path)
                    status = f"saved:{self.config.calibration_profile_path}"
                else:
                    status = "session-only"
                self.calibration_updated.emit(profile.to_dict(), status)
                self._calibration_frames = None

        now = time.perf_counter()
        fps_state["processed"] += 1
        fps_state["window_frames"] += 1
        if now - fps_state["window_start"] >= 0.5:
            fps_state["fps"] = fps_state["window_frames"] / (now - fps_state["window_start"])
            fps_state["window_frames"] = 0
            fps_state["window_start"] = now

        telemetry = {
            "state": "tracking" if performance.tracked else "tracking_lost",
            "elapsed_s": now - session_start,
            "processed_frames": fps_state["processed"],
            "canonical_processed_frames": fps_state["processed"],
            "current_fps": fps_state["fps"],
            "capture_fps": fps_state["fps"],
            "tracking_rate": (
                fps_state["tracked"] / fps_state["processed"]
                if fps_state["processed"] > 0
                else 0.0
            ),
            "source_backend": camera_info.backend if camera_info else "unknown",
            "source_width": source_frame.shape[1],
            "source_height": source_frame.shape[0],
            "source_reported_fps": camera_info.fps if camera_info else 0.0,
            "tracker_name": performance.tracker,
            "tracker_latency_ms": result.tracking_ms,
            "render_latency_ms": result.render_ms,
            "total_latency_ms": result.metrics.processing_ms,
            "pipeline_mode": self.config.performance_pipeline_mode,
            "queue_depth": result.queue_depth,
            "dropped_preview_frames": 0,
            "coalesced_presentation_frames": result.coalesced_preview_frames,
            "landmark_count": len(performance.landmarks),
            "blendshape_count": len(performance.blendshapes),
            "recording_cpc": recorder is not None,
            "recording_video": writer_holder[0] is not None,
            "virtual_camera": sink is not None,
            "vcam_device": sink.device if sink else None,
            "vcam_backend": sink.backend if sink else None,
            "runtime_loopback": runtime.address if runtime is not None else None,
            "calibration_status": (
                "measuring"
                if self._calibration_frames is not None
                else "measured"
            ),
        }
        self.telemetry_updated.emit(telemetry)
        if not self.config.no_window:
            self.frame_ready.emit(result.frame, performance, result.metrics)

    def run(self) -> None:
        self.state_changed.emit("initializing")
        writer_holder: list[cv2.VideoWriter | None] = [None]
        camera_info: CameraInfo | None = None

        try:
            tracker = build_tracker_from_config(self.config)
            renderer = build_renderer_from_config(self.config)
            source = build_frame_source_from_config(self.config)
            if self.config.performance_pipeline_mode == "threaded":
                pipeline = ThreadedPerformancePipeline(
                    renderer,
                    tracker=tracker,
                    queue_size=self.config.pipeline_queue_size,
                )
            else:
                pipeline = PerformancePipeline(renderer, tracker=tracker)
        except (RuntimeError, ValueError, FileNotFoundError, OSError, TypeError, AttributeError) as exc:
            self.error_occurred.emit(
                f"Failed to initialize session components: {exc}",
                (
                    f"Component Initialization Error: {exc}\n"
                    f"Platform: {platform.platform()} (Python {sys.version.split()[0]})\n"
                    f"Config: {self.config}\n\n{traceback.format_exc()}"
                ),
            )
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
                    fps = camera_info.fps if camera_info and camera_info.fps > 0 else 30.0
                    sink = stack.enter_context(VirtualCameraSink(vcam_w, vcam_h, fps))

                runtime = None
                if self.config.runtime_loopback_port is not None:
                    runtime = LoopbackJsonServer(self.config.runtime_loopback_port)
                    runtime.start()
                    stack.callback(runtime.close)

                self.state_changed.emit("running")
                session_start = time.perf_counter()
                fps_state = {
                    "processed": 0,
                    "tracked": 0,
                    "window_start": session_start,
                    "window_frames": 0,
                    "fps": 0.0,
                }
                pending = 0
                submitted = 0
                last_source_frame = None

                while self._running:
                    if self._recenter_requested:
                        while pending:
                            result = pipeline.receive(timeout=5.0)
                            pending -= 1
                            assert last_source_frame is not None
                            self._handle_result(
                                result,
                                recorder=recorder,
                                sink=sink,
                                runtime=runtime,
                                writer_holder=writer_holder,
                                camera_info=camera_info,
                                source_frame=last_source_frame,
                                session_start=session_start,
                                fps_state=fps_state,
                            )
                        if hasattr(renderer, "recenter"):
                            renderer.recenter()
                        self._calibration_frames = []
                        self._recenter_requested = False
                        self.calibration_updated.emit({}, "measuring")

                    if self.config.frames > 0 and submitted >= self.config.frames:
                        break

                    try:
                        frame = source.read()
                    except RuntimeError as read_exc:
                        if "end of video stream" in str(read_exc).lower():
                            break
                        raise
                    if self.config.mirror:
                        frame = cv2.flip(frame, 1)
                    last_source_frame = frame

                    if isinstance(pipeline, ThreadedPerformancePipeline):
                        pipeline.submit(frame)
                        pending += 1
                        submitted += 1
                        if pending < 2 and (
                            self.config.frames == 0 or submitted < self.config.frames
                        ):
                            continue
                        result = pipeline.receive(timeout=5.0)
                        pending -= 1
                    else:
                        result = pipeline.process(frame)
                        submitted += 1

                    self._handle_result(
                        result,
                        recorder=recorder,
                        sink=sink,
                        runtime=runtime,
                        writer_holder=writer_holder,
                        camera_info=camera_info,
                        source_frame=frame,
                        session_start=session_start,
                        fps_state=fps_state,
                    )

                if isinstance(pipeline, ThreadedPerformancePipeline):
                    while pending:
                        result = pipeline.receive(timeout=5.0)
                        pending -= 1
                        assert last_source_frame is not None
                        self._handle_result(
                            result,
                            recorder=recorder,
                            sink=sink,
                            runtime=runtime,
                            writer_holder=writer_holder,
                            camera_info=camera_info,
                            source_frame=last_source_frame,
                            session_start=session_start,
                            fps_state=fps_state,
                        )

        except (RuntimeError, ValueError, OSError, cv2.error, KeyError, AttributeError) as exc:
            if self._running:
                self.error_occurred.emit(
                    f"Capture loop encountered an error: {exc}",
                    (
                        f"Runtime Capture Loop Error: {exc}\n"
                        f"Platform: {platform.platform()} (Python {sys.version.split()[0]})\n"
                        f"Config: {self.config}\n\n{traceback.format_exc()}"
                    ),
                )
                self.state_changed.emit("error")
        finally:
            self.state_changed.emit("stopping")
            if writer_holder[0] is not None:
                writer_holder[0].release()
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
            tech_details = (
                f"Diagnostics Error: {exc}\n"
                f"Platform: {platform.platform()} (Python {sys.version.split()[0]})\n"
                f"{traceback.format_exc()}"
            )
            self.error_occurred.emit(user_msg, tech_details)


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
            tech_details = (
                f"Rig Derivation Error: {exc}\n"
                f"Character: {self.character_path}\n"
                f"Model: {self.model_path}\n"
                f"{traceback.format_exc()}"
            )
            self.error_occurred.emit(user_msg, tech_details)
