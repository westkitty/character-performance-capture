# Operational State: Character Performance Capture

<!-- operational-state:metadata
{
  "schema_version": 1,
  "project_id": "character-performance-capture",
  "project_name": "Character Performance Capture",
  "project_root": "westkitty/character-performance-capture",
  "artifact_path": null,
  "state_revision": 1,
  "last_updated": "2026-09-01",
  "current_baseline": {
    "identity": "initial-empty-repository",
    "state": "current-baseline",
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

- **Primary artifact:** `initial-empty-repository`
- **Baseline state:** `current-baseline`
- **Source/build/install identity:** Repository existed but contained no files before this state file.
- **Active default user route:** Not yet implemented.
- **Delivery state:** GitHub repository is writable; runtime is not yet implemented.
- **Last verified baseline:** Repository metadata inspected 2026-09-01; runtime validation not yet possible.

## 3. Artifact Contract

The project will be a clean-room implementation with a testable headless core. The initial runnable route is webcam -> tracking seam -> rendering seam -> preview and optional virtual-camera output. Model-specific code must remain behind adapters. No user media or heavyweight model weights are committed to Git.

## 4. Active Invariants

- **INV-001 — Clean-room boundary:** Do not copy source code from Deep-Live-Cam, DeepFaceLive, or other copyleft prior art into this repository. Architectural concepts may be independently reimplemented.
- **INV-002 — Local-first:** Core capture/render workflows must not require uploading frames, reference images, or performance data to a remote service.
- **INV-003 — Media/model exclusion:** User recordings, reference portraits, generated characters, downloaded model weights, caches, and secrets must remain outside Git.
- **INV-004 — Commercial-path licensing:** A renderer/tracker cannot be marked production/commercial-ready while it depends on a model restricted to non-commercial research use.
- **INV-005 — Pluggable pipeline:** Capture, tracking, rendering, and output must remain separable so a model can be replaced without rebuilding the entire app.
- **INV-006 — Testable core:** Camera hardware and GUI state must not be required to unit-test core frame transformation and lifecycle behavior.
- **INV-007 — Authorized character use:** The product is designed around owned, licensed, fictional, or otherwise authorized character/reference material; deceptive real-person impersonation is not a product requirement.

## 5. Verified Working Behavior

None yet.

## 6. Known Not Working

None confirmed yet; the repository has not had a runnable implementation.

## 7. Implemented but Unverified

- **UNV-001:** Operational-state control plane initialized in the target repository.

## 8. Unknown or Evidence-Stale State

- **UNK-001:** Actual webcam throughput on the M1 MacBook Air is unknown.
- **UNK-002:** Actual webcam/render throughput on the M4 Big Mac is unknown.
- **UNK-003:** OBS virtual-camera availability and latency on the target Macs are unknown.
- **UNK-004:** Best production renderer is not yet frozen; LivePortrait is a candidate only after replacing its InsightFace detection dependency for a commercial path.

## 9. Pending Work

- **PND-001:** Build a minimal camera/preview pipeline with clean tracking and rendering interfaces.
- **PND-002:** Add optional virtual-camera output suitable for OBS.
- **PND-003:** Add a real performance tracker and record/replay format.
- **PND-004:** Prototype a character renderer without importing restricted model licensing into the core.
- **PND-005:** Benchmark M1 and M4 Apple Silicon paths before choosing a live renderer.

## 10. Active Decisions, Defaults, and Prohibitions

- **DEC-001:** `westkitty/character-performance-capture` is the implementation repository.
- **DEC-002:** Deep-Live-Cam is prior art, not the project base or fork.
- **DEC-003:** Start with a model-agnostic runnable core; do not make InsightFace/Inswapper a required dependency.
- **DEC-004:** Prefer a small Python headless core before committing to a desktop UI framework.
- **DEC-005:** Keep this project distinct from Big Mac FaceTools/FaceFusion.

## 11. Validation and Evidence Matrix

| ID | Claim or behavior | State | Evidence | Validation method | Artifact/revision | Last checked | Recheck trigger |
|---|---|---|---|---|---|---|---|
| INV-001 | Clean-room boundary | requested | User continuation plus repository initialization decision | Review committed dependencies/source provenance | rev 1 | 2026-09-01 | Any external-code import |
| INV-002 | Local-first core | requested | Architecture decision | Network-free runtime test | rev 1 | 2026-09-01 | First model integration |
| UNV-001 | State file exists | implemented-unverified | GitHub write | Fetch committed file | rev 1 | 2026-09-01 | State update |

## 12. Current Change Scope and Impact Radius

- **Allowed to change:** Initialize repository structure, runnable capture core, tests, architecture/recon documentation, Git hygiene, and optional virtual-camera seam.
- **Must remain unchanged:** Clean-room, local-first, license, media-exclusion, and pluggable-pipeline invariants.
- **Potentially affected behavior:** Entire project; no prior runtime behavior exists.
- **Mandatory checks:** Python syntax/import checks where executable runtime is available; unit tests for pure frame/pipeline logic; source/dependency review for clean-room compliance.
- **Checks deliberately reused:** None.
- **Repair class:** Greenfield foundation.

## 13. Compact Revision Log

### Revision 1 — 2026-09-01

- **Artifact/source identity:** `initial-empty-repository`
- **State deltas:** Initialized operational state and project invariants before implementation.
- **New evidence:** Target repository confirmed writable and empty before initialization.
- **Validation not performed:** Webcam, virtual camera, model inference, and target-Mac runtime validation remain pending.
