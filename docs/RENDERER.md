# Rig-warp character renderer

`RigWarpRenderer` is the first production-capable renderer behind the
`CharacterRenderer` seam. It is deterministic, license-clean (pure OpenCV/NumPy
piecewise-affine warping — no generative face model, no restricted weights), and
runs on CPU-only Apple Silicon.

## What it does

Given an authorized character reference image plus its neutral rig mesh, each
frame it:

1. reads the performer landmark mesh from the `PerformanceFrame`;
2. captures the first tracked frame as the performer's neutral pose;
3. fits a similarity transform (scale + rotation + translation) from the
   performer neutral to the current performer mesh using expression-stable
   points (eye corners, nose bridge, brow centre, temples);
4. takes the residual per-point offsets as the current **expression**, rescaled
   from the performer's inter-ocular distance to the character's;
5. adds that expression to the character's own neutral mesh, then applies a
   cheap 2D head-pose transform (roll rotates, yaw/pitch foreshorten) about the
   character face centre;
6. clamps per-point travel and absolute position so pathological geometry cannot
   blow up the warp;
7. piecewise-affine-warps the character image from its neutral mesh to the target
   mesh over a Delaunay triangulation, with eight fixed frame-edge anchors so the
   background stays still.

The character's pixels are warped; the performer's face is never composited in.
Identity is preserved by construction.

## The rig contract

A rig sidecar is JSON next to the reference image, named `<image>.rig.json`:

```json
{
  "topology": "mediapipe-face-landmarker-478",
  "name": "hero",
  "width": 820,
  "height": 1024,
  "points": [[x, y], ...]
}
```

- `points` are **pixel** coordinates in the reference image, in the tracker's
  landmark ordering. With MediaPipe Face Landmarker that is 478 points; the
  renderer warps a curated ~110-point control subset of them (face oval, brows,
  eyes, lips, nose, iris centres, cheek/jaw anchors).
- `width`/`height` must match the reference image (the CLI resizes the image to
  the rig if they differ).
- Malformed rigs (missing keys, non-finite or wrongly shaped points, fewer than
  three points, non-positive dimensions) are rejected with `RigFormatError`.

Derive a rig once from a front-facing, neutral-expression reference:

```bash
cpc --derive-rig --character hero.png --model face_landmarker.task
```

This is the only renderer path that imports MediaPipe. For a stylised character
that a detector cannot read, author the sidecar by hand or generate it alongside
the artwork.

## Supported reference contract, and limits

- **Supported:** a single, roughly front-facing character face whose rig is in
  MediaPipe 478 topology (derived or authored). Small authored rigs (any point
  count, warped in full) also work and are what the unit tests use.
- **Reacts to:** head roll/yaw/pitch and relative facial expression (brows,
  eyes/blink, mouth/jaw, lip shape) of the performer.
- **Not supported:** arbitrary-image generative animation, large out-of-plane
  head rotation, occlusion handling, hair/tongue/teeth simulation, relighting,
  multiple faces. These need a generative model whose licensing has not been
  cleared for this repository's intended use.
- **Safe degradation:** an untracked frame, a low-confidence frame, a landmark
  count below the rig's, or non-finite performer geometry all return the last
  good render (or the plain reference image) rather than a broken frame.

## Working resolution

The warp cost scales with output pixels, so the renderer works at a bounded
resolution (640 px long edge by default, `work_max_edge`). A 820×1024 reference
renders at 512×640. Measured on an Apple M1 (CPU, `mediapipe` 0.10.35):

| stage | fps | ms/frame |
|---|---:|---:|
| MediaPipe tracker | ~75 | ~13 |
| rig-warp renderer | ~30 | ~34 |
| full pipeline (serial) | ~21 | ~47 |

Tracker and renderer run serially today; overlapping them on two threads is the
obvious next step if a higher live frame-rate is needed.
