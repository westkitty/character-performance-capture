# Architecture

## Goal

Provide a local-first character-performance pipeline whose camera, tracking, rendering, and output layers can evolve independently.

## Layer contract

### 1. Frame source

Owns camera/file acquisition and resource lifecycle. It returns ordinary BGR NumPy frames. It does not know which tracker or renderer will consume them.

### 2. Performance tracker

Future layer. Converts a performer frame into compact performance state such as head pose, eye state, mouth state, expression coefficients, landmarks, or other backend-specific controls. The canonical capture format should be serializable so a performance can be replayed without the original video.

### 3. Character renderer

Future model adapter. Consumes source character/reference material plus performer state and produces a rendered frame. Renderer packages must declare their code license, model license, hardware path, expected latency, and whether commercial use is allowed.

### 4. Output sink

Preview, file recorder, or virtual-camera output. Output must not be entangled with model inference.

## Current slice

`CameraSource -> Pipeline -> PassthroughRenderer -> OpenCV preview`

This proves the application loop and lifecycle before model integration.

## Prior-art findings

Deep-Live-Cam demonstrates useful separation between capture, face analysis, frame processors, provider selection, and in-memory video processing. We adopt the architectural lesson but not its source code.

DeepFaceLive demonstrates the value of a live-first pipeline, but its repository is archived and GPL-3.0, making it a poor implementation base for this clean-room project.

LivePortrait is a stronger future rendering experiment because its project code is MIT. Its own license warns that bundled InsightFace detection models are non-commercial and must be replaced for a fully commercial MIT path. The upstream README also warns that its stock Apple-Silicon path can be dramatically slower than an RTX 4090, so it should be treated as a renderer experiment rather than a foundational dependency.

## Near-term sequence

1. Prove webcam preview on M1 and M4 hardware and record baseline FPS/latency.
2. Add a tracker interface that emits serializable performance state.
3. Add performance recording/replay before adding a generative renderer.
4. Add virtual-camera sink.
5. Benchmark at least one lightweight live renderer and one high-quality offline renderer.
6. Freeze production renderer only after license and target-device performance evidence exist.

## Deliberate non-goals for the foundation

- Reproducing Deep-Live-Cam's UI.
- Bundling Inswapper or InsightFace weights.
- Making cloud inference mandatory.
- Tying capture semantics to a single human-face representation.
- Treating popularity or demo quality as proof of production fitness.
