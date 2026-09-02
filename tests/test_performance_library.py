from pathlib import Path

from cpc.performance import PerformanceFrame
from cpc.performance_library import Judgment, PerformanceLibrary
from cpc.recording import PerformanceRecorder


def write_capture(path: Path, jaw_values: list[float], *, subject: str = "test") -> Path:
    with PerformanceRecorder(
        path,
        tracker="fake",
        profile="test-52",
        metadata={"subject": subject},
    ) as recorder:
        for index, jaw in enumerate(jaw_values):
            recorder.write(
                PerformanceFrame(
                    frame_index=index,
                    timestamp_s=float(index),
                    tracked=True,
                    tracker="fake",
                    profile="test-52",
                    tracking_confidence=0.95,
                    blendshapes={"jawOpen": jaw, "eyeBlinkLeft": 0.1},
                    head_rotation_deg=(0.0, float(index) * 2.0, 0.0),
                )
            )
    return path


def test_index_capture_creates_searchable_segments(tmp_path: Path):
    capture = write_capture(tmp_path / "take.cpc", [0.0, 0.2, 0.4, 0.6])
    db = tmp_path / "library.sqlite3"

    with PerformanceLibrary(db) as library:
        indexed = library.index_capture(
            capture,
            segment_duration_s=2.0,
            overlap_s=0.0,
            build_id="build-a",
            fixture_key="smile-left",
            title="calm smile left turn",
            tags=["approved", "smile"],
        )
        assert len(indexed.segment_ids) == 2
        results = library.search("smile", tag="approved")

    assert results
    assert results[0].fixture_key == "smile-left"
    assert results[0].text_score is not None and results[0].text_score > 0


def test_reference_search_prefers_kinematically_similar_segment(tmp_path: Path):
    capture_a = write_capture(tmp_path / "a.cpc", [0.1, 0.2, 0.3, 0.4])
    capture_b = write_capture(tmp_path / "b.cpc", [0.1, 0.2, 0.31, 0.41])
    capture_c = write_capture(tmp_path / "c.cpc", [0.9, 0.9, 0.0, 0.0])

    with PerformanceLibrary(tmp_path / "library.sqlite3") as library:
        a = library.index_capture(capture_a, segment_duration_s=10.0)
        b = library.index_capture(capture_b, segment_duration_s=10.0)
        c = library.index_capture(capture_c, segment_duration_s=10.0)
        results = library.search(reference_segment_id=a.segment_ids[0], limit=3)

    assert results[0].segment_id == a.segment_ids[0]
    positions = {result.segment_id: index for index, result in enumerate(results)}
    assert positions[b.segment_ids[0]] < positions[c.segment_ids[0]]


def test_semantic_embedding_can_be_combined_without_core_model_dependency(tmp_path: Path):
    capture_a = write_capture(tmp_path / "a.cpc", [0.1, 0.2])
    capture_b = write_capture(tmp_path / "b.cpc", [0.8, 0.9])

    with PerformanceLibrary(tmp_path / "library.sqlite3") as library:
        a = library.index_capture(capture_a, segment_duration_s=10.0)
        b = library.index_capture(capture_b, segment_duration_s=10.0)
        library.put_embedding(a.segment_ids[0], provider="local-qwen", model="demo", vector=[1.0, 0.0])
        library.put_embedding(b.segment_ids[0], provider="local-qwen", model="demo", vector=[0.0, 1.0])
        results = library.search(
            query_embedding=[0.95, 0.05],
            provider="local-qwen",
            model="demo",
            limit=2,
        )

    assert results[0].segment_id == a.segment_ids[0]
    assert results[0].semantic_score is not None


def test_promote_bug_produces_traceable_evidence_packet(tmp_path: Path):
    capture = write_capture(tmp_path / "take.cpc", [0.0, 0.5, 0.0])

    with PerformanceLibrary(tmp_path / "library.sqlite3") as library:
        indexed = library.index_capture(
            capture,
            segment_duration_s=10.0,
            build_id="build-17",
            calibration_id="cal-3",
            rig_id="rig-face-v2",
            fixture_key="jaw-turn",
        )
        packet = library.promote_bug(
            indexed.segment_ids[0],
            "JAW-004",
            "jaw wobbles during left turn",
            expected_behavior="jaw remains stable while yaw changes",
        )
        failure = library.search(judgment=Judgment.FAILURE)

    assert packet["bug_id"] == "JAW-004"
    assert packet["capture"]["build_id"] == "build-17"
    assert packet["capture"]["fixture_key"] == "jaw-turn"
    assert failure[0].segment_id == indexed.segment_ids[0]


def test_review_queue_surfaces_known_failure_similarity(tmp_path: Path):
    failure_capture = write_capture(tmp_path / "failure.cpc", [0.1, 0.8, 0.1, 0.8])
    similar_capture = write_capture(tmp_path / "similar.cpc", [0.1, 0.79, 0.1, 0.81])
    ordinary_capture = write_capture(tmp_path / "ordinary.cpc", [0.1, 0.1, 0.1, 0.1])

    with PerformanceLibrary(tmp_path / "library.sqlite3") as library:
        failure = library.index_capture(failure_capture, segment_duration_s=10.0)
        similar = library.index_capture(similar_capture, segment_duration_s=10.0)
        library.index_capture(ordinary_capture, segment_duration_s=10.0)
        library.set_judgment(failure.segment_ids[0], Judgment.FAILURE, "known wobble")
        queue = library.review_queue(limit=10, neighbors=1)

    similar_item = next(item for item in queue if item.segment_id == similar.segment_ids[0])
    assert similar_item.failure_similarity >= 0.85
    assert "known-failure similarity" in similar_item.reasons


def test_build_diff_ranks_changed_canonical_fixture(tmp_path: Path):
    build_a_capture = write_capture(tmp_path / "a.cpc", [0.1, 0.2, 0.3, 0.4])
    build_b_capture = write_capture(tmp_path / "b.cpc", [0.9, 0.1, 0.9, 0.1])

    with PerformanceLibrary(tmp_path / "library.sqlite3") as library:
        library.index_capture(
            build_a_capture,
            segment_duration_s=10.0,
            build_id="A",
            fixture_key="canonical-smile",
        )
        library.index_capture(
            build_b_capture,
            segment_duration_s=10.0,
            build_id="B",
            fixture_key="canonical-smile",
        )
        deltas = library.compare_builds("A", "B")

    assert len(deltas) == 1
    assert deltas[0].fixture_key == "canonical-smile"
    assert deltas[0].drift > 0.0
