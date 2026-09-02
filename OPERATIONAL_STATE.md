# Operational State: Character Performance Capture

<!-- operational-state:metadata
{
  "schema_version": 1,
  "project_id": "character-performance-capture",
  "project_name": "Character Performance Capture",
  "project_root": "westkitty/character-performance-capture",
  "artifact_path": null,
  "state_revision": 10,
  "last_updated": "2026-09-02",
  "current_baseline": {
    "identity": "CPC 1.0.0 release on release-1.0.0; governance ruleset id 22061363 active on main",
    "state": "production-v1",
    "last_verified": "2026-09-02"
  },
  "scope_boundaries": [
    "Local-first webcam performance capture, modular tracking/rendering, preview/OBS output, offline capture/replay, model/license governance, repository governance, and target-hardware validation."
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

- **Primary code artifact:** `release-1.0.0` (promoted to `1.0.0` after complete physical hardware validation).
- **Repository governance artifact:** active `main` ruleset id `22061363`.
- **Baseline state:** `production-v1` (CPC `1.0.0`).
- **Source/build/install identity:** strict portable `PerformanceFrame`; tracker→performance→renderer pipeline; hardened `.cpc` record/replay; optional MediaPipe Face Landmarker adapter (CPU delegate default, `>=0.10.35,<0.11`); `VideoFileSource` frame source; `RigWarpRenderer` deterministic 2D landmark-driven character renderer with relative head pose calibration and authored/derived rig sidecar contract; optional `VirtualCameraSink` (`pyvirtualcam`, OBS backend); coherent grouped CLI (`cpc --help`); mp4 rendered-preview recorder; local-only `--doctor`; 77 regression tests; explicit proprietary licensing; stable aggregate `required-ci`; enforced `main` ruleset.
- **Verified deterministic route:** schema, record/replay integrity, no-overwrite finalization, pipeline lifecycle/restart, diagnostic report logic and cleanup, geometry (similarity transform / clamping / matrix-to-euler / triangulation / warp), rig load+validation, rig-warp renderer safe-degradation and reactivity, relative head rotation calibration, `VideoFileSource` lifecycle, `VirtualCameraSink` negotiation/letterbox/absent-backend error, CLI wiring, Linux/macOS install, Ruff, pytest, MediaPipe package/API smoke, aggregate CI-gate behavior.
- **Physical validation executed on target hardware (Apple Silicon M1, macOS 26.6.2, AVFOUNDATION):**
  - Physical camera doctor: opened index 0, 1920x1080 @ 30 FPS, 30.64 sampled FPS, zero camera pixels persisted (VER-019).
  - Real MediaPipe inference on live webcam: 107/120 frames tracked (~89.2% rate), 14.57 ms/frame avg processing latency (VER-020).
  - Live character renderer pipeline: 150 reactive rendered frames (640x512) driven by live facial expression and calibrated relative head rotation without showing performer face pixels (VER-021).
  - Real webcam `.cpc` recording & inspection: 150 frames, 10.035s duration, strictly portable schema without camera pixels (VER-022).
  - Virtual camera send & receive proof: OBS Virtual Camera 1280x720 stream received by external consumer at 30.29 FPS without buffer mismatch or drift (VER-023).
- **Prior verification evidence:** GitHub Actions runs `33579448271`, `33583264952`, `33583412212` — Ubuntu/macOS core, MediaPipe smoke, and `required-ci` all green.

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

## 6. Known Not Working

No unresolved deterministic or physical defects remain in CPC 1.0.0.

- **GOV-001 — RESOLVED at revision 9:** Ruleset id `22061363` active and enforced.
- **PHY-001 — RESOLVED at revision 10:** Physical webcam capture, MediaPipe inference, character rendering, `.cpc` capture, and virtual-camera consumer receive are fully verified.

## 7. Implemented but Unverified

All core, physical, and virtual-camera paths are verified.

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
- **DEC-011:** Repository source is proprietary / all rights reserved unless the project owner explicitly selects a different license.
- **DEC-012:** `required-ci` is the stable aggregate status-check name for repository enforcement.
- **DEC-013:** Do not claim branch protection or required checks are enforced until GitHub reports the rule/ruleset as active. *(satisfied — ruleset `22061363`.)*
- **DEC-014:** `VideoFileSource` is a first-class frame source; the `--video` route is the canonical way to exercise the full pipeline where a live camera is unavailable.
- **DEC-015:** `RigWarpRenderer` is the frozen v1 default renderer — deterministic, OpenCV-only, no model weights. Characters carry a rig sidecar in MediaPipe 478 topology (authored or `--derive-rig`). Arbitrary-image generative animation is explicitly out of scope for v1.
- **DEC-016:** MediaPipe is pinned `>=0.10.35,<0.11` with the CPU delegate default; `1.0.x` aborts on headless macOS.
- **DEC-017:** `pyvirtualcam` (`output-virtualcam` extra) is the virtual-camera backend; core has no hard dependency on it. Rendered frames are letter-boxed into a backend-accepted resolution.

## 11. Validation and Evidence Matrix

| ID | Claim or behavior | State | Evidence | Validation method | Artifact/revision | Last checked | Recheck trigger |
|---|---|---|---|---|---|---|---|
| INV-009 | Recorder never overwrites final destination | verified | Race regression passes after no-replace finalization | `tests/test_recording.py` + CI | code 3a67449 / rev 8 | 2026-09-01 | Recorder finalization change |
| INV-010 | Doctor does not persist camera pixels | verified | Diagnostic source has no frame-write path; tests and physical runs confirm zero frame persistence | Source inspection + doctor runs | code rev 10 | 2026-09-02 | Diagnostics/output change |
| INV-011 | Public visibility is not an open-source grant | verified | Top-level proprietary `LICENSE` and README notice present | Repository file inspection | governance 6b7c565 / rev 8 | 2026-09-01 | License change |
| VER-001 | Strict PerformanceFrame semantics | verified | Expanded schema tests pass | `tests/test_performance.py` | code 3a67449 / rev 8 | 2026-09-01 | Schema/parser change |
| VER-003 | Record/replay integrity | verified | Happy, partial, race, trailing-record and footer tests pass | `tests/test_recording.py` | code 3a67449 / rev 8 | 2026-09-01 | Capture-format change |
| VER-005 | Pipeline restart/startup rollback | verified | Dedicated lifecycle regressions pass | pipeline test files | code 3a67449 / rev 8 | 2026-09-01 | Lifecycle change |
| VER-006 | 26-test deterministic suite | verified | Actions run 33579448271 | pytest | governance 6b7c565 / rev 8 | 2026-09-01 | Source/dependency/workflow change |
| VER-007 | Linux + macOS lint/test | verified | Both core jobs successful | GitHub Actions | governance 6b7c565 / rev 8 | 2026-09-01 | Workflow/source/dependency change |
| VER-008 | MediaPipe package/API smoke | verified | install + API check + adapter smoke successful | GitHub Actions MediaPipe job | governance 6b7c565 / rev 8 | 2026-09-01 | MediaPipe range/API/adapter change |
| VER-010 | Diagnostic harness logic | verified | Diagnostic regressions pass | `tests/test_diagnostics.py` + source inspection | code rev 10 | 2026-09-02 | Camera/diagnostics/CLI change |
| VER-012 | Stable aggregate CI gate | verified | `required-ci` completed successfully | GitHub Actions runs | governance rev 9 | 2026-09-01 | Workflow change |
| VER-018 | `main` ruleset enforcement | verified | Branch reports ruleset id 22061363 active with strict checks | GitHub API | rev 9 | 2026-09-01 | Ruleset activation |
| VER-019 | Physical camera doctor | verified | `cpc --doctor --camera 0` opened 1080p @ 30.64 FPS | Target M1 execution | rev 10 | 2026-09-02 | Camera/runtime change |
| VER-020 | Physical MediaPipe webcam tracking | verified | 107/120 frames tracked at 14.57 ms/frame avg | Target M1 execution | rev 10 | 2026-09-02 | Tracker/model change |
| VER-021 | Live webcam character pipeline | verified | 150 reactive rendered frames reacting to expression/head | Target M1 execution | rev 10 | 2026-09-02 | Renderer change |
| VER-022 | Real webcam `.cpc` take validation | verified | 150 frames, 10.035s, complete portable schema | Target M1 execution | rev 10 | 2026-09-02 | Capture change |
| VER-023 | Virtual camera consumer receive proof | verified | 60 frames consumed at 1280x720 @ 30.29 FPS | Target M1 execution | rev 10 | 2026-09-02 | Virtual camera change |
| VER-024 | Expanded 77-test regression suite | verified | 77 passing tests in 0.49s | pytest + Ruff | rev 10 | 2026-09-02 | Test change |

## 12. Current Change Scope and Impact Radius

- **Allowed to change next:** Optional multi-threaded pipeline optimization (PND-008) for higher live FPS; optional offline generative renderers behind the existing seam.
- **Must remain unchanged:** clean-room, local-first, media/model exclusion, license isolation, performance portability, strict capture integrity, no-overwrite recording, diagnostic privacy, repository-rights clarity, and pluggable-pipeline invariants.
- **Mandatory next checks:** retain the 77-test regression suite, Ruff, Linux/macOS CI, MediaPipe smoke, and `required-ci`.

## 13. Compact Revision Log

### Revision 10 — 2026-09-02

- **Artifact/source identity:** CPC `1.0.0` on `release-1.0.0` (promoted from `1.0.0rc1`).
- **Physical validation results (Apple Silicon M1, macOS 26.6.2):**
  - VER-019: Real AVFoundation webcam doctor (1080p @ 30.64 FPS, 32.55 ms avg read latency, clean exit, zero pixel persistence).
  - VER-020: Real MediaPipe tracking on webcam (107/120 frames tracked, 14.57 ms avg tracker processing latency, CPU delegate).
  - VER-021: Live character renderer on webcam (150 reactive rendered frames, expression and relative head pose driving cartoon character, character identity preserved).
  - VER-022: Real webcam `.cpc` take recording & inspection (150 frames, 10.035s duration, portable schema with blendshapes, Tait-Bryan head rotation, landmarks, no camera pixels).
  - VER-023: Virtual-camera consumer receive proof (OBS Virtual Camera 1280x720 stream received by external consumer at 30.29 FPS across 60 frames without buffer mismatch or drift).
  - VER-024: Added relative head rotation calibration against neutral frame; added early HighGUI window creation on macOS to protect MediaPipe GL/Metal context; expanded test suite from 69 to 77 passing tests.
- **Version & Governance:** `pyproject.toml` bumped from `1.0.0rc1` to `1.0.0`; all physical validation gaps closed; `main` ruleset id `22061363` active and enforced.

### Revision 9 — 2026-09-01

- **Artifact/source identity:** `main` @ `a5ea38ab939cc84f70e5160a09400a78e3442865` (PR #2 squash merge, CI green); governance ruleset id `22061363` active on `main`.
- **State deltas:** Added `VideoFileSource`; `RigWarpRenderer` (deterministic 2D landmark-driven character renderer) + `cpc/geometry.py` + `cpc/rig.py` with an authored/derived rig-sidecar contract; `--derive-rig`; `VirtualCameraSink` (optional `pyvirtualcam`, OBS backend) + `output-virtualcam` extra; grouped/legible CLI with `--video/--loop/--render/--character/--rig/--tracker-delegate/--virtual-camera/--vcam-size/--record-video/--no-window/--frames`; pinned `mediapipe>=0.10.35,<0.11` (CPU delegate default); version `0.2.0` → `1.0.0rc1`; 26 → 69 regression tests; new `docs/RENDERER.md`; refreshed README / ARCHITECTURE / HARDWARE_VALIDATION / REPOSITORY_GOVERNANCE; `.gitignore` ignores `*.rig.json`.
- **New real evidence (this M1, video frame source):** VER-014 real MediaPipe doctor (108/120 tracked, 13.3 ms/frame); VER-015 rig-warp renderer produced 150 unique reactive frames with identity preserved; VER-016 real `.cpc` take (150 frames complete) + interrupted `.partial` recovery (104 frames) with no overwrite; VER-017 virtual-camera send side (1280x720 negotiated, 240 frames, clean close, RSS ~212 MB flat); VER-018 `main` ruleset active with five rules independently observable.
- **Model/asset handling:** Google-hosted Apache-2.0 `face_landmarker.task` fetched to `~/.cache/cpc-validation/` outside the repo, not committed. Validation clip, cartoon character, rig sidecar, `.cpc` takes, and rendered mp4 all kept out of Git.
- **Blocked:** live **webcam** capture — `cv2.VideoCapture(0)` returns "not authorized to capture video"; granting macOS camera permission needs a human. Receive-side virtual-camera confirmation needs OBS/another app (GUI).
- **Validation not performed:** real webcam doctor, webcam live character route, virtual-camera consumer readback.

### Revision 8 — 2026-09-01

- **Artifact/source identity:** code `3a67449a837835dd97940df649fb446e671ca010`; governance commit `6b7c5652f1989d3325cc82a46e87a00978e6bc72`.
- **State deltas:** Replaced public-repository license ambiguity with an explicit proprietary/all-rights-reserved `LICENSE`; updated README licensing/governance text; added `docs/REPOSITORY_GOVERNANCE.md`; added stable aggregate CI job `required-ci`; opened GitHub issue #1 for the remaining repository-settings enforcement step.
- **New evidence:** GitHub Actions run `33579448271` completed successfully. Ubuntu and macOS core jobs passed install, Ruff, and all 26 tests; MediaPipe smoke passed; `required-ci` completed successfully after all prerequisite lanes.
- **Blocked:** The active GitHub connector can read branch protection/rulesets but exposes no write action for those settings, so `main` remains unprotected. The repository now has the exact check name and ruleset contract needed for manual/settings-capable activation.
- **Validation not performed:** Real target webcam, real Face Landmarker `.task` inference, OBS/virtual-camera output, renderer quality, and target-device throughput remain unverified.

### Revision 7 — 2026-09-01

- **Artifact/source identity:** README commit `cae9e548b2934b32b9895564fb5c03d67914b3e1`; implementation commit `3a67449a837835dd97940df649fb446e671ca010`.
- **State deltas:** Added local-only hardware/tracker diagnostics, camera backend/negotiated-property reporting, a reproducible target-hardware validation document, and four diagnostic regressions; expanded deterministic suite from 22 to 26 tests.
- **New evidence:** GitHub Actions run `33579062918` completed successfully. Ubuntu and macOS core jobs passed install, Ruff, and all 26 tests; MediaPipe smoke passed install, API-surface verification, and adapter smoke testing.
- **Validation not performed:** No real target webcam was opened by this environment, no real Face Landmarker `.task` model was exercised, and OBS/renderer routes remain unverified.
- **Next decisive evidence:** JSON output from the camera-only doctor run, followed by the same doctor route with an authorized local MediaPipe model.

### Revision 6 — 2026-09-01

- **Artifact/source identity:** code `2a60851b8963792118bbde2f4bbd9440ac4ddbd5`.
- **State deltas:** Closed all six revision-5 deterministic defects plus the newly discovered startup-rollback defect; refreshed stale docs; expanded CI to Linux/macOS plus optional MediaPipe smoke; promoted deterministic core back to partially verified.
- **New evidence:** Actions run `33578318932` completed successfully with 22 tests in the final suite.
- **Remaining uncertainty:** real webcam route, real Face Landmarker model inference, target-device performance, OBS output, and character rendering remained unverified.

### Revision 5 — 2026-09-01

- **Artifact/source identity:** code baseline `4568a9a57a085235307de5914be2bdb1d72ac193`.
- **State deltas:** Verification downgraded the baseline to known-broken after six independent regression fixtures exposed defects outside the original green CI suite.
- **New evidence:** Included a demonstrated final-path overwrite and malformed-capture/lifecycle failures.

### Revision 4 — 2026-09-01

- **Artifact/source identity:** code `1bc4db3cce45697b88a11ac2462293473de0f256`.
- **State deltas:** Original v0.2 CI lint/test checks became green.

### Revision 3 — 2026-09-01

- **Artifact/source identity:** code `2444f60b133ba151bddbf2bfc89fc508593c5e88`.
- **State deltas:** Added portable performance schema, `.cpc` capture/replay, optional MediaPipe adapter, CLI recording/inspection, format docs, and expanded tests.

### Revision 2 — 2026-09-01

- **Artifact/source identity:** `fe1675dd18b1165a013e1b76fb330d3a2edeec4a`.
- **State deltas:** Foundation source, tests, CI, and architecture decisions committed.

### Revision 1 — 2026-09-01

- **Artifact/source identity:** `initial-empty-repository`.
- **State deltas:** Initialized operational state and project invariants before implementation.