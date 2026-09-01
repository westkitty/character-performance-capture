# CPC Performance Capture Format v1

CPC separates **performance** from **rendering**. A `.cpc` file contains performer-state data only; it does not contain camera pixels, reference portraits, generated character frames, or model weights.

## Why this exists

A captured take should survive a renderer change. The format therefore stores portable named expression coefficients, optional normalized landmarks, optional gaze/head state, and an optional 4x4 face transform instead of renderer-specific tensors.

## Container

The file is UTF-8 JSON Lines (one JSON object per line):

1. `header`
2. zero or more `frame` records
3. `end` when the recording closes cleanly

The writer records to `<name>.cpc.partial` and atomically renames it to `<name>.cpc` only after the end record is durable. If the process is interrupted, the `.partial` file remains inspectable and replayable up to the last complete line.

## Header

Required fields:

- `format`: `cpc-performance-capture`
- `version`: `1`
- `tracker`: backend identity
- `profile`: coefficient naming/profile identity
- `started_at_utc`: ISO-8601 timestamp
- `metadata`: JSON-safe capture metadata

## Frame

Every frame has:

- monotonically increasing `frame_index`
- monotonically increasing `timestamp_s`
- `tracked`
- `tracker`
- `profile`

Optional portable state:

- `tracking_confidence` in `[0, 1]`
- named normalized `blendshapes` in `[0, 1]`
- `head_rotation_deg` as `(pitch, yaw, roll)`
- normalized per-eye gaze vectors
- flattened 4x4 `face_transform`
- tracker-neutral landmark records
- JSON-safe metadata

## End record

A clean recording ends with declared `frame_count` and `duration_s`. Readers treat a capture without this record as incomplete but recoverable.

## Compatibility rule

Unknown future format versions must be rejected rather than silently guessed. New tracker profiles may add coefficient names without changing the container version as long as the meanings of existing fields remain stable.
