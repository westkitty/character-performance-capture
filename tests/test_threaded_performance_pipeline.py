import time

import numpy as np
import pytest

from cpc.performance import PerformanceFrame
from cpc.performance_pipeline import ThreadedPerformancePipeline


class Tracker:
    name = "test"
    profile = "test"
    def start(self): self.started = True
    def track(self, frame, *, frame_index, timestamp_s):
        if frame_index == 2 and frame[0, 0, 0] == 99:
            raise ValueError("boom")
        time.sleep(0.002)
        return PerformanceFrame(frame_index, timestamp_s, True, self.name, self.profile)
    def close(self): self.started = False


class Renderer:
    name = "test"
    def start(self): self.started = True
    def render(self, frame, performance):
        time.sleep(0.001)
        return frame.copy()
    def close(self): self.started = False


def test_threaded_pipeline_preserves_order_and_bounds_queue():
    pipeline = ThreadedPerformancePipeline(Renderer(), Tracker(), queue_size=2)
    pipeline.start()
    try:
        for i in range(4):
            pipeline.submit(np.full((1, 1, 3), i, dtype=np.uint8), timestamp_s=i / 30)
            assert pipeline.queue_depth <= 2
        results = [pipeline.receive(timeout=1) for _ in range(4)]
        assert [r.performance.frame_index for r in results] == [0, 1, 2, 3]
    finally:
        pipeline.close()
    assert not pipeline.worker_alive


def test_threaded_pipeline_propagates_worker_error_and_closes():
    pipeline = ThreadedPerformancePipeline(Renderer(), Tracker(), queue_size=2)
    pipeline.start()
    pipeline.submit(np.zeros((1, 1, 3), dtype=np.uint8))
    assert pipeline.receive(timeout=1).performance.frame_index == 0
    pipeline.submit(np.zeros((1, 1, 3), dtype=np.uint8))
    assert pipeline.receive(timeout=1).performance.frame_index == 1
    pipeline.submit(np.full((1, 1, 3), 99, dtype=np.uint8))
    with pytest.raises(RuntimeError, match="worker failed"):
        pipeline.receive(timeout=1)
    pipeline.close()
    assert not pipeline.worker_alive


def test_threaded_pipeline_restarts_after_close():
    pipeline = ThreadedPerformancePipeline(Renderer(), Tracker(), queue_size=1)
    frame = np.zeros((1, 1, 3), dtype=np.uint8)
    assert pipeline.process(frame).performance.frame_index == 0
    pipeline.close()
    assert pipeline.process(frame).performance.frame_index == 0
    pipeline.close()
