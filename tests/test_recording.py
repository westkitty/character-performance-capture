from pathlib import Path

import pytest

from cpc.performance import PerformanceFrame
from cpc.recording import PerformanceRecorder, PerformanceReplay, read_capture


def make_frame(index: int, timestamp_s: float) -> PerformanceFrame:
    return PerformanceFrame(
        frame_index=index,
        timestamp_s=timestamp_s,
        tracked=True,
        tracker="fake",
        profile="test-52",
        blendshapes={"jawOpen": index / 10.0},
    )


def test_capture_round_trip_and_replay(tmp_path: Path):
    path = tmp_path / "take-01.cpc"

    with PerformanceRecorder(path, tracker="fake", profile="test-52") as recorder:
        recorder.write(make_frame(0, 0.0))
        recorder.write(make_frame(1, 0.04))

    capture = read_capture(path)
    replayed = list(PerformanceReplay(path).frames())

    assert capture.complete is True
    assert capture.frame_count == 2
    assert capture.duration_s == pytest.approx(0.04)
    assert replayed == list(capture.frames)
    assert not Path(f"{path}.partial").exists()


def test_exception_preserves_recoverable_partial_capture(tmp_path: Path):
    path = tmp_path / "interrupted.cpc"

    with pytest.raises(RuntimeError, match="boom"):
        with PerformanceRecorder(path, tracker="fake", profile="test") as recorder:
            recorder.write(make_frame(0, 0.0))
            raise RuntimeError("boom")

    partial = Path(f"{path}.partial")
    assert not path.exists()
    assert partial.exists()

    capture = read_capture(partial)
    assert capture.complete is False
    assert capture.frame_count == 1


def test_recorder_refuses_to_overwrite_existing_capture(tmp_path: Path):
    path = tmp_path / "existing.cpc"
    path.write_text("do not replace", encoding="utf-8")

    recorder = PerformanceRecorder(path, tracker="fake", profile="test")
    with pytest.raises(FileExistsError):
        recorder.start()
