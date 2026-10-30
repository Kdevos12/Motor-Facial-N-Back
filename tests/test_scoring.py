import numpy as np
import pytest

from mfnb.motion.library import get_library
from mfnb.motion.scoring import ResponseInput, judge, keypose_indices, score_motor
from mfnb.motion.skeleton import J, mirror_seq
from mfnb.sim import synth_response


@pytest.fixture(scope="module")
def lib():
    return get_library(include_imported=False)


def resp(frames, rng=None, **kw):
    rng = rng or np.random.default_rng(0)
    f, t = synth_response(frames, rng, **kw)
    return ResponseInput(f, t)


def test_identity_scores_near_one(lib):
    it = lib.get("box.cross")
    r = resp(it.frames, speed=1.0, noise_m=0.0, depth_noise_m=0.0, amplitude=1.0)
    assert score_motor([it.frames], r)["target"]["score"] > 0.95


def test_noisy_time_warped_copy_passes(lib):
    rng = np.random.default_rng(3)
    for iid in ("box.jab", "kick.rear_low_round", "tkd.dollyo_chagi", "taichi.cloud_hands", "grapple.snap_down"):
        it = lib.get(iid)
        r = resp(it.frames, rng, style_m=0.03, amplitude=0.85)
        assert score_motor([it.frames], r)["target"]["score"] >= 0.55, iid


def test_different_move_fails(lib):
    jab, squat = lib.get("box.jab"), lib.get("fit.squat")
    assert score_motor([jab.frames], resp(squat.frames))["target"]["score"] < 0.3
    assert score_motor([squat.frames], resp(jab.frames))["target"]["score"] < 0.3


def test_wrong_side_is_detected(lib):
    it = lib.get("box.rear_hook")
    right = score_motor([it.frames], resp(it.frames))["target"]["score"]
    wrong = score_motor([it.frames], resp(mirror_seq(it.frames)))["target"]["score"]
    assert right > 0.8 and wrong < 0.45


def test_static_posture_hold_found_after_idle(lib):
    it = lib.get("pose.tree_l")
    hold = np.repeat(it.frames[-1:], 40, 0)
    rest = np.repeat(lib.get("fit.squat").frames[:1], 45, 0)
    r = ResponseInput(np.concatenate([rest, hold, rest]), None)
    assert score_motor([it.frames], r, static=True)["target"]["score"] > 0.9


def test_score_short_and_idle_response(lib):
    it = lib.get("box.jab")
    idle = ResponseInput(np.repeat(it.frames[:1], 90, 0), None)
    assert score_motor([it.frames], idle)["target"]["score"] < 0.5
    short = ResponseInput(it.frames[:8], None)
    out = score_motor([it.frames], short)["target"]
    assert out["valid"] is False


def test_score_invalid_when_low_visibility(lib):
    it = lib.get("box.jab")
    f, t = synth_response(it.frames, np.random.default_rng(0))
    vis = np.full(f.shape[:2], 0.2)
    out = score_motor([it.frames], ResponseInput(f, t, vis))["target"]
    assert out["valid"] is False and "visible" in out["reason"]


def test_kick_with_legs_out_of_view_is_not_judged(lib):
    it = lib.get("kick.rear_low_round")
    f, t = synth_response(it.frames, np.random.default_rng(5))
    vis = np.ones(f.shape[:2])
    vis[:, [J[n] for n in ("l_knee", "r_knee", "l_ankle", "r_ankle", "l_foot", "r_foot")]] = 0.0
    out = score_motor([it.frames], ResponseInput(f, t, vis))["target"]
    assert out["valid"] is False and "out of view" in out["reason"]


def test_lure_confusion_reported(lib):
    a, b = lib.get("box.jab"), lib.get("box.lead_hook")
    res = score_motor([a.frames], resp(b.frames), lures=[b.frames], lure_static=[False])
    correct, confused = judge(res["target"]["score"], res["lures"])
    assert not correct and confused == 0


def test_sequence_order_matters(lib):
    a, b = lib.get("box.jab"), lib.get("kick.rear_knee")
    ab = np.concatenate([a.frames, b.frames])
    ba = np.concatenate([b.frames, a.frames])
    good = score_motor([a.frames, b.frames], resp(ab))["target"]["score"]
    bad = score_motor([a.frames, b.frames], resp(ba))["target"]["score"]
    assert good > 0.8 and bad < good - 0.3


def test_keyposes_and_feedback_fields(lib):
    it = lib.get("combo.jab+cross+lead_hook")
    kps = keypose_indices(it.frames)
    assert 1 <= len(kps) <= 4
    out = score_motor([it.frames], resp(it.frames))["target"]
    assert out["keyposes"] and out["worst_bones"] and "left forearm" in out["per_bone_deg"]


def test_calibration_loaded_into_library(lib):
    from mfnb.motion.calibration import load_calibration
    calib = load_calibration()
    assert len(calib) >= 500
    jab = lib.get("box.jab")
    assert jab.threshold == calib["box.jab"]["threshold"]
    assert 0.45 <= jab.threshold <= 0.75
    # symmetric moves can never be chiral
    assert not any(i.chiral and not i.sided for i in lib.items.values())
