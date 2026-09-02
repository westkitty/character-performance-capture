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
    "identity": "4568a9a57a085235307de5914be2bdb1d72ac193",
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

- **Primary artifact:** code commit `4568a9a57a085235307de5914be2bdb1d72ac193`
- **Baseline state:** `known-broken`
- **Source/build/install identity:** CPC v0.2.0 with portable `PerformanceFrame`, tracker/renderer pipeline, crash-tolerant `.cpc` recording/replay, optional MediaPipe Face Landmarker adapter, CLI recording/inspection, and expanded tests.
- **Active default user route:** `cpc --camera 0` remains the intended zero-model preview route; not yet runtime-verified on target Mac hardware.
- **Delivery state:** v0.2 source is committed to `main`; repository CI is green for the existing suite, but an independent verification sweep found six defects not covered by that suite.
- **Last verified baseline:** GitHub Actions run 33556653108 succeeded on 2026-09-01 after install, Ruff, and pytest all passed. Independent verification on the exact GitHub source blobs then found six failing regression fixtures outside the existing test coverage.

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
- **INV-009 — No-overwrite capture:** Starting and committing a performance recording must never overwrite an existing final capture or an independently created destination file.

## 5. Verified Working Behavior

- **VER-001:** `PerformanceFrame` serialization round-trips a valid portable state record under the current tested happy path.
- **VER-002:** `PerformancePipeline` passes tracker state into the renderer and enforces tracker-start -> renderer-start -> track -> render -> renderer-close -> tracker-close lifecycle ordering for a single tested session.
- **VER-003:** `PerformanceRecorder` writes and replays a normal finalized `.cpc` capture, and an exception inside its context leaves a readable `.cpc.partial` for the tested path.
- **VER-004:** The repository's original v0.2 suite passed locally: 11 tests, 0 failures. `python3 -m compileall -q src tests` also passed.
- **VER-005:** GitHub Actions run `33556653108` for commit `4568a9a57a085235307de5914be2bdb1d72ac193` completed successfully: dependency installation passed, `ruff check src tests` passed, and `pytest` passed under Python 3.11 on Ubuntu.

## 6. Known Not Working

- **BUG-001 — Recorder final-path overwrite race — High:** `PerformanceRecorder.start()` checks that the final path is absent, but `close(commit=True)` uses `os.replace()`. If another file appears at the final path while recording is in progress, commit silently replaces it, violating the no-overwrite invariant.
- **BUG-002 — Capture reader accepts malformed/trailing end state — Medium:** `iter_capture_frames()` stops at the first `end` record and ignores any records after it, so malformed captures can be replayed as if valid. `read_capture()` catches some trailing records but does not validate all footer semantics consistently.
- **BUG-003 — Capture footer validation is incomplete — Medium:** `read_capture()` trusts `duration_s` without requiring it to be finite, non-negative, or consistent with frame timestamps. Malformed or misleading capture metadata can therefore be accepted.
- **BUG-004 — PerformanceFrame coercion accepts invalid semantic types — Medium:** `PerformanceFrame.from_dict()` coerces values with `bool()`, `int()`, `float()`, and `str()` rather than requiring the intended JSON types. Examples such as `tracked="false"` become `True`, and boolean frame indexes can be accepted through Python's int/bool relationship.
- **BUG-005 — Pipeline restart metrics leak prior session state — Medium:** both `Pipeline` and `PerformancePipeline` leave frame counters / `_last_frame_time` populated after `close()`, so reusing a pipeline produces non-zero first-frame FPS and continued frame indexes instead of a fresh session.
- **BUG-006 — Recorder write failure can retain open state until explicit close — Medium:** if `write()` rejects an invalid/non-monotonic frame, the recorder remains open with a partial file unless the caller is inside a context manager or explicitly closes it. The safe failure behavior is under-specified and untested.
- **DOC-001 — Architecture document is stale — Low:** `docs/ARCHITECTURE.md` still labels the performance tracker and character renderer as future layers and describes the current slice as the old frame-only `Pipeline`, despite v0.2 implementing the tracker protocol, portable performance layer, and `PerformancePipeline`.

## 7. Implemented but Unverified

- **UNV-001:** OpenCV `CameraSource` with explicit open/read/close lifecycle.
- **UNV-002:** Existing frame-only utility `Pipeline` and passthrough processor path.
- **UNV-003:** Live FPS / processing-latency / tracking-status overlay.
- **UNV-004:** CLI preview route via `cpc --camera 0`, with optional mirror/size/FPS arguments.
- **UNV-005:** Optional MediaPipe Face Landmarker adapter using a caller-supplied local model asset; no model is bundled or auto-downloaded.
- **UNV-006:** Live `--record-performance` path combining webcam capture, tracker, renderer, and recorder.
- **UNV-007:** MediaPipe optional dependency range currently permits `mediapipe>=0.10.35,<2`; current package major-version compatibility has not been validated by repository CI.

## 8. Unknown or Evidence-Stale State

- **UNK-001:** Actual webcam throughput on the M1 MacBook Air is unknown.
- **UNK-002:** Actual webcam/tracker throughput on the M4 Big Mac is unknown.
- **UNK-003:** OBS virtual-camera availability and latency on the target Macs are unknown.
- **UNK-004:** Best production renderer is not frozen. LivePortrait remains only a candidate pending dependency/model-license replacement and benchmark evidence.
- **UNK-005:** Actual MediaPipe Face Landmarker model inference with a chosen `.task` asset has not been run in this project.
- **UNK-006:** macOS/Apple-Silicon installation is not exercised in CI; the current CI matrix is Python 3.11 on Ubuntu only.

## 9. Pending Work

- **PND-001:** Fix BUG-001 through BUG-006 and add regression fixtures before expanding into OBS or renderer work.
- **PND-002:** Refresh `docs/ARCHITECTURE.md` to match v0.2 reality.
- **PND-003:** Add optional-dependency CI coverage that imports/constructs the MediaPipe adapter against a supported dependency version without bundling a model.
- **PND-004:** Run zero-model preview on target Apple Silicon and record camera-only FPS/latency.
- **PND-005:** Run the optional MediaPipe adapter with an explicitly chosen local Face Landmarker asset and capture a real `.cpc` take.
- **PND-006:** Add optional virtual-camera output suitable for OBS only after the verified defects above are closed.
- **PND-007:** Prototype a character renderer without importing restricted model licensing into the core.

## 10. Active Decisions, Defaults, and Prohibitions

- **DEC-001:** `westkitty/character-performance-capture` is the implementation repository.
- **DEC-002:** Deep-Live-Cam is prior art, not the project base or fork.
- **DEC-003:** Do not make InsightFace/Inswapper a required dependency.
- **DEC-004:** Prefer a small Python headless core before committing to a desktop UI framework.
- **DEC-005:** Keep this project distinct from Big Mac FaceTools/FaceFusion.
- **DEC-006:** Performance capture/replay precedes production renderer selection.
- **DEC-007:** `.cpc` format v1 is UTF-8 JSON Lines with header, frame records, and a clean end record; interrupted recordings remain as recoverable `.partial` files and completed recordings must not overwrite an independently existing final path.
- **DEC-008:** Named normalized blendshapes plus optional landmarks/gaze/head/4x4 transform form the portable performance contract; tracker-specific coefficient naming is identified by `profile`.
- **DEC-009:** MediaPipe is an optional tracker experiment only. Its Python package is not a core dependency, and CPC does not redistribute or auto-download its model asset.

## 11. Validation and Evidence Matrix

| ID | Claim or behavior | State | Evidence | Validation method | Artifact/revision | Last checked | Recheck trigger |
|---|---|---|---|---|---|---|---|
| INV-001 | Clean-room boundary | partially-verified | Independently authored source and isolated optional adapter | Source/dependency provenance review | rev 5 | 2026-09-01 | Any external-code import |
| INV-002 | Local-first core | partially-verified | Core and recorder perform local file/memory operations only | Target network-free runtime test | rev 5 | 2026-09-01 | First real model/render integration |
| INV-009 | Recorder never overwrites final destination | failed | Focused regression creates final path after recorder start; `os.replace()` overwrites it | Add race regression and no-replace commit primitive | v0.2 / rev 5 | 2026-09-01 | Recorder finalization change |
| VER-001 | Valid PerformanceFrame round-trip | verified | Existing pytest + independent exact-source inspection | `tests/test_performance.py` | v0.2 / rev 5 | 2026-09-01 | Schema change |
| VER-002 | Single-session tracker -> renderer lifecycle | verified | Existing pytest + green repository CI | `tests/test_performance_pipeline.py` | v0.2 / rev 5 | 2026-09-01 | Pipeline change |
| VER-003 | Happy-path record/replay + context exception partial | partially-verified | Existing pytest; independent malformed/race fixtures expose gaps | `tests/test_recording.py` plus new regression set | v0.2 / rev 5 | 2026-09-01 | Capture-format change |
| VER-005 | Existing repository CI | verified | Actions run 33556653108: install/Ruff/pytest passed | GitHub Actions | commit 4568a9a / rev 5 | 2026-09-01 | Source/workflow/dependency change |
| BUG-002 | Parser rejects records after end | failed | Focused exact-source regression | Add trailing-record rejection tests | v0.2 / rev 5 | 2026-09-01 | Reader change |
| BUG-003 | Footer semantic validation | failed | Focused exact-source regression | Reject invalid/non-finite/negative/inconsistent duration | v0.2 / rev 5 | 2026-09-01 | Reader/footer change |
| BUG-004 | PerformanceFrame rejects semantic type confusion | failed | Focused exact-source regression | Strict JSON field-type tests | v0.2 / rev 5 | 2026-09-01 | Schema parser change |
| BUG-005 | Pipeline restart resets session metrics/index | failed | Focused restart regression | start/process/close/start/process fixture for both pipelines | v0.2 / rev 5 | 2026-09-01 | Lifecycle change |
| UNV-004 | Webcam preview | implemented-unverified | Source committed | Launch on target Mac with webcam | v0.2 / rev 5 | 2026-09-01 | Capture/UI change |
| UNV-005 | MediaPipe tracking | implemented-unverified | Adapter source committed; missing-model failure test passed | Real model + webcam test | v0.2 / rev 5 | 2026-09-01 | Adapter/model change |

## 12. Current Change Scope and Impact Radius

- **Allowed to change next:** `performance.py`, `recording.py`, `pipeline.py`, `performance_pipeline.py`, related regression tests, CI optional-dependency coverage, and stale architecture documentation.
- **Must remain unchanged:** Clean-room, local-first, license, media-exclusion, performance-portability, no-overwrite recording, and pluggable-pipeline invariants.
- **Potentially affected behavior:** Performance schema parsing, capture finalization/reading, replay validation, session lifecycle metrics, and CI dependency coverage.
- **Mandatory checks:** Existing regression suite plus six independent verification fixtures, Ruff, compileall, GitHub Actions, and exact-source inspection after writes.
- **Checks deliberately reused:** Target hardware checks remain pending; they do not need to block repair of deterministic core defects.
- **Repair class:** Bounded correctness repair before feature expansion.

## 13. Compact Revision Log

### Revision 5 — 2026-09-01

- **Artifact/source identity:** code baseline `4568a9a57a085235307de5914be2bdb1d72ac193`.
- **State deltas:** Repository-wide verification downgraded the baseline from partially verified to known-broken after independent regression fixtures exposed six defects outside the green CI suite; added no-overwrite invariant and stale-doc finding.
- **New evidence:** Current `main` tree was enumerated completely. Existing GitHub Actions run 33556653108 was green. Exact GitHub source blobs for the capture/schema modules were independently exercised against malformed/race fixtures. Six verification fixtures failed, including an actual final-path overwrite. Static dependency review also found MediaPipe optional CI coverage absent and Apple-Silicon runtime coverage still missing.
- **Validation not performed:** Target-Mac webcam runtime, real MediaPipe model inference, M1/M4 throughput, OBS output, and character rendering remain unverified.

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
