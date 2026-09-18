from pathlib import Path

import numpy as np

from cpc.performance import PerformanceFrame
from cpc.recording import PerformanceRecorder
from cpc.takes import TakeAnnotations, TakeMarker, TakeTimeline, replay_through_renderer


def _make_take(path: Path) -> None:
    with PerformanceRecorder(path, tracker="test", profile="generic") as rec:
        for i in range(5):
            rec.write(PerformanceFrame(i, i * 0.1, True, "test"))


def test_seek_step_loop_and_annotations_do_not_mutate_take(tmp_path: Path):
    path = tmp_path / "take.cpc"
    _make_take(path)
    original = path.read_bytes()
    timeline = TakeTimeline.open(path)
    assert timeline.seek_time(0.21).frame_index == 3
    timeline.set_loop(1, 3)
    timeline.position = 3
    assert timeline.step(1).frame_index == 1
    notes = TakeAnnotations(path)
    notes.add(TakeMarker(2, "good expression"))
    notes.save()
    assert path.read_bytes() == original
    assert TakeAnnotations.load(path).markers[0].note == "good expression"


def test_replay_drives_renderer_contract(tmp_path: Path):
    path = tmp_path / "take.cpc"
    _make_take(path)

    class Renderer:
        name = "test"
        def start(self): self.started = True
        def render(self, frame, performance): return frame + performance.frame_index
        def close(self): self.started = False

    output = replay_through_renderer(path, Renderer(), source_frame=np.zeros((2, 2, 3), dtype=np.uint8))
    assert len(output) == 5
    assert output[-1][0, 0, 0] == 4
