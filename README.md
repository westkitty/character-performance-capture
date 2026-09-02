# Character Performance Capture

Local-first, model-agnostic character performance capture for webcam-driven character rendering.

This project is a **clean-room implementation**. Deep-Live-Cam, DeepFaceLive, LivePortrait, ARKit, MediaPipe, and similar systems may inform architecture research, but their source code is not copied into this repository.

## Current phase: v0.2 foundation

Implemented source now contains:

- explicit OpenCV webcam capture lifecycle
- portable `PerformanceFrame` schema
- tracker -> performance -> renderer pipeline
- crash-tolerant `.cpc` performance recording
- replay source independent of renderer choice
- no-op tracker and renderer for zero-model foundation testing
- optional MediaPipe Face Landmarker adapter
- live FPS / processing latency / tracking-status overlay
- local-only hardware/tracker diagnostics via `cpc --doctor`
- local Performance Black Box indexing/search/evidence tooling on the feature branch
- unit tests and GitHub Actions checks

Runtime validation on the target Macs is still required before any webcam, MLX/Qwen, or throughput claim is considered verified.

## Install core

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Run the zero-model preview:

```bash
cpc --camera 0 --mirror
```

Quit with `q` or Escape.

## Hardware proof

Before relying on preview behavior or throughput claims, run the headless local diagnostics route:

```bash
cpc --doctor --camera 0 --doctor-frames 120
```

The JSON report records the active OpenCV camera backend, requested versus reported camera settings, observed frame size, real frame-read timing, overall sampled FPS, runtime versions, and tracker timing. It does not persist camera pixels or require network access.

See [`docs/HARDWARE_VALIDATION.md`](docs/HARDWARE_VALIDATION.md) for the target-hardware validation procedure and the MediaPipe variant.

## MediaPipe tracker experiment

MediaPipe is optional and is deliberately kept out of the core dependency set.

```bash
pip install -e '.[tracker-mediapipe,dev]'
cpc --tracker mediapipe --model /path/to/face_landmarker.task --camera 0 --mirror
```

CPC does **not** download or redistribute the Face Landmarker model. Supply a local model asset you are authorized to use.

Record portable performer state while previewing:

```bash
cpc \
  --tracker mediapipe \
  --model /path/to/face_landmarker.task \
  --record-performance takes/take-001.cpc \
  --camera 0 \
  --mirror
```

The `.cpc` file contains performance data only, not camera pixels.

Inspect a take without opening the camera:

```bash
cpc --inspect-performance takes/take-001.cpc
```

See [`docs/PERFORMANCE_CAPTURE_FORMAT.md`](docs/PERFORMANCE_CAPTURE_FORMAT.md) for the format contract.

## Performance Black Box

The Black Box is downstream of `.cpc`: it stores derived searchable segments, kinematic fingerprints, optional semantic vectors, human evidence states, bug packets, review queues, and build-to-build retrieval benchmarks without changing the canonical capture format.

Initialize and index a take:

```bash
cpc-blackbox init
cpc-blackbox index takes/take-001.cpc \
  --media media/take-001.mp4 \
  --build build-17 \
  --fixture canonical-smile-left
```

Find similar motion or promote a visible failure into durable evidence:

```bash
cpc-blackbox search --reference 12
cpc-blackbox bug 12 JAW-004 "jaw wobbles during left turn" \
  --expected "jaw remains stable while yaw changes"
```

### MacBook Air / Apple Silicon semantic path

The constrained Apple-Silicon route uses the optional MIT-licensed `mlx-vlm` runtime and the Apache-2.0 `mlx-community/Qwen3-VL-Embedding-2B-4bit` model. CPC still requires a local model directory at runtime; only the explicit bootstrap command below downloads the selected model.

On the MacBook feature branch:

```bash
./scripts/macbook_blackbox_bootstrap.sh
```

The bootstrap performs the existing 120-frame camera doctor first, creates an isolated project venv under `~/Library/Application Support/CharacterPerformanceCapture/blackbox`, downloads the 4-bit MLX model if absent, then runs a text+synthetic-image embedding smoke test under `/usr/bin/time -l`. It does not persist a camera frame for the semantic smoke.

The Mac profile intentionally samples each indexed performance window as at most four chronological images at up to 448 px rather than decoding a whole video into the embedding model:

```bash
cpc-blackbox qwen-embed \
  --capture-id 4 \
  --runtime mlx \
  --model-path "$HOME/Library/Application Support/CharacterPerformanceCapture/blackbox/models/Qwen3-VL-Embedding-2B-4bit" \
  --dimensions 768
```

Directorial text + image search uses the same vector namespace and can still add a CPC kinematic reference segment:

```bash
cpc-blackbox qwen-search "same expression, eyes toward camera" \
  --image refs/expression.png \
  --reference 12 \
  --runtime mlx \
  --model-path "$HOME/Library/Application Support/CharacterPerformanceCapture/blackbox/models/Qwen3-VL-Embedding-2B-4bit" \
  --dimensions 768
```

After matching canonical fixtures exist in two builds, benchmark whether semantics actually help rather than trusting cosine scores:

```bash
cpc-blackbox benchmark build-17 build-18 \
  --provider qwen3-vl-mlx \
  --model 'mlx-community/Qwen3-VL-Embedding-2B-4bit@768d'
```

See [`docs/PERFORMANCE_BLACK_BOX.md`](docs/PERFORMANCE_BLACK_BOX.md) for the data model, evidence rules, model boundaries, and benchmark contract.

## Architectural boundary

```text
camera / video
     |
     v
performance tracker
     |
     v
portable PerformanceFrame -----> .cpc recorder / replay
     |                                  |
     v                                  v
character renderer               Performance Black Box
     |                           (derived local evidence)
     v
preview / recorder / virtual camera
```

Tracking and rendering are deliberately separate. The renderer should be replaceable without invalidating recorded performances. The Black Box is also replaceable: embeddings and fingerprints are derived from canonical `.cpc` data plus explicitly associated local media.

## Repository license

This repository is currently **proprietary / all rights reserved**. Public visibility is not an open-source license grant. See [`LICENSE`](LICENSE).

Third-party components, optional dependencies, models, datasets, and assets remain governed by their own licenses and terms.

## Licensing boundary

The repository core has no InsightFace or Inswapper dependency. Optional third-party trackers/renderers/embedding runtimes must be evaluated as separate adapters, including their code and model licenses. A backend is not production/commercial-ready merely because one layer of its stack is permissively licensed.

The MacBook semantic adapter uses `mlx-vlm` (MIT) rather than the GPL `mlx-embeddings` package so the committed CPC integration does not introduce that GPL dependency.

## Repository governance

CI runs on Linux and macOS plus a macOS MediaPipe smoke lane. The workflow exposes a stable aggregate `required-ci` job intended to be the single required status check for `main` once GitHub branch rules are enabled.

See [`docs/REPOSITORY_GOVERNANCE.md`](docs/REPOSITORY_GOVERNANCE.md) for the exact ruleset contract and current enforcement state.

## Privacy boundary

The intended path is local-first. No camera frame, reference image, recorded performance, semantic embedding source media, or character asset is uploaded by the core pipeline.

Do not commit user media, recorded takes, reference portraits, generated outputs, downloaded model weights, caches, or secrets.
