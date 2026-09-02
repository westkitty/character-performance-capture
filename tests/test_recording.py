import json
from pathlib import Path

import pytest

from cpc.performance import PerformanceFrame
from cpc.recording import (
    CaptureFormatError,
    PerformanceRecorder,
    PerformanceReplay,
    read_capture,
)


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

    with (
        pytest.raises(RuntimeError, match="boom"),
        PerformanceRecorder(path, tracker="fake", profile="test") as recorder,
    ):
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


def test_recorder_refuses_destination_created_during_recording(tmp_path: Path):
    path = tmp_path / "race.cpc"
    recorder = PerformanceRecorder(path, tracker="fake", profile="test")
    recorder.start()
    recorder.write(make_frame(0, 0.0))

    path.write_text("independent file", encoding="utf-8")

    with pytest.raises(FileExistsError, match="appeared before commit"):
        recorder.close(commit=True)

    assert path.read_text(encoding="utf-8") == "independent file"
    partial = Path(f"{path}.partial")
    assert partial.exists()
    assert read_capture(partial).complete is True


def test_failed_write_aborts_without_later_committing(tmp_path: Path):
    path = tmp_path / "invalid-sequence.cpc"
    recorder = PerformanceRecorder(path, tracker="fake", profile="test")
    recorder.write(make_frame(0, 0.0))

    with pytest.raises(ValueError, match="strictly increasing"):
        recorder.write(make_frame(0, 0.01))

    recorder.close(commit=True)
    assert not path.exists()

    partial = Path(f"{path}.partial")
    assert partial.exists()
    capture = read_capture(partial)
    assert capture.complete is False
    assert capture.frame_count == 1


def test_replay_rejects_record_after_end(tmp_path: Path):
    path = tmp_path / "trailing.cpc"
    with PerformanceRecorder(path, tracker="fake", profile="test") as recorder:
        recorder.write(make_frame(0, 0.0))

    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "record_type": "frame",
                    "frame": make_frame(1, 0.04).to_dict(),
                }
            )
        )
        handle.write("\n")

    with pytest.raises(CaptureFormatError, match="after end"):
        list(PerformanceReplay(path).frames())

    with pytest.raises(CaptureFormatError, match="after end"):
        read_capture(path)


def test_footer_duration_must_match_frame_timestamps(tmp_path: Path):
    path = tmp_path / "bad-duration.cpc"
    with PerformanceRecorder(path, tracker="fake", profile="test") as recorder:
        recorder.write(make_frame(0, 0.0))
        recorder.write(make_frame(1, 0.04))

    lines = path.read_text(encoding="utf-8").splitlines()
    footer = json.loads(lines[-1])
    footer["duration_s"] = -1.0
    lines[-1] = json.dumps(footer)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(CaptureFormatError, match="finite non-negative"):
        read_capture(path)

    with pytest.raises(CaptureFormatError, match="finite non-negative"):
        list(PerformanceReplay(path).frames())
