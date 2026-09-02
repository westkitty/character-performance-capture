# Repository Governance

This document defines the repository-level controls intended to protect `main` while keeping Character Performance Capture easy to continue and verify.

## Licensing posture

The repository is currently proprietary / all rights reserved. Public visibility does not grant an open-source license. See the top-level `LICENSE` file.

This posture is deliberately conservative: it makes the existing default explicit without granting third-party reuse rights. A future open-source or source-available license is a separate project-owner decision.

Third-party code, optional dependencies, models, datasets, trademarks, likenesses, and assets remain governed by their own licenses and terms.

## CI contract

The `CI` workflow runs these verification lanes:

- core install, Ruff, and pytest on Ubuntu
- core install, Ruff, and pytest on macOS
- optional MediaPipe install, API-surface check, and adapter smoke test on macOS
- one stable aggregate job named `required-ci`

`required-ci` succeeds only when the full core matrix and MediaPipe smoke job both succeed. This gives branch protection one stable status-check name instead of coupling policy to matrix-generated job labels.

## Intended `main` ruleset

When GitHub repository rules are enabled, target the default branch and require:

1. pull requests before changes are merged
2. status check `required-ci`
3. the branch to be up to date before merge
4. no force pushes
5. no branch deletion

Administrator bypass should remain narrow and deliberate. Emergency bypasses should be followed by a successful `required-ci` run on the resulting `main` head.

## Current enforcement state

Repository CI is implemented, but GitHub-side branch protection/rulesets must be enabled in repository settings before the policy is technically enforced. Until then, direct pushes can still land even if CI later reports failure.

The active ChatGPT GitHub connector can read branch protection and rulesets but does not expose a write action for those repository settings. Therefore this repository must not claim branch enforcement until GitHub reports `main` as protected or an active ruleset targeting `main` is observable.

## Verification rule

A green CI run proves the deterministic checks represented by that workflow. It does not prove real webcam behavior, actual Face Landmarker model inference, OBS/virtual-camera operation, target-device latency, or renderer quality.
