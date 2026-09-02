#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="${CPC_MACBOOK_STATE_DIR:-$HOME/Library/Application Support/CharacterPerformanceCapture/blackbox}"
VENV="$STATE_DIR/venv"
MODEL_DIR="$STATE_DIR/models/Qwen3-VL-Embedding-2B-4bit"
SMOKE_DB="$STATE_DIR/smoke.sqlite3"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DOCTOR_REPORT="$STATE_DIR/camera-doctor-$STAMP.json"
QWEN_REPORT="$STATE_DIR/qwen-mlx-smoke-$STAMP.txt"
SMOKE_IMAGE="$STATE_DIR/synthetic-vision-smoke.png"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ "$(uname -s)" != "Darwin" ] || [ "$(uname -m)" != "arm64" ]; then
  echo "BLOCKED: this bootstrap requires Apple Silicon macOS (Darwin arm64)." >&2
  exit 2
fi

MEM_BYTES="$(sysctl -n hw.memsize)"
MIN_MEM=$((7 * 1024 * 1024 * 1024))
if [ "$MEM_BYTES" -lt "$MIN_MEM" ]; then
  echo "BLOCKED: less than 7 GiB physical memory reported." >&2
  exit 2
fi

FREE_KB="$(df -Pk "$HOME" | awk 'NR==2 {print $4}')"
MIN_FREE_KB=$((6 * 1024 * 1024))
if [ "$FREE_KB" -lt "$MIN_FREE_KB" ]; then
  echo "BLOCKED: need at least 6 GiB free disk for the isolated venv, model, and cache." >&2
  exit 2
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("BLOCKED: Python 3.11+ is required")
print(f"python={sys.version.split()[0]}")
PY

mkdir -p "$STATE_DIR/models"

if [ ! -x "$VENV/bin/python" ]; then
  "$PYTHON_BIN" -m venv "$VENV"
fi

PY="$VENV/bin/python"
PIP="$VENV/bin/pip"

"$PIP" install --upgrade pip setuptools wheel
"$PIP" install -e "${REPO_ROOT}[blackbox-mlx]"

if [ ! -f "$MODEL_DIR/config.json" ] || [ ! -f "$MODEL_DIR/model.safetensors" ]; then
  MODEL_DIR="$MODEL_DIR" "$PY" - <<'PY'
import os
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="mlx-community/Qwen3-VL-Embedding-2B-4bit",
    local_dir=os.environ["MODEL_DIR"],
    allow_patterns=[
        "*.json",
        "*.safetensors",
        "*.jinja",
        "*.txt",
        "*.model",
    ],
)
PY
fi

SMOKE_IMAGE="$SMOKE_IMAGE" "$PY" - <<'PY'
import os
from PIL import Image

size = 224
image = Image.new("RGB", (size, size))
pixels = image.load()
for y in range(size):
    for x in range(size):
        pixels[x, y] = (x * 255 // (size - 1), y * 255 // (size - 1), 96)
image.save(os.environ["SMOKE_IMAGE"])
PY

{
  echo "system=$(sw_vers -productVersion)"
  echo "machine=$(uname -m)"
  echo "memory_bytes=$MEM_BYTES"
  echo "free_kb_before=$FREE_KB"
  echo "repo=$REPO_ROOT"
  echo "model=$MODEL_DIR"
} > "$QWEN_REPORT"

# Collect the project's canonical local camera evidence first. This may trigger
# the normal macOS camera-permission prompt on first use.
"$VENV/bin/cpc" --doctor --camera 0 --doctor-frames 120 > "$DOCTOR_REPORT"

# Prove model load plus text+vision embedding on the constrained MLX path. The
# synthetic image avoids persisting any camera frame for this semantic smoke run.
/usr/bin/time -l "$VENV/bin/cpc-blackbox" \
  --db "$SMOKE_DB" \
  qwen-search "simple synthetic gradient reference" \
  --image "$SMOKE_IMAGE" \
  --runtime mlx \
  --model-path "$MODEL_DIR" \
  --model-id "mlx-community/Qwen3-VL-Embedding-2B-4bit" \
  --dimensions 768 \
  >> "$QWEN_REPORT" 2>&1

rm -f "$SMOKE_IMAGE"

echo "PASS: MacBook camera doctor and MLX Qwen semantic smoke completed."
echo "doctor_report=$DOCTOR_REPORT"
echo "qwen_report=$QWEN_REPORT"
echo "model_dir=$MODEL_DIR"
echo
echo "Next: index one .cpc take with its matching local media, then run qwen-embed"
echo "with --runtime mlx and benchmark the resulting provider/model namespace."
