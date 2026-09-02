import numpy as np

from cpc.performance import PerformanceFrame
from cpc.performance_pipeline import PerformancePipeline
from cpc.processors import PassthroughRenderer


def test_performance_pipeline_routes_tracker_state_into_renderer():
    events = []

    class Tracker:
        name = "fake"
        profile = "test"

        def start(self):
            events.append("tracker:start")

        def track(self, frame, *, frame_index, timestamp_s):
            events.append("tracker:track")
            return PerformanceFrame(
                frame_index=frame_index,
                timestamp_s=timestamp_s,
                tracked=True,
                tracker=self.name,
                profile=self.profile,
                blendshapes={"jawOpen": 0.5},
            )

        def close(self):
            events.append("tracker:close")

    class Renderer:
        name = "fake-renderer"

        def start(self):
            events.append("renderer:start")

        def render(self, frame, performance):
            events.append(f"renderer:{performance.blendshapes['jawOpen']}")
            return frame + 1

        def close(self):
            events.append("renderer:close")

    source = np.zeros((2, 2, 3), dtype=np.uint8)
    pipeline = PerformancePipeline(Renderer(), tracker=Tracker())

    result = pipeline.process(source, timestamp_s=1.25)
    pipeline.close()

    assert np.array_equal(result.frame, np.ones((2, 2, 3), dtype=np.uint8))
    assert result.performance.frame_index == 0
    assert result.performance.timestamp_s == 1.25
    assert events == [
        "tracker:start",
        "renderer:start",
        "tracker:track",
        "renderer:0.5",
        "renderer:close",
        "tracker:close",
    ]


def test_performance_pipeline_restart_resets_frame_index_and_fps():
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    pipeline = PerformancePipeline(PassthroughRenderer())

    first = pipeline.process(frame)
    pipeline.close()
    restarted = pipeline.process(frame)
    pipeline.close()

    assert first.metrics.frame_index == 0
    assert first.metrics.fps == 0.0
    assert first.performance.frame_index == 0
    assert restarted.metrics.frame_index == 0
    assert restarted.metrics.fps == 0.0
    assert restarted.performance.frame_index == 0
