# Operational State: Character Performance Capture

<!-- operational-state:metadata
{
  "schema_version": 1,
  "project_id": "character-performance-capture",
  "project_name": "Character Performance Capture",
  "project_root": "westkitty/character-performance-capture",
  "artifact_path": null,
  "state_revision": 14,
  "last_updated": "2026-09-02",
  "current_baseline": {
    "identity": "CPC 1.1.0 with Production Creator Studio GUI (cpc-ui); Autonomous Quality-of-Life Megapass; Clean Preview Projector Window; Presets with Dirty State; Neutral Pose Recenter Calibration; Batch Takes Inspection; Actionable Fix-This Preflight Navigation; 109 automated regression tests; native Mac visual and runtime verification; ruleset 22061363 active.",
    "state": "production-v1.1",
    "last_verified": "2026-09-02"
  },
  "scope_boundaries": [
    "Local-first webcam performance capture, modular tracking/rendering, preview/OBS output, offline capture/replay, model/license governance, repository governance, target-hardware validation, and creator desktop interface."
  ],
  "linked_parent_state": null
}
-->

## 1. Project Identity and Scope

- **Project ID:** `character-performance-capture`
- **Purpose:** Build a local-first character-performance-capture system that can drive approved fictional or owned character references from a live performer without binding the product to one face-swap model.
- **Project type:** Python / macOS-first local media tooling.
- **Primary root or artifact:** `westkitty/character-performance-capture`
- **Canonical authority:** This repository plus the newest explicit user instruction.
- **Governed scope:** Camera ingest, performance tracking, portable performer state, character rendering, preview/output sinks, recording/replay, model adapters, telemetry, target-hardware diagnostics, dependency/model licensing, and repository-level CI/license governance.

## 2. Current Baseline

- **Primary code artifact:** `main` — CPC `1.0.0`; release implementation baseline `f348242b5382628a6124411d4b8abc776d9883d4` (PR #4 squash merge). Subsequent documentation/state-only commits on `main` do not alter that implementation baseline.
- **Feature branch artifact:** `feat/desktop-ui` — CPC `1.1.0` Creator Studio GUI with comprehensive Quality-of-Life megapass, Clean Preview projector window, presets with dirty state, neutral pose recentering, drag-and-drop across all panels, batch take inspection, diagnostics transfer, and 109 automated unit/regression tests.
- **Repository governance artifact:** active `main` ruleset id `22061363`.
- **Baseline state:** `production-v1.1` (CPC `1.1.0` on `feat/desktop-ui`).
- **Source/build/install identity:** strict portable `PerformanceFrame`; tracker→performance→renderer pipeline; hardened `.cpc` record/replay; optional MediaPipe Face Landmarker adapter (CPU delegate default, `>=0.10.35,<0.11`); `VideoFileSource` frame source; `RigWarpRenderer` deterministic 2D landmark-driven character renderer with relative head pose calibration and authored/derived rig sidecar contract; optional `VirtualCameraSink` (`pyvirtualcam`, OBS backend); coherent grouped CLI (`cpc --help`); mp4 rendered-preview recorder; local-only `--doctor`; 109 regression tests; explicit proprietary licensing; stable aggregate `required-ci`; enforced `main` ruleset.
- **Verified deterministic route:** schema, record/replay integrity, no-overwrite finalization, pipeline lifecycle/restart, diagnostic report logic and cleanup, geometry (similarity transform / clamping / matrix-to-euler / triangulation / warp), rig load+validation, rig-warp renderer safe-degradation and reactivity, relative head rotation calibration, `VideoFileSource` lifecycle, `VirtualCameraSink` negotiation/letterbox/absent-backend error, CLI wiring, Linux/macOS install, Ruff, pytest, MediaPipe package/API smoke, aggregate CI-gate behavior.
- **Physical validation executed on target hardware (Apple Silicon M1, macOS 26.6.2, AVFOUNDATION):**
  - Physical camera doctor: opened index 0, 1920x1080 @ 30 FPS, 30.64 sampled FPS, zero camera pixels persisted (VER-019).
  - Real MediaPipe inference on live webcam: 107/120 frames tracked (~89.2% rate), 14.57 ms/frame avg processing latency (VER-020).
  - Live character renderer pipeline: 150 reactive rendered frames (640x512) driven by live facial expression and calibrated relative head rotation without showing performer face pixels (VER-021).
  - Real webcam `.cpc` recording & inspection: 150 frames, 10.035s duration, strictly portable schema without camera pixels (VER-022).
  - Virtual camera send & receive proof: OBS Virtual Camera 1280x720 stream received by external consumer at 30.29 FPS without buffer mismatch or drift (VER-023).
- **Prior verification evidence:** GitHub Actions release run `33598377667` on `main` (PR #4 merge commit `f348242b5382628a6124411d4b8abc776d9883d4`) — Ubuntu core, macOS core, MediaPipe smoke, and `required-ci` all successful; earlier runs `33579448271`, `33583264952`, `33583412212` green.

## 3. Artifact Contract

The project is a clean-room implementation with a testable headless core. The principal seam is webcam/video -> tracker -> portable `PerformanceFrame` -> renderer -> output. `.cpc` files store performer-state data, not camera pixels. `cpc --doctor` may sample live frames transiently for measurement but does not persist camera pixels. Model-specific code remains behind optional adapters. User media, captures, model weights, caches, and secrets remain outside Git.

## 4. Active Invariants

- **INV-001 — Clean-room boundary:** Do not copy source code from Deep-Live-Cam, DeepFaceLive, or other copyleft prior art into this repository.
- **INV-002 — Local-first:** Core capture/render/diagnostic workflows must not require uploading frames, references, or performance data to a remote service.
- **INV-003 — Media/model exclusion:** User recordings, references, outputs, downloaded model weights, caches, and secrets remain outside Git.
- **INV-004 — Commercial-path licensing:** A backend is not production/commercial-ready while code or model licensing forbids the intended use.
- **INV-005 — Pluggable pipeline:** Capture, tracking, portable state, rendering, and output remain separable.
- **INV-006 — Testable core:** Hardware/GUI access is not required to unit-test deterministic schema, recording/replay, lifecycle, and diagnostic-report behavior.
- **INV-007 — Authorized character use:** The product targets owned, licensed, fictional, or otherwise authorized character/reference material.
- **INV-008 — Performance portability:** Canonical takes store renderer-independent performer state rather than renderer-specific latent tensors.
- **INV-009 — No-overwrite capture:** Recording finalization must never overwrite an independently existing final destination.
- **INV-010 — Diagnostic privacy:** Hardware diagnostics may inspect live frames in memory but must not persist camera pixels, auto-download models, or require a network service.
- **INV-011 — Repository rights clarity:** Public repository visibility must not be represented as an open-source license grant unless the project owner explicitly changes the top-level license.
- **INV-012 — Enforcement honesty:** CI may be described as required only after GitHub reports an active branch rule/ruleset enforcing the stable `required-ci` status check.

## 5. Verified Working Behavior

- **VER-001 — Strict portable schema:** Valid `PerformanceFrame` records round-trip; semantic type confusion such as string booleans, boolean indexes, string coefficients, and non-numeric landmark coordinates is rejected.
- **VER-002 — Performance pipeline lifecycle:** Tracker state reaches the renderer; startup/close ordering is covered; restarting begins a fresh frame-index/FPS session.
- **VER-003 — Hardened `.cpc` record/replay:** Normal finalized captures replay; interrupted/aborted recordings preserve recoverable partial evidence; existing destination paths are not overwritten, including the race where a destination appears after recording starts.
- **VER-004 — Capture integrity validation:** Readers reject records after an end record, non-monotonic frame state, inconsistent footer counts, and invalid/non-finite/negative/inconsistent footer duration.
- **VER-005 — Base pipeline lifecycle:** Restart resets metrics/index and failed multi-processor startup rolls back already-started processors.
- **VER-006 — Expanded regression suite:** 26 tests pass on both Linux and macOS CI lanes.
- **VER-007 — Repository quality gate:** Ruff and pytest pass on both Ubuntu and macOS.
- **VER-008 — MediaPipe dependency/API smoke:** The optional MediaPipe dependency installs on the macOS CI runner, `mediapipe.tasks.vision` is present, and `tests/test_mediapipe_tracker.py` passes. This does not prove real `.task` inference.
- **VER-009 — Documentation alignment:** Architecture, performance-capture, README, hardware-validation, and repository-governance docs describe the implemented v0.2 seams and current evidence boundary.
- **VER-010 — Diagnostic harness logic:** Tests verify hardware-report construction, active-backend/property reporting through `CameraSource.info()`, tracker/camera cleanup on failure, sample-count validation, privacy flags, and requested-versus-reported camera metadata handling. `probe_runtime` now also accepts any pre-built frame source (camera or `VideoFileSource`).
- **VER-011 — Explicit repository license:** A top-level `LICENSE` states the repository is proprietary / all rights reserved and that public visibility is not an open-source grant.
- **VER-012 — Stable aggregate CI gate:** GitHub Actions run `33579448271` completed with `required-ci` successful after the Linux, macOS, and MediaPipe lanes.
- **VER-013 — Renderer / geometry / rig determinism:** 43 regression tests. `test_geometry.py` proves the similarity transform recovers a known scale/rotation/translation, clamping bounds pathological (`inf`/`nan`/`1e30`) input, Delaunay indices are valid, and the warp is identity when src==dst. `test_rig.py` round-trips a rig and rejects nine malformed shapes. `test_renderer.py` proves untracked / low-confidence / short-landmark / wild-geometry frames degrade safely to the reference, a shifted mesh visibly changes the output while staying finite/uint8, and `close()` is idempotent and restartable. `test_video_source.py` and `test_virtualcam.py` cover the new source/sink lifecycles. `test_app_cli.py` covers CLI wiring.
- **VER-014 — Real MediaPipe inference (video frames):** `cpc --doctor --video driver.mp4 --loop --tracker mediapipe --model <apache-2.0 face_landmarker.task> --doctor-frames 120` — model loads, 120 frames reach the tracker, 108/120 tracked (0.90 rate), tracker processing 13.3 ms avg / 13.8 ms p95, cleanup succeeds. `mediapipe==1.0.1` aborts the process on this headless M1 (GPU delegate, no Metal service); `0.10.35` + CPU delegate is the validated range and is now pinned.
- **VER-015 — Rig-warp renderer live proof (video frames):** `cpc --video driver.mp4 --loop --mirror --tracker mediapipe --model ... --render rig --character cartoon.png --record-video rendered.mp4 --frames 150` produced 150 rendered frames, all unique (mean frame-to-frame Δ up to 3.5/255), character identity preserved, reacting to head roll/yaw/pitch and expression from real tracking.
- **VER-016 — Real `.cpc` capture/replay (video frames + real tracker):** the same run recorded `validation.cpc` (150 frames, complete, 8.16 s coherent duration); frame records carry only portable state (`blendshapes`, `landmarks`, `face_transform`, …) with no pixel keys; `--inspect-performance` parses it fully. A SIGTERM mid-record left `interrupted.cpc.partial` (104 frames, "partial/recoverable"), no final file written — no-overwrite and crash-tolerance hold with the real tracker in the loop.
- **VER-017 — Virtual-camera sink end-to-end (send side):** `cpc --video driver.mp4 --loop --tracker mediapipe --model ... --render rig --character cartoon.png --virtual-camera --vcam-size 1280x720 --frames 240` opened the OBS Virtual Camera backend, negotiated 1280x720, letter-boxed and sent 240 rendered frames with no "pixel buffer size mismatch", and closed cleanly. Max RSS ~212 MB, flat across 240–300 frame soaks.
- **VER-018 — `main` ruleset enforced:** ruleset id `22061363`, `enforcement: active`. `GET /repos/westkitty/character-performance-capture/rules/branches/main` independently returns five rules: `pull_request`, `required_status_checks` (`required-ci`, strict), `non_fast_forward`, `deletion`, `required_linear_history`. Admin bypass scoped to `pull_request`.
- **VER-019 — Real AVFoundation webcam capture:** `cpc --doctor --camera 0 --doctor-frames 120` opened camera 0 via AVFOUNDATION backend, negotiated 1920x1080 @ 30 FPS, sampled 120 frames at 30.64 FPS (average read 32.55 ms), cleanly shut down with zero pixel persistence.
- **VER-020 — Real MediaPipe tracking on live webcam:** `cpc --doctor --camera 0 --tracker mediapipe --model face_landmarker.task --doctor-frames 120` tracked 107/120 frames (0.892 rate) with average tracker processing latency 14.57 ms (p95 16.17 ms, ~68.6 effective tracker FPS) on CPU delegate.
- **VER-021 — Live webcam character pipeline:** `cpc --camera 0 --mirror --tracker mediapipe --model face_landmarker.task --render rig --character cartoon.png --record-performance validation.cpc --record-video rendered.mp4 --no-window --frames 150` generated 150 unique character-rendered frames reacting to performer expressions and calibrated relative head rotation without showing performer face pixels.
- **VER-022 — Real webcam `.cpc` take validation:** Inspection of the 150-frame webcam take verified full schema validity (52 blendshapes, Tait-Bryan head rotation, 478 landmarks, 10.035s duration, coherent end record) with zero camera pixel keys.
- **VER-023 — Virtual-camera external consumer receive proof:** CPC streaming live 1280x720 character frames to OBS Virtual Camera concurrently received by an external consumer at 30.29 FPS across 60 sampled frames with continuous frame differences and zero buffer size mismatch.
- **VER-024 — Relative head rotation calibration & HighGUI macOS context fix:** Head rotation is computed relative to calibrated neutral pose so performer resting posture does not permanently deform the character; HighGUI preview window is initialized cleanly before GL/Metal context creation. Expanded test suite to 77 passing tests.
- **VER-025 — Desktop Studio GUI (`cpc-ui`):** Local-first PySide6 / Qt creator studio featuring Live Studio (webcam/video ingest, MediaPipe tracking, rig-warp render, live telemetry, `.cpc` & MP4 recording, OBS virtual camera streaming), Character & Rig derivation/visualizer, Takes Inspector, Diagnostics Studio, Settings/About readiness dashboard, 100% CLI parity registry, background QThread workers, and 98 passing unit/smoke tests.
- **VER-026 — Production Creator Studio Hardening & Verification (CPC 1.1.0):** Elevated semantic dark creator design system; full backpressure handling and display frame coalescing without dropping recording streams; explicit QImage memory buffer ownership safety; session token lifecycle tracking and multi-cycle restart proof; named session presets (save/load/export/import JSON); recent items management; distraction-free Performance Mode (`Cmd+P`) with sleek live HUD; Spotlight-style Quick Actions / Command Palette (`Cmd+K`); dismissible first-run onboarding; post-session summary drawer with Finder reveal and Takes Studio inspection; interactive wireframe visualizer with overwrite protection; 105 automated regression tests passing across all suites.
- **VER-027 — Autonomous Quality-of-Life Megapass & UX Uplift (CPC 1.1.0):** Standalone Clean Preview Projector Window (`CleanPreviewWindow`) with Always-on-Top, Fullscreen (`F11`), and HUD toggles (`Cmd+Shift+P`); Neutral Face & Head Calibration (`Cmd+R` / `C`); Actionable "Fix This" preflight navigation; Session countdown timer (3s / 5s); Safe collision-free filename generator (`generate_timestamped_filename`); Presets with dirty state tracking (`• Modified`), duplication, and renaming; Per-character memory and favorites (★); Drag-and-drop across all inputs, models, and takes; Batch multi-take inspection table; Diagnostics setup transfer; Global Panic Stop (`Escape`); 109 automated regression tests passing with clean Ruff linting.

## 6. Known Not Working

No unresolved deterministic or physical defects remain in CPC 1.0.0 / 1.1.0.

- **GOV-001 — RESOLVED at revision 9:** Ruleset id `22061363` active and enforced.
- **PHY-001 — RESOLVED at revision 10:** Physical webcam capture, MediaPipe inference, character rendering, `.cpc` capture, and virtual-camera consumer receive are fully verified.

## 7. Implemented but Unverified

All core, physical, GUI, and virtual-camera paths are verified.

- **UNV-001 — RESOLVED at revision 10:** Real webcam doctor and live character route fully verified (VER-019..VER-022).
- **UNV-002 — RESOLVED at revision 10:** Receive-side virtual-camera consumption verified with external consumer at 30.29 FPS (VER-023).
- **UNV-004..UNV-007 — RESOLVED via video & real camera sources:** real Face Landmarker inference (VER-014, VER-020), production character renderer (VER-015, VER-021), real `.cpc` capture/replay with a real tracker (VER-016, VER-022), virtual-camera output and receive (VER-017, VER-023).

## 8. Unknown or Evidence-Stale State

- **UNK-001 — RESOLVED at revision 10:** Live webcam throughput measured at 30.64 FPS (read latency 19.04-32.55 ms), tracker at 14.57 ms (~68 FPS), virtual camera consumer at 30.29 FPS.
- **UNK-002 — RESOLVED at revision 9:** MediaPipe `0.10.35` CPU delegate pinned and verified.
- **UNK-003 — RESOLVED at revision 10:** OBS Virtual Camera receive side proven at 1280x720 @ 30.29 FPS.
- **UNK-004:** High-quality offline generative renderer remains a potential post-1.0 exploration behind the same `CharacterRenderer` seam.
- **UNK-007 — RESOLVED at revision 9:** `main` ruleset active and independently observable (VER-018).

## 9. Pending Work

- **PND-001 — RESOLVED at revision 10:** Real webcam doctor executed and verified.
- **PND-002 — RESOLVED at revision 10:** Real webcam + MediaPipe executed and verified.
- **PND-005 — RESOLVED at revision 10:** Virtual camera consumer receive side executed and verified.
- **PND-006:** If public reuse is later intended, explicitly replace the proprietary license rather than assuming public visibility grants reuse rights.
- **PND-008:** Optional tracker/renderer threading for higher live FPS (post-1.0 optimization).
- **PND-009 — RESOLVED at revision 10:** Real webcam run recorded and promoted to `1.0.0`.
- **PND-010 — RESOLVED at revision 12:** Desktop studio GUI (`cpc-ui`) implemented and verified.
- **PND-011 — RESOLVED at revision 14:** Production desktop QoL megapass (Clean Preview projector, presets with dirty state, neutral pose recentering, drag-and-drop, batch inspection) implemented and verified.

## 10. Active Decisions, Defaults, and Prohibitions

- **DEC-001:** `westkitty/character-performance-capture` is the implementation repository.
- **DEC-002:** Deep-Live-Cam is prior art, not the project base or fork.
- **DEC-003:** InsightFace/Inswapper is not a required core dependency.
- **DEC-004:** Maintain a small testable Python core before committing to a desktop UI framework.
- **DEC-005:** Keep this project distinct from unrelated FaceTools/FaceFusion work.
- **DEC-006:** Performance capture/replay precedes production renderer selection.
- **DEC-007:** `.cpc` v1 is UTF-8 JSON Lines with strict header/frame/end semantics; interrupted takes remain recoverable; finalization may not replace an independently existing destination.
- **DEC-008:** Named normalized blendshapes plus optional landmarks/gaze/head/4x4 transform form the portable performance contract.
- **DEC-009:** MediaPipe remains an optional tracker adapter; CPC does not bundle or auto-download its model asset.
- **DEC-010:** `cpc --doctor` is the canonical evidence bridge for target camera/tracker measurements. It reports requested, backend-reported, and observed state separately and stores no sampled camera pixels.
- **DEC-011:** Desktop interface built in PySide6 under `src/cpc/ui/` with zero breaking changes to the headless core engine.
- **DEC-012:** Live preview rendering uses aspect-preserving QPainter with smooth transforms and non-blocking backpressure skipping to preserve 100% recording capture integrity.
- **DEC-013:** Session presets store clean serializable configuration dicts in native QSettings with export/import JSON schema versioning.
- **DEC-014:** Clean Preview Window operates as an independent projector surface that can be closed or manipulated without terminating active capture sessions.