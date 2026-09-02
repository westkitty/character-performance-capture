# Hardware validation

CPC deliberately separates deterministic CI proof from physical webcam/model proof.

The `--doctor` route exercises the same local camera and tracker adapters without opening a preview window and without persisting camera pixels.

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

## 3. Evidence boundary

A successful doctor run can verify the specific machine, camera, dependency set, and tracker/model combination used in that run. It does not prove another machine, another camera, OBS output, or a future character renderer.

When comparing machines, preserve the JSON output from the same command and sample count. Requested camera settings are not treated as proof of negotiated settings; the report records both requested values and the values reported by the active OpenCV backend.
