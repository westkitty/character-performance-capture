# Operational State: Character Performance Capture

<!-- operational-state:metadata
{
  "schema_version": 1,
  "project_id": "character-performance-capture",
  "project_name": "Character Performance Capture",
  "project_root": "westkitty/character-performance-capture",
  "artifact_path": null,
  "state_revision": 9,
  "last_updated": "2026-09-01",
  "current_baseline": {
    "identity": "feature branch feat/performance-black-box-macbook based on main 110cac66b4fb8555f8f2539415fcf75552fcf438",
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

- **VER-010 — Black Box deterministic slice:** 16 focused tests pass in the reconstructed harness against the current strict `PerformanceFrame`/recording modules. Coverage includes capture segmentation/indexing, kinematic retrieval, evidence states/history, bug packets, review ranking, build drift, external semantic vectors, dimension-safe namespaces, bounded media sampling, canonical retrieval benchmark math, and the Mac MLX runtime selection/segment packaging contract.
- **VER-011 — Source/package preflight:** Black Box Python sources compile; `pyproject.toml` parses; `cpc-blackbox qwen-search --help` exposes explicit `--runtime {torch,mlx}`; the Mac bootstrap passes `bash -n`.
- **VER-012 — Licensing route selection:** The Mac adapter uses MIT-licensed `mlx-vlm` rather than GPL `mlx-embeddings`. The selected MLX Qwen checkpoint is Apache-2.0. The GPL draft was discarded before repository publication.

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
- **UNV-006:** Real `mlx-community/Qwen3-VL-Embedding-2B-4bit` inference through the `blackbox-mlx` adapter on the target 8 GB Apple-Silicon MacBook.
- **UNV-007:** Real-take semantic retrieval quality and kinematic-vs-semantic-vs-hybrid benchmark results.

## 8. Unknown or Evidence-Stale State

- **UNK-001:** Physical webcam throughput/latency on the target MacBook remains unknown until `cpc --doctor` runs there.
- **UNK-002:** Real MediaPipe tracker throughput and tracking quality remain unknown.
- **UNK-003:** OBS/virtual-camera availability and end-to-end latency remain unknown.
- **UNK-004:** Best production renderer remains unfrozen.
- **UNK-005:** MLX Qwen first-load latency, maximum resident set size, swap pressure, per-query/segment latency, and thermal behavior on the 8 GB M1 remain unknown.
- **UNK-006:** Four-frame/448px chronological sampling may or may not retain enough temporal semantics for CPC's corpus; only the canonical retrieval benchmark can answer that.
- **UNK-007:** Server-side `main` ruleset enforcement remains disabled until independently observed active.

## 9. Pending Work

- **PND-001:** On the physical MacBook, switch to `feat/performance-black-box-macbook` and run `./scripts/macbook_blackbox_bootstrap.sh`.
- **PND-002:** Preserve the generated camera-doctor JSON and `/usr/bin/time -l` MLX semantic-smoke report as target-hardware evidence.
- **PND-003:** Index one real `.cpc` take with matching local media, embed that capture using `--runtime mlx`, and record failures/latency/memory.
- **PND-004:** Capture matching canonical fixtures across two builds and run `cpc-blackbox benchmark` for kinematic, semantic, and hybrid Hit@1/3/5 + MRR.
- **PND-005:** Change MLX sampling/dimension defaults only if benchmark/resource evidence justifies it.
- **PND-006:** Run the existing mainline MediaPipe doctor with an authorized local model, then continue optional output-sink and renderer experiments behind the stable `PerformanceFrame` seam.
- **PND-007:** Enable the documented GitHub `main` ruleset requiring `required-ci`, up-to-date pull requests, no force pushes, and no branch deletion; tracked by issue #1.

## 10. Active Decisions, Defaults, and Prohibitions

- **DEC-001:** `westkitty/character-performance-capture` is the implementation repository; `feat/performance-black-box-macbook` isolates this feature until proof/review.
- **DEC-002:** Deep-Live-Cam/SentrySearch remain prior art, not code bases to copy.
- **DEC-003:** `.cpc` v1 stays unchanged by the Black Box.
- **DEC-004:** Black Box SQLite is derived local state; source capture/media are not migrated into it.
- **DEC-005:** Human evidence state (`gold`, `failure`, `interesting`, `unreviewed`, `superseded`) is authoritative over anomaly/similarity scores.
- **DEC-006:** Semantic vectors are exact-namespaced by provider + model + dimension; incompatible spaces are never mixed silently.
- **DEC-007:** Qwen semantic adoption is benchmark-gated; cosine similarity is not treated as calibrated confidence.
- **DEC-008:** Torch Qwen remains optional behind `blackbox-qwen`; it is not the preferred 8 GB Mac route.
- **DEC-009:** The 8 GB Apple-Silicon route uses `mlx-vlm>=0.6.17,<0.7` and `mlx-community/Qwen3-VL-Embedding-2B-4bit`, with defaults 768 dimensions, 2 sampled frames/sec, at most 4 chronological frames, and 448px maximum image side.
- **DEC-010:** MLX inference requires an existing local model directory. The Mac bootstrap may explicitly download the pinned model as a setup action; the runtime adapter itself never resolves a remote model ID.
- **DEC-011:** The Mac semantic smoke uses a generated synthetic image so model/vision proof does not persist a webcam frame.
- **DEC-012:** Repository source is proprietary/all-rights-reserved; third-party code/model licenses remain separate. GPL `mlx-embeddings` is not a CPC dependency.
- **DEC-013:** `required-ci` remains the stable aggregate status-check name; do not claim enforcement until GitHub reports the ruleset active.

## 11. Validation and Evidence Matrix

| ID | Claim | State | Evidence | Recheck trigger |
|---|---|---|---|---|
| INV-009 | Capture finalization does not overwrite an independent destination | verified | mainline race regression + CI | recorder change |
| INV-010 | Doctor does not persist camera pixels | partially-verified | source/tests; physical filesystem observation still pending | diagnostics change / target run |
| INV-011 | Public visibility is not an open-source grant | verified | top-level proprietary `LICENSE` + README | license change |
| INV-013 | Semantic namespaces reject dimension drift | verified | focused Black Box tests | embedding schema/search change |
| VER-006 | 26-test mainline deterministic suite | verified | Actions `33579448271` | mainline source/dependency change |
| VER-010 | Black Box deterministic/semantic plumbing | verified | 16 focused tests | Black Box schema/search/benchmark change |
| VER-011 | Mac bootstrap/source preflight | verified | compileall, TOML parse, CLI help, `bash -n` | Mac adapter/bootstrap change |
| GOV-001 | `main` ruleset enforcement | blocked | GitHub reports unprotected main; settings write unavailable here | ruleset activation |
| UNV-006 | Real 4-bit MLX Qwen inference on target MacBook | implemented-unverified | no physical target execution from this chat | first bootstrap run |
| UNV-007 | Semantic retrieval improves CPC search | unknown | benchmark harness exists; no real canonical corpus result yet | canonical benchmark run |

## 12. Current Change Scope and Impact Radius

- **Allowed feature-branch changes:** derived indexing/search/evidence modules, optional semantic adapters/extras, Black Box CLI/tests/docs, and target-Mac bootstrap tooling.
- **Must remain unchanged:** current strict `PerformanceFrame`, `.cpc` v1 semantics, no-overwrite recording, doctor privacy, camera default route, clean-room boundary, proprietary repository license, repository-rights clarity, and stable CI jobs.
- **Mandatory feature checks:** focused Black Box tests; compileall; TOML/script/CLI preflight; repository Ruff + full Linux/macOS/MediaPipe CI after branch publication; physical Mac doctor + MLX smoke before any hardware promotion.
- **Checks deliberately reused:** mainline recording/replay/lifecycle/diagnostic evidence remains current because this feature does not modify those modules.
- **Repair class:** feature expansion with target-hardware proof gate; no mainline deterministic repair is currently open.

## 13. Compact Revision Log

### Revision 9 — 2026-09-01

- **Artifact/source identity:** `feat/performance-black-box-macbook` based on main `110cac66b4fb8555f8f2539415fcf75552fcf438`.
- **State deltas:** Added Performance Black Box feature scope while inheriting mainline hardware-doctor and repository-governance authority; selected a permissive MIT `mlx-vlm` Mac route; added a bounded 8 GB Apple-Silicon profile and target-Mac bootstrap proof route.
- **New evidence:** 16 focused Black Box tests pass; compileall/TOML/CLI/script preflights pass. Current external sources document `mlx-vlm` 0.6.17 as MIT and the selected 4-bit Qwen MLX checkpoint as Apache-2.0 / approximately 1.78 GB.
- **Validation not performed:** real physical Mac camera/model inference, full branch CI after publication, real-take embeddings, canonical retrieval benchmark, OBS, or renderer proof.

### Revision 8 — 2026-09-01

- **Artifact/source identity:** code `3a67449a837835dd97940df649fb446e671ca010`; governance commit `6b7c5652f1989d3325cc82a46e87a00978e6bc72`; state commit later advanced to `110cac66b4fb8555f8f2539415fcf75552fcf438`.
- **State deltas:** Replaced public-repository license ambiguity with an explicit proprietary/all-rights-reserved `LICENSE`; added repository-governance docs and stable aggregate `required-ci`; tracked remaining branch-ruleset activation in issue #1.
- **Evidence:** Actions `33579448271` passed Ubuntu/macOS core, MediaPipe smoke, and `required-ci` with 26 core tests.

### Revision 7 — 2026-09-01

- **Artifact/source identity:** hardware-diagnostics implementation `3a67449a837835dd97940df649fb446e671ca010` plus subsequent docs.
- **State deltas:** Added local-only `cpc --doctor`, camera backend/negotiated-property reporting, hardware-validation docs, and diagnostic regressions; expanded deterministic suite to 26 tests.
- **Evidence:** Actions `33579062918` passed Linux/macOS core and MediaPipe smoke.

### Revision 6 — 2026-09-01

- **Artifact/source identity:** `2a60851b8963792118bbde2f4bbd9440ac4ddbd5`.
- **State deltas:** Closed revision-5 deterministic recording/schema/lifecycle defects and expanded CI.

### Revision 5 — 2026-09-01

- **Artifact/source identity:** `4568a9a57a085235307de5914be2bdb1d72ac193`.
- **State deltas:** Verification exposed six deterministic defects outside the original green suite.

### Revisions 1-4 — 2026-09-01

Foundation through v0.2 introduced the clean-room core, camera lifecycle, portable performer schema, tracker/renderer seam, `.cpc` capture/replay, MediaPipe adapter experiment, documentation, and initial CI.
