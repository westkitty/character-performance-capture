import json
import socket

from cpc.performance import PerformanceFrame
from cpc.runtime_adapter import FrameCallbackAdapter, LoopbackJsonServer


def _frame():
    return PerformanceFrame(0, 0.0, True, "test", blendshapes={"jawOpen": 0.5})


def test_callback_maps_portable_state():
    seen = []
    adapter = FrameCallbackAdapter(seen.append)
    adapter.publish(_frame())
    assert seen[0]["frame_index"] == 0
    assert seen[0]["blendshapes"]["jawOpen"] == 0.5
    assert "pixels" not in seen[0]


def test_loopback_server_binds_local_only_and_cleans_disconnect():
    server = LoopbackJsonServer(0)
    server.start()
    host, port = server.address
    assert host == "127.0.0.1"
    client = socket.create_connection((host, port))
    server.poll_client()
    server.publish(_frame())
    payload = json.loads(client.recv(4096).decode().strip())
    assert payload["tracker"] == "test"
    client.close()
    server.publish(_frame())
    server.close()
    assert server.address is None
