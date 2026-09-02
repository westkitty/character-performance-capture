from __future__ import annotations

import math
import platform
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .semantic_qwen import SemanticEmbeddingError, sample_video_window

DEFAULT_MLX_MODEL_ID = "mlx-community/Qwen3-VL-Embedding-2B-4bit"
DEFAULT_DIMENSIONS = 768
DEFAULT_SAMPLE_FPS = 2.0
DEFAULT_MAX_FRAMES = 4
DEFAULT_MAX_SIDE = 448
PROVIDER = "qwen3-vl-mlx"


class Qwen3VLMLXEmbedder:
    """Apple-Silicon Qwen3-VL embedding adapter using the MIT mlx-vlm runtime.

    CPC requires a pre-downloaded local model directory. Passing a local path to
    mlx-vlm keeps model resolution local; the separate MacBook bootstrap is the
    only path in this project that explicitly downloads the selected model.

    The 8 GB MacBook profile deliberately represents a performance window as a
    small chronological set of still frames rather than handing a full video to
    the model. This bounds activation pressure while keeping visual semantics in
    one multimodal embedding input.
    """

    provider = PROVIDER

    def __init__(
        self,
        model_path: str | Path,
        *,
        model_id: str = DEFAULT_MLX_MODEL_ID,
        dimensions: int = DEFAULT_DIMENSIONS,
        sample_fps: float = DEFAULT_SAMPLE_FPS,
        max_frames: int = DEFAULT_MAX_FRAMES,
        max_side: int = DEFAULT_MAX_SIDE,
        verbose: bool = False,
    ) -> None:
        self.model_path = Path(model_path).expanduser().resolve()
        if not self.model_path.is_dir():
            raise FileNotFoundError(f"local MLX Qwen model directory not found: {self.model_path}")
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than zero")
        if sample_fps <= 0 or not math.isfinite(sample_fps):
            raise ValueError("sample_fps must be finite and greater than zero")
        if max_frames <= 0:
            raise ValueError("max_frames must be greater than zero")
        if max_side <= 0:
            raise ValueError("max_side must be greater than zero")

        self.model_id = model_id.strip() or self.model_path.name
        self.dimensions = dimensions
        self.sample_fps = sample_fps
        self.max_frames = max_frames
        self.max_side = max_side
        self.verbose = verbose
        self.model = f"{self.model_id}@{self.dimensions}d"
        self._model: Any = None
        self._processor: Any = None
        self._mx: Any = None
        self._prepare_inputs: Any = None
        self._get_chat_template: Any = None
        self._create_causal_mask: Any = None

    @staticmethod
    def _require_apple_silicon() -> None:
        if platform.system() != "Darwin" or platform.machine().lower() != "arm64":
            raise SemanticEmbeddingError(
                "the MLX Qwen runtime requires Apple Silicon macOS (Darwin arm64)"
            )

    def _load(self) -> None:
        if self._model is not None:
            return
        self._require_apple_silicon()
        try:
            import mlx.core as mx
            from mlx_vlm import load
            from mlx_vlm.models.cache import create_causal_mask
            from mlx_vlm.prompt_utils import get_chat_template
            from mlx_vlm.utils import prepare_inputs
        except ImportError as exc:
            raise SemanticEmbeddingError(
                "MLX dependencies are missing. Install "
                "character-performance-capture[blackbox-mlx]."
            ) from exc

        try:
            # model_path is already verified to be a local directory. mlx-vlm's
            # loader therefore does not resolve a Hub repository here.
            model, processor = load(str(self.model_path))
        except Exception as exc:
            raise SemanticEmbeddingError(
                f"failed to load local MLX Qwen model from {self.model_path}: {exc}"
            ) from exc

        if not hasattr(model, "get_input_embeddings") or not hasattr(model, "language_model"):
            raise SemanticEmbeddingError("loaded MLX model does not expose Qwen3-VL hidden states")

        self._mx = mx
        self._model = model
        self._processor = processor
        self._prepare_inputs = prepare_inputs
        self._get_chat_template = get_chat_template
        self._create_causal_mask = create_causal_mask

    def _attention_mask(self, attention_mask: Any) -> Any:
        mx = self._mx
        if attention_mask is None or bool(mx.all(attention_mask).item()):
            return "causal"
        valid = attention_mask.astype(mx.bool_)
        causal = self._create_causal_mask(attention_mask.shape[1])
        key_mask = mx.expand_dims(valid, axis=(1, 2))
        query_mask = mx.expand_dims(valid, axis=(1, 3))
        return causal[None, None, :, :] & key_mask & query_mask

    def _finalize_vector(self, hidden_states: Any, attention_mask: Any) -> list[float]:
        mx = self._mx
        if attention_mask is None:
            vector = hidden_states[0, -1]
        else:
            from_end = mx.argmax(attention_mask[:, ::-1], axis=1)
            columns = attention_mask.shape[1] - from_end - 1
            vector = hidden_states[mx.arange(hidden_states.shape[0]), columns][0]

        if vector.shape[-1] < self.dimensions:
            raise SemanticEmbeddingError(
                f"requested {self.dimensions} dimensions but model produced {vector.shape[-1]}"
            )
        vector = vector[: self.dimensions]
        norm = mx.linalg.norm(vector)
        mx.eval(vector, norm)
        norm_value = float(norm.item())
        if not math.isfinite(norm_value) or norm_value <= 0.0:
            raise SemanticEmbeddingError("MLX Qwen produced a zero or non-finite embedding norm")
        vector = vector / norm
        mx.eval(vector)
        return [float(value) for value in vector.tolist()]

    def _embed_content(
        self,
        *,
        images: Sequence[Any] = (),
        text: str = "",
        instruction: str,
    ) -> list[float]:
        self._load()
        content: list[dict[str, Any]] = [{"type": "image"} for _ in images]
        if text.strip():
            content.append({"type": "text", "text": text.strip()})
        if not content:
            raise ValueError("semantic query requires text and/or an image")

        messages = [
            {"role": "system", "content": [{"type": "text", "text": instruction}]},
            {"role": "user", "content": content},
        ]
        try:
            prompt = self._get_chat_template(
                self._processor,
                messages,
                add_generation_prompt=True,
            )
            image_token_index = getattr(
                getattr(self._model, "config", None), "image_token_index", None
            )
            inputs = self._prepare_inputs(
                self._processor,
                images=list(images) or None,
                prompts=prompt,
                image_token_index=image_token_index,
                padding_side="right",
                truncation=True,
                max_length=8192,
            )
            input_ids = inputs["input_ids"]
            attention_mask = inputs.get("attention_mask")
            features = self._model.get_input_embeddings(
                input_ids=input_ids,
                pixel_values=inputs.get("pixel_values"),
                pixel_values_videos=inputs.get("pixel_values_videos"),
                image_grid_thw=inputs.get("image_grid_thw"),
                video_grid_thw=inputs.get("video_grid_thw"),
                mask=attention_mask,
            )
            hidden_states = self._model.language_model.model(
                input_ids,
                inputs_embeds=features.inputs_embeds,
                mask=self._attention_mask(attention_mask),
                position_ids=features.position_ids,
                visual_pos_masks=features.visual_pos_masks,
                deepstack_visual_embeds=features.deepstack_visual_embeds,
            )
            return self._finalize_vector(hidden_states, attention_mask)
        except SemanticEmbeddingError:
            raise
        except Exception as exc:
            raise SemanticEmbeddingError(f"MLX Qwen embedding failed: {exc}") from exc

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
            images=frames,
            text="Chronological frames sampled from one performance segment.",
            instruction="Represent this performance segment for retrieval.",
        )

    def embed_query(self, text: str = "", *, image_path: str | Path | None = None) -> list[float]:
        images: list[Any] = []
        if image_path is not None:
            try:
                from PIL import Image
            except ImportError as exc:
                raise SemanticEmbeddingError(
                    "Pillow is required for MLX image queries. Install "
                    "character-performance-capture[blackbox-mlx]."
                ) from exc
            source = Path(image_path).expanduser()
            if not source.is_file():
                raise FileNotFoundError(f"query image not found: {source}")
            with Image.open(source) as image:
                images.append(image.convert("RGB").copy())
        return self._embed_content(
            images=images,
            text=text,
            instruction="Retrieve performance segments relevant to this query.",
        )
