import numpy as np
import pytest

from cpc.pipeline import Pipeline
from cpc.processors import PassthroughRenderer


def test_passthrough_pipeline_preserves_frame_values():
    frame = np.arange(27, dtype=np.uint8).reshape(3, 3, 3)
    pipeline = Pipeline([PassthroughRenderer()])

    output, metrics = pipeline.process(frame)

    assert np.array_equal(output, frame)
    assert metrics.frame_index == 0
    assert metrics.processing_ms >= 0
    pipeline.close()


def test_pipeline_lifecycle_is_idempotent():
    events = []

    class Processor:
        name = "test"

        def start(self):
            events.append("start")

        def process(self, frame):
            events.append("process")
            return frame

        def close(self):
            events.append("close")

    pipeline = Pipeline([Processor()])
    frame = np.zeros((2, 2, 3), dtype=np.uint8)

    pipeline.start()
    pipeline.start()
    pipeline.process(frame)
    pipeline.close()
    pipeline.close()

    assert events == ["start", "process", "close"]


def test_processors_run_in_declared_order_and_close_in_reverse():
    events = []

    class Processor:
        def __init__(self, name):
            self.name = name

        def start(self):
            events.append(f"start:{self.name}")

        def process(self, frame):
            events.append(f"process:{self.name}")
            return frame

        def close(self):
            events.append(f"close:{self.name}")

    pipeline = Pipeline([Processor("tracker"), Processor("renderer")])
    pipeline.process(np.zeros((2, 2, 3), dtype=np.uint8))
    pipeline.close()

    assert events == [
        "start:tracker",
        "start:renderer",
        "process:tracker",
        "process:renderer",
        "close:renderer",
        "close:tracker",
    ]


def test_pipeline_restart_begins_a_fresh_metrics_session():
    pipeline = Pipeline([PassthroughRenderer()])
    frame = np.zeros((2, 2, 3), dtype=np.uint8)

    _, first = pipeline.process(frame)
    pipeline.close()
    _, restarted = pipeline.process(frame)
    pipeline.close()

    assert first.frame_index == 0
    assert first.fps == 0.0
    assert restarted.frame_index == 0
    assert restarted.fps == 0.0


def test_pipeline_rolls_back_processors_when_start_fails():
    events = []

    class First:
        name = "first"

        def start(self):
            events.append("first:start")

        def process(self, frame):
            return frame

        def close(self):
            events.append("first:close")

    class Broken:
        name = "broken"

        def start(self):
            events.append("broken:start")
            raise RuntimeError("boom")

        def process(self, frame):
            return frame

        def close(self):
            events.append("broken:close")

    pipeline = Pipeline([First(), Broken()])

    with pytest.raises(RuntimeError, match="boom"):
        pipeline.start()

    assert events == ["first:start", "broken:start", "first:close"]
