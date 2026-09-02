# Character Performance Capture — Desktop Studio (`cpc-ui`)

**Character Performance Capture (CPC)** includes a local-first, creator-grade desktop application built with PySide6 / Qt for Python.

The desktop studio provides full capability parity with the `cpc` command-line tool, enabling performers, animators, and technical directors to operate capture sessions, derive character rigs, inspect take records, and run hardware diagnostics without terminal commands.

---

## 1. Installation

Install the desktop interface alongside your desired tracking and output adapters:

```bash
# Core desktop studio (PySide6)
pip install "character-performance-capture[ui]"

# Full production studio (UI + MediaPipe tracking + OBS Virtual Camera)
pip install "character-performance-capture[ui,tracker-mediapipe,output-virtualcam]"
```

---

## 2. Launching the Application

Launch the desktop studio using the console script:

```bash
cpc-ui
```

Or via Python module execution:

```bash
python -m cpc.ui.app
```

---

## 3. Studio Workspaces

The application is structured into 5 dedicated creator workspaces:

### 1. Studio (Live)
The primary live performance capture and preview hub.
* **Input Source**: Select live connected cameras (with camera index, custom width/height/FPS) or video files (with looping and horizontal mirroring).
* **Performance Tracker**: Select between MediaPipe Face Landmarker (478 landmarks + 52 ARKit blendshapes) or Null benchmark tracker. Configure model path and execution delegate (`cpu` or `gpu`).
* **Renderer & Character**: Choose between 2D Rig-Warp Mesh rendering or Passthrough preview. Select character reference images and custom `.rig.json` definitions.
* **Expression & Head Gains**: Real-time gain multipliers for mouth/brow expressiveness and head pose tracking.
* **Outputs & Recording**:
  * **`.cpc` Performance Take**: Record raw facial tracking vectors and blendshape coefficients to disk.
  * **Rendered MP4 Video**: Record real-time composited character output.
  * **Virtual Camera**: Stream rendered output live into OBS Studio, Zoom, Discord, or Google Meet with selectable resolution (e.g., 1280x720, 1920x1080).
* **Live Telemetry & Preview**: Aspect-preserving preview with real-time FPS, inference latency, render latency, tracking rate, and active output badges.
* **Command Preview**: Inspect the exact equivalent CLI command string in real time and copy it to the clipboard with one click.

### 2. Character & Rig Studio
Interactive character mesh derivation and inspection workspace.
* **Reference Image Loader**: Load PNG, JPG, or WebP character artwork.
* **Automatic Rig Derivation**: Detect facial landmarks from character artwork and compute optimal Delaunay triangulation meshes.
* **Rig Sidecar Generation**: Save and export deterministic `.rig.json` definition files.
* **Interactive Wireframe Overlay**: Visual inspector displaying landmark points and convex hull boundary over character artwork.
* **One-Click Studio Promotion**: Promotes the derived character and rig directly into the Live Studio.

### 3. Takes Inspector
Inspect, validate, and verify `.cpc` performance capture recordings.
* **Header & Format Validation**: Verify schema version (`v1`), tracker identity, profile, and UTC timestamp.
* **Performance Metrics**: View frame count, total duration, effective recording FPS, and file size.
* **Completion Status**: Distinguish complete takes from partial/interrupted recordings.
* **JSON Metadata Inspection**: View and copy formatted take metadata.

### 4. Diagnostics Studio
Hardware benchmarking and subsystem validation suite (GUI equivalent of `cpc --doctor`).
* **Sensor Probe**: Validate camera and video source frame rates, resolutions, and backend drivers.
* **Inference Benchmarking**: Measure real-world tracking execution latency and inference throughput.
* **Hardware & Privacy Verification**: Confirm local-first execution status and local storage isolation.
* **Export Report**: Copy or save diagnostic reports as JSON.

### 5. Settings / About
* **System Readiness Matrix**: Live dependency checklist for Core Engine, PySide6 UI, OpenCV, MediaPipe, and `pyvirtualcam`.
* **Preferences Management**: Manage and reset persistent UI window geometry and default settings.
* **Architecture & Privacy Contract**: Detailed statement on zero-telemetry, clean-room design, and performer privacy.

---

## 4. Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Space` | Start / Stop Live Capture Session (when not editing text) |
| `Esc` | Stop Active Live Capture Session |
| `Cmd+,` / `Ctrl+,` | Open Settings / About |

---

## 5. Local-First Privacy Contract

The CPC Desktop Interface adheres to strict privacy and data isolation standards:
* **Zero Telemetry**: No analytics, telemetry, crash reporters, or external tracking pings.
* **Zero Network Calls**: The interface operates 100% offline with zero remote service dependencies.
* **Performer Isolation**: `.cpc` take recordings store facial landmark coordinates and blendshapes only. Performer camera pixels are never stored in performance capture files.
