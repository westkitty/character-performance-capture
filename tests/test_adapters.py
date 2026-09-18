from cpc.adapters import default_adapter_registry


def test_registry_has_truthful_readiness_and_provenance(tmp_path):
    registry = {item.adapter_id: item for item in default_adapter_registry(mediapipe_model=tmp_path / "missing.task")}
    assert registry["tracker.null"].readiness == "ready"
    assert registry["renderer.rig-warp"].readiness == "ready"
    assert registry["reference.synthetic"].detail.startswith("Deterministic fixture")
    assert registry["tracker.mediapipe-face-landmarker"].readiness in {"missing-dependency", "missing-model"}
    assert all(item.provenance for item in registry.values())
