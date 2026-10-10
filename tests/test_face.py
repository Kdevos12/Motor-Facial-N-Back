import numpy as np
import pytest

from mfnb.face.blendshapes import D, DEAD, DIMS, IDX, TYPICAL_MAX, UNVERIFIED, from_mediapipe, mirror_vec
from mfnb.face.expressions import FACE_CATEGORIES, get_face_library
from mfnb.face.scoring import FaceCalibration, FaceTarget, neutral_from_frames, score_face, thresholds
from mfnb.sim import synth_face_neutral, synth_face_response


@pytest.fixture(scope="module")
def lib():
    return get_face_library()


def calib(rng):
    n, dz = neutral_from_frames(synth_face_neutral(rng))
    return FaceCalibration(neutral=n, deadzone=dz)


def score(lib, iid, frames, times, cal, mirrored=False, **kw):
    return score_face(FaceTarget.of(lib.get(iid), mirrored), frames, times, cal, **kw)["target"]


def test_blendshape_tables():
    assert D == 51 and len(set(DIMS)) == 51
    v = np.zeros(D)
    v[IDX["eyeBlinkLeft"]] = 1
    m = mirror_vec(v)
    assert m[IDX["eyeBlinkRight"]] == 1 and m[IDX["eyeBlinkLeft"]] == 0
    raw = np.zeros((2, 52))
    raw[:, 1 + IDX["jawLeft"]] = 0.7
    assert from_mediapipe(raw, lr_swap=True)[0, IDX["jawRight"]] == pytest.approx(0.7)
    assert all(TYPICAL_MAX[IDX[n]] < 0.02 for n in DEAD)
    assert np.allclose(TYPICAL_MAX, mirror_vec(TYPICAL_MAX))


def test_library_keys(lib):
    assert len(lib) >= 200
    assert {it.category for it in lib.items.values()} == set(FACE_CATEGORIES)
    for it in lib.items.values():
        assert it.keys, it.id
        assert not (it.shapes_needed & DEAD), it.id          # never rely on a shape the tracker does not output
    assert lib.get("combo.eyes_closed+nose_wrinkle").keys == [["eyeBlinkLeft", "eyeBlinkRight"],
                                                              ["mouthUpperUpLeft", "mouthUpperUpRight"]]
    assert "face.cheek_puff" not in lib.items and "face.jaw_forward" not in lib.items


def test_unverified_items_need_calibration(lib):
    free = {it.id for it in lib.filter(measured=set())}
    assert "face.smile" in free and "face.jaw_left" not in free and "face.lips_press" not in free
    assert all(not (lib.get(i).shapes_needed & UNVERIFIED) for i in free)
    unlocked = {it.id for it in lib.filter(measured={"jawLeft", "jawRight"})}
    assert "face.jaw_left" in unlocked and "face.lips_press" not in unlocked


@pytest.mark.parametrize("iid", ["emo.surprise", "face.pucker", "combo.brows_raise+smile", "face.wink_left",
                                 "face.look_left", "emo.happy", "face.nose_wrinkle"])
def test_performing_the_item_passes(lib, iid):
    rng = np.random.default_rng(0)
    cal = calib(rng)
    passed = 0
    for _ in range(10):
        f, t = synth_face_response(lib.get(iid).vector(), rng)
        passed += score(lib, iid, f, t, cal)["score"] >= 0.60
    assert passed >= 9, (iid, passed)


def test_wrong_expression_fails(lib):
    rng = np.random.default_rng(1)
    cal = calib(rng)
    for perf, iid in (("emo.anger", "emo.happy"), ("face.smile", "combo.brows_raise+smile"),
                      ("face.brows_raise", "combo.brows_raise+smile"), ("face.eyes_closed", "face.wink_left")):
        f, t = synth_face_response(lib.get(perf).vector(), rng)
        assert score(lib, iid, f, t, cal)["score"] < 0.60, (perf, iid)


def test_half_of_a_combination_is_reported_missing(lib):
    rng = np.random.default_rng(4)
    cal = calib(rng)
    f, t = synth_face_response(lib.get("face.smile").vector(), rng)
    r = score(lib, "combo.brows_raise+smile", f, t, cal)
    assert r["score"] < 0.60 and any("brow" in m for m in r["missing"])


def test_wrong_side_fails(lib):
    rng = np.random.default_rng(2)
    cal = calib(rng)
    for iid in ("face.wink_left", "face.smirk_left", "face.brow_left"):
        f, t = synth_face_response(lib.get(iid).vector(mirrored=True), rng)
        assert score(lib, iid, f, t, cal)["score"] < 0.60, iid
        assert score(lib, iid, f, t, cal, mirrored=True)["score"] >= 0.60, iid


def test_resting_face_matters():
    lib = get_face_library()
    rng = np.random.default_rng(3)
    rest = np.array(FaceCalibration().rest)
    rest[IDX["mouthSmileLeft"]] = rest[IDX["mouthSmileRight"]] = 0.35   # a resting face that reads as a slight smile
    f = np.repeat(rest[None], 60, 0) + rng.normal(0, 0.02, (60, D))
    t = np.arange(60) / 30
    own = FaceCalibration(neutral=rest)
    assert score(lib, "face.smile", f, t, own)["score"] < 0.3
    f2, t2 = synth_face_response(lib.get("face.smile").vector(), rng, rest=rest)
    assert score(lib, "face.smile", f2, t2, own)["score"] >= 0.60


def test_strictness_moves_both_rules():
    lo, hi = thresholds(0.7), thresholds(1.3)
    assert lo[0] < thresholds(1.0)[0] < hi[0] and lo[1] < hi[1]


def test_lures_scored_with_their_own_parts(lib):
    rng = np.random.default_rng(5)
    cal = calib(rng)
    f, t = synth_face_response(lib.get("face.smile").vector(), rng)
    out = score_face(FaceTarget.of(lib.get("combo.brows_raise+smile")), f, t, cal,
                     lures=[FaceTarget.of(lib.get("face.smile"))])
    assert out["lures"][0] >= 0.60 > out["target"]["score"]


def test_no_face_is_invalid(lib):
    out = score_face(FaceTarget.of(lib.get("face.smile")), np.zeros((1, D)))["target"]
    assert out["valid"] is False


def test_neutral_from_frames_clips_a_non_relaxed_face():
    rng = np.random.default_rng(6)
    f = synth_face_neutral(rng)
    f[:, IDX["mouthSmileLeft"]] = f[:, IDX["mouthSmileRight"]] = 0.8     # smiling during the neutral capture
    n, dz = neutral_from_frames(f)
    assert n[IDX["mouthSmileLeft"]] < 0.3 and (dz >= 0.03).all()
