# Operational State: Character Performance Capture

<!-- operational-state:metadata
{
  "schema_version": 1,
  "project_id": "character-performance-capture",
  "project_name": "Character Performance Capture",
  "project_root": "westkitty/character-performance-capture",
  "artifact_path": null,
  "state_revision": 2,
  "last_updated": "2026-09-01",
  "current_baseline": {
    "identity": "fe1675dd18b1165a013e1b76fb330d3a2edeec4a",
    "state": "implemented-unverified",
    "last_verified": null
  },
  "scope_boundaries": [
    "Local-first webcam performance capture, modular tracking/rendering, preview/OBS output, offline capture/replay, and model/license governance."
  ],
  "linked_parent_state": null
}
-->

## 1. Project Identity and Scope

- **Project ID:** `character-performance-capture`
- **Purpose:** Build a local-first character performance-capture system that can drive approved fictional or owned character references from a live performer without binding the product to one face-swap model.
- **Project type:** Python / macOS Apple Silicon local media tooling.
- **Primary root or artifact:** `westkitty/character-performance-capture`
- **Target environment:** macOS Apple Silicon first; portable seams for later Windows/Linux support.
- **Canonical authority:** This repository plus the newest explicit user instruction.
- **Governed scope:** Camera ingest, performance tracking, character rendering, preview/output sinks, recording/replay, model adapters, performance telemetry, and dependency/model licensing.
- **Explicitly not governed:** Big Mac FaceTools / FaceFusion installation, user media libraries, generated character assets, or unrelated webcam/deepfake tooling.

## 2. Current Baseline

- **Primary artifact:** commit `fe1675dd18b1165a013e1b76fb330d3a2edeec4a`
- **Baseline state:** `implemented-unverified`
- **Source/build/install identity:** Python package scaffold with OpenCV webcam source, model-agnostic pipeline, passthrough renderer, telemetry overlay, CLI preview, unit tests, CI definition, and architecture documentation.
- **Active default user route:** Intended route is `cpc --camera 0`; not yet runtime-verified on target hardware.
- **Delivery state:** Source is committed to GitHub.
- **Last verified baseline:** No runtime baseline yet.

## 3. Artifact Contract

The project is a clean-room implementation with a testable headless core. The initial runnable route is webcam -> processing seam -> renderer seam -> preview. Model-specific code remains behind adapters. No user media or heavyweight model weights are committed to Git.

## 4. Active Invariants

- **INV-001 — Clean-room boundary:** Do not copy source code from Deep-Live-Cam, DeepFaceLive, or other copyleft prior art into this repository. Architectural concepts may be independently reimplemented.
- **INV-002 — Local-first:** Core capture/render workflows must not require uploading frames, reference images, or performance data to a remote service.
- **INV-003 — Media/model exclusion:** User recordings, reference portraits, generated characters, downloaded model weights, caches, and secrets must remain outside Git.
- **INV-004 — Commercial-path licensing:** A renderer/tracker cannot be marked production/commercial-ready while it depends on a model restricted to non-commercial research use.
- **INV-005 — Pluggable pipeline:** Capture, tracking, rendering, and output must remain separable so a model can be replaced without rebuilding the entire app.
- **INV-006 — Testable core:** Camera hardware and GUI state must not be required to unit-test core frame transformation and lifecycle behavior.
- **INV-007 — Authorized character use:** The product is designed around owned, licensed, fictional, or otherwise authorized character/reference material; deceptive real-person impersonation is not a product requirement.

## 5. Verified Working Behavior

None yet. Source presence is not runtime verification.

## 6. Known Not Working

None confirmed yet.

## 7. Implemented but Unverified

- **UNV-001:** OpenCV `CameraSource` with explicit open/read/close lifecycle.
- **UNV-002:** Model-agnostic `Pipeline` with ordered processor startup, frame processing, reverse-order teardown, and frame metrics.
- **UNV-003:** Passthrough renderer plus FPS/processing-latency telemetry overlay.
- **UNV-004:** CLI preview route via `cpc --camera 0`, with optional mirror/size/FPS arguments.
- **UNV-005:** Unit tests cover passthrough values, idempotent lifecycle, and processor ordering.
- **UNV-006:** GitHub Actions workflow defines Ruff and pytest checks.
- **UNV-007:** Git exclusions cover user media, generated outputs, caches, and common model-weight formats.

## 8. Unknown or Evidence-Stale State

- **UNK-001:** Actual webcam throughput on the M1 MacBook Air is unknown.
- **UNK-002:** Actual webcam/render throughput on the M4 Big Mac is unknown.
- **UNK-003:** OBS virtual-camera availability and latency on the target Macs are unknown.
- **UNK-004:** Best production renderer is not frozen. LivePortrait is a candidate only after replacing its InsightFace detection dependency for a commercial path.
- **UNK-005:** CI completion state is not visible through the available connector evidence yet.

## 9. Pending Work

- **PND-001:** Run the foundation on target Apple Silicon and record baseline FPS/latency.
- **PND-002:** Add a real performance-tracker interface plus serializable capture/replay state.
- **PND-003:** Add optional virtual-camera output suitable for OBS.
- **PND-004:** Prototype a character renderer without importing restricted model licensing into the core.
- **PND-005:** Benchmark M1 and M4 Apple Silicon paths before choosing a live renderer.

## 10. Active Decisions, Defaults, and Prohibitions

- **DEC-001:** `westkitty/character-performance-capture` is the implementation repository.
- **DEC-002:** Deep-Live-Cam is prior art, not the project base or fork.
- **DEC-003:** Start with a model-agnostic runnable core; do not make InsightFace/Inswapper a required dependency.
- **DEC-004:** Prefer a small Python headless core before committing to a desktop UI framework.
- **DEC-005:** Keep this project distinct from Big Mac FaceTools/FaceFusion.
- **DEC-006:** Add performance capture/replay before selecting a generative renderer, so performer data is not welded to one model.

## 11. Validation and Evidence Matrix

| ID | Claim or behavior | State | Evidence | Validation method | Artifact/revision | Last checked | Recheck trigger |
|---|---|---|---|---|---|---|---|
| INV-001 | Clean-room boundary | implemented-unverified | Independently authored project files; prior-art docs contain concepts only | Dependency/source provenance review | rev 2 | 2026-09-01 | Any external-code import |
| INV-002 | Local-first core | implemented-unverified | Current dependencies are NumPy/OpenCV only | Network-free target runtime test | rev 2 | 2026-09-01 | First model integration |
| UNV-002 | Pipeline lifecycle | implemented-unverified | Source plus unit-test definitions committed | CI/local pytest | rev 2 | 2026-09-01 | Pipeline change |
| UNV-004 | Webcam preview | implemented-unverified | CLI source committed | Launch on target Mac with webcam | rev 2 | 2026-09-01 | Capture/UI change |
| UNV-006 | CI workflow | implemented-unverified | Workflow file committed | Observe successful Actions run | rev 2 | 2026-09-01 | Workflow/dependency change |

## 12. Current Change Scope and Impact Radius

- **Allowed to change:** Foundation capture pipeline, tests, architecture documentation, Git hygiene, future tracker/replay seam, and optional virtual-camera seam.
- **Must remain unchanged:** Clean-room, local-first, license, media-exclusion, and pluggable-pipeline invariants.
- **Potentially affected behavior:** Foundation package and future extension interfaces.
- **Mandatory checks:** Ruff, pytest, import/launch check, webcam preview on target Mac, latency/FPS baseline before model integration.
- **Checks deliberately reused:** None.
- **Repair class:** Greenfield foundation.

## 13. Compact Revision Log

### Revision 2 — 2026-09-01

- **Artifact/source identity:** commit `fe1675dd18b1165a013e1b76fb330d3a2edeec4a`
- **State deltas:** Foundation source, tests, CI, and architecture decisions committed.
- **New evidence:** GitHub accepted all foundation files; repository is no longer empty.
- **Validation not performed:** CI result, webcam runtime, OBS virtual camera, model inference, and target-Mac throughput remain unverified.

### Revision 1 — 2026-09-01

- **Artifact/source identity:** `initial-empty-repository`
- **State deltas:** Initialized operational state and project invariants before implementation.
- **New evidence:** Target repository confirmed writable and empty before initialization.
- **Validation not performed:** All runtime behavior remained pending.
