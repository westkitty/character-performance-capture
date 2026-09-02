import json
from pathlib import Path

import numpy as np
import pytest

from cpc.rig import CharacterRig, RigFormatError, default_rig_path, load_rig, save_rig


def _valid_payload() -> dict:
    pts = [[float(x), float(y)] for x, y in np.random.default_rng(0).integers(0, 200, (30, 2))]
    return {"topology": "test-30", "name": "unit", "width": 200, "height": 200, "points": pts}


def test_round_trip_save_and_load(tmp_path: Path):
    payload = _valid_payload()
    path = tmp_path / "char.png.rig.json"
    path.write_text(json.dumps(payload))
    rig = load_rig(path)
    assert rig.point_count == 30
    assert rig.width == 200 and rig.height == 200

    out = tmp_path / "again.rig.json"
    save_rig(rig, out)
    again = load_rig(out)
    assert np.allclose(again.points, rig.points)
    assert again.topology == "test-30"


def test_default_rig_path_sits_beside_reference():
    assert default_rig_path("a/b/hero.png") == Path("a/b/hero.png.rig.json")


def test_load_rig_missing_file_raises_filenotfound(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_rig(tmp_path / "nope.rig.json")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.pop("points"),
        lambda p: p.update(points=[]),
        lambda p: p.update(points=[[1.0, 2.0, 3.0]]),
        lambda p: p.update(points=[[1.0, "x"]]),
        lambda p: p.update(points=[[float("nan"), 1.0]] * 5),
        lambda p: p.update(width=0),
        lambda p: p.update(width=-10),
        lambda p: p.update(height="tall"),
        lambda p: p.update(points=[[1.0, 2.0], [3.0, 4.0]]),  # < 3 points
    ],
)
def test_load_rig_rejects_malformed(tmp_path: Path, mutate):
    payload = _valid_payload()
    mutate(payload)
    path = tmp_path / "bad.rig.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(RigFormatError):
        load_rig(path)


def test_load_rig_rejects_non_object_json(tmp_path: Path):
    path = tmp_path / "list.rig.json"
    path.write_text("[1, 2, 3]")
    with pytest.raises(RigFormatError):
        load_rig(path)


def test_character_rig_validates_on_construction():
    with pytest.raises(RigFormatError):
        CharacterRig(width=10, height=10, points=np.zeros((2, 2), dtype=np.float32))
    with pytest.raises(RigFormatError):
        CharacterRig(width=0, height=10, points=np.zeros((5, 2), dtype=np.float32))
