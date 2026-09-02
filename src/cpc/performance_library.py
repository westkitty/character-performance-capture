from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Iterable, Protocol, Sequence

from .performance import PerformanceFrame
from .recording import CaptureData, read_capture

SCHEMA_VERSION = 1
DEFAULT_LIBRARY_PATH = Path.home() / ".cpc" / "performance_library.sqlite3"
_TOKEN_RE = re.compile(r"[a-z0-9_:-]+")


class Judgment(StrEnum):
    UNREVIEWED = "unreviewed"
    GOLD = "gold"
    FAILURE = "failure"
    INTERESTING = "interesting"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class IndexedCapture:
    capture_id: int
    source_path: str
    source_sha256: str
    segment_ids: tuple[int, ...]


@dataclass(frozen=True)
class SearchResult:
    segment_id: int
    capture_id: int
    source_path: str
    start_s: float
    end_s: float
    judgment: str
    score: float
    kinematic_score: float | None
    semantic_score: float | None
    text_score: float | None
    notes: str
    tags: tuple[str, ...]
    build_id: str | None
    fixture_key: str | None


@dataclass(frozen=True)
class ReviewItem:
    segment_id: int
    source_path: str
    score: float
    novelty: float
    low_tracking: float
    failure_similarity: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class BuildDelta:
    fixture_key: str
    segment_index: int
    build_a_segment_id: int
    build_b_segment_id: int
    drift: float


@dataclass(frozen=True)
class EmbeddingFailure:
    segment_id: int
    error: str


@dataclass(frozen=True)
class EmbeddingBatchResult:
    provider: str
    model: str
    embedded_segment_ids: tuple[int, ...]
    skipped_segment_ids: tuple[int, ...]
    failures: tuple[EmbeddingFailure, ...]


@dataclass(frozen=True)
class RetrievalMetrics:
    mode: str
    query_count: int
    evaluated: int
    skipped: int
    hit_at_1: float
    hit_at_3: float
    hit_at_5: float
    mrr: float


class SemanticEmbedder(Protocol):
    provider: str
    model: str

    def embed_video_window(
        self,
        path: str | Path,
        start_s: float,
        end_s: float,
    ) -> Sequence[float]: ...


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_tags(tags: Iterable[str] | None) -> tuple[str, ...]:
    normalized = {tag.strip().lower() for tag in tags or () if tag.strip()}
    return tuple(sorted(normalized))


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _text_similarity(query: str, document: str) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    document_tokens = _tokens(document)
    if not document_tokens:
        return 0.0
    matched = len(query_tokens & document_tokens)
    return matched / math.sqrt(len(query_tokens) * len(document_tokens))


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _motion(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    return _mean([abs(right - left) for left, right in zip(values, values[1:])])


def _sparse_cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    keys = set(left) | set(right)
    dot = sum(left.get(key, 0.0) * right.get(key, 0.0) for key in keys)
    left_norm = math.sqrt(sum(left.get(key, 0.0) ** 2 for key in keys))
    right_norm = math.sqrt(sum(right.get(key, 0.0) ** 2 for key in keys))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot / (left_norm * right_norm)))


def _dense_cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot / (left_norm * right_norm)))


def _retrieval_metrics(
    mode: str,
    ranks: Sequence[int | None],
    *,
    query_count: int,
    skipped: int,
) -> RetrievalMetrics:
    evaluated = len(ranks)
    if evaluated == 0:
        return RetrievalMetrics(mode, query_count, 0, skipped, 0.0, 0.0, 0.0, 0.0)
    hit_at_1 = _mean([1.0 if rank is not None and rank <= 1 else 0.0 for rank in ranks])
    hit_at_3 = _mean([1.0 if rank is not None and rank <= 3 else 0.0 for rank in ranks])
    hit_at_5 = _mean([1.0 if rank is not None and rank <= 5 else 0.0 for rank in ranks])
    mrr = _mean([1.0 / rank if rank is not None else 0.0 for rank in ranks])
    return RetrievalMetrics(
        mode=mode,
        query_count=query_count,
        evaluated=evaluated,
        skipped=skipped,
        hit_at_1=hit_at_1,
        hit_at_3=hit_at_3,
        hit_at_5=hit_at_5,
        mrr=mrr,
    )


def fingerprint_frames(frames: Sequence[PerformanceFrame]) -> dict[str, float]:
    """Build a renderer-independent sparse motion fingerprint for a frame sequence."""
    if not frames:
        raise ValueError("cannot fingerprint an empty frame sequence")

    features: dict[str, float] = {}
    features["tracking:ratio"] = _mean([1.0 if frame.tracked else 0.0 for frame in frames])
    confidences = [
        frame.tracking_confidence
        for frame in frames
        if frame.tracking_confidence is not None
    ]
    if confidences:
        features["tracking:confidence_mean"] = _mean(confidences)
        features["tracking:confidence_std"] = _std(confidences)

    blendshape_names = sorted({name for frame in frames for name in frame.blendshapes})
    for name in blendshape_names:
        values = [frame.blendshapes.get(name, 0.0) for frame in frames]
        features[f"blend:{name}:mean"] = _mean(values)
        features[f"blend:{name}:std"] = _std(values)
        features[f"blend:{name}:motion"] = _motion(values)

    axis_names = ("pitch", "yaw", "roll")
    for axis, axis_name in enumerate(axis_names):
        values = [
            frame.head_rotation_deg[axis] / 180.0
            for frame in frames
            if frame.head_rotation_deg is not None
        ]
        if values:
            features[f"head:{axis_name}:mean"] = _mean(values)
            features[f"head:{axis_name}:std"] = _std(values)
            features[f"head:{axis_name}:motion"] = _motion(values)

    for side in ("left", "right"):
        for axis, axis_name in enumerate(("x", "y")):
            values = []
            for frame in frames:
                gaze = frame.gaze_left if side == "left" else frame.gaze_right
                if gaze is not None:
                    values.append(gaze[axis])
            if values:
                features[f"gaze:{side}:{axis_name}:mean"] = _mean(values)
                features[f"gaze:{side}:{axis_name}:std"] = _std(values)
                features[f"gaze:{side}:{axis_name}:motion"] = _motion(values)

    landmark_counts = [len(frame.landmarks) for frame in frames if frame.landmarks]
    if landmark_counts:
        features["landmarks:count_mean"] = min(1.0, _mean(landmark_counts) / 500.0)
        x_centroids = [_mean([point.x for point in frame.landmarks]) for frame in frames if frame.landmarks]
        y_centroids = [_mean([point.y for point in frame.landmarks]) for frame in frames if frame.landmarks]
        features["landmarks:centroid_x_mean"] = _mean(x_centroids)
        features["landmarks:centroid_y_mean"] = _mean(y_centroids)
        features["landmarks:centroid_motion"] = _motion(x_centroids) + _motion(y_centroids)

    return features


def _segment_frames(
    capture: CaptureData,
    segment_duration_s: float,
    overlap_s: float,
) -> list[tuple[int, tuple[PerformanceFrame, ...]]]:
    frames = capture.frames
    if not frames:
        return []
    if segment_duration_s <= 0:
        return [(0, frames)]
    if overlap_s < 0 or overlap_s >= segment_duration_s:
        raise ValueError("overlap_s must be non-negative and less than segment_duration_s")

    first = frames[0].timestamp_s
    last = frames[-1].timestamp_s
    step = segment_duration_s - overlap_s
    segments: list[tuple[int, tuple[PerformanceFrame, ...]]] = []
    segment_index = 0
    start = first
    while start <= last + 1e-9:
        end = start + segment_duration_s
        segment = tuple(frame for frame in frames if start <= frame.timestamp_s < end)
        if segment:
            segments.append((segment_index, segment))
            segment_index += 1
        start += step
    return segments


class PerformanceLibrary:
    """Local SQLite index for reusable performance evidence and regression memory."""

    def __init__(self, path: str | Path = DEFAULT_LIBRARY_PATH) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> "PerformanceLibrary":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _create_schema(self) -> None:
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS library_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS captures (
                id INTEGER PRIMARY KEY,
                capture_key TEXT NOT NULL UNIQUE,
                source_path TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                tracker TEXT NOT NULL,
                profile TEXT NOT NULL,
                started_at_utc TEXT NOT NULL,
                complete INTEGER NOT NULL,
                frame_count INTEGER NOT NULL,
                duration_s REAL NOT NULL,
                build_id TEXT,
                calibration_id TEXT,
                rig_id TEXT,
                fixture_key TEXT,
                media_path TEXT,
                title TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL,
                indexed_at_utc TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS captures_build_fixture
                ON captures(build_id, fixture_key);
            CREATE TABLE IF NOT EXISTS segments (
                id INTEGER PRIMARY KEY,
                capture_id INTEGER NOT NULL REFERENCES captures(id) ON DELETE CASCADE,
                segment_index INTEGER NOT NULL,
                start_s REAL NOT NULL,
                end_s REAL NOT NULL,
                start_frame INTEGER NOT NULL,
                end_frame INTEGER NOT NULL,
                fingerprint_json TEXT NOT NULL,
                judgment TEXT NOT NULL DEFAULT 'unreviewed',
                notes TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                created_at_utc TEXT NOT NULL,
                UNIQUE(capture_id, segment_index)
            );
            CREATE INDEX IF NOT EXISTS segments_judgment ON segments(judgment);
            CREATE TABLE IF NOT EXISTS embeddings (
                segment_id INTEGER NOT NULL REFERENCES segments(id) ON DELETE CASCADE,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                created_at_utc TEXT NOT NULL,
                PRIMARY KEY(segment_id, provider, model)
            );
            CREATE TABLE IF NOT EXISTS judgment_history (
                id INTEGER PRIMARY KEY,
                segment_id INTEGER NOT NULL REFERENCES segments(id) ON DELETE CASCADE,
                judgment TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at_utc TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bugs (
                id INTEGER PRIMARY KEY,
                bug_id TEXT NOT NULL UNIQUE,
                segment_id INTEGER NOT NULL REFERENCES segments(id) ON DELETE RESTRICT,
                description TEXT NOT NULL,
                expected_behavior TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                created_at_utc TEXT NOT NULL
            );
            """
        )
        self._db.execute(
            "INSERT OR REPLACE INTO library_meta(key, value) VALUES('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self._db.commit()

    def index_capture(
        self,
        path: str | Path,
        *,
        segment_duration_s: float = 2.0,
        overlap_s: float = 0.5,
        build_id: str | None = None,
        calibration_id: str | None = None,
        rig_id: str | None = None,
        fixture_key: str | None = None,
        media_path: str | Path | None = None,
        title: str = "",
        tags: Iterable[str] | None = None,
        notes: str = "",
        metadata: dict[str, object] | None = None,
    ) -> IndexedCapture:
        source = Path(path).expanduser().resolve()
        capture = read_capture(source)
        digest = _sha256(source)
        capture_key = "|".join((digest, build_id or "", fixture_key or ""))
        tags_tuple = _canonical_tags(tags)
        library_metadata = dict(metadata or {})
        library_metadata["capture_header_metadata"] = capture.header.metadata
        media = str(Path(media_path).expanduser().resolve()) if media_path else None

        with self._db:
            existing = self._db.execute(
                "SELECT id FROM captures WHERE capture_key = ?", (capture_key,)
            ).fetchone()
            if existing is not None:
                capture_id = int(existing["id"])
                self._db.execute("DELETE FROM captures WHERE id = ?", (capture_id,))

            cursor = self._db.execute(
                """
                INSERT INTO captures(
                    capture_key, source_path, source_sha256, tracker, profile,
                    started_at_utc, complete, frame_count, duration_s, build_id,
                    calibration_id, rig_id, fixture_key, media_path, title,
                    metadata_json, indexed_at_utc
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    capture_key,
                    str(source),
                    digest,
                    capture.header.tracker,
                    capture.header.profile,
                    capture.header.started_at_utc,
                    1 if capture.complete else 0,
                    capture.frame_count,
                    capture.duration_s,
                    build_id,
                    calibration_id,
                    rig_id,
                    fixture_key,
                    media,
                    title,
                    json.dumps(library_metadata, sort_keys=True, separators=(",", ":")),
                    _utc_now(),
                ),
            )
            capture_id = int(cursor.lastrowid)
            segment_ids: list[int] = []
            for segment_index, frames in _segment_frames(
                capture, segment_duration_s, overlap_s
            ):
                fingerprint = fingerprint_frames(frames)
                segment_cursor = self._db.execute(
                    """
                    INSERT INTO segments(
                        capture_id, segment_index, start_s, end_s, start_frame,
                        end_frame, fingerprint_json, judgment, notes, tags_json,
                        created_at_utc
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        capture_id,
                        segment_index,
                        frames[0].timestamp_s,
                        frames[-1].timestamp_s,
                        frames[0].frame_index,
                        frames[-1].frame_index,
                        json.dumps(fingerprint, sort_keys=True, separators=(",", ":")),
                        Judgment.UNREVIEWED.value,
                        notes,
                        json.dumps(tags_tuple),
                        _utc_now(),
                    ),
                )
                segment_ids.append(int(segment_cursor.lastrowid))
        return IndexedCapture(capture_id, str(source), digest, tuple(segment_ids))

    def put_embedding(
        self,
        segment_id: int,
        *,
        provider: str,
        model: str,
        vector: Sequence[float],
    ) -> None:
        values = [float(value) for value in vector]
        if not values or not all(math.isfinite(value) for value in values):
            raise ValueError("embedding vector must contain finite values")
        self._require_segment(segment_id)
        existing = self._db.execute(
            "SELECT vector_json FROM embeddings WHERE provider = ? AND model = ? LIMIT 1",
            (provider, model),
        ).fetchone()
        if existing is not None and len(json.loads(existing["vector_json"])) != len(values):
            raise ValueError(
                "embedding dimensions must remain constant within a provider/model namespace"
            )
        with self._db:
            self._db.execute(
                """
                INSERT INTO embeddings(segment_id, provider, model, vector_json, created_at_utc)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(segment_id, provider, model)
                DO UPDATE SET vector_json=excluded.vector_json, created_at_utc=excluded.created_at_utc
                """,
                (segment_id, provider, model, json.dumps(values), _utc_now()),
            )

    def embed_media_segments(
        self,
        embedder: SemanticEmbedder,
        *,
        segment_ids: Sequence[int] | None = None,
        capture_id: int | None = None,
        force: bool = False,
    ) -> EmbeddingBatchResult:
        clauses = ["c.media_path IS NOT NULL"]
        params: list[object] = []
        if segment_ids is not None:
            wanted = tuple(dict.fromkeys(int(value) for value in segment_ids))
            if not wanted:
                return EmbeddingBatchResult(embedder.provider, embedder.model, (), (), ())
            placeholders = ",".join("?" for _ in wanted)
            clauses.append(f"s.id IN ({placeholders})")
            params.extend(wanted)
        if capture_id is not None:
            clauses.append("c.id = ?")
            params.append(int(capture_id))
        rows = self._db.execute(
            f"""
            SELECT s.id, s.start_s, s.end_s, c.media_path
            FROM segments s
            JOIN captures c ON c.id = s.capture_id
            WHERE {' AND '.join(clauses)}
            ORDER BY s.id
            """,
            params,
        ).fetchall()

        embedded: list[int] = []
        skipped: list[int] = []
        failures: list[EmbeddingFailure] = []
        for row in rows:
            segment_id = int(row["id"])
            if not force and self._embedding(segment_id, embedder.provider, embedder.model) is not None:
                skipped.append(segment_id)
                continue
            media_path = Path(row["media_path"])
            if not media_path.is_file():
                failures.append(EmbeddingFailure(segment_id, f"media file not found: {media_path}"))
                continue
            try:
                vector = embedder.embed_video_window(
                    media_path,
                    float(row["start_s"]),
                    float(row["end_s"]),
                )
                self.put_embedding(
                    segment_id,
                    provider=embedder.provider,
                    model=embedder.model,
                    vector=vector,
                )
            except Exception as exc:
                failures.append(EmbeddingFailure(segment_id, str(exc)))
            else:
                embedded.append(segment_id)
        return EmbeddingBatchResult(
            provider=embedder.provider,
            model=embedder.model,
            embedded_segment_ids=tuple(embedded),
            skipped_segment_ids=tuple(skipped),
            failures=tuple(failures),
        )

    def set_judgment(self, segment_id: int, judgment: Judgment | str, note: str = "") -> None:
        normalized = Judgment(judgment).value
        self._require_segment(segment_id)
        with self._db:
            self._db.execute(
                "UPDATE segments SET judgment = ?, notes = CASE WHEN ? = '' THEN notes ELSE ? END WHERE id = ?",
                (normalized, note, note, segment_id),
            )
            self._db.execute(
                "INSERT INTO judgment_history(segment_id, judgment, note, created_at_utc) VALUES(?, ?, ?, ?)",
                (segment_id, normalized, note, _utc_now()),
            )

    def promote_bug(
        self,
        segment_id: int,
        bug_id: str,
        description: str,
        *,
        expected_behavior: str = "",
    ) -> dict[str, object]:
        bug_id = bug_id.strip()
        if not bug_id:
            raise ValueError("bug_id must not be empty")
        if not description.strip():
            raise ValueError("description must not be empty")
        self._require_segment(segment_id)
        with self._db:
            self._db.execute(
                "UPDATE segments SET judgment = ?, notes = ? WHERE id = ?",
                (Judgment.FAILURE.value, description, segment_id),
            )
            self._db.execute(
                "INSERT INTO judgment_history(segment_id, judgment, note, created_at_utc) VALUES(?, ?, ?, ?)",
                (segment_id, Judgment.FAILURE.value, description, _utc_now()),
            )
            self._db.execute(
                """
                INSERT INTO bugs(bug_id, segment_id, description, expected_behavior, created_at_utc)
                VALUES(?, ?, ?, ?, ?)
                """,
                (bug_id, segment_id, description, expected_behavior, _utc_now()),
            )
        return self.bug_packet(bug_id)

    def bug_packet(self, bug_id: str) -> dict[str, object]:
        row = self._db.execute(
            """
            SELECT b.bug_id, b.description, b.expected_behavior, b.status,
                   b.created_at_utc, s.id AS segment_id, s.segment_index,
                   s.start_s, s.end_s, s.start_frame, s.end_frame,
                   s.fingerprint_json, c.source_path, c.source_sha256,
                   c.build_id, c.calibration_id, c.rig_id, c.fixture_key,
                   c.media_path, c.tracker, c.profile, c.metadata_json
            FROM bugs b
            JOIN segments s ON s.id = b.segment_id
            JOIN captures c ON c.id = s.capture_id
            WHERE b.bug_id = ?
            """,
            (bug_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown bug_id: {bug_id}")
        return {
            "bug_id": row["bug_id"],
            "description": row["description"],
            "expected_behavior": row["expected_behavior"],
            "status": row["status"],
            "created_at_utc": row["created_at_utc"],
            "segment": {
                "id": int(row["segment_id"]),
                "segment_index": int(row["segment_index"]),
                "start_s": float(row["start_s"]),
                "end_s": float(row["end_s"]),
                "start_frame": int(row["start_frame"]),
                "end_frame": int(row["end_frame"]),
                "fingerprint": json.loads(row["fingerprint_json"]),
            },
            "capture": {
                "source_path": row["source_path"],
                "source_sha256": row["source_sha256"],
                "build_id": row["build_id"],
                "calibration_id": row["calibration_id"],
                "rig_id": row["rig_id"],
                "fixture_key": row["fixture_key"],
                "media_path": row["media_path"],
                "tracker": row["tracker"],
                "profile": row["profile"],
                "metadata": json.loads(row["metadata_json"]),
            },
        }

    def search(
        self,
        text: str = "",
        *,
        reference_segment_id: int | None = None,
        query_embedding: Sequence[float] | None = None,
        provider: str | None = None,
        model: str | None = None,
        judgment: Judgment | str | None = None,
        tag: str | None = None,
        build_id: str | None = None,
        fixture_key: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        if limit <= 0:
            return []
        reference_fp = None
        if reference_segment_id is not None:
            reference_fp = self._segment_fingerprint(reference_segment_id)
            if query_embedding is None and provider and model:
                query_embedding = self._embedding(reference_segment_id, provider, model)

        normalized_query_embedding = None
        if query_embedding is not None:
            if not provider or not model:
                raise ValueError("provider and model are required with query_embedding")
            normalized_query_embedding = [float(value) for value in query_embedding]
            if not normalized_query_embedding or not all(
                math.isfinite(value) for value in normalized_query_embedding
            ):
                raise ValueError("query embedding must contain finite values")
            namespace_row = self._db.execute(
                "SELECT vector_json FROM embeddings WHERE provider = ? AND model = ? LIMIT 1",
                (provider, model),
            ).fetchone()
            if namespace_row is not None:
                namespace_dimensions = len(json.loads(namespace_row["vector_json"]))
                if namespace_dimensions != len(normalized_query_embedding):
                    raise ValueError(
                        "query embedding dimensions must match the provider/model namespace"
                    )

        clauses = []
        params: list[object] = []
        if judgment is not None:
            clauses.append("s.judgment = ?")
            params.append(Judgment(judgment).value)
        if build_id is not None:
            clauses.append("c.build_id = ?")
            params.append(build_id)
        if fixture_key is not None:
            clauses.append("c.fixture_key = ?")
            params.append(fixture_key)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._db.execute(
            f"""
            SELECT s.*, c.source_path, c.build_id, c.fixture_key, c.title,
                   c.tracker, c.profile, c.metadata_json
            FROM segments s
            JOIN captures c ON c.id = s.capture_id
            {where}
            """,
            params,
        ).fetchall()

        wanted_tag = tag.strip().lower() if tag else None
        query_requested = (
            reference_fp is not None
            or normalized_query_embedding is not None
            or bool(text.strip())
        )
        results: list[SearchResult] = []
        for row in rows:
            tags = tuple(json.loads(row["tags_json"]))
            if wanted_tag and wanted_tag not in tags:
                continue

            fingerprint = json.loads(row["fingerprint_json"])
            kinematic_score = (
                _sparse_cosine(reference_fp, fingerprint) if reference_fp is not None else None
            )
            semantic_score = None
            if normalized_query_embedding is not None:
                candidate_embedding = self._embedding(int(row["id"]), provider, model)
                if candidate_embedding is not None:
                    semantic_score = _dense_cosine(normalized_query_embedding, candidate_embedding)

            document = " ".join(
                (
                    row["title"],
                    row["notes"],
                    " ".join(tags),
                    row["judgment"],
                    row["build_id"] or "",
                    row["fixture_key"] or "",
                    row["tracker"],
                    row["profile"],
                    row["metadata_json"],
                )
            )
            text_score = _text_similarity(text, document) if text.strip() else None

            components = [
                score for score in (kinematic_score, semantic_score, text_score) if score is not None
            ]
            if not components:
                if query_requested:
                    continue
                score = 1.0
            else:
                score = sum(components) / len(components)
            results.append(
                SearchResult(
                    segment_id=int(row["id"]),
                    capture_id=int(row["capture_id"]),
                    source_path=row["source_path"],
                    start_s=float(row["start_s"]),
                    end_s=float(row["end_s"]),
                    judgment=row["judgment"],
                    score=score,
                    kinematic_score=kinematic_score,
                    semantic_score=semantic_score,
                    text_score=text_score,
                    notes=row["notes"],
                    tags=tags,
                    build_id=row["build_id"],
                    fixture_key=row["fixture_key"],
                )
            )
        results.sort(key=lambda item: (-item.score, item.segment_id))
        return results[:limit]

    def review_queue(self, *, limit: int = 10, neighbors: int = 5) -> list[ReviewItem]:
        rows = self._db.execute(
            """
            SELECT s.id, s.fingerprint_json, s.judgment, c.source_path
            FROM segments s JOIN captures c ON c.id = s.capture_id
            WHERE s.judgment IN ('unreviewed', 'interesting')
            """
        ).fetchall()
        if not rows or limit <= 0:
            return []
        fingerprints = {int(row["id"]): json.loads(row["fingerprint_json"]) for row in rows}
        failures = [
            json.loads(row["fingerprint_json"])
            for row in self._db.execute(
                "SELECT fingerprint_json FROM segments WHERE judgment = ?",
                (Judgment.FAILURE.value,),
            ).fetchall()
        ]
        items: list[ReviewItem] = []
        for row in rows:
            segment_id = int(row["id"])
            fingerprint = fingerprints[segment_id]
            similarities = sorted(
                (
                    _sparse_cosine(fingerprint, other_fp)
                    for other_id, other_fp in fingerprints.items()
                    if other_id != segment_id
                ),
                reverse=True,
            )
            nearest = similarities[: max(1, neighbors)]
            novelty = 1.0 - (_mean(nearest) if nearest else 0.0)
            novelty = max(0.0, min(1.0, novelty))
            low_tracking = 1.0 - max(0.0, min(1.0, fingerprint.get("tracking:ratio", 0.0)))
            failure_similarity = max(
                (_sparse_cosine(fingerprint, failure_fp) for failure_fp in failures),
                default=0.0,
            )
            score = 0.5 * novelty + 0.25 * low_tracking + 0.25 * max(0.0, failure_similarity)
            reasons = []
            if novelty >= 0.35:
                reasons.append("rare motion")
            if low_tracking >= 0.25:
                reasons.append("low tracking")
            if failure_similarity >= 0.85:
                reasons.append("known-failure similarity")
            if not reasons:
                reasons.append("review candidate")
            items.append(
                ReviewItem(
                    segment_id=segment_id,
                    source_path=row["source_path"],
                    score=score,
                    novelty=novelty,
                    low_tracking=low_tracking,
                    failure_similarity=failure_similarity,
                    reasons=tuple(reasons),
                )
            )
        items.sort(key=lambda item: (-item.score, item.segment_id))
        return items[:limit]

    def compare_builds(self, build_a: str, build_b: str, *, limit: int = 20) -> list[BuildDelta]:
        rows = self._db.execute(
            """
            SELECT s.id, s.segment_index, s.fingerprint_json, c.build_id, c.fixture_key
            FROM segments s JOIN captures c ON c.id = s.capture_id
            WHERE c.build_id IN (?, ?) AND c.fixture_key IS NOT NULL
            """,
            (build_a, build_b),
        ).fetchall()
        by_key: dict[tuple[str, int], dict[str, sqlite3.Row]] = {}
        for row in rows:
            key = (row["fixture_key"], int(row["segment_index"]))
            by_key.setdefault(key, {})[row["build_id"]] = row
        deltas: list[BuildDelta] = []
        for (fixture, segment_index), pair in by_key.items():
            if build_a not in pair or build_b not in pair:
                continue
            left = pair[build_a]
            right = pair[build_b]
            similarity = _sparse_cosine(
                json.loads(left["fingerprint_json"]),
                json.loads(right["fingerprint_json"]),
            )
            deltas.append(
                BuildDelta(
                    fixture_key=fixture,
                    segment_index=segment_index,
                    build_a_segment_id=int(left["id"]),
                    build_b_segment_id=int(right["id"]),
                    drift=max(0.0, 1.0 - similarity),
                )
            )
        deltas.sort(key=lambda item: (-item.drift, item.fixture_key, item.segment_index))
        return deltas[: max(0, limit)]

    def benchmark_build_retrieval(
        self,
        build_a: str,
        build_b: str,
        *,
        provider: str,
        model: str,
    ) -> list[RetrievalMetrics]:
        if build_a == build_b:
            raise ValueError("benchmark builds must be different")
        if not provider.strip() or not model.strip():
            raise ValueError("provider and model are required for semantic benchmark modes")

        rows = self._db.execute(
            """
            SELECT s.id, s.segment_index, c.build_id, c.fixture_key
            FROM segments s
            JOIN captures c ON c.id = s.capture_id
            WHERE c.build_id IN (?, ?) AND c.fixture_key IS NOT NULL
            """,
            (build_a, build_b),
        ).fetchall()
        paired: dict[tuple[str, int], dict[str, int]] = {}
        for row in rows:
            key = (str(row["fixture_key"]), int(row["segment_index"]))
            build = str(row["build_id"])
            slot = paired.setdefault(key, {})
            if build in slot:
                raise ValueError(
                    "benchmark fixture mapping is ambiguous: "
                    f"duplicate {key[0]!r} segment {key[1]} for build {build!r}"
                )
            slot[build] = int(row["id"])
        pairs = [
            (pair[build_a], pair[build_b])
            for pair in paired.values()
            if build_a in pair and build_b in pair
        ]
        query_count = len(pairs)
        candidate_count = int(
            self._db.execute(
                """
                SELECT COUNT(*) AS count
                FROM segments s JOIN captures c ON c.id = s.capture_id
                WHERE c.build_id = ?
                """,
                (build_b,),
            ).fetchone()["count"]
        )
        result_limit = max(1, candidate_count)

        kinematic_ranks: list[int | None] = []
        semantic_ranks: list[int | None] = []
        hybrid_ranks: list[int | None] = []
        semantic_skipped = 0
        hybrid_skipped = 0

        def rank_of(results: Sequence[SearchResult], target_id: int) -> int | None:
            return next(
                (index for index, result in enumerate(results, start=1) if result.segment_id == target_id),
                None,
            )

        for query_id, target_id in pairs:
            kinematic = self.search(
                reference_segment_id=query_id,
                build_id=build_b,
                limit=result_limit,
            )
            kinematic_ranks.append(rank_of(kinematic, target_id))

            query_embedding = self._embedding(query_id, provider, model)
            target_embedding = self._embedding(target_id, provider, model)
            if query_embedding is None or target_embedding is None:
                semantic_skipped += 1
                hybrid_skipped += 1
                continue

            semantic = self.search(
                query_embedding=query_embedding,
                provider=provider,
                model=model,
                build_id=build_b,
                limit=result_limit,
            )
            semantic_ranks.append(rank_of(semantic, target_id))

            hybrid = self.search(
                reference_segment_id=query_id,
                provider=provider,
                model=model,
                build_id=build_b,
                limit=result_limit,
            )
            hybrid_ranks.append(rank_of(hybrid, target_id))

        return [
            _retrieval_metrics(
                "kinematic",
                kinematic_ranks,
                query_count=query_count,
                skipped=0,
            ),
            _retrieval_metrics(
                "semantic",
                semantic_ranks,
                query_count=query_count,
                skipped=semantic_skipped,
            ),
            _retrieval_metrics(
                "hybrid",
                hybrid_ranks,
                query_count=query_count,
                skipped=hybrid_skipped,
            ),
        ]

    def list_segments(self, *, limit: int = 100) -> list[dict[str, object]]:
        rows = self._db.execute(
            """
            SELECT s.id, s.segment_index, s.start_s, s.end_s, s.judgment,
                   s.notes, s.tags_json, c.source_path, c.build_id, c.fixture_key,
                   c.title
            FROM segments s JOIN captures c ON c.id = s.capture_id
            ORDER BY s.id DESC LIMIT ?
            """,
            (max(0, limit),),
        ).fetchall()
        return [
            {
                "segment_id": int(row["id"]),
                "segment_index": int(row["segment_index"]),
                "source_path": row["source_path"],
                "start_s": float(row["start_s"]),
                "end_s": float(row["end_s"]),
                "judgment": row["judgment"],
                "notes": row["notes"],
                "tags": tuple(json.loads(row["tags_json"])),
                "build_id": row["build_id"],
                "fixture_key": row["fixture_key"],
                "title": row["title"],
            }
            for row in rows
        ]

    def _require_segment(self, segment_id: int) -> sqlite3.Row:
        row = self._db.execute("SELECT * FROM segments WHERE id = ?", (segment_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown segment_id: {segment_id}")
        return row

    def _segment_fingerprint(self, segment_id: int) -> dict[str, float]:
        row = self._require_segment(segment_id)
        return json.loads(row["fingerprint_json"])

    def _embedding(
        self,
        segment_id: int,
        provider: str | None,
        model: str | None,
    ) -> list[float] | None:
        if not provider or not model:
            return None
        row = self._db.execute(
            "SELECT vector_json FROM embeddings WHERE segment_id = ? AND provider = ? AND model = ?",
            (segment_id, provider, model),
        ).fetchone()
        return json.loads(row["vector_json"]) if row is not None else None
