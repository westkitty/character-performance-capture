import numpy as np

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
