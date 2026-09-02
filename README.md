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
- unit tests and GitHub Actions checks

Runtime validation on the target Macs is still required before any webcam or throughput claim is considered verified.

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

## Architectural boundary

```text
camera / video
     |
     v
performance tracker
     |
     v
portable PerformanceFrame -----> .cpc recorder / replay
     |
     v
character renderer
     |
     v
preview / recorder / virtual camera
```

Tracking and rendering are deliberately separate. The renderer should be replaceable without invalidating recorded performances.

## Repository license

This repository is currently **proprietary / all rights reserved**. Public visibility is not an open-source license grant. See [`LICENSE`](LICENSE).

Third-party components, optional dependencies, models, datasets, and assets remain governed by their own licenses and terms.

## Licensing boundary

The repository core has no InsightFace or Inswapper dependency. Optional third-party trackers/renderers must be evaluated as separate adapters, including their code and model licenses. A backend is not production/commercial-ready merely because its Python package is permissively licensed.

## Repository governance

CI runs on Linux and macOS plus a macOS MediaPipe smoke lane. The workflow exposes a stable aggregate `required-ci` job intended to be the single required status check for `main` once GitHub branch rules are enabled.

See [`docs/REPOSITORY_GOVERNANCE.md`](docs/REPOSITORY_GOVERNANCE.md) for the exact ruleset contract and current enforcement state.

## Privacy boundary

The intended path is local-first. No camera frame, reference image, recorded performance, or character asset is uploaded by the core pipeline.

Do not commit user media, recorded takes, reference portraits, generated outputs, downloaded model weights, caches, or secrets.
