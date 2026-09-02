# Architecture

## Goal

Provide a local-first character-performance pipeline whose camera, tracking, portable performance state, rendering, and output layers can evolve independently.

## Layer contract

### 1. Frame source

Owns camera/file acquisition and resource lifecycle. It returns ordinary BGR NumPy frames. It does not know which tracker or renderer will consume them. `CameraSource` wraps a live OpenCV camera; `VideoFileSource` reads a local video file (optionally looping) through the identical `open/info/read/close` contract so the whole pipeline runs without a webcam or camera permission.

### 2. Performance tracker

Converts a performer frame into portable `PerformanceFrame` state. The tracker contract includes lifecycle, frame index, timestamp, tracker/profile identity, normalized blendshapes, optional landmarks, and optional transform/gaze/head data. `NullTracker` proves the seam without a model; `MediaPipeFaceTracker` is the first optional real-tracker adapter.

### 3. Portable performance state

`PerformanceFrame` is the renderer-neutral handoff. `.cpc` format v1 records that state as UTF-8 JSON Lines so a take can be inspected or replayed without captured camera pixels and without depending on the renderer used later.

### 4. Character renderer

Consumes portable performer state and produces a rendered character frame.
`PassthroughRenderer` proves the contract with no character. `RigWarpRenderer` is
the first production-capable renderer: a deterministic, license-clean 2D
landmark-driven warp of an authorized character reference image
([`RENDERER.md`](RENDERER.md)). Any future renderer package must declare its code
license, model license, hardware path, expected latency, and whether commercial
use is allowed.

### 5. Output sink

Preview, file recorder, or virtual-camera output. Output must not be entangled
with model inference. OpenCV preview and an mp4 recorder exist; `VirtualCameraSink`
(optional `pyvirtualcam`, macOS OBS Virtual Camera backend) publishes rendered
frames with explicit dimension/FPS negotiation, aspect-preserving letterboxing, a
clean error when the backend is absent, and no disk or network writes.

## Current v1.0.0-rc1 slice

```text
CameraSource | VideoFileSource
    |
    v
PerformanceTracker (NullTracker or optional MediaPipeFaceTracker)
    |
    v
PerformanceFrame -----> PerformanceRecorder / PerformanceReplay (.cpc)
    |
    v
CharacterRenderer (PassthroughRenderer | RigWarpRenderer)
    |
    v
OpenCV preview + telemetry
    ├─ mp4 recorder
    └─ VirtualCameraSink (optional, OBS backend)
```

The older frame-only `Pipeline` remains as a small utility/compatibility path, while `PerformancePipeline` is the main tracker-to-renderer route.

## Reliability boundaries

- Completed capture finalization must never overwrite an independently existing destination path.
- `.cpc` readers reject malformed type coercion, records after an end record, invalid frame order, and inconsistent footer metadata.
- Closing and restarting a pipeline begins a fresh metrics/frame-index session.
- A failed multi-processor startup rolls back processors that already started.
- Real MediaPipe model inference, the rig-warp renderer, `.cpc` capture/replay,
  and the `pyvirtualcam`/OBS sink have been run end to end against a video frame
  source. Live **webcam** capture on the target Mac still needs a real run; it is
  blocked only by the macOS camera-permission prompt, not by code.

## Prior-art findings

Deep-Live-Cam demonstrates useful separation between capture, face analysis, frame processors, provider selection, and in-memory video processing. We adopt the architectural lesson but not its source code.

DeepFaceLive demonstrates the value of a live-first pipeline, but its repository is archived and GPL-3.0, making it a poor implementation base for this clean-room project.

LivePortrait is a stronger future rendering experiment because its project code is MIT. Its own license warns that bundled InsightFace detection models are non-commercial and must be replaced for a fully commercial MIT path. Its upstream documentation also warns that stock Apple-Silicon operation can be dramatically slower than high-end NVIDIA inference, so it remains a renderer experiment rather than a foundational dependency.

## Near-term sequence

1. Keep the deterministic regression suite green on Linux and Apple-Silicon CI. *(done)*
2. Smoke-test the optional MediaPipe package/API path in CI without bundling a model. *(done)*
3. Run one authorized local Face Landmarker model and create/replay a real `.cpc` take. *(done, video frame source)*
4. Ship a license-clean production-capable renderer behind the seam. *(done: `RigWarpRenderer`)*
5. Add a virtual-camera sink suitable for OBS. *(done: `VirtualCameraSink`)*
6. Record a real target **webcam** run (`cpc --doctor --camera 0`, then the live character route). *(pending: camera permission)*
7. If a higher live frame-rate is needed, overlap tracker and renderer on separate threads.
8. Optionally add a high-quality offline renderer; freeze a default only after license and device-performance evidence exist.

## Deliberate non-goals for the foundation

- Reproducing Deep-Live-Cam's UI.
- Bundling Inswapper or InsightFace weights.
- Making cloud inference mandatory.
- Tying capture semantics to a single human-face representation.
- Treating popularity or demo quality as proof of production fitness.
