from pathlib import Path

import cv2
import numpy as np
import pytest

from cpc.capture import VideoFileSource


def _write_clip(path: Path, frames: int = 8, size=(64, 48)) -> None:
    w, h = size
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 24.0, (w, h))
    for i in range(frames):
        frame = np.full((h, w, 3), i * 10 % 255, dtype=np.uint8)
        writer.write(frame)
    writer.release()


def test_video_source_reads_frames_and_reports_info(tmp_path: Path):
    clip = tmp_path / "clip.mp4"
    _write_clip(clip, frames=8)

    with VideoFileSource(clip) as source:
        info = source.info()
        assert info.width == 64 and info.height == 48
        assert info.fps > 0
        read = 0
        try:
            while True:
                frame = source.read()
                assert frame.shape == (48, 64, 3)
                read += 1
        except RuntimeError as exc:
            assert "end of video stream" in str(exc)
    assert read == 8


def test_video_source_loop_wraps_at_eof(tmp_path: Path):
    clip = tmp_path / "clip.mp4"
    _write_clip(clip, frames=4)
    source = VideoFileSource(clip, loop=True)
    source.open()
    frames = [source.read() for _ in range(10)]  # more than the clip length
    assert len(frames) == 10
    source.close()
    source.close()  # idempotent


def test_video_source_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        VideoFileSource(tmp_path / "absent.mp4").open()
