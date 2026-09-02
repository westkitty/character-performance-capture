from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .performance_library import DEFAULT_LIBRARY_PATH, Judgment, PerformanceLibrary


def _vector(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def _add_qwen_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument(
        "--runtime",
        choices=("torch", "mlx"),
        default="torch",
        help="Semantic runtime; MLX is the Apple-Silicon low-memory path",
    )
    parser.add_argument("--model-id")
    parser.add_argument("--dimensions", type=int, default=768)
    parser.add_argument("--device", choices=("auto", "cpu", "mps", "cuda"), default="auto")
    parser.add_argument("--sample-fps", type=float)
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--max-side", type=int)
    parser.add_argument("--verbose", action="store_true")


def _qwen_embedder(args):
    if args.runtime == "mlx":
        from . import semantic_qwen_mlx as qwen_mlx

        return qwen_mlx.Qwen3VLMLXEmbedder(
            args.model_path,
            model_id=args.model_id or qwen_mlx.DEFAULT_MLX_MODEL_ID,
            dimensions=args.dimensions,
            sample_fps=(
                args.sample_fps
                if args.sample_fps is not None
                else qwen_mlx.DEFAULT_SAMPLE_FPS
            ),
            max_frames=(
                args.max_frames
                if args.max_frames is not None
                else qwen_mlx.DEFAULT_MAX_FRAMES
            ),
            max_side=(
                args.max_side if args.max_side is not None else qwen_mlx.DEFAULT_MAX_SIDE
            ),
            verbose=args.verbose,
        )

    from . import semantic_qwen as qwen_torch

    return qwen_torch.Qwen3VLSemanticEmbedder(
        args.model_path,
        model_id=args.model_id or qwen_torch.DEFAULT_MODEL_ID,
        dimensions=args.dimensions,
        device=args.device,
        sample_fps=(
            args.sample_fps
            if args.sample_fps is not None
            else qwen_torch.DEFAULT_SAMPLE_FPS
        ),
        max_frames=(
            args.max_frames
            if args.max_frames is not None
            else qwen_torch.DEFAULT_MAX_FRAMES
        ),
        max_side=(
            args.max_side if args.max_side is not None else qwen_torch.DEFAULT_MAX_SIDE
        ),
        verbose=args.verbose,
    )


def _qwen_embedder_or_error(parser: argparse.ArgumentParser, args):
    try:
        return _qwen_embedder(args)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CPC Performance Black Box")
    parser.add_argument("--db", type=Path, default=DEFAULT_LIBRARY_PATH)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create or open the local performance library")

    index = sub.add_parser("index", help="Index a .cpc capture into overlapping segments")
    index.add_argument("capture", type=Path)
    index.add_argument("--segment-duration", type=float, default=2.0)
    index.add_argument("--overlap", type=float, default=0.5)
    index.add_argument("--build")
    index.add_argument("--calibration")
    index.add_argument("--rig")
    index.add_argument("--fixture")
    index.add_argument("--media", type=Path)
    index.add_argument("--title", default="")
    index.add_argument("--tag", action="append", default=[])
    index.add_argument("--notes", default="")

    listing = sub.add_parser("list", help="List indexed segments")
    listing.add_argument("--limit", type=int, default=50)

    search = sub.add_parser("search", help="Hybrid text/reference/embedding retrieval")
    search.add_argument("text", nargs="?", default="")
    search.add_argument("--reference", type=int)
    search.add_argument("--query-vector", type=_vector)
    search.add_argument("--provider")
    search.add_argument("--model")
    search.add_argument("--judgment", choices=[item.value for item in Judgment])
    search.add_argument("--tag")
    search.add_argument("--build")
    search.add_argument("--fixture")
    search.add_argument("--limit", type=int, default=10)

    embed = sub.add_parser("embed", help="Attach an externally produced semantic vector")
    embed.add_argument("segment_id", type=int)
    embed.add_argument("--provider", required=True)
    embed.add_argument("--model", required=True)
    embed.add_argument("--vector", type=_vector, required=True)

    qwen_embed = sub.add_parser(
        "qwen-embed",
        help="Embed indexed media windows with a pre-downloaded local Qwen3-VL model",
    )
    qwen_embed.add_argument("--capture-id", type=int)
    qwen_embed.add_argument("--segment", type=int, action="append")
    qwen_embed.add_argument("--force", action="store_true")
    _add_qwen_runtime_args(qwen_embed)

    qwen_search = sub.add_parser(
        "qwen-search",
        help="Run local semantic or directorial image+text search",
    )
    qwen_search.add_argument("text", nargs="?", default="")
    qwen_search.add_argument("--image", type=Path)
    qwen_search.add_argument("--reference", type=int)
    qwen_search.add_argument("--judgment", choices=[item.value for item in Judgment])
    qwen_search.add_argument("--tag")
    qwen_search.add_argument("--build")
    qwen_search.add_argument("--fixture")
    qwen_search.add_argument("--limit", type=int, default=10)
    _add_qwen_runtime_args(qwen_search)

    judge = sub.add_parser("judge", help="Assign human evidence state to a segment")
    judge.add_argument("segment_id", type=int)
    judge.add_argument("judgment", choices=[item.value for item in Judgment])
    judge.add_argument("--note", default="")

    bug = sub.add_parser("bug", help="Promote a visible failure into a durable bug packet")
    bug.add_argument("segment_id", type=int)
    bug.add_argument("bug_id")
    bug.add_argument("description")
    bug.add_argument("--expected", default="")

    show_bug = sub.add_parser("bug-show", help="Print a bug evidence packet")
    show_bug.add_argument("bug_id")

    review = sub.add_parser("review", help="Rank rare, low-confidence, and failure-like segments")
    review.add_argument("--limit", type=int, default=10)
    review.add_argument("--neighbors", type=int, default=5)

    diff = sub.add_parser("diff", help="Rank canonical fixture drift across two builds")
    diff.add_argument("build_a")
    diff.add_argument("build_b")
    diff.add_argument("--limit", type=int, default=20)

    benchmark = sub.add_parser(
        "benchmark",
        help="Compare kinematic, semantic, and hybrid retrieval across canonical builds",
    )
    benchmark.add_argument("build_a")
    benchmark.add_argument("build_b")
    benchmark.add_argument("--provider", required=True)
    benchmark.add_argument("--model", required=True)
    return parser


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    with PerformanceLibrary(args.db) as library:
        if args.command == "init":
            _print_json({"database": str(library.path), "status": "ready"})
        elif args.command == "index":
            result = library.index_capture(
                args.capture,
                segment_duration_s=args.segment_duration,
                overlap_s=args.overlap,
                build_id=args.build,
                calibration_id=args.calibration,
                rig_id=args.rig,
                fixture_key=args.fixture,
                media_path=args.media,
                title=args.title,
                tags=args.tag,
                notes=args.notes,
            )
            _print_json(result.__dict__)
        elif args.command == "list":
            _print_json(library.list_segments(limit=args.limit))
        elif args.command == "search":
            _print_json(
                [
                    result.__dict__
                    for result in library.search(
                        args.text,
                        reference_segment_id=args.reference,
                        query_embedding=args.query_vector,
                        provider=args.provider,
                        model=args.model,
                        judgment=args.judgment,
                        tag=args.tag,
                        build_id=args.build,
                        fixture_key=args.fixture,
                        limit=args.limit,
                    )
                ]
            )
        elif args.command == "embed":
            library.put_embedding(
                args.segment_id,
                provider=args.provider,
                model=args.model,
                vector=args.vector,
            )
            _print_json({"segment_id": args.segment_id, "status": "embedded"})
        elif args.command == "qwen-embed":
            if args.capture_id is None and not args.segment:
                parser.error("qwen-embed requires --capture-id and/or --segment")
            embedder = _qwen_embedder_or_error(parser, args)
            result = library.embed_media_segments(
                embedder,
                segment_ids=args.segment,
                capture_id=args.capture_id,
                force=args.force,
            )
            _print_json(asdict(result))
        elif args.command == "qwen-search":
            if not args.text.strip() and args.image is None:
                parser.error("qwen-search requires query text and/or --image")
            embedder = _qwen_embedder_or_error(parser, args)
            try:
                query_vector = embedder.embed_query(args.text, image_path=args.image)
            except (FileNotFoundError, ValueError, RuntimeError) as exc:
                parser.error(str(exc))
            _print_json(
                [
                    result.__dict__
                    for result in library.search(
                        reference_segment_id=args.reference,
                        query_embedding=query_vector,
                        provider=embedder.provider,
                        model=embedder.model,
                        judgment=args.judgment,
                        tag=args.tag,
                        build_id=args.build,
                        fixture_key=args.fixture,
                        limit=args.limit,
                    )
                ]
            )
        elif args.command == "judge":
            library.set_judgment(args.segment_id, args.judgment, args.note)
            _print_json({"segment_id": args.segment_id, "judgment": args.judgment})
        elif args.command == "bug":
            _print_json(
                library.promote_bug(
                    args.segment_id,
                    args.bug_id,
                    args.description,
                    expected_behavior=args.expected,
                )
            )
        elif args.command == "bug-show":
            _print_json(library.bug_packet(args.bug_id))
        elif args.command == "review":
            _print_json([item.__dict__ for item in library.review_queue(limit=args.limit, neighbors=args.neighbors)])
        elif args.command == "diff":
            _print_json([item.__dict__ for item in library.compare_builds(args.build_a, args.build_b, limit=args.limit)])
        elif args.command == "benchmark":
            _print_json(
                [
                    asdict(item)
                    for item in library.benchmark_build_retrieval(
                        args.build_a,
                        args.build_b,
                        provider=args.provider,
                        model=args.model,
                    )
                ]
            )


if __name__ == "__main__":
    main()
