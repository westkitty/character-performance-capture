from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any, Sequence

import cv2

DEFAULT_MODEL_ID = "Qwen/Qwen3-VL-Embedding-2B"
DEFAULT_DIMENSIONS = 768
DEFAULT_SAMPLE_FPS = 4.0
DEFAULT_MAX_FRAMES = 16
DEFAULT_MAX_SIDE = 640
PROVIDER = "qwen3-vl-local"


class SemanticEmbeddingError(RuntimeError):
    """Raised when an optional local semantic embedding operation cannot run."""


def _resolve_device(torch: Any, requested: str) -> tuple[str, Any]:
    if requested not in {"auto", "cpu", "mps", "cuda"}:
        raise ValueError(f"unsupported device: {requested}")
    if requested == "cuda":
        if not torch.cuda.is_available():
            raise SemanticEmbeddingError("CUDA requested but no CUDA device is available")
        return "cuda", torch.bfloat16
    if requested == "mps":
        if not (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()):
            raise SemanticEmbeddingError("MPS requested but Apple Metal acceleration is unavailable")
        return "mps", torch.float16
    if requested == "cpu":
        return "cpu", torch.float32
    if torch.cuda.is_available():
        return "cuda", torch.bfloat16
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps", torch.float16
    return "cpu", torch.float32


def sample_video_window(
    path: str | Path,
    start_s: float,
    end_s: float,
    *,
    sample_fps: float = DEFAULT_SAMPLE_FPS,
    max_frames: int = DEFAULT_MAX_FRAMES,
    max_side: int = DEFAULT_MAX_SIDE,
) -> list[Any]:
    """Sample a bounded media window as PIL RGB frames without external FFmpeg tooling."""
    source = Path(path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"media file not found: {source}")
    if start_s < 0 or not math.isfinite(start_s):
        raise ValueError("start_s must be finite and non-negative")
    if end_s <= start_s or not math.isfinite(end_s):
        raise ValueError("end_s must be finite and greater than start_s")
    if sample_fps <= 0 or not math.isfinite(sample_fps):
        raise ValueError("sample_fps must be finite and greater than zero")
    if max_frames <= 0:
        raise ValueError("max_frames must be greater than zero")
    if max_side <= 0:
        raise ValueError("max_side must be greater than zero")

    try:
        from PIL import Image
    except ImportError as exc:
        raise SemanticEmbeddingError(
            "Pillow is required for local Qwen video embeddings. "
            "Install character-performance-capture[blackbox-qwen]."
        ) from exc

    duration = end_s - start_s
    count = min(max_frames, max(1, int(math.ceil(duration * sample_fps))))
    safe_end = max(start_s, end_s - 1e-3)
    if count == 1:
        times = [start_s]
    else:
        times = [start_s + (safe_end - start_s) * index / (count - 1) for index in range(count)]

    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        capture.release()
        raise SemanticEmbeddingError(f"could not open media file: {source}")

    frames: list[Any] = []
    try:
        for timestamp_s in times:
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp_s * 1000.0)
            ok, frame = capture.read()
            if not ok or frame is None:
                continue
            height, width = frame.shape[:2]
            largest = max(height, width)
            if largest > max_side:
                scale = max_side / largest
                frame = cv2.resize(
                    frame,
                    (max(1, round(width * scale)), max(1, round(height * scale))),
                    interpolation=cv2.INTER_AREA,
                )
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(Image.fromarray(rgb))
    finally:
        capture.release()

    if not frames:
        raise SemanticEmbeddingError(
            f"no readable frames in media window {start_s:.3f}-{end_s:.3f}s: {source}"
        )
    return frames


class Qwen3VLSemanticEmbedder:
    """Local-only Qwen3-VL semantic adapter for CPC performance-library segments.

    The adapter requires a pre-downloaded local model directory. It never resolves
    a remote Hugging Face model ID and passes ``local_files_only=True`` to model
    and processor loading.
    """

    provider = PROVIDER

    def __init__(
        self,
        model_path: str | Path,
        *,
        model_id: str = DEFAULT_MODEL_ID,
        dimensions: int = DEFAULT_DIMENSIONS,
        device: str = "auto",
        sample_fps: float = DEFAULT_SAMPLE_FPS,
        max_frames: int = DEFAULT_MAX_FRAMES,
        max_side: int = DEFAULT_MAX_SIDE,
        verbose: bool = False,
    ) -> None:
        self.model_path = Path(model_path).expanduser().resolve()
        if not self.model_path.is_dir():
            raise FileNotFoundError(f"local Qwen model directory not found: {self.model_path}")
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than zero")
        self.model_id = model_id.strip() or self.model_path.name
        self.dimensions = dimensions
        self.device_request = device
        self.sample_fps = sample_fps
        self.max_frames = max_frames
        self.max_side = max_side
        self.verbose = verbose
        self.model = f"{self.model_id}@{self.dimensions}d"
        self._model: Any = None
        self._processor: Any = None
        self._torch: Any = None
        self._process_vision_info: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from qwen_vl_utils import process_vision_info
            from transformers.models.qwen3_vl.modeling_qwen3_vl import (
                Qwen3VLModel,
                Qwen3VLPreTrainedModel,
            )
            from transformers.models.qwen3_vl.processing_qwen3_vl import Qwen3VLProcessor
        except ImportError as exc:
            raise SemanticEmbeddingError(
                "Local Qwen embedding dependencies are missing. Install "
                "character-performance-capture[blackbox-qwen]."
            ) from exc

        device, dtype = _resolve_device(torch, self.device_request)
        if device == "mps":
            attention_backend = "eager"
            os.environ.setdefault("TRANSFORMERS_DISABLE_TORCH_CHECK", "1")
        else:
            attention_backend = None

        class _EmbeddingBackbone(Qwen3VLPreTrainedModel):
            def __init__(self, config: Any) -> None:
                super().__init__(config)
                self.model = Qwen3VLModel(config)
                self.post_init()

            def get_input_embeddings(self):
                return self.model.get_input_embeddings()

            def set_input_embeddings(self, value):
                self.model.set_input_embeddings(value)

            def forward(
                self,
                input_ids=None,
                attention_mask=None,
                pixel_values=None,
                pixel_values_videos=None,
                image_grid_thw=None,
                video_grid_thw=None,
                position_ids=None,
                past_key_values=None,
                inputs_embeds=None,
                cache_position=None,
                **kwargs,
            ):
                return self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    pixel_values=pixel_values,
                    pixel_values_videos=pixel_values_videos,
                    image_grid_thw=image_grid_thw,
                    video_grid_thw=video_grid_thw,
                    position_ids=position_ids,
                    past_key_values=past_key_values,
                    inputs_embeds=inputs_embeds,
                    cache_position=cache_position,
                    **kwargs,
                )

        load_kwargs: dict[str, Any] = {
            "local_files_only": True,
            "trust_remote_code": False,
            "torch_dtype": dtype,
        }
        if attention_backend is not None:
            load_kwargs["attn_implementation"] = attention_backend

        try:
            processor = Qwen3VLProcessor.from_pretrained(
                str(self.model_path),
                padding_side="right",
                local_files_only=True,
            )
            model = _EmbeddingBackbone.from_pretrained(str(self.model_path), **load_kwargs)
            model = model.to(device)
            model.eval()
        except Exception as exc:
            raise SemanticEmbeddingError(
                f"failed to load local Qwen embedding model from {self.model_path}: {exc}"
            ) from exc

        self._torch = torch
        self._process_vision_info = process_vision_info
        self._processor = processor
        self._model = model

    @staticmethod
    def _pool_last(hidden_state: Any, attention_mask: Any, torch: Any) -> Any:
        reversed_mask = attention_mask.flip(dims=[1])
        from_end = reversed_mask.argmax(dim=1)
        columns = attention_mask.shape[1] - from_end - 1
        rows = torch.arange(hidden_state.shape[0], device=hidden_state.device)
        return hidden_state[rows, columns]

    def _finalize_vector(self, vector: Any) -> list[float]:
        if vector.shape[-1] < self.dimensions:
            raise SemanticEmbeddingError(
                f"requested {self.dimensions} dimensions but model produced {vector.shape[-1]}"
            )
        vector = vector[: self.dimensions]
        norm = self._torch.linalg.vector_norm(vector)
        if norm <= 0:
            raise SemanticEmbeddingError("Qwen produced a zero-norm embedding")
        vector = vector / norm
        return vector.detach().cpu().float().tolist()

    def _embed_content(self, content: Sequence[dict[str, Any]], instruction: str) -> list[float]:
        self._load()
        conversation = [
            {"role": "system", "content": [{"type": "text", "text": instruction}]},
            {"role": "user", "content": list(content)},
        ]
        conversations = [conversation]
        try:
            prompt = self._processor.apply_chat_template(
                conversations,
                tokenize=False,
                add_generation_prompt=True,
            )
            images, video_inputs, video_kwargs = self._process_vision_info(
                conversations,
                image_patch_size=16,
                return_video_metadata=True,
                return_video_kwargs=True,
            )
            if video_inputs is not None:
                videos, video_metadata = zip(*video_inputs)
                videos = list(videos)
                video_metadata = list(video_metadata)
            else:
                videos, video_metadata = None, None
            inputs = self._processor(
                text=prompt,
                images=images,
                videos=videos,
                video_metadata=video_metadata,
                padding=True,
                return_tensors="pt",
                **video_kwargs,
            )
            moved = {
                key: value.to(self._model.device) if hasattr(value, "to") else value
                for key, value in inputs.items()
            }
            with self._torch.no_grad():
                output = self._model(**moved)
                pooled = self._pool_last(
                    output.last_hidden_state,
                    moved["attention_mask"],
                    self._torch,
                )[0]
            return self._finalize_vector(pooled)
        except SemanticEmbeddingError:
            raise
        except Exception as exc:
            raise SemanticEmbeddingError(f"Qwen embedding failed: {exc}") from exc

    def embed_video_window(self, path: str | Path, start_s: float, end_s: float) -> list[float]:
        frames = sample_video_window(
            path,
            start_s,
            end_s,
            sample_fps=self.sample_fps,
            max_frames=self.max_frames,
            max_side=self.max_side,
        )
        return self._embed_content(
            [{"type": "video", "video": frames}],
            "Represent this performance video segment for retrieval.",
        )

    def embed_query(self, text: str = "", *, image_path: str | Path | None = None) -> list[float]:
        content: list[dict[str, Any]] = []
        if image_path is not None:
            try:
                from PIL import Image
            except ImportError as exc:
                raise SemanticEmbeddingError(
                    "Pillow is required for image queries. Install "
                    "character-performance-capture[blackbox-qwen]."
                ) from exc
            source = Path(image_path).expanduser()
            if not source.is_file():
                raise FileNotFoundError(f"query image not found: {source}")
            with Image.open(source) as image:
                content.append({"type": "image", "image": image.convert("RGB").copy()})
        if text.strip():
            content.append({"type": "text", "text": text.strip()})
        if not content:
            raise ValueError("semantic query requires text and/or an image")
        return self._embed_content(
            content,
            "Retrieve performance video segments relevant to this query.",
        )
