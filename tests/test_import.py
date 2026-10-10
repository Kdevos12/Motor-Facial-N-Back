import numpy as np
import pytest

from mfnb.motion.importers.bvh import forward_kinematics, parse_bvh
from mfnb.motion.importers.cmu import CURATED, JOINT_MAP, face_camera, segment, to_canonical
from mfnb.motion.importers.pack import decode_frames, encode_frames, load_packs
from mfnb.motion.skeleton import J

MINI = """HIERARCHY
ROOT hip
{
  OFFSET 0 0 0
  CHANNELS 6 Xposition Yposition Zposition Zrotation Yrotation Xrotation
  JOINT abdomen
  {
    OFFSET 0 10 0
    CHANNELS 3 Zrotation Xrotation Yrotation
    End Site
    {
      OFFSET 0 5 0
    }
  }
  JOINT lThigh
  {
    OFFSET 10 0 0
    CHANNELS 3 Zrotation Xrotation Yrotation
    JOINT lShin
    {
      OFFSET 0 -40 0
      CHANNELS 3 Zrotation Xrotation Yrotation
      End Site
      {
        OFFSET 0 -40 0
      }
    }
  }
}
MOTION
Frames: 2
Frame Time: 0.0333333
0 90 0 0 0 0 0 0 0 0 0 0 0 0 0
5 90 0 0 90 0 0 0 0 90 0 0 0 0 0
"""


def test_parse_and_fk():
    b = parse_bvh(MINI)
    assert [j.name for j in b.joints] == ["hip", "abdomen", "lThigh", "lShin"]
    assert b.motion.shape == (2, 15)
    pos = forward_kinematics(b)
    np.testing.assert_allclose(pos["lShin"][0], [10, 50, 0])
    np.testing.assert_allclose(pos["lShin_end"][0], [10, 10, 0])
    # frame 1: root yawed 90 deg about Y, then the thigh rotated 90 deg about Z
    np.testing.assert_allclose(pos["hip"][1], [5, 90, 0])
    assert np.linalg.norm(pos["lShin_end"][1] - pos["lThigh"][1]) == pytest.approx(80)


def test_pack_roundtrip():
    f = np.random.default_rng(0).normal(0, 0.5, (10, 19, 3)).astype(np.float32)
    back = decode_frames(encode_frames(f), 10)
    np.testing.assert_allclose(back, f, atol=6e-4)


def fake_cmu(n=300):
    t = np.arange(n) / 30.0
    pos = {}
    base = {"lShldr": [18, 140, 0], "rShldr": [-18, 140, 0], "lForeArm": [45, 140, 0], "rForeArm": [-45, 140, 0],
            "lHand": [70, 140, 0], "rHand": [-70, 140, 0], "lIndex2_end": [82, 140, 0], "rIndex2_end": [-82, 140, 0],
            "lThigh": [10, 90, 0], "rThigh": [-10, 90, 0], "lShin": [10, 47, 0], "rShin": [-10, 47, 0],
            "lFoot": [10, 5, 0], "rFoot": [-10, 5, 0], "lFoot_end": [10, 0, 12], "rFoot_end": [-10, 0, 12],
            "head": [0, 155, 0], "leftEye": [4, 162, 8], "rightEye": [-4, 162, 8]}
    for k, v in base.items():
        pos[k] = np.tile(np.array(v, float), (n, 1))
    # a "punch" every 3 s separated by rest
    active = (t % 3.0) < 1.6
    pos["lHand"][:, 2] += np.where(active, 40 * np.sin(np.pi * (t % 3.0) / 1.6), 0)
    pos["lForeArm"][:, 2] += np.where(active, 20 * np.sin(np.pi * (t % 3.0) / 1.6), 0)
    return pos


def test_canonical_conversion_and_segmentation():
    frames = face_camera(to_canonical(fake_cmu()))
    assert set(JOINT_MAP) <= set(J)
    leg = np.linalg.norm(frames[0, J["l_knee"]] - frames[0, J["l_hip"]]) + np.linalg.norm(frames[0, J["l_ankle"]] - frames[0, J["l_knee"]])
    assert leg == pytest.approx(0.85, abs=1e-6)
    assert frames[0, J["nose"], 2] > frames[0, J["l_ear"], 2]  # facing the camera
    assert frames[:, [15, 16, 17, 18], 1].min() == pytest.approx(0.02, abs=1e-6)
    segs = segment(frames)
    assert 2 <= len(segs) <= 5


def test_curated_sources_are_categorised():
    from mfnb.motion.library import CATEGORIES
    assert all(s.category in CATEGORIES for s in CURATED)


def test_bundled_pack_loads():
    items = load_packs()
    assert len(items) >= 200
    assert {i.source for i in items} == {"cmu"}
    assert all(i.frames.shape[1:] == (19, 3) for i in items)
    assert {"tai chi & qigong", "boxing", "kicks", "karate", "dance"} <= {i.category for i in items}
