# Operational State: Character Performance Capture

<!-- operational-state:metadata
{
  "schema_version": 1,
  "project_id": "character-performance-capture",
  "project_name": "Character Performance Capture",
  "project_root": "westkitty/character-performance-capture",
  "artifact_path": null,
  "state_revision": 10,
  "last_updated": "2026-09-01",
  "current_baseline": {
    "identity": "feature code ac15bbc4fd702b75a307b94c61f4522bc12b40a3 on feat/performance-black-box-macbook",
    "state": "partially-verified",
    "last_verified": "2026-09-01"
  },
  "scope_boundaries": [
    "Local-first webcam performance capture, modular tracking/rendering, preview/OBS output, offline capture/replay, target-hardware validation, repository governance, local performance-memory/evidence indexing, and optional local semantic retrieval."
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
- **Governed scope:** Camera ingest, performance tracking, portable performer state, character rendering, preview/output sinks, recording/replay, model adapters, telemetry, target-hardware diagnostics, repository CI/license governance, local performance-memory/evidence indexing, semantic retrieval, and dependency/model licensing.

## 2. Current Baseline

- **Mainline parent:** `110cac66b4fb8555f8f2539415fcf75552fcf438` (`docs: record repository governance hardening`).
- **Mainline code artifact:** `3a67449a837835dd97940df649fb446e671ca010`.
- **Repository governance artifact:** `6b7c5652f1989d3325cc82a46e87a00978e6bc72`.
- **Current feature branch:** `feat/performance-black-box-macbook`.
- **Feature code artifact:** `ac15bbc4fd702b75a307b94c61f4522bc12b40a3`.
- **Feature CI evidence:** Actions run `33581471512` completed successfully across Ubuntu core, macOS core, MediaPipe smoke, and aggregate `required-ci`.
- **Baseline state:** `partially-verified`.
- **Mainline deterministic identity:** CPC v0.2.0 with strict portable `PerformanceFrame`, hardened `.cpc` recording/replay, optional MediaPipe adapter, local-only `cpc --doctor`, proprietary/all-rights-reserved repository licensing, Linux/macOS CI plus MediaPipe smoke, and a stable aggregate `required-ci` job.
- **Feature identity:** Performance Black Box SQLite library, kinematic/hybrid retrieval, human evidence states, bug packets, review queue, canonical build drift/benchmarking, optional local Qwen semantic adapters, and a constrained Apple-Silicon MLX route.
- **Verified mainline evidence:** GitHub Actions run `33579448271` passed Ubuntu core, macOS core, MediaPipe smoke, and aggregate `required-ci`; the core suite contains 26 tests.
- **Physical proof state:** no command from this session has executed on the user's physical MacBook. The branch provides the evidence-producing bootstrap; target-Mac MLX inference remains implemented-unverified until that script runs there.

## 3. Artifact Contract

`.cpc` v1 remains the authoritative portable performer-state source. Black Box SQLite rows, kinematic fingerprints, semantic embeddings, novelty scores, retrieval rankings, and build comparisons are derived state. Human judgments and bug packets are durable evidence layered on top. Optional `media_path` values refer to local footage but do not copy pixels into `.cpc` or Git. `cpc --doctor` may inspect camera frames transiently but does not persist camera pixels.

## 4. Active Invariants

- **INV-001 — Clean-room boundary:** Do not copy source from Deep-Live-Cam, DeepFaceLive, or incompatible prior art into CPC.
- **INV-002 — Local-first:** Core capture, rendering, diagnostics, Black Box indexing, and model inference must not require uploading frames, references, or performance data.
- **INV-003 — Media/model exclusion:** User recordings, references, outputs, downloaded model weights, caches, and secrets remain outside Git.
- **INV-004 — Commercial-path licensing:** A backend is not production/commercial-ready while any required code/model license conflicts with intended use.
- **INV-005 — Pluggable pipeline:** Capture, tracking, portable state, rendering, output, and semantic retrieval remain separable.
- **INV-006 — Testable core:** Hardware/GUI/model weights are not required to unit-test deterministic schema, recording/replay, lifecycle, diagnostics, Black Box indexing/search, and benchmark math.
- **INV-007 — Authorized character use:** The product targets owned, licensed, fictional, or otherwise authorized character/reference material.
- **INV-008 — Performance portability:** Canonical takes store renderer-independent performer state, not renderer or embedding-model latent tensors.
- **INV-009 — No-overwrite capture:** Recording finalization never replaces an independently existing final destination.
- **INV-010 — Diagnostic privacy:** `cpc --doctor` may inspect live frames in memory but does not persist camera pixels or require network services.
- **INV-011 — Repository rights clarity:** Public repository visibility is not an open-source grant; top-level repository source remains proprietary/all rights reserved unless the project owner explicitly changes the license.
- **INV-012 — Enforcement honesty:** CI is described as server-required only after GitHub reports an active branch rule/ruleset enforcing `required-ci`.
- **INV-013 — Derived semantic state:** Embeddings are exact-namespaced by provider/model/dimension and may be regenerated without changing canonical captures or human evidence.
- **INV-014 — No silent model acquisition:** CPC inference adapters require an existing local model directory. Any model download is an explicit operator action such as the MacBook bootstrap.

## 5. Verified Working Behavior

### Mainline evidence

- **VER-001:** Strict `PerformanceFrame` schema rejects semantic type confusion and preserves valid portable state.
- **VER-002:** Tracker -> renderer lifecycle, restart frame-index behavior, and FPS reset are regression-covered.
- **VER-003:** Hardened `.cpc` record/replay preserves partial evidence and prevents final-path overwrite races.
- **VER-004:** Capture readers reject trailing records, invalid footer counts/durations, non-finite values, and non-monotonic frame state.
- **VER-005:** Processor/pipeline startup rollback and restart lifecycle are regression-covered.
- **VER-006:** The 26-test mainline deterministic suite passes on Linux and macOS CI.
- **VER-007:** Mainline Ruff plus Linux/macOS tests and MediaPipe package/API smoke pass; `required-ci` passed in Actions run `33579448271`.
- **VER-008:** `cpc --doctor` report construction, cleanup, privacy flags, camera backend/property reporting, and sample-count validation are regression-covered.
- **VER-009:** Repository has an explicit proprietary/all-rights-reserved `LICENSE`; CI exposes aggregate `required-ci` for branch-rule enforcement.

### Feature-branch evidence produced in this session

- **VER-010 — Black Box deterministic slice:** 16 focused tests pass in the reconstructed harness against the current strict `PerformanceFrame`/recording modules. Coverage includes capture segmentation/indexing, kinematic retrieval, evidence states/history, bug packets, review ranking, build drift, external semantic vectors, dimension-safe namespaces, bounded media sampling, canonical retrieval benchmark math, and the Mac MLX.runtime selection/segment packaging contract.
- **VER-011 — Source/package preflight:** Black Box Python sources compile; `pyproject.toml` parses; `cpc-blackbox qwen-search --help` exposes explicit `--runtime {torch,mlx}`; the MacBook bootstrap passes `bash -n`.
- **VER-012 — Licensing route selection:** The Mac adapter uses MIT-licensed `mlx-vlm` rather than GPL `mlx-embeddings`. The selected MLX Qwen checkpoint is Apache-2.0. The GPL draft was discarded before repository publication.
- **VER-013 — Published feature CI:** Feature code `ac15bbc4fd702b75a307b94c61f4522bc12b40a3` passed Ubuntu install/Ruff/pytest, macOS install/Ruff/pytest, MediaPipe smoke, and aggregate `required-ci` in Actions run `33581471512`.

## 6. Known Not Working

No deterministic mainline core defect is currently confirmed. No Black Box deterministic defect remains in the focused 16-test slice.

- **GOV-001 — Branch enforcement pending:** `main` remains unprotected because the active GitHub connector can read but cannot write repository rulesets/branch-protection settings. GitHub issue #1 tracks settings-side activation of the documented `required-ci` ruleset.

A target-hardware or semantic-runtime failure must not be inferred merely because physical execution is pending. Conversely, no MacBook throughput/memory/retrieval claim is promoted to verified until target-machine evidence exists.

## 7. Implemented but Unverified

- **UNV-001:** Real `cpc --doctor` run against the user's target webcam.
- **UNV-002:** Live preview FPS/latency/status on the physical target MacBook.
- **UNV-003:** Real MediaPipe Face Landmarker inference with an authorized local `.task` asset.
- **UNV-004:** Any production character renderer or OBS/virtual-camera sink.
- **UNV-005:** Real `Qwen/Qwen3-VL-Embedding-2B` Torch/MPS inference through the optional `blackbox-qwen` adapter.
- **UNV-006:** Real `mlx-community/Qwen3-VL-Embedding-2B-4bit` 