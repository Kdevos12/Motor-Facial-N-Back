"""Camera angle and upper-body framing for motor scoring."""
import numpy as np
import pytest

from mfnb.motion.library import get_library
from mfnb.motion.scoring import (ResponseInput, Tolerance, estimate_view, rot_y, score_motor)
from mfnb.motion.skeleton import J, mirror_seq
from mfnb.sim import synth_response


def rot_x(deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def camera(frames, yaw_deg, pitch_deg=0.0):
    """What a camera placed off-axis sees: the body rotated about the vertical, then tilted."""
    R = rot_x(pitch_deg) @ rot_y(np.radians(yaw_deg))
    return np.asarray(frames) @ R.T


@pytest.fixture(scope="module")
def lib():
    return get_library()


@pytest.fixture(scope="module")
def rest(lib):
    rng = np.random.default_rng(0)
    return lib.get("pose.mountain").frames[0][None].repeat(60, 0) + rng.normal(0, 0.01, (60, 19, 3))


@pytest.mark.parametrize("yaw,pitch", [(0, 0), (40, 0), (-35, 15), (60, -10)])
def test_view_undoes_the_camera_angle(rest, yaw, pitch):
    seen = camera(rest, yaw, pitch)
    v = estimate_view(seen)
    assert abs(v.yaw_deg - yaw) < 6 and abs(v.tilt_deg - abs(pitch)) < 6
    back = seen @ v.R.T
    assert np.abs(back - rest).mean() < 0.03


def pass_rate(lib, ids, yaw, pitch, use_view, rest, rng, mirrored=False, framing="full"):
    v = estimate_view(camera(rest, yaw, pitch)) if use_view else None
    ok = 0
    for iid in ids:
        it = lib.get(iid)
        perf = mirror_seq(it.frames) if mirrored else it.frames
        f, t = synth_response(perf, rng)
        res = score_motor([it.frames], ResponseInput(camera(f, yaw, pitch), t), static=it.static, view=v,
                          framing=framing, lures=[mirror_seq(it.frames)] if it.sided else None)
        thr = lib.threshold(iid, framing)
        ok += res["target"]["score"] >= thr and not (res["lures"] and res["lures"][0] > res["target"]["score"] + 0.03)
    return ok / len(ids)


IDS = ["box.jab", "box.cross", "daily.wave", "daily.salute", "fit.squat", "box.lead_hook", "daily.point_forward",
       "fit.side_bend", "daily.clap", "pose.warrior2_l"]


def test_off_axis_camera_scores_like_a_frontal_one(lib, rest):
    base = pass_rate(lib, IDS, 0, 0, False, rest, np.random.default_rng(1))
    raw = pass_rate(lib, IDS, 45, 15, False, rest, np.random.default_rng(1))
    fixed = pass_rate(lib, IDS, 45, 15, True, rest, np.random.default_rng(1))
    assert base >= 0.8
    assert fixed >= base - 0.1 and fixed > raw


def test_wrong_side_still_fails_with_the_view(lib, rest):
    chiral = [i for i in IDS if lib.get(i).sided and lib.get(i).chiral]
    assert pass_rate(lib, chiral, 45, 15, True, rest, np.random.default_rng(2), mirrored=True) <= 0.2


def test_upper_framing_ignores_invented_legs(lib):
    it = lib.get("daily.wave")
    rng = np.random.default_rng(3)
    f, t = synth_response(it.frames, rng)
    legs = [J[n] for n in ("l_knee", "r_knee", "l_ankle", "r_ankle", "l_foot", "r_foot")]
    f = f.copy()
    f[:, legs] += rng.normal(0, 0.25, (len(f), len(legs), 3))      # what the model guesses below the picture
    vis = np.ones((len(f), 19))
    vis[:, legs] = 0.0                                             # out of frame (set by the browser)
    full = score_motor([it.frames], ResponseInput(f, t, vis))["target"]
    upper = score_motor([it.frames], ResponseInput(f, t, vis), framing="upper")["target"]
    assert not full["valid"]
    assert upper["valid"] and upper["score"] >= lib.threshold("daily.wave", "upper")


def test_upper_framing_without_hips(lib):
    it = lib.get("box.jab")
    f, t = synth_response(it.frames, np.random.default_rng(4))
    vis = np.ones((len(f), 19))
    vis[:, [J["l_hip"], J["r_hip"], J["l_knee"], J["r_knee"], J["l_ankle"], J["r_ankle"]]] = 0.0
    res = score_motor([it.frames], ResponseInput(f, t, vis), framing="upper")["target"]
    assert res["valid"] and "torso" not in res["per_bone_deg"] and "left thigh" not in res["per_bone_deg"]


def test_filters(lib):
    upper = lib.filter(framing="upper")
    assert upper and all(it.body_part == "upper" for it in upper)
    assert all(lib.get(i.id).threshold_upper is not None for i in upper if i.source in ("procedural", "cmu"))
    turning = [it for it in lib.items.values() if 70 < it.heading_max_deg < 95 and it.heading_min_deg > -20]
    assert turning
    ids = {it.id for it in lib.filter(complexity=(1, 5), flexibility="high", space="large")}
    shifted = {it.id for it in lib.filter(complexity=(1, 5), flexibility="high", space="large", camera_yaw_deg=40)}
    assert turning[0].id in ids and turning[0].id not in shifted


def test_tolerance_default_unchanged(lib):
    """Without framing or view, scoring is what the bundled thresholds were calibrated with."""
    it = lib.get("box.jab")
    f, t = synth_response(it.frames, np.random.default_rng(5))
    a = score_motor([it.frames], ResponseInput(f, t))["target"]["score"]
    b = score_motor([it.frames], ResponseInput(f, t), tolerance=Tolerance(), framing="full", view=None)["target"]["score"]
    assert a == b


def test_turn_away_judged_for_both_sides(lib):
    from mfnb.motion.library import MotionLibrary
    it = lib.get("pose.warrior2_l")        # one-sided, turns the trunk: also asked mirrored
    assert it.sided and not it.stance_based
    lo, hi = it.heading_min_deg, it.heading_max_deg
    both = MotionLibrary.away_from_camera(it, 40)
    assert both == pytest.approx(max(abs(40 + lo), abs(40 + hi), abs(40 - hi), abs(40 - lo)))
