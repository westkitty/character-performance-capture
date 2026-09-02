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

The application is structured around a calm, stage-first information architecture across 5 dedicated workspaces:

### 1. Studio (Live)
The primary live performance capture, preview, and streaming hub.
* **Stage-First Dominant Viewport**: The live preview stage commands the vast majority of the screen with distraction-free presentation and zero permanent sidebar walls.
* **The Session Strip**: A compact, interactive status strip (`[ 📷 Source ] [ 👤 Character ] [ 🎯 Tracker ] [ 📹 Output ] [ ⚙ Preset ]`) positioned immediately below the stage. Clicking any pill opens the Context Inspector directly to that section.
* **Context Inspector**: A sleek ~360px contextual slide-out drawer on the right side replaces all permanent sidebars and nested scrolling columns.
* **Truthful Scoped Readiness**: Displays observable readiness states (`● Preview Ready (No Tracking)`, `● Tracking Ready (Passthrough)`, `● Ready to Perform`, or `▲ Issues (Needs Attention)`).
* **Lifecycle Transport Controls**: Single dominant **`[ ▶ Start Performing ]`** action when idle, transitioning to **`[ ● LIVE ]`**, **`[ 🎯 Recenter (Cmd+R) ]`**, and **`[ ■ Stop Session (Esc) ]`** when active.
* **Neutral Calibration / Recenter (`Cmd+R` / `C`)**: Real-time calibration button to zero out resting facial expression and head pose offsets, enabling relative performance capturing from the performer's natural neutral face.
* **Clean Preview Window / Projector (`Cmd+Shift+P`)**: Dedicated, standalone projector window for secondary monitors or OBS screen grabs. Supports Always-on-Top (`Qt.WindowStaysOnTopHint`), Fullscreen (`F11`), and HUD display modes without interrupting capture.
* **Session Presets with Dirty State**: Save, load, duplicate, rename, delete, import, and export named local presets with `• Modified` indicator.
* **Automatic Safe Filename Generator**: One-click timestamp generator creating deterministic, collision-safe filenames (e.g. `take_2026-09-02_043512.cpc`).
* **Performance Mode (`Cmd+P`)**: Distraction-free full-preview canvas view with minimal live HUD overlays and quick-stop control.
* **Dual Gain Controls**: Real-time sliders and numeric double spinboxes (`0.00x` to `3.00x`) for mouth/brow expressiveness and head pose tracking, with single-click reset (`↺`).
* **Outputs & Recording**:
  * **`.cpc` Performance Take**: Record raw facial tracking vectors and blendshape coefficients to disk.
  * **Rendered MP4 Video**: Record real-time composited character output.
  * **Virtual Camera**: Stream rendered output live into OBS Studio, Zoom, Discord, or Google Meet.

### 2. Character Setup (Guided Workflow)
Interactive 6-stage guided character onboarding and mesh visualizer workspace.
* **Progressive 6-Stage Journey**:
  1. **Character**: Prominent artwork dropzone (PNG, JPG, WebP), automatic dimension detection, loaded character card, and automatic existing rig sidecar discovery.
  2. **Tracking**: Curated model selection with pre-selected Recommended MediaPipe Face Landmarker model, 1-click user-initiated installation, and advanced path/delegate disclosure.
  3. **Build Rig**: Automatic `<character>.rig.json` sidecar calculation, progress stages ("Detecting landmarks...", "Building Delaunay mesh..."), overwrite protection, and human-friendly error guidance if no face is found.
  4. **Verify**: Dedicated visualizer canvas with toggleable Landmark Points, Mesh Triangles (wireframe), and Boundary Hull overlays, alongside a verification checklist.
  5. **Calibrate & Test**: 3-2-1 countdown neutral pose calibration setting resting face references, with motion responsiveness prompts ("Try blinking, smiling, turning head").
  6. **Ready**: Summary confirmation card and primary **`[ ▶ Start Performing in Live Studio ]`** action that seamlessly transfers all configuration directly to Live Studio.
* **Clean Top Navigation Rail**: Step indicators (`1 Character` → `2 Tracking` → `3 Build Rig` → `4 Verify` → `5 Calibrate` → `6 Ready`) with isolated verification overlays.

### 3. Takes Library
Inspect, validate, and verify `.cpc` performance capture recordings.
* **Recent-Takes-First Table**: Library table showing recent recordings with status badges, durations, frame counts, and file sizes.
* **Contextual Details Drawer**: Selected take overview card with direct "Reveal in Finder" action.
* **Collapsible Raw JSON**: Technical JSON metadata tucked behind an expandable disclosure.

### 4. Diagnostics Studio
Hardware benchmarking and subsystem validation suite (GUI equivalent of `cpc --doctor`).
* **System Health Check**: 4 high-level health cards (`Camera Ingest`, `Tracking Engine`, `Local-First Privacy`, `Output Pipeline`) initializing with truthful `— Not Checked` states before execution.
* **One-Click Execution**: `[ ⚡ Run System Health Check ]` button initiates live hardware and inference probes.
* **Collapsible Advanced Probe Settings**: Detailed benchmark configuration, sampling frames, and support copy tools located in a collapsible section.

### 5. Settings / About
* **Quiet Preferences Layout**: Clean default takes directory and session countdown configurations.
* **Tracking Models & Library**: View installable model assets, file sizes, and readiness status. "No Tracking" is treated as an operational mode, not an installed model file.
* **System & Dependency Status**: Clear status indicators for Core Engine, Desktop Studio, OpenCV, MediaPipe Adapter, and Virtual Camera Output.

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
* **Zero Network Calls**: The interface operates 100% offline with zero remote service dependencies once models are installed.
* **Performer Isolation**: `.cpc` take recordings store facial landmark coordinates and blendshapes only. Performer camera pixels are never stored in performance capture files.
