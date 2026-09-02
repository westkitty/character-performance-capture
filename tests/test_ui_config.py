from __future__ import annotations

from cpc.app import build_parser
from cpc.capture import CameraSource, VideoFileSource
from cpc.processors import PassthroughRenderer
from cpc.session import (
    SessionConfig,
    build_frame_source_from_config,
    build_renderer_from_config,
    build_tracker_from_config,
)
from cpc.tracking import NullTracker


def test_session_config_defaults():
    cfg = SessionConfig()
    assert cfg.source_type == "camera"
    assert cfg.camera_index == 0
    assert cfg.video_path is None
    assert cfg.tracker_type == "null"
    assert cfg.renderer_type == "passthrough"
    assert cfg.expression_gain == 1.0
    assert cfg.head_gain == 1.0
    assert cfg.virtual_camera is False
    assert cfg.vcam_size == (1280, 720)
    assert cfg.validate() == []


def test_session_config_from_args_and_to_cli_args(tmp_path):
    parser = build_parser()
    video_file = tmp_path / "test.mp4"
    video_file.touch()

    args = parser.parse_args([
        "--video", str(video_file),
        "--loop",
        "--mirror",
        "--tracker", "null",
        "--render", "passthrough",
        "--virtual-camera",
        "--vcam-size", "1920x1080",
        "--frames", "150",
    ])

    cfg = SessionConfig.from_args(args)
    assert cfg.source_type == "video"
    assert cfg.video_path == video_file
    assert cfg.loop_video is True
    assert cfg.mirror is True
    assert cfg.virtual_camera is True
    assert cfg.vcam_size == (1920, 1080)
    assert cfg.frames == 150

    cli_tokens = cfg.to_cli_args()
    assert "--video" in cli_tokens
    assert str(video_file) in cli_tokens
    assert "--loop" in cli_tokens
    assert "--mirror" in cli_tokens
    assert "--virtual-camera" in cli_tokens
    assert "--vcam-size" in cli_tokens
    assert "1920x1080" in cli_tokens
    assert "--frames" in cli_tokens
    assert "150" in cli_tokens

    cmd_str = cfg.to_command_string()
    assert cmd_str.startswith("cpc ")
    assert "--video" in cmd_str


def test_session_config_validation(tmp_path):
    # 1. Non-existent video file
    cfg = SessionConfig(source_type="video", video_path=tmp_path / "non_existent.mp4")
    errs = cfg.validate()
    assert any("does not exist" in e for e in errs)

    # 2. Empty video path
    cfg_empty_vid = SessionConfig(source_type="video", video_path=None)
    assert any("no video file" in e for e in cfg_empty_vid.validate())

    # 3. Negative camera index
    cfg_cam = SessionConfig(source_type="camera", camera_index=-1)
    assert any("Camera index must be non-negative" in e for e in cfg_cam.validate())

    # 4. MediaPipe without model
    cfg_mp = SessionConfig(tracker_type="mediapipe", model_path=None)
    assert any("MediaPipe tracker requires" in e for e in cfg_mp.validate())

    # 5. MediaPipe with non-existent model
    cfg_mp_bad = SessionConfig(tracker_type="mediapipe", model_path=tmp_path / "bad.task")
    assert any("Model file does not exist" in e for e in cfg_mp_bad.validate())

    # 6. Rig renderer without character
    cfg_rig = SessionConfig(renderer_type="rig", character_path=None)
    assert any("Rig-Warp renderer requires a character" in e for e in cfg_rig.validate())

    # 7. Rig renderer with missing sidecar and missing model
    char_file = tmp_path / "char.png"
    char_file.touch()
    cfg_rig_nomodel = SessionConfig(renderer_type="rig", character_path=char_file, rig_path=None, model_path=None)
    assert any("No rig sidecar found" in e for e in cfg_rig_nomodel.validate())

    # 8. Performance capture existing destination
    rec_file = tmp_path / "take.cpc"
    rec_file.touch()
    cfg_rec = SessionConfig(record_performance_path=rec_file)
    assert any("already exists" in e for e in cfg_rec.validate())

    # 9. Invalid dimension / fps
    cfg_dim = SessionConfig(requested_width=0, requested_height=-10, requested_fps=-5.0)
    errs_dim = cfg_dim.validate()
    assert any("Requested width" in e for e in errs_dim)
    assert any("Requested height" in e for e in errs_dim)
    assert any("Requested FPS" in e for e in errs_dim)


def test_builders_from_config(tmp_path):
    # Camera Source
    cfg_cam = SessionConfig(source_type="camera", camera_index=0)
    src_cam = build_frame_source_from_config(cfg_cam)
    assert isinstance(src_cam, CameraSource)

    # Video Source
    vid_file = tmp_path / "clip.mp4"
    vid_file.touch()
    cfg_vid = SessionConfig(source_type="video", video_path=vid_file, loop_video=True)
    src_vid = build_frame_source_from_config(cfg_vid)
    assert isinstance(src_vid, VideoFileSource)
    assert src_vid.loop is True

    # Tracker Builder
    cfg_trk = SessionConfig(tracker_type="null")
    trk = build_tracker_from_config(cfg_trk)
    assert isinstance(trk, NullTracker)

    # Renderer Builder
    cfg_rnd = SessionConfig(renderer_type="passthrough")
    rnd = build_renderer_from_config(cfg_rnd)
    assert isinstance(rnd, PassthroughRenderer)
