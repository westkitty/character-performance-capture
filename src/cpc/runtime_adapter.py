from __future__ import annotations

import json
import socket
from collections.abc import Callable
from dataclasses import dataclass

from .performance import PerformanceFrame


def performance_payload(frame: PerformanceFrame) -> dict:
    return {
        "frame_index": frame.frame_index,
        "timestamp_s": frame.timestamp_s,
        "tracked": frame.tracked,
        "tracker": frame.tracker,
        "profile": frame.profile,
        "tracking_confidence": frame.tracking_confidence,
        "blendshapes": dict(frame.blendshapes),
        "head_rotation_deg": list(frame.head_rotation_deg) if frame.head_rotation_deg else None,
        "gaze_left": list(frame.gaze_left) if frame.gaze_left else None,
        "gaze_right": list(frame.gaze_right) if frame.gaze_right else None,
        "face_transform": list(frame.face_transform) if frame.face_transform else None,
        "landmarks": [point.to_dict() for point in frame.landmarks],
    }


@dataclass
class FrameCallbackAdapter:
    callback: Callable[[dict], None]

    def publish(self, frame: PerformanceFrame) -> None:
        self.callback(performance_payload(frame))

    def close(self) -> None:
        return None


class LoopbackJsonServer:
    """Single-client newline-delimited JSON performance stream bound to loopback only."""

    def __init__(self, port: int = 0) -> None:
        self.port = int(port)
        self._server: socket.socket | None = None
        self._client: socket.socket | None = None

    @property
    def address(self) -> tuple[str, int] | None:
        if self._server is None:
            return None
        host, port = self._server.getsockname()
        return str(host), int(port)

    def start(self) -> None:
        if self._server is not None:
            return
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", self.port))
        server.listen(1)
        server.setblocking(False)
        self._server = server

    def poll_client(self) -> None:
        if self._server is None:
            self.start()
        if self._client is not None:
            return
        assert self._server is not None
        try:
            client, _ = self._server.accept()
        except BlockingIOError:
            return
        client.setblocking(False)
        self._client = client

    def publish(self, frame: PerformanceFrame) -> None:
        self.poll_client()
        if self._client is None:
            return
        data = (json.dumps(performance_payload(frame), separators=(",", ":")) + "\n").encode()
        try:
            self._client.sendall(data)
        except (BrokenPipeError, ConnectionResetError, OSError):
            try:
                self._client.close()
            finally:
                self._client = None

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
        if self._server is not None:
            self._server.close()
            self._server = None
