# Operational State: Character Performance Capture

<!-- operational-state:metadata
{
  "schema_version": 1,
  "project_id": "character-performance-capture",
  "project_name": "Character Performance Capture",
  "project_root": "westkitty/character-performance-capture",
  "artifact_path": null,
  "state_revision": 5,
  "last_updated": "2026-09-01",
  "current_baseline": {
    "identity": "1bc4db3cce45697b88a11ac2462293473de0f256",
    "state": "known-broken",
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

- **Primary artifact:** code commit `1bc4db3cce45697b88a11ac2462293473de0f256`; repository head after this state update is documentation-only.
- **Baseline state:** `known-broken`.
- **Source/build/install identity:** CPC v0.2.0 with portable `PerformanceFrame`, tracker/renderer pipeline, crash-tolerant `.cpc` recording/replay, optional MediaPipe Face Landmarker adapter, CLI recording/inspection, and expanded tests.
- **Active default user route:** `cpc --camera 0` remains the intended zero-model preview route; not yet runtime-verified on target Mac hardware.
- **Delivery state:** v0.2 source is committed to `main`; existing repository CI is green, but verification found defects outside the current regression suite.
- **Last verified baseline:** GitHub Actions run `33556653108` on repository head `4568a9a57a085235307de5914be2bdb1d72ac193` succeeded after install, Ruff, and pytest all passed. A separate verification harness against Git-blob-identical current source reproduced eight failing assertions across six root-cause defects.

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
- **INV-009 — No-overwrite recording:** Finalizing a capture must never replace an independently existing final capture path.

## 5. Verified Working Behavior

- **VER-001:** For well-typed valid input, `PerformanceFrame` serialization round-trips named blendshapes, landmarks, gaze/head fields, transforms, tracker/profile identity, and metadata while rejecting invalid normalized coefficients and malformed transforms.
- **VER-002:** `PerformancePipeline` passes tracker state into the renderer and enforces tracker-start -> renderer-start -> track -> render -> renderer-close -> tracker-close lifecycle ordering in the tested single-session path.
- **VER-003:** Normal-path `PerformanceRecorder` writes a finalized `.cpc`, `PerformanceReplay` reproduces ordinary recorded frames, an exception during recording leaves a readable `.cpc.partial`, and recorder startup rejects a final path that already exists at startup. This does **not** prove race-safe no-overwrite finalization; see KNB-001.
- **VER-004:** The repository's committed regression suite contains 11 tests covering the original v0.2 pure-data/lifecycle slice.
- **VER-005:** GitHub Actions run `33556653108` for repository head `4568a9a57a085235307de5914be2bdb1d72ac193` completed successfully: dependency installation passed, `ruff check src tests` passed, and `pytest` passed under Python 3.11 on Ubuntu.
- **VER-006:** Repository scan found no tracked use of common network-client/subprocess modules or obvious embedded credential literals; `.gitignore` excludes recorded takes, media, model assets, environment files, keys, and PEM files.

## 6. Known Not Working

- **KNB-001 — HIGH — Recorder finalization can overwrite a file created after recording starts:** `PerformanceRecorder.start()` checks that the final path is absent, but `close(commit=True)` later uses `os.replace(partial, final)`. A verification test created the final path between start and close and proved that CPC silently replaced it. This violates INV-009 and the prior no-overwrite claim. Required repair: use an atomic no-replace finalization primitive on the same filesystem and add a race regression fixture.
- **KNB-002 — MEDIUM — Replay accepts trailing records after the end record:** `iter_capture_frames()` stops at the first `end` and never validates remaining records. `read_capture()` correctly rejects a frame after `end`, while `PerformanceReplay.frames()` accepts the same malformed file. Required repair: make replay use strict streamed validation and reject any nonblank record after the terminal end record.
- **KNB-003 — MEDIUM — Capture schema parsing is permissive and inconsistent:** verification proved three manifestations: non-finite footer `duration_s` is accepted; a required header field can escape as raw `KeyError` instead of `CaptureFormatError`; and `PerformanceFrame.from_dict()` converts the string `"false"` to boolean `True`. Required repair: strict field/type/schema validation, strict JSON constants, finite/nonnegative footer validation, and consistent `CaptureFormatError` wrapping for external capture parsing.
- **KNB-004 — LOW — Pipeline FPS telemetry leaks across restart boundaries:** both `Pipeline` and `PerformancePipeline` leave `_last_frame_time` populated after close/restart, so the first frame of a new session reports nonzero FPS based on the prior session. Required repair: reset session timing state on restart and add restart regression tests; explicitly decide/document whether frame indices are session-local or lifetime-continuous.
- **KNB-005 — MEDIUM — Recorder header serialization failure leaks state:** if header metadata is not JSON serializable, `PerformanceRecorder.start()` opens the `.partial` file and then raises while writing the header, leaving the file handle open and a stale partial file behind. Required repair: validate header fields before opening, or guarantee cleanup/unlink on start failure, with a regression fixture.
- **KNB-006 — LOW — `docs/ARCHITECTURE.md` is stale:** it still describes the tracker/renderer as future layers and lists tracker interface plus performance recording/replay as future work even though v0.2 implements those seams. Required repair: update the architecture/current-slice and near-term sequence to match source and README.

## 7. Implemented but Unverified

- **UNV-001:** OpenCV `CameraSource` with explicit open/read/close lifecycle on target Macs.
- **UNV-002:** Live FPS / processing-latency / tracking-status overlay on target hardware.
- **UNV-003:** CLI preview route via `cpc --camera 0`, with optional mirror/size/FPS arguments, on target hardware.
- **UNV-004:** Optional MediaPipe Face Landmarker adapter using a caller-supplied local model asset; no model is bundled or auto-downloaded.
- **UNV-005:** Live `--record-performance` path combining webcam capture, tracker, renderer, and recorder.

## 8. Unknown or Evidence-Stale State

- **UNK-001:** Actual webcam throughput on the M1 MacBook Air is unknown.
- **UNK-002:** Actual webcam/tracker throughput on the M4 Big Mac is unknown.
- **UNK-003:** OBS virtual-camera availability and latency on the target Macs are unknown.
- **UNK-004:** Best production renderer is not frozen. LivePortrait remains only a candidate pending dependency/model-license replacement and benchmark evidence.
- **UNK-005:** Actual MediaPipe Face Landmarker model inference with a chosen `.task` asset has not been run in this project.
- **UNK-006:** The optional dependency range `mediapipe>=0.10.35,<2` currently admits MediaPipe 1.0.1, including an Apple-Silicon wheel. The current Google API still documents the Face Landmarker VIDEO methods/options used by CPC, but CPC CI does not install or execute the optional MediaPipe path, so compatibility with 1.0.1 remains unverified.
- **UNK-007:** `main` is currently unprotected and does not require CI status checks before updates; whether branch protection is desired is a project-governance decision, not an established product requirement.

## 9. Pending Work

- **PND-001:** Repair KNB-001 through KNB-005 and add focused regression fixtures before promoting capture integrity/lifecycle behavior back to verified.
- **PND-002:** Update `docs/ARCHITECTURE.md` to remove v0.1-era future-work drift.
- **PND-003:** Add CI coverage for the optional MediaPipe dependency/API surface, preferably with a version strategy that does not silently absorb untested major releases.
- **PND-004:** Run zero-model preview on target Apple Silicon and record camera-only FPS/latency.
- **PND-005:** Run the optional MediaPipe adapter with an explicitly chosen local Face Landmarker asset and capture a real `.cpc` take.
- **PND-006:** Add optional virtual-camera output suitable for OBS.
- **PND-007:** Prototype a character renderer without importing restricted model licensing into the core.
- **PND-008:** Benchmark M1 and M4 Apple Silicon paths before choosing a live renderer.

## 10. Active Decisions, Defaults, and Prohibitions

- **DEC-001:** `westkitty/character-performance-capture` is the implementation repository.
- **DEC-002:** Deep-Live-Cam is prior art, not the project base or fork.
- **DEC-003:** Do not make InsightFace/Inswapper a required dependency.
- **DEC-004:** Prefer a small Python headless core before committing to a desktop UI framework.
- **DEC-005:** Keep this project distinct from Big Mac FaceTools/FaceFusion.
- **DEC-006:** Performance capture/replay precedes production renderer selection.
- **DEC-007:** `.cpc` format v1 is UTF-8 JSON Lines with header, frame records, and a clean end record; interrupted recordings remain as recoverable `.partial` files and completed recordings are atomically finalized.
- **DEC-008:** Named normalized blendshapes plus optional landmarks/gaze/head/4x4 transform form the portable performance contract; tracker-specific coefficient naming is identified by `profile`.
- **DEC-009:** MediaPipe is an optional tracker experiment only. Its Python package is not a core dependency, and CPC does not redistribute or auto-download its model asset.

## 11. Validation and Evidence Matrix

| ID | Claim or behavior | State | Evidence | Validation method | Artifact/revision | Last checked | Recheck trigger |
|---|---|---|---|---|---|---|---|
| INV-001 | Clean-room boundary | partially-verified | Independently authored source and isolated optional adapter | Source/dependency provenance review | rev 5 | 2026-09-01 | Any external-code import |
| INV-002 | Local-first core | partially-verified | Core source contains no common network client/subprocess path; frames/performance remain in process/files | Target network-observation runtime test | rev 5 | 2026-09-01 | First real model/render integration |
| INV-009 | No-overwrite recording | known-broken | Focused race fixture proved `os.replace` overwrites a final path created after recorder startup | Concurrent/final-path race fixture | v0.2 / rev 5 | 2026-09-01 | Recorder finalization change |
| VER-001 | Valid PerformanceFrame round-trip | verified | Existing pytest + green repository CI | `tests/test_performance.py` | v0.2 / rev 5 | 2026-09-01 | Schema change |
| VER-002 | Tracker -> renderer lifecycle order | verified | Existing pytest + green repository CI | `tests/test_performance_pipeline.py` | v0.2 / rev 5 | 2026-09-01 | Pipeline lifecycle change |
| VER-003 | Ordinary record/replay + partial recovery | partially-verified | Existing tests pass; race/integrity audit found adjacent defects | Existing tests plus focused audit harness | v0.2 / rev 5 | 2026-09-01 | Capture-format/finalization change |
| VER-005 | Repository CI | verified | Actions run 33556653108: install/Ruff/pytest passed | GitHub Actions | head 4568a9a / rev 5 | 2026-09-01 | Source/workflow/dependency change |
| KNB-002 | Replay terminal-record integrity | known-broken | Replay accepted trailing frame that strict reader rejects | Focused malformed-capture fixture | v0.2 / rev 5 | 2026-09-01 | Replay parser change |
| KNB-003 | Strict capture schema/error contract | known-broken | NaN footer accepted; missing header emitted KeyError; string false became true | Focused malformed-capture fixtures | v0.2 / rev 5 | 2026-09-01 | Parser/schema change |
| KNB-004 | Restart FPS telemetry | known-broken | Both pipeline classes report nonzero first-frame FPS after restart | Focused lifecycle restart fixtures | v0.2 / rev 5 | 2026-09-01 | Timing/lifecycle change |
| KNB-005 | Recorder start-failure cleanup | known-broken | Invalid metadata leaves open handle/stale partial | Focused start-failure fixture | v0.2 / rev 5 | 2026-09-01 | Recorder initialization change |
| UNV-003 | Webcam preview | implemented-unverified | Source committed | Launch on target Mac with webcam | v0.2 / rev 5 | 2026-09-01 | Capture/UI change |
| UNV-004 | MediaPipe tracking | implemented-unverified | Adapter source aligns with current documented API; no real local model run | Real model + webcam test | v0.2 / rev 5 | 2026-09-01 | Adapter/model/dependency change |

## 12. Current Change Scope and Impact Radius

- **Allowed to change next:** Bounded repairs to recording finalization, capture/replay validation, pipeline restart timing, recorder startup cleanup, architecture documentation, optional-dependency CI, then target-hardware benchmark/output work.
- **Must remain unchanged:** Clean-room, local-first, license, media-exclusion, performance-portability, no-overwrite intent, crash-recoverable partial recording, and pluggable-pipeline invariants.
- **Potentially affected behavior:** `.cpc` writer/reader/replay, restart telemetry, error behavior for malformed captures, and documentation. A format-container version bump is not justified for stricter validation that preserves existing valid v1 files.
- **Mandatory checks:** Existing 11-test regression suite plus new fixtures for final-path race protection, strict terminal record validation, strict capture types/non-finite values, recorder start cleanup, both pipeline restart paths, Ruff, CI, target-Mac preview, real tracker capture/replay, and output-sink validation when those phases begin.
- **Checks deliberately reused:** Existing CI and ordinary happy-path tests remain valid only for the narrow behaviors they actually cover; they no longer justify the broader no-overwrite/integrity claims.
- **Repair class:** Bounded integrity repair before feature expansion.

## 13. Compact Revision Log

### Revision 5 — 2026-09-01

- **Artifact/source identity:** code baseline `1bc4db3cce45697b88a11ac2462293473de0f256`; verification performed against current repository tree at head `4568a9a57a085235307de5914be2bdb1d72ac193` before this state-only update.
- **State deltas:** Repository verification demoted the baseline from partially verified to known-broken for capture integrity/lifecycle correctness; added six confirmed defects and three major coverage/governance unknowns; narrowed prior VER-003 claims to what existing tests actually prove.
- **New evidence:** Current-head Actions run `33556653108` is green. A separate focused harness executed against Git-blob-identical current `performance.py`, `recording.py`, `pipeline.py`, `tracking.py`, and `performance_pipeline.py` and produced eight expected failing assertions demonstrating KNB-001 through KNB-005. Static source/doc reconciliation confirmed KNB-006. Current public dependency documentation shows MediaPipe 1.0.1 is admitted by the optional range and provides an Apple-Silicon wheel; current Face Landmarker API names used by the adapter remain documented.
- **Validation not performed:** Target-Mac webcam runtime, actual MediaPipe model inference, M1/M4 throughput, OBS output, character rendering, strict network observation, and repaired-source regression validation remain unperformed because source repairs were not part of this verification request.

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
