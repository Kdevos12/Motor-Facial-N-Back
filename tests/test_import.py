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


MIXAMO = """HIERARCHY
ROOT mixamorig:Hips
{
  OFFSET 0 100 0
  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation
  JOINT mixamorig:Spine
  {
    OFFSET 0 10 0
    CHANNELS 3 Zrotation Xrotation Yrotation
    JOINT mixamorig:Neck
    {
      OFFSET 0 40 0
      CHANNELS 3 Zrotation Xrotation Yrotation
      JOINT mixamorig:Head
      {
        OFFSET 0 10 2
        CHANNELS 3 Zrotation Xrotation Yrotation
        End Site
        {
          OFFSET 0 18 0
        }
      }
    }
    JOINT mixamorig:LeftShoulder
    {
      OFFSET 5 38 0
      CHANNELS 3 Zrotation Xrotation Yrotation
      JOINT mixamorig:LeftArm
      {
        OFFSET 12 0 0
        CHANNELS 3 Zrotation Xrotation Yrotation
        JOINT mixamorig:LeftForeArm
        {
          OFFSET 28 0 0
          CHANNELS 3 Zrotation Xrotation Yrotation
          JOINT mixamorig:LeftHand
          {
            OFFSET 25 0 0
            CHANNELS 3 Zrotation Xrotation Yrotation
            End Site
            {
              OFFSET 15 0 0
            }
          }
        }
      }
    }
    JOINT mixamorig:RightShoulder
    {
      OFFSET -5 38 0
      CHANNELS 3 Zrotation Xrotation Yrotation
      JOINT mixamorig:RightArm
      {
        OFFSET -12 0 0
        CHANNELS 3 Zrotation Xrotation Yrotation
        JOINT mixamorig:RightForeArm
        {
          OFFSET -28 0 0
          CHANNELS 3 Zrotation Xrotation Yrotation
          JOINT mixamorig:RightHand
          {
            OFFSET -25 0 0
            CHANNELS 3 Zrotation Xrotation Yrotation
            End Site
            {
              OFFSET -15 0 0
            }
          }
        }
      }
    }
  }
  JOINT mixamorig:LeftUpLeg
  {
    OFFSET 9 -5 0
    CHANNELS 3 Zrotation Xrotation Yrotation
    JOINT mixamorig:LeftLeg
    {
      OFFSET 0 -45 0
      CHANNELS 3 Zrotation Xrotation Yrotation
      JOINT mixamorig:LeftFoot
      {
        OFFSET 0 -42 0
        CHANNELS 3 Zrotation Xrotation Yrotation
        JOINT mixamorig:LeftToeBase
        {
          OFFSET 0 -6 12
          CHANNELS 3 Zrotation Xrotation Yrotation
          End Site
          {
            OFFSET 0 0 5
          }
        }
      }
    }
  }
  JOINT mixamorig:RightUpLeg
  {
    OFFSET -9 -5 0
    CHANNELS 3 Zrotation Xrotation Yrotation
    JOINT mixamorig:RightLeg
    {
      OFFSET 0 -45 0
      CHANNELS 3 Zrotation Xrotation Yrotation
      JOINT mixamorig:RightFoot
      {
        OFFSET 0 -42 0
        CHANNELS 3 Zrotation Xrotation Yrotation
        JOINT mixamorig:RightToeBase
        {
          OFFSET 0 -6 12
          CHANNELS 3 Zrotation Xrotation Yrotation
          End Site
          {
            OFFSET 0 0 5
          }
        }
      }
    }
  }
}
MOTION
Frames: 1
Frame Time: 0.0333333
""" + " ".join(["0"] * 63) + "\n"


@pytest.mark.parametrize("name,expected", [
    ("LeftUpLeg", ("l", "upleg")), ("mixamorig:RightForeArm", ("r", "forearm")), ("lShldr", ("l", "shldr")),
    ("UpperArm_L", ("l", "upperarm")), ("Hand_R", ("r", "hand")), ("Hips", (None, "hips")), ("Toes_L", ("l", "toes")),
])
def test_split_side(name, expected):
    from mfnb.motion.importers.generic import split_side
    assert split_side(name) == expected


def test_generic_import_of_a_mixamo_rig():
    from mfnb.motion.importers.generic import auto_map, bvh_to_frames
    m = auto_map(parse_bvh(MIXAMO))
    assert m["l_shoulder"] == "mixamorig:LeftArm"      # not the clavicle
    assert m["r_knee"] == "mixamorig:RightLeg" and m["l_hip"] == "mixamorig:LeftUpLeg"
    assert m["l_foot"] == "mixamorig:LeftToeBase_end" and m["head_top"] == "mixamorig:Head_end"
    f = bvh_to_frames(MIXAMO)
    assert f.shape == (1, 19, 3)
    assert f[0, J["l_hip"], 0] > f[0, J["r_hip"], 0]        # subject's left = +x
    assert f[0, J["nose"], 2] > f[0, J["l_ear"], 2]           # faces +z
    assert f[0, J["nose"], 1] > f[0, J["l_shoulder"], 1] > f[0, J["l_knee"], 1]
