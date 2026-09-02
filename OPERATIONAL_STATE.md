# Operational State: Character Performance Capture

<!-- operational-state:metadata
{
  "schema_version": 1,
  "project_id": "character-performance-capture",
  "project_name": "Character Performance Capture",
  "project_root": "westkitty/character-performance-capture",
  "artifact_path": null,
  "state_revision": 8,
  "last_updated": "2026-09-01",
  "current_baseline": {
    "identity": "code 3a67449a837835dd97940df649fb446e671ca010; governance 6b7c5652f1989d3325cc82a46e87a00978e6bc72",
    "state": "partially-verified",
    "last_verified": "2026-09-01"
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

- **Primary code artifact:** `3a67449a837835dd97940df649fb446e671ca010`
- **Repository governance artifact:** `6b7c5652f1989d3325cc82a46e87a00978e6bc72`
- **Baseline state:** `partially-verified`
- **Source/build/install identity:** CPC v0.2.0 with strict portable `PerformanceFrame`, tracker/renderer pipeline, hardened `.cpc` recording/replay, optional MediaPipe adapter, CLI recording/inspection, local-only `--doctor` hardware diagnostics, 26 regression tests, explicit proprietary licensing, and a stable aggregate `required-ci` status job.
- **Verified deterministic route:** schema, record/replay integrity, no-overwrite finalization, pipeline lifecycle/restart behavior, diagnostic report logic and cleanup, Linux/macOS installation, Ruff, pytest, optional MediaPipe package/API smoke, and aggregate CI-gate behavior.
- **Active physical validation route:** `cpc --doctor --camera 0 --doctor-frames 120`; implemented but not yet run against an actual target webcam.
- **Verification evidence:** GitHub Actions run `33579448271` completed successfully for governance commit `6b7c5652f1989d3325cc82a46e87a00978e6bc72`. Ubuntu core, macOS core, MediaPipe smoke, and the aggregate `required-ci` job all completed successfully; the core suite contains 26 passing tests.

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
- **VER-010 — Diagnostic harness logic:** Tests verify hardware-report construction, active-backend/property reporting through `CameraSource.info()`, tracker/camera cleanup on failure, sample-count validation, privacy flags, and requested-versus-reported camera metadata handling.
- **VER-011 — Explicit repository license:** A top-level `LICENSE` now states the repository is proprietary / all rights reserved and explicitly says public visibility is not an open-source grant.
- **VER-012 — Stable aggregate CI gate:** GitHub Actions run `33579448271` completed with `required-ci` successful after the Linux, macOS, and MediaPipe verification lanes all succeeded.

## 6. Known Not Working

No unresolved deterministic-core bug is confirmed at revision 8.

- **GOV-001 — Branch enforcement pending:** `main` remains unprotected because the active GitHub connector can read but cannot write repository rulesets/branch-protection settings. The repository now exposes the stable `required-ci` check and documents the exact intended ruleset. GitHub issue #1 tracks the remaining settings-side activation.

The revision-5 defects remain fixed and regression-covered. No target-hardware failure may be inferred merely because target-hardware validation has not yet been executed.

## 7. Implemented but Unverified

- **UNV-001:** Real `cpc --doctor` execution against an actual target webcam, including active camera backend, negotiated properties, observed dimensions, frame-read timing, and overall sampled FPS.
- **UNV-002:** Live FPS / processing-latency / tracking-status overlay in a real camera preview session.
- **UNV-003:** CLI preview route `cpc --camera 0` on target hardware.
- **UNV-004:** Real MediaPipe Face Landmarker inference using an explicitly selected local `.task` model.
- **UNV-005:** Real MediaPipe `--doctor` run measuring tracking rate and processing timing on live frames.
- **UNV-006:** Live `--record-performance` using real webcam + real tracker inference.
- **UNV-007:** Any production character renderer.

## 8. Unknown or Evidence-Stale State

- **UNK-001:** Actual webcam throughput/latency on target Apple Silicon hardware remains unknown.
- **UNK-002:** Real MediaPipe tracker throughput and tracking quality remain unknown.
- **UNK-003:** OBS/virtual-camera availability and end-to-end latency remain unknown.
- **UNK-004:** Best production renderer remains unfrozen.
- **UNK-005:** No real Face Landmarker model has been exercised by CPC CI or a target user route.
- **UNK-007 — Branch enforcement:** The intended `main` ruleset is specified, but GitHub-side enforcement remains disabled until repository settings are changed and independently observed.

## 9. Pending Work

- **PND-001:** Run `cpc --doctor --camera 0 --doctor-frames 120` on target hardware and preserve the JSON metadata report as evidence.
- **PND-002:** Run `cpc --doctor --tracker mediapipe --model <authorized-face-landmarker.task> --camera 0 --doctor-frames 120` with an explicitly authorized local model and preserve the JSON metadata report.
- **PND-003:** After real camera/tracker proof, add and validate an optional virtual-camera/OBS output sink.
- **PND-004:** Prototype a character renderer behind the `PerformanceFrame` seam without importing restricted model licensing into the core.
- **PND-005:** Benchmark representative target machines with the same doctor sample contract before freezing a live renderer.
- **PND-006:** If public reuse is later intended, explicitly replace the proprietary license with a project-owner-selected license rather than assuming public visibility grants reuse rights.
- **PND-007:** Enable a GitHub `main` ruleset requiring `required-ci`, up-to-date pull requests, no force pushes, and no branch deletion; tracked by issue #1.

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
- **DEC-013:** Do not claim branch protection or required checks are enforced until GitHub reports the rule/ruleset as active.

## 11. Validation and Evidence Matrix

| ID | Claim or behavior | State | Evidence | Validation method | Artifact/revision | Last checked | Recheck trigger |
|---|---|---|---|---|---|---|---|
| INV-009 | Recorder never overwrites final destination | verified | Race regression passes after no-replace finalization | `tests/test_recording.py` + CI | code 3a67449 / rev 8 | 2026-09-01 | Recorder finalization change |
| INV-010 | Doctor does not persist camera pixels | partially-verified | Diagnostic source has no frame-write path; tests verify declared privacy contract | Source inspection + tests; target filesystem observation still pending | code 3a67449 / rev 8 | 2026-09-01 | Diagnostics/output change |
| INV-011 | Public visibility is not an open-source grant | verified | Top-level proprietary `LICENSE` and README notice present | Repository file inspection | governance 6b7c565 / rev 8 | 2026-09-01 | License change |
| VER-001 | Strict PerformanceFrame semantics | verified | Expanded schema tests pass | `tests/test_performance.py` | code 3a67449 / rev 8 | 2026-09-01 | Schema/parser change |
| VER-003 | Record/replay integrity | verified | Happy, partial, race, trailing-record and footer tests pass | `tests/test_recording.py` | code 3a67449 / rev 8 | 2026-09-01 | Capture-format change |
| VER-005 | Pipeline restart/startup rollback | verified | Dedicated lifecycle regressions pass | pipeline test files | code 3a67449 / rev 8 | 2026-09-01 | Lifecycle change |
| VER-006 | 26-test deterministic suite | verified | Actions run 33579448271 | pytest | governance 6b7c565 / rev 8 | 2026-09-01 | Source/dependency/workflow change |
| VER-007 | Linux + macOS lint/test | verified | Both core jobs successful | GitHub Actions | governance 6b7c565 / rev 8 | 2026-09-01 | Workflow/source/dependency change |
| VER-008 | MediaPipe package/API smoke | verified | install + API check + adapter smoke successful | GitHub Actions MediaPipe job | governance 6b7c565 / rev 8 | 2026-09-01 | MediaPipe range/API/adapter change |
| VER-010 | Diagnostic harness logic | verified | Four diagnostic regressions pass inside 26-test suite | `tests/test_diagnostics.py` + source inspection | code 3a67449 / rev 8 | 2026-09-01 | Camera/diagnostics/CLI change |
| VER-012 | Stable aggregate CI gate | verified | `required-ci` completed successfully after all prerequisite lanes | GitHub Actions run 33579448271 | governance 6b7c565 / rev 8 | 2026-09-01 | Workflow change |
| GOV-001 | `main` ruleset enforcement | blocked | Branch reports protected=false and rulesets collection is empty; connector exposes reads but no ruleset write | GitHub settings-side action required | rev 8 | 2026-09-01 | Ruleset activation |
| UNV-001 | Real camera doctor | implemented-unverified | Hardware route exists but no target camera result has been supplied | Run `cpc --doctor` on target hardware | rev 8 | 2026-09-01 | Camera/runtime change |
| UNV-004 | Real MediaPipe inference | implemented-unverified | No real `.task` model exercised | Run MediaPipe doctor with authorized model | rev 8 | 2026-09-01 | Adapter/model change |

## 12. Current Change Scope and Impact Radius

- **Allowed to change next:** GitHub ruleset activation when a settings-capable path is available, bounded fixes revealed by real doctor evidence, optional output sink after physical capture proof, and renderer experiments behind existing interfaces.
- **Must remain unchanged:** clean-room, local-first, media/model exclusion, license isolation, performance portability, strict capture integrity, no-overwrite recording, diagnostic privacy, repository-rights clarity, and pluggable-pipeline invariants.
- **Mandatory next checks:** retain the 26-test regression suite, Ruff, Linux/macOS CI, MediaPipe smoke, and `required-ci`; use doctor output as the decisive evidence for real camera/model claims.
- **Checks deliberately not repeated:** deterministic record/replay/lifecycle evidence remains current because governance hardening did not alter runtime semantics and the full suite re-passed.
- **Repair class:** repository license ambiguity fixed; stable CI enforcement target implemented and verified; GitHub-side branch-rule activation remains blocked by connector capability.

## 13. Compact Revision Log

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