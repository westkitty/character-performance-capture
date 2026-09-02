# Performance Black Box

## Purpose

The Performance Black Box turns recorded performer state into reusable local evidence. It is deliberately downstream of the portable `.cpc` format: captures remain canonical performer-state records, while search fingerprints, judgments, embeddings, and bug packets are derived library state that can be regenerated or replaced.

## Authority and privacy

- `.cpc` capture data remains the authoritative performance source.
- Fingerprints and semantic embeddings are derived caches, never canonical performance state.
- Human judgments (`gold`, `failure`, `interesting`, `unreviewed`, `superseded`) are evidence and are preserved separately from derived vectors.
- Camera pixels are not added to `.cpc` files.
- `media_path` is only an optional local reference to external footage. The Black Box never copies or uploads that media.
- No semantic model is a core dependency. The optional Qwen adapter is local-only and requires a pre-downloaded model directory; it never resolves or downloads a remote model ID.

## Storage

The default library is SQLite at:

```text
~/.cpc/performance_library.sqlite3
```

Tables separate:

- capture identity and provenance
- overlapping performance segments
- renderer-independent kinematic fingerprints
- optional semantic vectors by provider/model
- current human judgment plus judgment history
- durable bug evidence packets

Deleting the SQLite database deletes derived search/evidence state but does not alter source `.cpc` files.

## Kinematic fingerprint

Each segment is summarized from portable `PerformanceFrame` data using sparse named features:

- tracked-frame ratio and confidence distribution
- blendshape mean, standard deviation, and temporal motion
- normalized head pitch/yaw/roll mean, spread, and temporal motion
- gaze mean, spread, and temporal motion
- coarse landmark count, centroid, and centroid motion

Because features are named rather than positional, different tracker profiles can coexist without forcing one global blendshape dimension. Similarity is cosine similarity over the union of available sparse features.

## Hybrid retrieval

`PerformanceLibrary.search()` can combine any available evidence lane:

1. **Reference motion** - cosine similarity to another indexed segment fingerprint.
2. **Semantic vector** - cosine similarity to an explicitly supplied vector from a named provider/model.
3. **Text context** - token similarity over title, notes, tags, judgment, build, fixture, tracker/profile, and capture metadata.

Only available lanes participate in scoring. Candidates that lack a specifically requested semantic embedding are excluded from semantic-only retrieval instead of receiving a misleading neutral score. A directorial query can combine a reference motion with an image+text semantic query such as "this expression, but eyes toward camera."

## Review queue

The review queue ranks unreviewed/interesting segments using three signals:

- novelty relative to nearest performance neighbors
- low tracked-frame ratio
- similarity to confirmed failure fingerprints

The queue is a prioritization aid, not an automatic defect verdict. Statistical rarity is not equivalent to bad performance.

## Human evidence states

- `unreviewed` - no human decision yet
- `gold` - known-good reference suitable for canonical/regression use
- `failure` - confirmed bad behavior
- `interesting` - unusual and worth preserving/reviewing
- `superseded` - historical evidence retained but no longer controlling

Changing judgment appends a history record rather than treating a vector score as truth.

## Make This a Bug

`promote_bug()` binds a confirmed failure to:

- stable bug ID
- exact source capture SHA-256
- segment/frame/time bounds
- tracker/profile and optional build/calibration/rig/fixture identity
- local media path when one was explicitly associated
- the segment fingerprint
- observed failure description
- expected behavior

This packet is intended to feed later visual QA, repair-contract, and regression-fixture workflows without pretending the pixels reveal a hidden code root cause.

## Semantic build diff

Canonical test performances can be indexed with the same `fixture_key` under different `build_id` values. `compare_builds()` pairs matching fixture segments and ranks kinematic fingerprint drift.

A high drift score means "this performance changed" - not automatically "this build is broken." Human review or a stronger regression oracle decides whether the change is acceptable.

## Semantic embedding seam

The core still does not select or download an embedding model. `put_embedding(segment_id, provider, model, vector)` remains the generic adapter seam. Search requires an exact provider/model match, rejects dimension drift inside one namespace, and rejects a query vector whose dimension does not match that namespace so incompatible vector spaces are not silently mixed.

## Optional local Qwen3-VL adapter

`cpc.semantic_qwen.Qwen3VLSemanticEmbedder` implements the first local multimodal adapter. It is intentionally outside the core dependency set. Install the optional runtime only when needed:

```bash
pip install -e '.[blackbox-qwen]'
```

The adapter requires a **pre-downloaded local model directory**. It passes `local_files_only=True` to model and processor loading and never downloads model weights. The recommended starting model is `Qwen/Qwen3-VL-Embedding-2B`; larger variants remain an explicit operator choice.

Unlike a generic video indexer, CPC does not hand the whole media file to the model. The library already knows each performance segment's exact time bounds, so the adapter samples only that bounded local media window with OpenCV, resizes frames to a configurable maximum side, and passes the resulting frame sequence to Qwen. This avoids an additional torchcodec/FFmpeg dependency and keeps the semantic lane aligned with the same segment boundaries used by the kinematic fingerprint.

Index a `.cpc` take together with the local footage that corresponds to the same timeline:

```bash
cpc-blackbox index takes/take-001.cpc \
  --media media/take-001.mp4 \
  --build build-17 \
  --fixture canonical-smile-left
```

Embed only an explicit capture or segment selection:

```bash
cpc-blackbox qwen-embed \
  --capture-id 4 \
  --model-path models/Qwen3-VL-Embedding-2B \
  --model-id Qwen/Qwen3-VL-Embedding-2B \
  --dimensions 768
```

The provider/model namespace includes the requested Matryoshka dimension, for example:

```text
provider: qwen3-vl-local
model: Qwen/Qwen3-VL-Embedding-2B@768d
```

This prevents a 512-dimensional truncation from being compared accidentally with a 768- or 2048-dimensional vector under the same label.

### Directorial image + text search

Qwen queries can contain text, a reference image, or both. They can also be combined with a CPC reference segment so visual semantics and performer motion contribute independently:

```bash
cpc-blackbox qwen-search "same expression, eyes toward camera" \
  --image refs/expression.png \
  --reference 12 \
  --model-path models/Qwen3-VL-Embedding-2B \
  --dimensions 768
```

The image and text are encoded together in Qwen's multimodal space. `--reference` adds the existing kinematic fingerprint lane; it does not turn the reference clip into hidden semantic truth.

## Retrieval benchmark

`benchmark_build_retrieval()` provides an objective comparison of the three retrieval modes:

- `kinematic` - sparse CPC performance fingerprint only
- `semantic` - stored provider/model embedding only
- `hybrid` - both lanes together

Ground truth comes from canonical build fixtures: a segment under `(fixture_key, segment_index)` in build A is expected to retrieve the matching segment in build B from the complete build-B candidate set. Duplicate mappings for the same fixture/segment/build are rejected as ambiguous rather than silently choosing one. This makes the benchmark deterministic without pretending raw cosine values are calibrated confidence scores.

Metrics are Hit@1, Hit@3, Hit@5, and MRR. Semantic/hybrid queries are reported as skipped when either side of the canonical pair lacks the requested embedding, rather than being scored as retrieval failures or silently borrowing another model's vector.

```bash
cpc-blackbox benchmark build-17 build-18 \
  --provider qwen3-vl-local \
  --model 'Qwen/Qwen3-VL-Embedding-2B@768d'
```

This benchmark is the gate for deciding whether a semantic model improves CPC's actual performance-library retrieval enough to justify its memory and inference cost.

## Apple-Silicon MLX path

The low-memory Mac path uses `cpc.semantic_qwen_mlx.Qwen3VLMLXEmbedder` behind the optional `blackbox-mlx` extra. The committed runtime dependency is `mlx-vlm>=0.6.17,<0.7`, whose project license is MIT. The recommended starting checkpoint is `mlx-community/Qwen3-VL-Embedding-2B-4bit`, an Apache-2.0 MLX conversion whose weights are roughly 1.78 GB.

The adapter still refuses a remote model identifier: `--model-path` must be a directory that already exists. `mlx-vlm` receives that local path, so model resolution during CPC inference stays local. The explicit MacBook bootstrap is the only CPC-provided workflow that downloads the chosen checkpoint, and it does so before the smoke run.

For the 8 GB MacBook profile, CPC samples at most four chronological still frames per performance window at 2 frames/second and caps the longest image side at 448 pixels. Those frames are encoded together with a short segment description as one multimodal input. This is a resource bound, not a claim that four stills are equivalent to full-video understanding; the retrieval benchmark decides whether the trade is good enough.

```bash
pip install -e '.[blackbox-mlx]'

cpc-blackbox qwen-search "eyes toward camera" \
  --runtime mlx \
  --model-path /local/path/Qwen3-VL-Embedding-2B-4bit \
  --dimensions 768
```

The MLX implementation follows Qwen's documented embedding contract: use the final hidden state at the last non-padding token, truncate to the selected Matryoshka dimension, then L2-normalize. CPC uses `mlx-vlm` only for model loading, multimodal input preparation, and Qwen3-VL forward execution; it does not depend on `mlx-embeddings`.

### MacBook bootstrap proof

`scripts/macbook_blackbox_bootstrap.sh` is the target-machine evidence route. Before installation or model work it verifies Darwin/arm64, at least 7 GiB reported physical memory, at least 6 GiB free disk, and Python 3.11+. It then:

1. creates an isolated state/venv under `~/Library/Application Support/CharacterPerformanceCapture/blackbox`;
2. installs CPC with `blackbox-mlx`;
3. explicitly downloads the 4-bit checkpoint if absent;
4. runs `cpc --doctor --camera 0 --doctor-frames 120` and preserves the JSON report;
5. generates a temporary synthetic image, runs a real text+vision Qwen query under `/usr/bin/time -l`, preserves the timing/memory report, then removes the synthetic image.

A successful bootstrap proves only camera sampling plus one local semantic query on that machine. It does **not** prove real-take retrieval quality. The next gate is to index a matching `.cpc` + local media take, embed its segments with `--runtime mlx`, then benchmark canonical fixtures across builds.
