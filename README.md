# Character Performance Capture

Local-first, model-agnostic character performance capture for Apple Silicon first.

The project is intentionally **not** a fork of Deep-Live-Cam. Deep-Live-Cam, DeepFaceLive, LivePortrait, and related projects are treated as prior art. This repository keeps camera ingest, performance tracking, character rendering, and output sinks behind explicit interfaces so model backends can be replaced without rebuilding the application.

## Current phase

Foundation / vertical slice.

Implemented in the initial slice:

- webcam capture through OpenCV;
- model-agnostic frame processor interface;
- passthrough renderer for proving the pipeline before model integration;
- live FPS/latency telemetry overlay;
- clean shutdown and resource release;
- headless-testable processing core;
- Git exclusions for user media, generated outputs, caches, and model weights.

Not implemented yet:

- facial performance tracking;
- character identity rendering;
- record/replay performance data;
- OBS/virtual-camera sink;
- production model backend.

## Why the architecture is split

```text
camera / file source
        |
        v
   frame source
        |
        v
 performance tracker  ---> optional capture/replay data
        |
        v
 character renderer
        |
        v
 preview / recorder / virtual camera
```

The core application must remain usable even if the tracking or rendering backend changes.

## Quick start

Requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cpc --camera 0
```

Press `q` or `Esc` to exit the preview.

Run tests:

```bash
pytest
```

## Licensing boundary

Do not commit or silently bundle model weights whose terms are incompatible with the intended use of this project.

In particular, several face-processing projects use InsightFace code under permissive terms while distributing or depending on model weights restricted to non-commercial research. Those restrictions apply to the model even when surrounding application code is permissively licensed. Production backends must therefore be reviewed independently.

## Privacy boundary

The default architecture is local-first. Frames, reference material, and captured performance data are not intended to leave the machine unless a future explicitly selected backend documents otherwise.

User media, reference portraits, generated outputs, model weights, and secrets are excluded from Git by default.
