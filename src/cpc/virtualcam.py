from __future__ import annotations

from typing import Any, Self

import cv2
import numpy as np

from .pipeline import Frame

_INSTALL_HINT = (
    "virtual-camera output requested but pyvirtualcam is not installed. "
    "Install character-performance-capture[output-virtualcam]. On macOS this "
    "backend also requires the OBS Virtual Camera system extension (install OBS "
    "and start its Virtual Camera once)."
)


class VirtualCameraSink:
    """Replaceable output sink that publishes rendered BGR frames to a virtual camera.

    It performs no disk writes and no network access. Dimensions and FPS are
    negotiated explicitly with the backend at ``start()``; frames of a different
    size are resized to the negotiated size before sending.
    """

    name = "virtualcam"

    def __init__(
        self,
        width: int,
        height: int,
        fps: float = 30.0,
        *,
        backend: str | None = None,
        camera_factory: Any | None = None,
    ) -> None:
        if int(width) <= 0 or int(height) <= 0:
            raise ValueError("virtual camera width/height must be positive")
        if not (fps and fps > 0):
            raise ValueError("virtual camera fps must be positive")
        self.width = int(width)
        self.height = int(height)
        self.fps = float(fps)
        self.backend = backend
        self._camera_factory = camera_factory
        self._camera: Any = None
        self.device: str | None = None

    def start(self) -> None:
        if self._camera is not None:
            return
        factory = self._camera_factory
        if factory is None:
            try:
                import pyvirtualcam
            except ImportError as exc:  # pragma: no cover - needs the extra absent
                raise RuntimeError(_INSTALL_HINT) from exc

            def factory(**kwargs: Any) -> Any:
                return pyvirtualcam.Camera(**kwargs)

        kwargs: dict[str, Any] = {
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "print_fps": False,
        }
        if self.backend:
            kwargs["backend"] = self.backend
        try:
            self._camera = factory(**kwargs)
        except Exception as exc:
            raise RuntimeError(f"could not open virtual camera backend: {exc}") from exc
        self.device = getattr(self._camera, "device", None)
        self.backend = getattr(self._camera, "backend", self.backend)

    def send(self, frame: Frame) -> None:
        if self._camera is None:
            self.start()
        assert self._camera is not None
        if frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("virtual camera frames must be (H, W, 3) BGR")
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = self._letterbox(frame)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self._camera.send(np.ascontiguousarray(rgb, dtype=np.uint8))
        sleeper = getattr(self._camera, "sleep_until_next_frame", None)
        if callable(sleeper):
            sleeper()

    def _letterbox(self, frame: Frame) -> np.ndarray:
        """Aspect-preserving fit into the negotiated size with black padding."""

        src_h, src_w = frame.shape[:2]
        scale = min(self.width / src_w, self.height / src_h)
        new_w = max(1, round(src_w * scale))
        new_h = max(1, round(src_h * scale))
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        off_x = (self.width - new_w) // 2
        off_y = (self.height - new_h) // 2
        canvas[off_y : off_y + new_h, off_x : off_x + new_w] = resized
        return canvas

    def close(self) -> None:
        if self._camera is None:
            return
        try:
            self._camera.close()
        finally:
            self._camera = None

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
