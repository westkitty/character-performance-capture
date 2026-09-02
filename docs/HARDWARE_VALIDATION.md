# Hardware validation

CPC deliberately separates deterministic CI proof from physical webcam/model proof.

The `--doctor` route exercises the same local camera and tracker adapters without opening a preview window and without persisting camera pixels.

## 0. Frame source note

On macOS, opening a camera from a shell/CLI process requires the parent
application to hold the camera-permission (TCC) grant. Where that grant cannot be
given (headless CI, an automation agent), run every route below with
`--video CLIP.mp4 [--loop]` in place of `--camera N`: the capture → tracker →
renderer → output path is byte-for-byte the same, only the frame source differs.
A real webcam run additionally proves camera open/negotiation/backend selection.

## 1. Camera-only proof

From an installed development environment:

```bash
cpc --doctor --camera 0 --doctor-frames 120
```

The command prints a JSON report containing:

- OS, machine architecture, Python, OpenCV, and optional MediaPipe versions
- OpenCV camera backend actually selected
- requested versus camera-reported width, height, and FPS
- observed frame dimensions
- sampled frame count
- overall loop FPS
- average and p95 camera-read time
- tracker timing and tracked-frame count

With the default null tracker, `tracked_frames` is expected to be zero. This run is still useful because it verifies camera opening, real frame reads, backend selection, negotiated camera properties, and the local execution environment.

To preserve the metadata report for comparison without storing camera pixels:

```bash
cpc --doctor --camera 0 --doctor-frames 120 > camera-doctor.json
```

## 2. Real MediaPipe proof

Install the optional adapter and supply a Face Landmarker `.task` model you are authorized to use:

```bash
pip install -e '.[tracker-mediapipe,dev]'
cpc \
  --doctor \
  --tracker mediapipe \
  --model /path/to/face_landmarker.task \
  --camera 0 \
  --doctor-frames 120
```

This path opens the camera, initializes the supplied local model, runs real tracker inference on sampled camera frames, and reports tracker processing time plus the number/rate of frames on which a face was tracked.

CPC does not download the model and does not write sampled frames to disk.

## 3. Character renderer and virtual-camera proof

```bash
pip install -e '.[tracker-mediapipe,output-virtualcam,dev]'

# derive the character rig once (front-facing neutral reference)
cpc --derive-rig --character char.png --model /path/to/face_landmarker.task

# full live route to a rendered mp4 and .cpc take
cpc --video clip.mp4 --loop --mirror \
    --tracker mediapipe --model /path/to/face_landmarker.task \
    --render rig --character char.png \
    --record-performance takes/validation.cpc --record-video rendered.mp4 \
    --no-window --frames 150
cpc --inspect-performance takes/validation.cpc

# full live route to the virtual camera
cpc --video clip.mp4 --loop \
    --tracker mediapipe --model /path/to/face_landmarker.task \
    --render rig --character char.png \
    --virtual-camera --vcam-size 1280x720 --no-window --frames 240
```

Verify: model loads; frames reach the tracker; real tracking state and timings;
the rendered video varies frame to frame (renderer reacts); the `.cpc` holds only
portable state; an interrupted run leaves a recoverable `.partial`; the virtual
camera negotiates its size and closes cleanly. Both the virtual-camera output
(send side) and an external consumer reading the 1280x720 stream at 30 FPS
(receive side) have been verified on Apple Silicon.

## 4. Evidence tiers and boundary

Validation is organized into three distinct, non-overlapping evidence tiers:

1. **Deterministic CI proof**: Automated tests in CI verify schema constraints, geometry algorithms, rig parsing, safe degradation, lifecycle rollback, and CLI mechanics without requiring physical hardware or GUI access.
2. **Physical webcam & MediaPipe proof**: Real AVFoundation webcam capture (1080p @ 30 FPS), real-time MediaPipe CPU tracking (~14.5 ms/frame, ~89% face tracking rate), live rig-warp character rendering, and portable `.cpc` take recording/replay without camera pixels.
3. **Virtual-camera receive proof**: OBS Virtual Camera 1280x720 output actively consumed by an external capture client at 30.29 FPS with clean startup/shutdown and no buffer mismatch.

When comparing machines, preserve the JSON output from the same command and sample count. Requested camera settings are not treated as proof of negotiated settings; the report records both requested values and the values reported by the active OpenCV backend.
