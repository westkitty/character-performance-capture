from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np
import pytest

from cpc.performance import PerformanceFrame
from cpc.performance_library import PerformanceLibrary
from cpc.recording import PerformanceRecorder
from cpc.semantic_qwen import Qwen3VLSemanticEmbedder, sample_video_window


def write_capture(path: Path, jaw_values: list[float]) -> Path:
    with PerformanceRecorder(path, tracker="fake", profile="test") as recorder:
        for index, jaw in enumerate(jaw_values):
            recorder.write(
                PerformanceFrame(
                    frame_index=index,
                    timestamp_s=float(index),
                    tracked=True,
                    tracker="fake",
                    profile="test",
                    tracking_confidence=0.95,
                    blendshapes={"jawOpen": jaw},
                    head_rotation_deg=(0.0, float(index), 0.0),
                )
            )
    return path


class FakeEmbedder:
    provider = "fake-local"
    model = "fake-model@2d"

    def __init__(self) -> None:
        self.calls: list[tuple[Path, float, float]] = []

    def embed_video_window(self, path: str | Path, start_s: float, end_s: float):
        source = Path(path)
        self.calls.append((source, start_s, end_s))
        return [1.0, start_s + end_s + 1.0]


def test_batch_media_embedding_is_explicit_and_idempotent(tmp_path: Path):
    capture = write_capture(tmp_path / "take.cpc", [0.1, 0.2, 0.3, 0.4])
    media = tmp_path / "take.mp4"
    media.write_bytes(b"local-media-placeholder")
    embedder = FakeEmbedder()

    with PerformanceLibrary(tmp_path / "library.sqlite3") as library:
        indexed = library.index_capture(
            capture,
            segment_duration_s=2.0,
            overlap_s=0.0,
            media_path=media,
        )
        first = library.embed_media_segments(embedder, capture_id=indexed.capture_id)
        second = library.embed_media_segments(embedder, capture_id=indexed.capture_id)
        forced = library.embed_media_segments(
            embedder,
            capture_id=indexed.capture_id,
            force=True,
        )

    assert first.embedded_segment_ids == indexed.segment_ids
    assert first.failures == ()
    assert second.embedded_segment_ids == ()
    assert second.skipped_segment_ids == indexed.segment_ids
    assert forced.embedded_segment_ids == indexed.segment_ids
    assert len(embedder.calls) == 4


def test_semantic_only_search_excludes_candidates_without_requested_embedding(tmp_path: Path):
    a = write_capture(tmp_path / "a.cpc", [0.1, 0.2])
    b = write_capture(tmp_path / "b.cpc", [0.7, 0.8])
    c = write_capture(tmp_path / "c.cpc", [0.4, 0.5])

    with PerformanceLibrary(tmp_path / "library.sqlite3") as library:
        ai = library.index_capture(a, segment_duration_s=10.0)
        bi = library.index_capture(b, segment_duration_s=10.0)
        ci = library.index_capture(c, segment_duration_s=10.0)
        library.put_embedding(ai.segment_ids[0], provider="p", model="m", vector=[1.0, 0.0])
        library.put_embedding(bi.segment_ids[0], provider="p", model="m", vector=[0.0, 1.0])
        results = library.search(
            query_embedding=[0.9, 0.1],
            provider="p",
            model="m",
            limit=10,
        )

    ids = [result.segment_id for result in results]
    assert ids[0] == ai.segment_ids[0]
    assert ci.segment_ids[0] not in ids


def test_embedding_namespace_rejects_dimension_drift(tmp_path: Path):
    capture = write_capture(tmp_path / "take.cpc", [0.1, 0.2, 0.3])
    with PerformanceLibrary(tmp_path / "library.sqlite3") as library:
        indexed = library.index_capture(capture, segment_duration_s=10.0)
        library.put_embedding(indexed.segment_ids[0], provider="p", model="m", vector=[1.0, 0.0])
        with pytest.raises(ValueError, match="dimensions must remain constant"):
            library.put_embedding(indexed.segment_ids[0], provider="p", model="m", vector=[1.0, 0.0, 0.0])


def test_build_retrieval_benchmark_can_prove_semantic_uplift(tmp_path: Path):
    query_capture = write_capture(tmp_path / "query.cpc", [0.2, 0.2, 0.2])
    distractor_capture = write_capture(tmp_path / "distractor.cpc", [0.2, 0.2, 0.2])
    target_capture = write_capture(tmp_path / "target.cpc", [0.2, 0.2, 0.2])

    with PerformanceLibrary(tmp_path / "library.sqlite3") as library:
        query = library.index_capture(
            query_capture,
            segment_duration_s=10.0,
            build_id="A",
            fixture_key="canonical-expression",
        )
        distractor = library.index_capture(
            distractor_capture,
            segment_duration_s=10.0,
            build_id="B",
            fixture_key="other-expression",
        )
        target = library.index_capture(
            target_capture,
            segment_duration_s=10.0,
            build_id="B",
            fixture_key="canonical-expression",
        )
        library.put_embedding(query.segment_ids[0], provider="p", model="m", vector=[1.0, 0.0])
        library.put_embedding(distractor.segment_ids[0], provider="p", model="m", vector=[0.0, 1.0])
        library.put_embedding(target.segment_ids[0], provider="p", model="m", vector=[1.0, 0.0])
        metrics = {
            item.mode: item
            for item in library.benchmark_build_retrieval(
                "A",
                "B",
                provider="p",
                model="m",
            )
        }

    assert metrics["kinematic"].query_count == 1
    assert metrics["kinematic"].hit_at_1 == 0.0
    assert metrics["semantic"].hit_at_1 == 1.0
    assert metrics["hybrid"].hit_at_1 == 1.0
    assert metrics["semantic"].mrr > metrics["kinematic"].mrr


def test_semantic_search_rejects_query_dimension_mismatch(tmp_path: Path):
    capture = write_capture(tmp_path / "take.cpc", [0.1, 0.2])
    with PerformanceLibrary(tmp_path / "library.sqlite3") as library:
        indexed = library.index_capture(capture, segment_duration_s=10.0)
        library.put_embedding(
            indexed.segment_ids[0],
            provider="p",
            model="m",
            vector=[1.0, 0.0],
        )
        with pytest.raises(ValueError, match="dimensions must match"):
            library.search(
                query_embedding=[1.0, 0.0, 0.0],
                provider="p",
                model="m",
            )


def test_build_retrieval_benchmark_rejects_ambiguous_fixture_mapping(tmp_path: Path):
    query_capture = write_capture(tmp_path / "query.cpc", [0.1, 0.2])
    target_one = write_capture(tmp_path / "target-one.cpc", [0.1, 0.2])
    target_two = write_capture(tmp_path / "target-two.cpc", [0.1, 0.3])

    with PerformanceLibrary(tmp_path / "library.sqlite3") as library:
        library.index_capture(
            query_capture,
            segment_duration_s=10.0,
            build_id="A",
            fixture_key="canonical",
        )
        library.index_capture(
            target_one,
            segment_duration_s=10.0,
            build_id="B",
            fixture_key="canonical",
        )
        library.index_capture(
            target_two,
            segment_duration_s=10.0,
            build_id="B",
            fixture_key="canonical",
        )
        with pytest.raises(ValueError, match="ambiguous"):
            library.benchmark_build_retrieval("A", "B", provider="p", model="m")


def test_video_window_sampler_uses_only_bounded_local_frames(tmp_path: Path, monkeypatch):
    media = tmp_path / "local.mp4"
    media.write_bytes(b"placeholder")

    class FakeCapture:
        def __init__(self) -> None:
            self.positions: list[float] = []
            self.released = False

        def isOpened(self):
            return True

        def set(self, prop, value):
            self.positions.append(value)
            return True

        def read(self):
            frame = np.full((100, 200, 3), 127, dtype=np.uint8)
            return True, frame

        def release(self):
            self.released = True

    class FakeImage:
        def __init__(self, array):
            self.size = (array.shape[1], array.shape[0])

    fake_pil = types.ModuleType("PIL")
    fake_pil.Image = types.SimpleNamespace(fromarray=lambda array: FakeImage(array))
    monkeypatch.setitem(sys.modules, "PIL", fake_pil)

    fake = FakeCapture()
    monkeypatch.setattr("cpc.semantic_qwen.cv2.VideoCapture", lambda path: fake)

    frames = sample_video_window(
        media,
        2.0,
        3.0,
        sample_fps=4.0,
        max_frames=8,
        max_side=50,
    )

    assert len(frames) == 4
    assert all(frame.size == (50, 25) for frame in frames)
    assert fake.released is True
    assert fake.positions[0] == pytest.approx(2000.0)
    assert fake.positions[-1] < 3000.0


def test_qwen_adapter_requires_local_model_directory_and_namespaces_dimensions(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        Qwen3VLSemanticEmbedder(tmp_path / "missing")

    model_dir = tmp_path / "Qwen3-VL-Embedding-2B"
    model_dir.mkdir()
    embedder = Qwen3VLSemanticEmbedder(
        model_dir,
        model_id="Qwen/Qwen3-VL-Embedding-2B",
        dimensions=512,
    )

    assert embedder.provider == "qwen3-vl-local"
    assert embedder.model == "Qwen/Qwen3-VL-Embedding-2B@512d"


def test_mlx_adapter_packages_bounded_frames_as_multi_image_input(tmp_path: Path, monkeypatch):
    from cpc.semantic_qwen_mlx import Qwen3VLMLXEmbedder

    model_dir = tmp_path / "Qwen3-VL-Embedding-2B-4bit"
    model_dir.mkdir()
    media = tmp_path / "take.mp4"
    media.write_bytes(b"placeholder")
    frames = [object(), object(), object(), object()]
    seen = {}

    monkeypatch.setattr(
        "cpc.semantic_qwen_mlx.sample_video_window",
        lambda *args, **kwargs: frames,
    )

    embedder = Qwen3VLMLXEmbedder(model_dir, dimensions=512)

    def fake_embed(*, images=(), text="", instruction=""):
        seen["images"] = list(images)
        seen["text"] = text
        seen["instruction"] = instruction
        return [1.0, 0.0]

    monkeypatch.setattr(embedder, "_embed_content", fake_embed)
    result = embedder.embed_video_window(media, 1.0, 2.0)

    assert result == [1.0, 0.0]
    assert seen["images"] == frames
    assert "Chronological frames" in seen["text"]
    assert embedder.provider == "qwen3-vl-mlx"
    assert embedder.model == "mlx-community/Qwen3-VL-Embedding-2B-4bit@512d"


def test_qwen_cli_exposes_explicit_mlx_runtime(tmp_path: Path):
    from cpc.blackbox_cli import build_parser

    model_dir = tmp_path / "model"
    model_dir.mkdir()
    args = build_parser().parse_args(
        [
            "qwen-search",
            "smile",
            "--model-path",
            str(model_dir),
            "--runtime",
            "mlx",
        ]
    )

    assert args.runtime == "mlx"
    assert args.sample_fps is None
    assert args.max_frames is None
    assert args.max_side is None
