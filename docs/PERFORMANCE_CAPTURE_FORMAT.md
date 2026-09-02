# CPC Performance Capture Format v1

CPC separates **performance** from **rendering**. A `.cpc` file contains performer-state data only; it does not contain camera pixels, reference portraits, generated character frames, or model weights.

## Why this exists

A captured take should survive a renderer change. The format therefore stores portable named expression coefficients, optional normalized landmarks, optional gaze/head state, and an optional 4x4 face transform instead of renderer-specific tensors.

## Container

The file is UTF-8 JSON Lines (one JSON object per line):

1. `header`
2. zero or more `frame` records
3. `end` when the recording closes cleanly

The writer records to `<name>.cpc.partial`. On clean close it durably writes the end record, then commits the completed file without replacing an independently existing `<name>.cpc`. If another process or user creates that final path while recording is in progress, CPC leaves the final file untouched and preserves the completed `.partial` file for recovery.

If the process is interrupted before clean close, the `.partial` file remains inspectable and replayable up to the last complete line.

## Header

Required fields:

- `format`: `cpc-performance-capture`
- `version`: integer `1`
- `tracker`: non-empty backend identity string
- `profile`: non-empty coefficient naming/profile identity string
- `started_at_utc`: non-empty ISO-8601 timestamp string
- `metadata`: JSON-safe object

## Frame

Every frame has:

- non-negative integer `frame_index`, strictly increasing across the capture
- finite non-negative numeric `timestamp_s`, monotonically increasing across the capture
- boolean `tracked`
- non-empty string `tracker`
- non-empty string `profile`

Optional portable state:

- finite numeric `tracking_confidence` in `[0, 1]`
- named finite numeric `blendshapes` in `[0, 1]`
- `head_rotation_deg` as three finite numeric values `(pitch, yaw, roll)`
- per-eye gaze vectors as two finite numeric values
- flattened 4x4 `face_transform` as 16 finite numeric values
- tracker-neutral landmark records with finite coordinates
- JSON-safe metadata

Readers reject semantic type confusion rather than coercing strings, booleans, or other JSON types into these fields.

## End record

A clean recording ends with:

- non-negative integer `frame_count`, exactly matching the number of frame records
- finite non-negative numeric `duration_s`, matching the elapsed time between the first and last frame timestamps (or `0.0` for fewer than two frames)

No record may appear after the end record. A capture without an end record is incomplete but recoverable.

## Compatibility rule

Unknown future format versions must be rejected rather than silently guessed. New tracker profiles may add coefficient names without changing the container version as long as the meanings of existing fields remain stable.
