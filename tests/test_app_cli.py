import numpy as np
import pytest

from cpc.app import build_frame_source, build_renderer, build_tracker
from cpc.capture import CameraSource, VideoFileSource
from cpc.processors import PassthroughRenderer


def _args(**overrides):
    from cpc.app import build_parser

    parser = build_parser()
    base = parser.parse_args([])
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_parser_exposes_core_workflow_flags():
    from cpc.app import build_parser

    parsed = build_parser().parse_args(
        ["--video", "a.mp4", "--render", "rig", "--character", "c.png", "--virtual-camera"]
    )
    assert str(parsed.video) == "a.mp4"
    assert parsed.render == "rig"
    assert parsed.virtual_camera is True


def test_build_frame_source_picks_video_when_given(tmp_path):
    src = build_frame_source(_args(video=tmp_path / "x.mp4"))
    assert isinstance(src, VideoFileSource)
    assert isinstance(build_frame_source(_args(video=None)), CameraSource)


def test_build_renderer_requires_character_for_rig():
    with pytest.raises(ValueError, match="--character"):
        build_renderer(_args(render="rig", character=None))


def test_build_renderer_passthrough_default():
    assert isinstance(build_renderer(_args()), PassthroughRenderer)


def test_build_tracker_mediapipe_requires_model():
    with pytest.raises(ValueError, match="--model is required"):
        build_tracker("mediapipe", None)


def test_build_renderer_rig_with_sidecar(tmp_path):
    import cv2

    from cpc.rig import CharacterRig, save_rig

    img = np.zeros((80, 64, 3), dtype=np.uint8)
    char = tmp_path / "c.png"
    cv2.imwrite(str(char), img)
    pts = np.column_stack(
        [np.linspace(5, 59, 20), np.linspace(5, 75, 20)]
    ).astype(np.float32)
    save_rig(CharacterRig(width=64, height=80, points=pts), tmp_path / "c.png.rig.json")

    renderer = build_renderer(_args(render="rig", character=char))
    assert renderer.name == "rig-warp"
