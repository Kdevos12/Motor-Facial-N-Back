import numpy as np
import pytest

from mfnb.face.blendshapes import D, DIMS, IDX, from_mediapipe, mirror_vec
from mfnb.face.expressions import FACE_CATEGORIES, get_face_library
from mfnb.face.scoring import FaceCalibration, score_face
from mfnb.sim import synth_face_response


@pytest.fixture(scope="module")
def lib():
    return get_face_library()


def test_blendshape_tables():
    assert D == 51 and len(set(DIMS)) == 51
    v = np.zeros(D)
    v[IDX["eyeBlinkLeft"]] = 1
    m = mirror_vec(v)
    assert m[IDX["eyeBlinkRight"]] == 1 and m[IDX["eyeBlinkLeft"]] == 0
    raw = np.zeros((2, 52))
    raw[:, 1 + IDX["jawLeft"]] = 0.7
    assert from_mediapipe(raw, lr_swap=True)[0, IDX["jawRight"]] == pytest.approx(0.7)


def test_library_size(lib):
    assert len(lib) >= 100
    assert {it.category for it in lib.items.values()} == set(FACE_CATEGORIES)
    assert all(0.62 <= it.threshold <= 0.85 for it in lib.items.values())


def test_identity_and_noisy_copy_pass(lib):
    rng = np.random.default_rng(0)
    for iid in ("emo.surprise", "face.pucker", "combo.brows_raise+smile", "face.wink_left"):
        it = lib.get(iid)
        f, t = synth_face_response(it.vector(), rng)
        s = score_face(it.vector(), f, t)["target"]["score"]
        assert s >= it.threshold, (iid, s, it.threshold)


def test_wrong_expression_fails(lib):
    rng = np.random.default_rng(1)
    a, b = lib.get("emo.happy"), lib.get("emo.anger")
    f, t = synth_face_response(b.vector(), rng)
    assert score_face(a.vector(), f, t)["target"]["score"] < a.threshold


def test_wrong_side_fails(lib):
    rng = np.random.default_rng(2)
    it = lib.get("face.wink_left")
    f, t = synth_face_response(it.vector(mirrored=True), rng)
    assert score_face(it.vector(), f, t)["target"]["score"] < it.threshold


def test_neutral_baseline_and_gain_calibration(lib):
    it = lib.get("face.smile")
    rng = np.random.default_rng(3)
    resting = np.zeros(D)
    resting[IDX["mouthSmileLeft"]] = 0.3   # someone whose resting face reads as a slight smile
    resting[IDX["mouthSmileRight"]] = 0.3
    f, t = synth_face_response(lib.get("face.frown_brows").vector(), rng)
    f = np.clip(f + resting, 0, 1)
    raw = score_face(it.vector(), f, t)["target"]["score"]
    calibrated = score_face(it.vector(), f, t, calib=FaceCalibration(neutral=resting))["target"]["score"]
    assert calibrated < raw


def test_no_face_is_invalid(lib):
    out = score_face(lib.get("face.smile").vector(), np.zeros((1, D)))["target"]
    assert out["valid"] is False
