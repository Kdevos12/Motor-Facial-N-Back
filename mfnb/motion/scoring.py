"""Motor response scoring: bone-direction features + subsequence DTW.

The target (the move to reproduce) is aligned with the best-matching part of the response
window, so idle time before/after and tempo differences do not matter. Per aligned frame
the error is a weighted mean of squared bone angles over per-bone tolerances; the score is
``exp(-mean_error)`` in (0, 1].
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from dtaidistance.subsequence.dtw import subsequence_alignment

from .skeleton import BONES, J, LOWER_BODY_BONES, mirror_seq, point

FEATURE_FPS = 15.0
SOURCE_FPS = 30.0
BONE_NAMES = [b[0] for b in BONES]
BONE_WEIGHTS = np.array([b[3] for b in BONES])
LOWER_MASK = np.array([b[0] in LOWER_BODY_BONES for b in BONES])
FLEX_FACTOR = {"low": 1.6, "medium": 1.25, "high": 1.0}
MAIN_JOINTS = [J[n] for n in ("l_shoulder", "r_shoulder", "l_elbow", "r_elbow", "l_wrist", "r_wrist",
                              "l_hip", "r_hip", "l_knee", "r_knee", "l_ankle", "r_ankle")]
ARM_JOINTS = [J[n] for n in ("l_shoulder", "r_shoulder", "l_elbow", "r_elbow", "l_wrist", "r_wrist")]
HIP_JOINTS = [J["l_hip"], J["r_hip"]]
LEG_JOINTS = [J[n] for n in ("l_knee", "r_knee", "l_ankle", "r_ankle")]
FRAMINGS = ("full", "upper")   # whole body in view / head to mid-thigh (seated or close camera)
DEFAULT_THRESHOLD = 0.45
# per-item thresholds (motion/calibration.py) reject near-misses of clean copies; a real webcam response is noisier,
# so no move asks for more than this
THRESHOLD_CAP = 0.50
COST_CAP = 3.0
MIN_KEYPOSE_DEV = 0.15
KEYPOSE_SLACK = 4  # frames (at FEATURE_FPS) searched around the aligned key pose
# a key pose counts from KEYPOSE_FLOOR of the way from the start stance to it, fully reproduced at KEYPOSE_FULL
KEYPOSE_FLOOR = 0.05
KEYPOSE_FULL = 0.50


@dataclass(frozen=True)
class Tolerance:
    angle_deg: float = 52.0      # webcam pose tracking is noisy: about 40-50 deg on a correct move
    strictness: float = 1.0        # >1 stricter, <1 more lenient
    flexibility: str = "medium"    # scales lower-body tolerance
    depth_weight: float = 0.5      # monocular depth is noisy: z counts less

    def taus(self) -> np.ndarray:
        tau = np.full(len(BONES), np.radians(self.angle_deg) / max(self.strictness, 0.1))
        tau[LOWER_MASK] *= FLEX_FACTOR.get(self.flexibility, 1.25)
        return tau


@dataclass
class Prepared:
    dirs: np.ndarray       # (T, B, 3) unit bone directions
    feats: np.ndarray      # (T, D) DTW features
    weights: np.ndarray    # (B,) bone weights used


@dataclass
class MotorScore:
    score: float
    valid: bool = True
    reason: str = ""
    matched: tuple[float, float] = (0.0, 0.0)
    per_bone_deg: dict[str, float] = field(default_factory=dict)
    worst_bones: list[str] = field(default_factory=list)
    keyposes: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": round(float(self.score), 4), "valid": self.valid, "reason": self.reason,
            "matched": [round(float(self.matched[0]), 2), round(float(self.matched[1]), 2)],
            "per_bone_deg": {k: round(v, 1) for k, v in self.per_bone_deg.items()},
            "worst_bones": self.worst_bones, "keyposes": self.keyposes,
        }


def bone_dirs(frames: np.ndarray) -> np.ndarray:
    vecs = np.stack([point(frames, b) - point(frames, a) for _, a, b, _ in BONES], axis=-2)
    n = np.linalg.norm(vecs, axis=-1, keepdims=True)
    return vecs / np.maximum(n, 1e-9)


def resample(frames: np.ndarray, times_s: np.ndarray | None, fps: float, src_fps: float = SOURCE_FPS) -> np.ndarray:
    """Linear resampling of (T, J, 3) to ``fps``; ``times_s`` (T,) defaults to a regular grid."""
    frames = np.asarray(frames, dtype=float)
    if len(frames) < 2:
        return frames
    t = np.arange(len(frames)) / src_fps if times_s is None else np.asarray(times_s, dtype=float) - times_s[0]
    t_new = np.arange(0.0, t[-1] + 1e-9, 1.0 / fps)
    flat = frames.reshape(len(frames), -1)
    out = np.stack([np.interp(t_new, t, flat[:, k]) for k in range(flat.shape[1])], -1)
    return out.reshape(len(t_new), *frames.shape[1:])


class Scorer:
    def __init__(self, tolerance: Tolerance = Tolerance(), velocity_weight: float = 0.6, penalty: float = 0.05):
        self.tol = tolerance
        self.tau = tolerance.taus()
        self.vw = velocity_weight
        self.penalty = penalty

    def prepare(self, frames: np.ndarray, weights: np.ndarray | None = None) -> Prepared:
        w = BONE_WEIGHTS if weights is None else weights
        dirs = bone_dirs(frames)
        scaled = dirs * np.array([1.0, 1.0, self.tol.depth_weight])
        coef = np.sqrt(w / w.sum()) / self.tau
        pos = (scaled * coef[None, :, None]).reshape(len(dirs), -1)
        vel = np.vstack([np.zeros((1, pos.shape[1])), np.diff(pos, axis=0)]) * self.vw
        return Prepared(dirs=dirs, feats=np.ascontiguousarray(np.hstack([pos, vel]), dtype=np.double), weights=w)

    def frame_costs(self, a_dirs: np.ndarray, b_dirs: np.ndarray, w: np.ndarray) -> np.ndarray:
        """Weighted mean (angle/tau)^2 between aligned direction arrays (N, B, 3) -> (N,)."""
        z = np.array([1.0, 1.0, self.tol.depth_weight])
        d2 = np.sum(((a_dirs - b_dirs) * z) ** 2, axis=-1)  # ~ angle^2 for small angles
        cost = (d2 / self.tau ** 2 * w).sum(-1) / w.sum()
        return np.minimum(cost, COST_CAP)  # one bad frame (tracking glitch) cannot sink a trial

    def deviation(self, target: Prepared) -> np.ndarray:
        """Per-frame distance of the target from its own starting pose (same units as costs)."""
        return self.frame_costs(target.dirs, np.broadcast_to(target.dirs[:1], target.dirs.shape), target.weights)

    @staticmethod
    def activity(dev: np.ndarray) -> np.ndarray:
        """Per-frame importance: frames far from the starting pose (the actual move) weigh
        more than the stance held before/after it."""
        top = float(dev.max())
        if top < 1e-6:
            return np.ones(len(dev))
        return 0.15 + dev / top

    def align(self, target: Prepared, response: Prepared) -> list[tuple[int, int]]:
        sa = subsequence_alignment(target.feats, response.feats, penalty=self.penalty, use_c=True)
        return [(int(i), int(j)) for i, j in sa.best_match().path]

    def score_dynamic(self, target: Prepared, response: Prepared, keyposes: list[int] | None = None) -> MotorScore:
        """Absolute accuracy along the alignment x reproduction of every key pose.

        A key pose counts as reproduced when the response gets most of the way from the
        starting stance to it; an idle response, the wrong side or a missing part of a
        sequence fails the key poses even if the stance held around them matches."""
        path = self.align(target, response)
        qi = np.array([p[0] for p in path])
        rj = np.array([p[1] for p in path])
        costs = self.frame_costs(target.dirs[qi], response.dirs[rj], target.weights)
        n_t = len(target.dirs)
        per_query = np.bincount(qi, weights=costs, minlength=n_t) / np.maximum(np.bincount(qi, minlength=n_t), 1)
        dev = self.deviation(target)
        act = self.activity(dev)
        mean_cost = float((per_query * act).sum() / act.sum())
        s_abs = float(np.exp(-mean_cost))
        kps = keyposes if keyposes else [int(np.argmax(dev))]
        kp_out, repro = [], []
        for k in kps:
            sel = qi == k
            if not sel.any():
                continue
            j0 = int(rj[sel][0])
            lo, hi = max(0, j0 - KEYPOSE_SLACK), min(len(response.dirs), j0 + KEYPOSE_SLACK + 1)
            window = self.frame_costs(np.broadcast_to(target.dirs[k], response.dirs[lo:hi].shape),
                                      response.dirs[lo:hi], target.weights)
            jbest = lo + int(np.argmin(window))
            c = float(window.min())
            r = 1.0 - c / max(float(dev[k]), MIN_KEYPOSE_DEV)
            q = float(np.clip((r - KEYPOSE_FLOOR) / (KEYPOSE_FULL - KEYPOSE_FLOOR), 0.0, 1.0))
            repro.append(q)
            kp_out.append({"t_target": round(k / FEATURE_FPS, 2), "t_response": round(jbest / FEATURE_FPS, 2),
                           "hit": q >= 0.5, "reproduced": round(q, 2)})
        s_rel = 0.5 * min(repro) + 0.5 * float(np.mean(repro)) if repro else 1.0
        score = s_abs * s_rel
        span_r = int(rj.max() - rj.min())
        ratio = span_r / max(n_t - 1, 1)
        if ratio < 0.35:  # the whole move squeezed into a blink: not a real execution
            score *= (ratio / 0.35) ** 2
        angles = np.degrees(np.arccos(np.clip(np.sum(target.dirs[qi] * response.dirs[rj], -1), -1, 1)))
        per_bone = {n: float(angles[:, k].mean()) for k, n in enumerate(BONE_NAMES) if target.weights[k] > 0}
        worst = sorted(per_bone, key=lambda n: -per_bone[n] * BONE_WEIGHTS[BONE_NAMES.index(n)])[:3]
        return MotorScore(score=float(score), matched=(rj.min() / FEATURE_FPS, rj.max() / FEATURE_FPS),
                          per_bone_deg=per_bone, worst_bones=worst, keyposes=kp_out)

    def score_static(self, target: Prepared, response: Prepared, hold_s: float = 0.8) -> MotorScore:
        tail = max(1, int(0.5 * FEATURE_FPS))
        pose = target.dirs[-tail:].mean(0)
        pose /= np.linalg.norm(pose, axis=-1, keepdims=True)
        costs = self.frame_costs(np.broadcast_to(pose, response.dirs.shape), response.dirs, target.weights)
        win = max(1, min(len(costs), int(round(hold_s * FEATURE_FPS))))
        smooth = np.convolve(costs, np.ones(win) / win, mode="valid")
        j = int(np.argmin(smooth))
        score = float(np.exp(-smooth[j]))
        seg = response.dirs[j:j + win]
        angles = np.degrees(np.arccos(np.clip(np.sum(seg * pose, -1), -1, 1)))
        per_bone = {n: float(angles[:, k].mean()) for k, n in enumerate(BONE_NAMES) if target.weights[k] > 0}
        worst = sorted(per_bone, key=lambda n: -per_bone[n] * BONE_WEIGHTS[BONE_NAMES.index(n)])[:3]
        return MotorScore(score=score, matched=(j / FEATURE_FPS, (j + win) / FEATURE_FPS), per_bone_deg=per_bone,
                          worst_bones=worst, keyposes=[{"t_target": 0.0, "t_response": round(j / FEATURE_FPS, 2),
                                                        "hit": bool(smooth[j] < 1.0), "error": round(float(smooth[j]), 3)}])


def bone_weights(framing: str = "full", hips_ok: bool = True) -> np.ndarray:
    """Bones scored for a framing: 'upper' drops the legs, and the hip line and torso when the hips are out of
    the picture."""
    w = BONE_WEIGHTS.astype(float).copy()
    if framing == "upper":
        w[LOWER_MASK] = 0.0
        if not hips_ok:
            w[[BONE_NAMES.index("torso"), BONE_NAMES.index("hip line")]] = 0.0
    return w


def keypose_indices(frames_30: np.ndarray, max_n: int = 4, weights: np.ndarray | None = None) -> list[int]:
    """Key poses of a target (indices at FEATURE_FPS): extreme poses (local maxima of the
    deviation from the starting pose) and slow-down points, all far from the start.
    ``weights`` restricts both to the scored bones (upper-body framing)."""
    f = resample(frames_30, None, FEATURE_FPS)
    if len(f) < 3:
        return [len(f) - 1]
    sc = Scorer()
    dev = sc.deviation(sc.prepare(f, weights))
    top = float(dev.max())
    if top < 1e-6:
        return [len(f) - 1]
    moving = np.diff(f, axis=0)
    if weights is not None and weights[LOWER_MASK].sum() == 0:
        moving[:, LEG_JOINTS + [J["l_foot"], J["r_foot"]]] = 0.0
    speed = np.linalg.norm(moving, axis=-1).sum(-1)
    speed = np.concatenate([[speed[0]], speed])
    cands = [int(np.argmax(dev))]
    for i in range(1, len(f) - 1):
        if dev[i] < 0.4 * top:
            continue
        peak = dev[i] >= dev[i - 1] and dev[i] >= dev[i + 1]
        still = speed[i] <= speed[i - 1] and speed[i] <= speed[i + 1]
        if peak or still:
            cands.append(i)
    chosen: list[int] = []
    for i in sorted(set(cands), key=lambda i: -dev[i]):
        if all(abs(i - c) >= 3 for c in chosen):
            chosen.append(i)
        if len(chosen) >= max_n:
            break
    return sorted(chosen)


@dataclass
class ResponseInput:
    frames: np.ndarray                 # (T, 19, 3) canonical
    times_s: np.ndarray | None = None  # (T,)
    visibility: np.ndarray | None = None  # (T, 19)


def clean_framed(resp: ResponseInput, framing: str = "full") -> tuple[np.ndarray | None, str, bool]:
    """Drop low-visibility frames and resample to FEATURE_FPS. Returns (frames, reason-if-invalid, hips_ok).
    The browser sets the visibility of joints outside the picture to 0. In 'upper' framing only the arms are
    required; the hips count when they are in the picture in at least 80% of the frames."""
    frames = np.asarray(resp.frames, dtype=float)
    times = None if resp.times_s is None else np.asarray(resp.times_s, dtype=float)
    if frames.ndim != 3:
        return None, "no tracking data", False
    finite = np.isfinite(frames).all(axis=(1, 2))      # a frame the tracker could not fill is dropped, not fatal
    frames = frames[finite]
    times = None if times is None or len(times) != len(finite) else times[finite]
    if len(frames) < 5:
        return None, "no tracking data", False
    hips_ok = True
    if resp.visibility is not None and len(resp.visibility) == len(finite):
        vis_all = np.asarray(resp.visibility, dtype=float)[finite]
        if framing == "upper":
            hips_ok = float(np.mean(vis_all[:, HIP_JOINTS].min(-1) > 0.5)) >= 0.8
            joints = ARM_JOINTS + (HIP_JOINTS if hips_ok else [])
        else:
            joints = MAIN_JOINTS
        vis = vis_all[:, joints]
        ok = (vis.min(-1) >= 0.25) & (vis.mean(-1) >= 0.5)
        if ok.mean() < 0.5:
            return None, ("arms not fully visible" if framing == "upper" else "body not fully visible"), hips_ok
        frames = frames[ok]
        times = None if times is None else times[ok]
    if times is None:
        times = np.arange(len(frames)) / SOURCE_FPS
    if times[-1] - times[0] < 0.5:
        return None, "response too short", hips_ok
    return resample(frames, times, FEATURE_FPS), "", hips_ok


def clean_response(resp: ResponseInput) -> tuple[np.ndarray | None, str]:
    """Drop low-visibility frames and resample to FEATURE_FPS. Returns (frames, reason-if-invalid)."""
    frames, reason, _ = clean_framed(resp, "full")
    return frames, reason


# ---- camera viewpoint ----------------------------------------------------------------------------------------
# MediaPipe's world landmarks follow the camera's axes. A camera placed to the side, or tilted, makes a correct
# move look rotated. A fixed rotation measured while the user stands relaxed facing the SCREEN (start of the
# block) brings the response back to the screen's frame; the user's heading at the start of each trial (while
# still relaxed, before the move) corrects a small drift. Neither looks at the target, so a move done without its
# defining turn, or on the wrong side, is not rotated into a pass.
UP = np.array([0.0, 1.0, 0.0])


def _unit(v):
    v = np.asarray(v, float)
    return v / max(float(np.linalg.norm(v)), 1e-9)


def rot_y(rad: float) -> np.ndarray:
    c, s = np.cos(rad), np.sin(rad)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_between(u, v) -> np.ndarray:
    """Smallest rotation taking direction u onto v."""
    u, v = _unit(u), _unit(v)
    axis = np.cross(u, v)
    s, c = np.linalg.norm(axis), float(np.dot(u, v))
    if s < 1e-9:
        return np.eye(3)
    k = axis / s
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    ang = np.arctan2(s, c)
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K


def _mid(f, a, b):
    return (f[..., J[a], :] + f[..., J[b], :]) / 2


def lateral(f, use_hips: bool = True):
    """The subject's right-to-left line (shoulders, plus hips)."""
    v = f[..., J["l_shoulder"], :] - f[..., J["r_shoulder"], :]
    return v + (f[..., J["l_hip"], :] - f[..., J["r_hip"], :] if use_hips else 0.0)


def yaw_of(lat) -> float:
    """Facing angle (rad) about the vertical of a lateral line: 0 = facing the camera (+z)."""
    return float(np.arctan2(-lat[2], lat[0]))


@dataclass
class View:
    """Rotation taking camera-frame coordinates into the frame of the screen the user faces."""
    R: np.ndarray = field(default_factory=lambda: np.eye(3))
    yaw_deg: float = 0.0     # where the camera sees the user from: 0 = straight in front, > 0 = on their right
    tilt_deg: float = 0.0    # camera pitch/roll

    def to_dict(self) -> dict:
        return {"R": np.round(self.R, 5).tolist(), "yaw_deg": round(self.yaw_deg, 1), "tilt_deg": round(self.tilt_deg, 1)}

    @classmethod
    def from_dict(cls, d: dict | None) -> "View | None":
        if not d:
            return None
        return cls(np.asarray(d["R"], float), float(d.get("yaw_deg", 0.0)), float(d.get("tilt_deg", 0.0)))


def estimate_view(frames: np.ndarray, visibility: np.ndarray | None = None, framing: str = "full") -> View:
    """From ~2 s of the user standing (or sitting) relaxed, facing the screen. 'Up' is the trunk (and the legs
    when in view) made vertical; 'front' makes the shoulder and hip lines parallel to the screen."""
    f = np.asarray(frames, float)
    vis = None if visibility is None else np.asarray(visibility, float)

    def seen(idx):
        return vis is None or float(np.mean(vis[:, idx].min(-1) > 0.5)) >= 0.8
    hips = seen(HIP_JOINTS) if framing == "upper" else True
    legs = framing == "full" and seen(LEG_JOINTS)
    if hips:
        up = np.mean([_unit(v) for v in _mid(f, "l_shoulder", "r_shoulder") - _mid(f, "l_hip", "r_hip")], axis=0)
        if legs:
            up = up + np.mean([_unit(v) for v in _mid(f, "l_hip", "r_hip") - _mid(f, "l_ankle", "r_ankle")], axis=0)
        R_up = rot_between(up, UP)
        tilt = float(np.degrees(np.arccos(np.clip(_unit(up)[1], -1, 1))))
    else:
        # hips out of the picture: the trunk direction is unknown, assume a level camera
        R_up, tilt = np.eye(3), 0.0
    yaw = yaw_of((lateral(f, hips) @ R_up.T).mean(0))
    return View(rot_y(-yaw) @ R_up, float(np.degrees(yaw)), tilt)


def rest_heading(frames15: np.ndarray, hips_ok: bool = True, framing: str = "full", win_s: float = 0.4,
                 max_deg: float = 60.0) -> float | None:
    """The user's heading (rad) in the first moments after GO, when they still stand relaxed: arms down and trunk
    upright. None when they are already moving or in a stance (then only the block's view applies)."""
    n = max(2, int(round(win_s * FEATURE_FPS)))
    r = np.asarray(frames15[:n], float)
    if len(r) < 2:
        return None
    wrists = r[:, [J["l_wrist"], J["r_wrist"]], 1]
    if hips_ok:
        mh = _mid(r, "l_hip", "r_hip")
        relaxed = bool(np.all(wrists < mh[:, None, 1] + 0.05))
        upright = float(np.mean([_unit(v)[1] for v in _mid(r, "l_shoulder", "r_shoulder") - mh])) > np.cos(np.radians(20))
    else:
        ms = _mid(r, "l_shoulder", "r_shoulder")
        relaxed, upright = bool(np.all(wrists < ms[:, None, 1] - 0.35)), True
    if not (relaxed and upright):
        return None
    yaw = yaw_of(lateral(r, hips_ok).mean(0))
    return None if abs(yaw) > np.radians(max_deg) else yaw


def score_motor(targets: list[np.ndarray], response: ResponseInput, *, static: bool = False,
                tolerance: Tolerance = Tolerance(), lures: list[np.ndarray] | None = None,
                lure_static: list[bool] | None = None, framing: str = "full", view: View | None = None) -> dict:
    """Score a response against the (concatenated) targets, plus optional lures.

    ``targets`` are 30 fps (T,19,3) arrays already mirrored if the instruction asked for it.
    ``framing`` 'upper' scores the arms and trunk only. ``view`` (from ``estimate_view``) undoes the camera's
    angle; the user's heading at the start of the trial is corrected on top of it.
    Returns ``{"target": MotorScore dict, "lures": [scores], "view": {...}}``.
    """
    scorer = Scorer(tolerance)
    clean, reason, hips_ok = clean_framed(response, framing)
    if clean is None:
        return {"target": MotorScore(score=0.0, valid=False, reason=reason).to_dict(), "lures": [], "view": None}
    w = bone_weights(framing, hips_ok)
    view_out = None
    if view is not None:
        clean = clean @ view.R.T
        d = rest_heading(clean, hips_ok, framing)
        if d is not None:
            clean = clean @ rot_y(-d).T
        view_out = {"yaw_deg": round(view.yaw_deg, 1), "rest_yaw_deg": None if d is None else round(float(np.degrees(d)), 1)}
    upper = framing == "upper"
    resp = scorer.prepare(clean, w)
    target_30 = np.concatenate(targets, axis=0)
    target = scorer.prepare(resample(target_30, None, FEATURE_FPS), w)
    if static and len(targets) == 1:
        res = scorer.score_static(target, resp)
    else:
        kps, offset = [], 0
        for seg in targets:
            kps += [offset + k for k in keypose_indices(seg, weights=w if upper else None)]
            offset += len(resample(seg, None, FEATURE_FPS))
        kps = [min(k, len(target.dirs) - 1) for k in kps]
        res = scorer.score_dynamic(target, resp, kps)
    lure_scores = []
    for k, lure in enumerate(lures or []):
        lp = scorer.prepare(resample(lure, None, FEATURE_FPS), w)
        st = bool(lure_static[k]) if lure_static else False
        lure_scores.append(round((scorer.score_static(lp, resp) if st else
                                  scorer.score_dynamic(lp, resp, keypose_indices(lure, weights=w if upper else None))).score, 4))
    return {"target": res.to_dict(), "lures": lure_scores, "view": view_out}


def judge(target_score: float, lure_scores: list[float], threshold: float = DEFAULT_THRESHOLD,
          margin: float = 0.03) -> tuple[bool, int | None]:
    """Correct if the target passes its threshold and no lure matches clearly better.
    Returns (correct, index of the confusing lure or None)."""
    best_lure = int(np.argmax(lure_scores)) if lure_scores else None
    if best_lure is not None and lure_scores[best_lure] > target_score + margin:
        return False, best_lure
    return target_score >= threshold, None


__all__ = ["Tolerance", "Scorer", "ResponseInput", "score_motor", "judge", "keypose_indices", "bone_dirs",
           "resample", "mirror_seq", "View", "estimate_view", "rest_heading", "bone_weights", "FRAMINGS"]
