# Architecture

## Goal

Provide a local-first character-performance pipeline whose camera, tracking, portable performance state, rendering, and output layers can evolve independently.

## Layer contract

### 1. Frame source

Owns camera/file acquisition and resource lifecycle. It returns ordinary BGR NumPy frames. It does not know which tracker or renderer will consume them.

### 2. Performance tracker

Converts a performer frame into portable `PerformanceFrame` state. The tracker contract includes lifecycle, frame index, timestamp, tracker/profile identity, normalized blendshapes, optional landmarks, and optional transform/gaze/head data. `NullTracker` proves the seam without a model; `MediaPipeFaceTracker` is the first optional real-tracker adapter.

### 3. Portable performance state

`PerformanceFrame` is the renderer-neutral handoff. `.cpc` format v1 records that state as UTF-8 JSON Lines so a take can be inspected or replayed without captured camera pixels and without depending on the renderer used later.

### 4. Character renderer

Consumes a source frame plus portable performer state and produces a rendered frame. `PassthroughRenderer` currently proves the contract without a character model. Future renderer packages must declare their code license, model license, hardware path, expected latency, and whether commercial use is allowed.

### 5. Output sink

Preview, file recorder, or virtual-camera output. Output must not be entangled with model inference. OpenCV preview exists today; virtual-camera output remains pending.

## Current v0.2 slice

```text
CameraSource
    |
    v
PerformanceTracker (NullTracker or optional MediaPipeFaceTracker)
    |
    v
PerformanceFrame -----> PerformanceRecorder / PerformanceReplay (.cpc)
    |
    v
CharacterRenderer (PassthroughRenderer today)
    |
    v
OpenCV preview + telemetry
```

The older frame-only `Pipeline` remains as a small utility/compatibility path, while `PerformancePipeline` is the main tracker-to-renderer route.

## Reliability boundaries

- Completed capture finalization must never overwrite an independently existing destination path.
- `.cpc` readers reject malformed type coercion, records after an end record, invalid frame order, and inconsistent footer metadata.
- Closing and restarting a pipeline begins a fresh metrics/frame-index session.
- A failed multi-processor startup rolls back processors that already started.
- Camera, real MediaPipe model inference, and OBS/virtual-camera behavior still require target-hardware proof.

## Prior-art findings

Deep-Live-Cam demonstrates useful separation between capture, face analysis, frame processors, provider selection, and in-memory video processing. We adopt the architectural lesson but not its source code.

DeepFaceLive demonstrates the value of a live-first pipeline, but its repository is archived and GPL-3.0, making it a poor implementation base for this clean-room project.

LivePortrait is a stronger future rendering experiment because its project code is MIT. Its own license warns that bundled InsightFace detection models are non-commercial and must be replaced for a fully commercial MIT path. Its upstream documentation also warns that stock Apple-Silicon operation can be dramatically slower than high-end NVIDIA inference, so it remains a renderer experiment rather than a foundational dependency.

## Near-term sequence

1. Keep the deterministic schema/recording/lifecycle regression suite green on Linux and Apple-Silicon CI.
2. Smoke-test the optional MediaPipe package/API path in CI without bundling a model.
3. Prove zero-model webcam preview on target Apple Silicon and record baseline FPS/latency.
4. Run one authorized local Face Landmarker model and create/replay a real `.cpc` take.
5. Add a virtual-camera sink suitable for OBS.
6. Benchmark at least one lightweight live renderer and one high-quality offline renderer.
7. Freeze a production renderer only after license and target-device performance evidence exist.

## Deliberate non-goals for the foundation

- Reproducing Deep-Live-Cam's UI.
- Bundling Inswapper or InsightFace weights.
- Making cloud inference mandatory.
- Tying capture semantics to a single human-face representation.
- Treating popularity or demo quality as proof of production fitness.
