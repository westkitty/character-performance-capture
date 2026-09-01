# Operational State: Character Performance Capture

<!-- operational-state:metadata
{
  "schema_version": 1,
  "project_id": "character-performance-capture",
  "project_name": "Character Performance Capture",
  "project_root": "westkitty/character-performance-capture",
  "artifact_path": null,
  "state_revision": 4,
  "last_updated": "2026-09-01",
  "current_baseline": {
    "identity": "1bc4db3cce45697b88a11ac2462293473de0f256",
    "state": "partially-verified",
    "last_verified": "2026-09-01"
  },
  "scope_boundaries": [
    "Local-first webcam performance capture, modular tracking/rendering, preview/OBS output, offline capture/replay, and model/license governance."
  ],
  "linked_parent_state": null
}
-->

## 1. Project Identity and Scope

- **Project ID:** `character-performance-capture`
- **Purpose:** Build a local-first character-performance-capture system that can drive approved fictional or owned character references from a live performer without binding the product to one face-swap model.
- **Project type:** Python / macOS Apple Silicon local media tooling.
- **Primary root or artifact:** `westkitty/character-performance-capture`
- **Target environment:** macOS Apple Silicon first; portable seams for later Windows/Linux support.
- **Canonical authority:** This repository plus the newest explicit user instruction.
- **Governed scope:** Camera ingest, performance tracking, character rendering, preview/output sinks, recording/replay, model adapters, performance telemetry, and dependency/model licensing.
- **Explicitly not governed:** Big Mac FaceTools / FaceFusion installation, user media libraries, generated character assets, or unrelated webcam/deepfake tooling.

## 2. Current Baseline

- **Primary artifact:** code commit `1bc4db3cce45697b88a11ac2462293473de0f256`
- **Baseline state:** `partially-verified`
- **Source/build/install identity:** CPC v0.2.0 with portable `PerformanceFrame`, tracker/renderer pipeline, crash-tolerant `.cpc` recording/replay, optional MediaPipe Face Landmarker adapter, CLI recording/inspection, and expanded tests.
- **Active default user route:** `cpc --camera 0` remains the intended zero-model preview route; not yet runtime-verified on target Mac hardware.
- **Delivery state:** v0.2 source and CI lint repairs are committed to `main`.
- **Last verified baseline:** GitHub Actions run 33556559459 succeeded on 2026-09-01 after install, Ruff, and pytest all passed. Local container tests previously produced 11 passing tests and a successful `compileall` pass.

## 3. Artifact Contract

The project is a clean-room implementation with a testable headless core. The principal seam is webcam/video -> tracker -> portable `PerformanceFrame` -> renderer -> output. `.cpc` files store performer-state data, not camera pixels. Model-specific code remains behind optional adapters. No user media or heavyweight model weights are committed to Git.

## 4. Active Invariants

- **INV-001 — Clean-room boundary:** Do not copy source code from Deep-Live-Cam, DeepFaceLive, or other copyleft prior art into this repository. Architectural concepts may be independently reimplemented.
- **INV-002 — Local-first:** Core capture/render workflows must not require uploading frames, reference images, or performance data to a remote service.
- **INV-003 — Media/model exclusion:** User recordings, reference portraits, generated characters, downloaded model weights, caches, and secrets must remain outside Git.
- **INV-004 — Commercial-path licensing:** A renderer/tracker cannot be marked production/commercial-ready while it depends on a model restricted to non-commercial research use.
- **INV-005 — Pluggable pipeline:** Capture, tracking, rendering, and output must remain separable so a model can be replaced without rebuilding the entire app.
- **INV-006 — Testable core:** Camera hardware and GUI state must not be required to unit-test core frame transformation, performance serialization, recording/replay, and lifecycle behavior.
- **INV-007 — Authorized character use:** The product is designed around owned, licensed, fictional, or otherwise authorized character/reference material; deceptive real-person impersonation is not a product requirement.
- **INV-008 — Performance portability:** Recorded takes must preserve renderer-independent performer state and must not silently store renderer-specific latent tensors as the canonical performance format.

## 5. Verified Working Behavior

- **VER-001:** `PerformanceFrame` serialization round-trips named blendshapes, landmarks, gaze/head fields, transforms, tracker/profile identity, and metadata while rejecting invalid normalized coefficients and malformed transforms.
- **VER-002:** `PerformancePipeline` passes tracker state into the renderer and enforces tracker-start -> renderer-start -> track -> render -> renderer-close -> tracker-close lifecycle ordering in the tested path.
- **VER-003:** `PerformanceRecorder` writes finalized `.cpc` captures without overwriting an existing capture, `PerformanceReplay` reproduces recorded frames, and interrupted recording leaves a readable `.cpc.partial` instead of replacing the intended final file.
- **VER-004:** The repository's v0.2 pure-data/lifecycle suite passed locally: 11 tests, 0 failures. `python3 -m compileall -q src tests` also passed.
- **VER-005:** GitHub Actions run `33556559459` for commit `1bc4db3cce45697b88a11ac2462293473de0f256` completed successfully: dependency installation passed, `ruff check src tests` passed, and `pytest` passed under Python 3.11 on Ubuntu.

## 6. Known Not Working

None confirmed on target hardware yet. Absence of target-hardware failures is not evidence that live paths work.

## 7. Implemented but Unverified

- **UNV-001:** OpenCV `CameraSource` with explicit open/read/close lifecycle.
- **UNV-002:** Existing frame-only utility `Pipeline` and passthrough processor path.
- **UNV-003:** Live FPS / processing-latency / tracking-status overlay.
- **UNV-004:** CLI preview route via `cpc --camera 0`, with optional mirror/size/FPS arguments.
- **UNV-005:** Optional MediaPipe Face Landmarker adapter using a caller-supplied local model asset; no model is bundled or auto-downloaded.
- **UNV-006:** Live `--record-performance` path combining webcam capture, tracker, renderer, and recorder.

## 8. Unknown or Evidence-Stale State

- **UNK-001:** Actual webcam throughput on the M1 MacBook Air is unknown.
- **UNK-002:** Actual webcam/tracker throughput on the M4 Big Mac is unknown.
- **UNK-003:** OBS virtual-camera availability and latency on the target Macs are unknown.
- **UNK-004:** Best production renderer is not frozen. LivePortrait remains only a candidate pending dependency/model-license replacement and benchmark evidence.
- **UNK-005:** Actual MediaPipe Face Landmarker model inference with a chosen `.task` asset has not been run in this project.

## 9. Pending Work

- **PND-001:** Run zero-model preview on target Apple Silicon and record camera-only FPS/latency.
- **PND-002:** Run the optional MediaPipe adapter with an explicitly chosen local Face Landmarker asset and capture a real `.cpc` take.
- **PND-003:** Add optional virtual-camera output suitable for OBS.
- **PND-004:** Prototype a character renderer without importing restricted model licensing into the core.
- **PND-005:** Benchmark M1 and M4 Apple Silicon paths before choosing a live renderer.

## 10. Active Decisions, Defaults, and Prohibitions

- **DEC-001:** `westkitty/character-performance-capture` is the implementation repository.
- **DEC-002:** Deep-Live-Cam is prior art, not the project base or fork.
- **DEC-003:** Do not make InsightFace/Inswapper a required dependency.
- **DEC-004:** Prefer a small Python headless core before committing to a desktop UI framework.
- **DEC-005:** Keep this project distinct from Big Mac FaceTools/FaceFusion.
- **DEC-006:** Performance capture/replay precedes production renderer selection.
- **DEC-007:** `.cpc` format v1 is UTF-8 JSON Lines with header, frame records, and a clean end record; interrupted recordings remain as recoverable `.partial` files and completed recordings are atomically renamed into place.
- **DEC-008:** Named normalized blendshapes plus optional landmarks/gaze/head/4x4 transform form the portable performance contract; tracker-specific coefficient naming is identified by `profile`.
- **DEC-009:** MediaPipe is an optional tracker experiment only. Its Python package is not a core dependency, and CPC does not redistribute or auto-download its model asset.

## 11. Validation and Evidence Matrix

| ID | Claim or behavior | State | Evidence | Validation method | Artifact/revision | Last checked | Recheck trigger |
|---|---|---|---|---|---|---|---|
| INV-001 | Clean-room boundary | partially-verified | Independently authored source and isolated optional adapter | Source/dependency provenance review | rev 4 | 2026-09-01 | Any external-code import |
| INV-002 | Local-first core | partially-verified | Core and recorder perform local file/memory operations only | Target network-free runtime test | rev 4 | 2026-09-01 | First real model/render integration |
| VER-001 | Performance schema round-trip | verified | Local pytest + green repository CI | `tests/test_performance.py` | v0.2 / rev 4 | 2026-09-01 | Schema change |
| VER-002 | Tracker -> renderer lifecycle | verified | Local pytest + green repository CI | `tests/test_performance_pipeline.py` | v0.2 / rev 4 | 2026-09-01 | Pipeline change |
| VER-003 | Record/replay + partial recovery | verified | Local pytest + green repository CI | `tests/test_recording.py` | v0.2 / rev 4 | 2026-09-01 | Capture-format change |
| VER-004 | Local test suite / compile | verified | Container: 11 passed; compileall passed | `pytest`; `compileall` | v0.2 / rev 4 | 2026-09-01 | Source/test change |
| VER-005 | Repository CI | verified | Actions run 33556559459: install/Ruff/pytest passed | GitHub Actions | commit 1bc4db3 / rev 4 | 2026-09-01 | Source/workflow/dependency change |
| UNV-004 | Webcam preview | implemented-unverified | Source committed | Launch on target Mac with webcam | v0.2 / rev 4 | 2026-09-01 | Capture/UI change |
| UNV-005 | MediaPipe tracking | implemented-unverified | Adapter source committed; missing-model failure test passed | Real model + webcam test | v0.2 / rev 4 | 2026-09-01 | Adapter/model change |

## 12. Current Change Scope and Impact Radius

- **Allowed to change next:** Output sink/virtual camera, target-hardware benchmark harness, and bounded tracker integration fixes revealed by real hardware proof.
- **Must remain unchanged:** Clean-room, local-first, license, media-exclusion, performance-portability, no-overwrite recording, and pluggable-pipeline invariants.
- **Potentially affected behavior:** Live preview/recording and output delivery; portable capture format should remain stable unless a versioned migration is explicitly justified.
- **Mandatory checks:** Existing 11-test regression suite, Ruff, target-Mac preview, real tracker capture/replay, and output-sink validation for the next phase.
- **Checks deliberately reused:** v0.2 data/lifecycle and CI evidence remain valid until affected source or dependency configuration changes.
- **Repair class:** Bounded feature expansion.

## 13. Compact Revision Log

### Revision 4 — 2026-09-01

- **Artifact/source identity:** code commit `1bc4db3cce45697b88a11ac2462293473de0f256`.
- **State deltas:** Reconciled CI evidence after lint repair; promoted repository lint and test checks to verified.
- **New evidence:** Initial v0.2 CI exposed Ruff-only findings; commits `40f18e895acfc41d0030a130ef7c67f28b13771b` and `1bc4db3cce45697b88a11ac2462293473de0f256` resolved the reported findings. Actions run `33556559459` then completed successfully with install, Ruff, and pytest all passing.
- **Validation not performed:** Target-Mac webcam runtime, MediaPipe model inference, M1/M4 throughput, OBS output, and character rendering remain unverified.

### Revision 3 — 2026-09-01

- **Artifact/source identity:** code commit `2444f60b133ba151bddbf2bfc89fc508593c5e88`.
- **State deltas:** Added portable performance schema, versioned `.cpc` capture/replay, optional MediaPipe tracker adapter, live recording/inspection CLI paths, format documentation, and expanded tests.
- **New evidence:** Local execution produced 11 passing tests and a successful `compileall` pass. The code commit was present on `main`.
- **Validation not performed:** Target-Mac webcam runtime, MediaPipe model inference, M1/M4 throughput, OBS output, and completed GitHub Actions status were unverified at that revision.

### Revision 2 — 2026-09-01

- **Artifact/source identity:** commit `fe1675dd18b1165a013e1b76fb330d3a2edeec4a`
- **State deltas:** Foundation source, tests, CI, and architecture decisions committed.
- **New evidence:** GitHub accepted all foundation files; repository was no longer empty.
- **Validation not performed:** CI result, webcam runtime, OBS virtual camera, model inference, and target-Mac throughput remained unverified.

### Revision 1 — 2026-09-01

- **Artifact/source identity:** `initial-empty-repository`
- **State deltas:** Initialized operational state and project invariants before implementation.
- **New evidence:** Target repository confirmed writable and empty before initialization.
- **Validation not performed:** All runtime behavior remained pending.
