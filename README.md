# Character Performance Capture

Local-first, model-agnostic character performance capture for webcam-driven character rendering.

This project is a **clean-room implementation**. Deep-Live-Cam, DeepFaceLive, LivePortrait, ARKit, MediaPipe, and similar systems may inform architecture research, but their source code is not copied into this repository.

## Status: v1.0.0

The full live route is implemented, verified, and proven on target hardware:

```text
webcam / video
      │
      ▼
performance tracker  (null · MediaPipe Face Landmarker)
      │
      ▼
portable PerformanceFrame ───────► .cpc recorder / replay
      │
      ▼
character renderer   (passthrough · rig-warp 2D)
      │
      ▼
preview  ├─ optional .cpc recording
         └─ optional virtual-camera output
```

The system is validated across three distinct tiers (see [`docs/HARDWARE_VALIDATION.md`](docs/HARDWARE_VALIDATION.md) and [`OPERATIONAL_STATE.md`](OPERATIONAL_STATE.md)):
- **Deterministic CI proof**: 77 automated regressions across Linux and macOS covering schema, geometry, rig parsing, safe degradation, lifecycle rollback, `.cpc` recording/recovery, and CLI wiring.
- **Physical webcam & MediaPipe proof**: live Apple Silicon AVFoundation camera capture at 30 FPS, real-time MediaPipe face tracking (~14 ms/frame, ~89% track rate), live rig-warp character rendering, and portable `.cpc` take recording/replay without camera pixels.
- **Virtual-camera receive proof**: OBS Virtual Camera 1280x720 output actively received and consumed by external video consumer at 30 FPS without buffer mismatch or drift.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Optional extras (kept out of the core dependency set):

```bash
pip install -e '.[tracker-mediapipe]'    # MediaPipe Face Landmarker adapter
pip install -e '.[output-virtualcam]'    # virtual-camera / OBS output sink
```

## Zero-model quickstart

Preview the raw camera with live telemetry (no tracker, no character):

```bash
cpc --camera 0 --mirror
```

Quit with `q` or `Escape`. Read the whole workflow from `cpc --help`.

## Hardware proof (no model required)

```bash
cpc --doctor --camera 0 --doctor-frames 120 > camera-doctor.json
```

The JSON report records the active OpenCV backend, requested vs reported camera
settings, observed frame size, real frame-read timing, sampled FPS, runtime
versions, and tracker timing. It never persists camera pixels and never touches
the network. `--video CLIP.mp4` runs the same probe against a file instead of a
camera.

## MediaPipe tracker

MediaPipe is optional and deliberately outside the core. Supply a local Face
Landmarker `.task` model you are authorized to use — CPC never downloads or
redistributes one.

```bash
pip install -e '.[tracker-mediapipe]'
cpc --tracker mediapipe --model /path/to/face_landmarker.task --camera 0 --mirror
```

The CPU delegate is the default; the GPU delegate can abort on headless macOS.

## Character renderer

The rig-warp renderer drives an **authorized local character reference image**
from `PerformanceFrame` data. It warps the character's own pixels toward the
performer's relative expression and head motion, so the character keeps its
identity — the performer's face is never shown.

Each character ships with a **rig sidecar** (`<image>.rig.json`) holding a
neutral landmark mesh in MediaPipe Face Landmarker topology. Derive one once from
a front-facing neutral reference:

```bash
cpc --derive-rig --character char.png --model /path/to/face_landmarker.task
# writes char.png.rig.json
```

Then run the live character route:

```bash
cpc --tracker mediapipe --model /path/to/face_landmarker.task \
    --render rig --character char.png --camera 0 --mirror
```

See [`docs/RENDERER.md`](docs/RENDERER.md) for the rig contract and limits.

## Record and replay a performance

```bash
cpc --tracker mediapipe --model /path/to/face_landmarker.task \
    --render rig --character char.png \
    --record-performance takes/take-001.cpc --camera 0 --mirror

cpc --inspect-performance takes/take-001.cpc
```

`.cpc` files contain portable performer state only — no camera pixels. Recording
finalization never overwrites an existing file; an interrupted take leaves a
recoverable `.partial`. Format contract:
[`docs/PERFORMANCE_CAPTURE_FORMAT.md`](docs/PERFORMANCE_CAPTURE_FORMAT.md).

## Virtual-camera / OBS output

```bash
pip install -e '.[output-virtualcam]'
cpc --tracker mediapipe --model /path/to/face_landmarker.task \
    --render rig --character char.png --camera 0 --virtual-camera --vcam-size 1280x720
```

On macOS this backend needs the **OBS Virtual Camera** system extension (install
OBS, start its Virtual Camera once). `--vcam-size` must be a resolution the
backend accepts; the rendered frame is letter-boxed into it. The sink writes no
files and opens no network connection. If the backend is missing you get a clear,
actionable error.

## Video-file frame source

Any route above accepts `--video CLIP.mp4 [--loop]` instead of `--camera N`. This
runs the full capture → tracker → renderer → output path with no webcam and no
camera permission — useful for validation, regression, and replaying an
authorized recorded performer clip.

## Repository license

This repository is **proprietary / all rights reserved**. Public visibility is
not an open-source license grant. See [`LICENSE`](LICENSE).

Third-party components, optional dependencies, models, datasets, and assets
remain governed by their own licenses and terms. A backend is not
production/commercial-ready merely because its Python package is permissively
licensed.

## Repository governance

CI runs on Linux and macOS plus a macOS MediaPipe smoke lane and exposes one
stable aggregate status check, `required-ci`. An **active** ruleset on `main`
requires a pull request, a passing `required-ci`, an up-to-date branch, and
blocks force pushes and branch deletion. See
[`docs/REPOSITORY_GOVERNANCE.md`](docs/REPOSITORY_GOVERNANCE.md).

## Privacy boundary

The working path is local-first. No camera frame, reference image, recorded
performance, or character asset is uploaded by the core pipeline. Do not commit
user media, recorded takes, reference portraits, rig sidecars derived from real
faces, generated outputs, model weights, caches, or secrets.
