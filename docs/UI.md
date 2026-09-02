# Character Performance Capture — Desktop Studio (`cpc-ui`)

**Character Performance Capture (CPC)** includes a local-first, creator-grade desktop application built with PySide6 / Qt for Python.

The desktop studio provides complete capability parity with the `cpc` command-line tool, enabling performers, animators, streamers, and technical directors to operate live capture sessions, manage session presets, derive character rigs, inspect take records, and run hardware diagnostics without terminal commands.

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
The primary live performance capture, preview, and streaming hub.
* **Preflight Readiness Summary & Actionable "Fix This" Navigation**: Live status verifying Source, Tracker, Character, and Output settings before launching a session. Clicking on any issue jumps directly to the offending input or opens the Character Studio.
* **Neutral Calibration / Recenter (`Cmd+R` / `C`)**: Real-time calibration button to zero out resting facial expression and head pose offsets, enabling relative performance capturing from the performer's natural neutral face.
* **Clean Preview Window / Projector (`Cmd+Shift+P`)**: Dedicated, standalone projector window for secondary monitors or OBS screen grabs. Supports Always-on-Top (`Qt.WindowStaysOnTopHint`), Fullscreen (`F11`), and HUD display modes (Full, Minimal, Hidden) without interrupting capture.
* **Session Countdown**: Optional configurable 3-second or 5-second countdown timer before live recording commences.
* **Session Presets with Dirty State**: Save, load, duplicate, rename, delete, import, and export named local presets. Indicates modified configurations with a `• Modified` indicator.
* **Automatic Safe Filename Generator**: One-click "⚡ Auto Name" timestamp generator creating deterministic, collision-safe filenames (e.g. `take_2026-09-02_043512.cpc`).
* **Performance Mode (`Cmd+P`)**: Distraction-free full-preview canvas view with minimal live HUD overlays (Active state, Rec badges, VCam status, FPS) and quick-stop control.
* **Drag-and-Drop Ingest**: Drag video files (.mp4/.mov/.avi/.mkv) or MediaPipe task models (.task) directly into the setup panels.
* **Input Source**: Select live connected cameras (with camera index, custom width/height/FPS, and rescan) or video files (with looping and horizontal mirroring).
* **Performance Tracker**: Select between MediaPipe Face Landmarker (478 landmarks + 52 ARKit blendshapes) or Null benchmark tracker. Configure model path and compute delegate (`cpu` or `gpu`).
* **Renderer & Character**: Choose between 2D Rig-Warp Mesh rendering or Passthrough preview. Select character reference images and custom `.rig.json` definitions.
* **Dual Gain Controls**: Real-time sliders and numeric double spinboxes (`0.00x` to `3.00x`) for mouth/brow expressiveness and head pose tracking, with single-click reset (`↺`).
* **Outputs & Recording**:
  * **`.cpc` Performance Take**: Record raw facial tracking vectors and blendshape coefficients to disk.
  * **Rendered MP4 Video**: Record real-time composited character output.
  * **Virtual Camera**: Stream rendered output live into OBS Studio, Zoom, Discord, or Google Meet with selectable resolution (e.g., 1280x720, 1920x1080).
* **Live Telemetry & Preview**: Aspect-preserving preview with real-time FPS, inference latency, render latency, tracking rate, and active output badges.
* **Session Summary Card**: Clean post-session summary providing total frames, duration, effective FPS, with direct "Reveal in Finder" and "Open in Takes Studio" actions.
* **Activity & Technical Details Drawer**: Non-intrusive status drawer with one-click "Copy Technical Details" for diagnostics and troubleshooting.

### 2. Character Setup (Guided Workflow)
Interactive 6-stage guided character onboarding and mesh visualizer workspace.
* **Progressive 6-Stage Journey**:
  1. **Character**: Drag & drop character artwork (PNG, JPG, WebP), automatic dimension detection, recent characters & favorites (★), and automatic existing rig sidecar discovery.
  2. **Tracking**: Curated model selection with pre-selected Recommended MediaPipe Face Landmarker model, 1-click user-initiated installation, and advanced path/delegate disclosure.
  3. **Build Rig**: Automatic `<character>.rig.json` sidecar calculation, progress stages ("Detecting landmarks...", "Building Delaunay mesh..."), overwrite protection, and human-friendly error guidance if no face is found.
  4. **Verify**: Interactive visualizer canvas with toggleable Landmark Points, Mesh Triangles (wireframe), and Boundary Hull overlays, alongside a verification checklist.
  5. **Calibrate & Test**: 3-2-1 countdown neutral pose calibration setting resting face references, with motion responsiveness prompts ("Try blinking, smiling, turning head").
  6. **Ready**: Summary confirmation card and primary **`[ ▶ Start Performing in Live Studio ]`** action that seamlessly transfers all configuration directly to Live Studio.
* **Top Navigation Rail**: Clickable step buttons (`1 Character` → `2 Tracking` → `3 Build Rig` → `4 Verify` → `5 Calibrate` → `6 Ready`) enabling easy backwards navigation to completed stages.

### 3. Takes Inspector
Inspect, validate, and verify `.cpc` performance capture recordings.
* **Single & Batch Multi-Take Inspection**: View individual take metadata or compare multiple takes in a comprehensive batch table.
* **Drag & Drop Takes**: Drag `.cpc` or `.partial` files directly into the inspector.
* **Header & Format Validation**: Verify schema version (`v1`), tracker identity, profile, and UTC timestamp.
* **Performance Metrics**: View frame count, total duration, effective recording FPS, and file size.
* **Completion Status**: Distinguish complete takes from partial/interrupted recordings.
* **JSON Metadata Export**: View, copy, and export formatted take metadata JSON files.

### 4. Diagnostics Studio
Hardware benchmarking and subsystem validation suite (GUI equivalent of `cpc --doctor`).
* **Diagnose Current Setup**: One-click transfer of active Live Studio settings into Diagnostics for immediate verification.
* **Sampling Depth Presets**: Quick (30 frames), Standard (60 frames), and Extended (180 frames) sampling benchmarks.
* **Sensor Probe**: Validate camera and video source frame rates, resolutions, and backend drivers.
* **Inference Benchmarking**: Measure real-world tracking execution latency and inference throughput.
* **Sanitized Support Info**: One-click "Copy Support Info" to clipboard for troubleshooting without exposing personal file paths.
* **Hardware & Privacy Verification**: Confirm local-first execution status and local storage isolation.

### 5. Settings / About
* **Tracking Models & Library**: View installed model assets, file sizes, and readiness status. Actions to "Reveal Models Folder in Finder", "Import Custom Model...", and "Install / Reinstall Recommended Model".
* **Dependency Installation Commands**: One-click copyable `pip install` commands for optional extras (`[tracker-mediapipe]`, `[output-virtualcam]`, and full studio).
* **Default Output Directory Preference**: Set and manage custom default save folders.
* **Default Countdown Timer**: Set default session launch delay (Immediate, 3s, 5s).
* **Reset UI Settings**: Restore all preferences and onboarding states to defaults.
* **Architecture & Privacy Contract**: Detailed statement on zero-telemetry, clean-room design, and performer privacy.

---

## 4. Keyboard Shortcuts & Quick Actions

| Shortcut | Action | Scope |
| :--- | :--- | :--- |
| `Cmd+K` / `Ctrl+K` | Open Quick Actions / Command Palette | Global |
| `Space` | Start / Stop Live Capture Session | Global (when not editing text) |
| `Cmd+R` / `Ctrl+R` | Calibrate Neutral Pose (Recenter) | Global |
| `Cmd+Shift+P` / `Ctrl+Shift+P` | Open Standalone Clean Preview Projector Window | Global |
| `Cmd+P` / `Ctrl+P` | Toggle Performance Mode (Full Canvas Preview) | Global |
| `Escape` | Panic Stop / Exit Performance Mode / Dismiss | Global |
| `Cmd+1` / `Ctrl+1` | Switch to Studio (Live) Workspace | Global |
| `Cmd+2` / `Ctrl+2` | Switch to Character & Rig Studio | Global |
| `Cmd+3` / `Ctrl+3` | Switch to Takes Inspector | Global |
| `Cmd+4` / `Ctrl+4` | Switch to Diagnostics Studio | Global |
| `Cmd+5` / `Ctrl+5` | Switch to Settings / About | Global |
| `Cmd+O` / `Ctrl+O` | Open Performer Video File | Global |
| `Cmd+Shift+O` / `Ctrl+Shift+O` | Open Character Artwork | Global |
| `Cmd+Shift+C` / `Ctrl+Shift+C` | Copy Equivalent CLI Terminal Command | Global |

---

## 5. Local-First Privacy Contract

The CPC Desktop Interface adheres to strict privacy and data isolation standards:
* **Zero Telemetry**: No analytics, telemetry, crash reporters, or external tracking pings.
* **Zero Network Calls**: The interface operates 100% offline with zero remote service dependencies.
* **Performer Isolation**: `.cpc` take recordings store facial landmark coordinates and blendshapes only. Performer camera pixels are never stored in performance capture files.
