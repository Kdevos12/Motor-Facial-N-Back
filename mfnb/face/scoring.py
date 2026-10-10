"""Facial response scoring.

Every response is read relative to the user's own resting face (a 2-s neutral clip taken at the camera check, or
the calibration one). An expression passes when, over its best 0.5-s hold:

(a) the response looks like the expected one (similarity >= threshold, 0.60 at normal strictness), where the
    expected response is the target scaled to what the tracker reports for this user (``expected``);
(b) every key part of the expression clearly moved: at least ``gamma`` (0.35) of the way from the user's neutral
    to that shape's maximum (their calibrated maximum, else the typical maximum on real faces);
(c) a one-sided key part (a wink, one eyebrow, half a smile) moved clearly more on that side: the other side rose at
    most 0.7 x as much.

Tested on real MediaPipe output of 15 people's posed photos with their own neutral photos (tests/test_face_real.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .blendshapes import (D, DEAD_MASK, DIMS, GAZE_MASK, MIRROR_PERM, REST_MEAN, REST_P90, TYPICAL_MAX, WEIGHTS,
                          mirror_vec)

COS_WEIGHT = 0.7
ACTIVE_TARGET = 0.05
ACTIVE_RESPONSE = 0.3
BASE_THRESHOLD = 0.60
BASE_GAMMA = 0.35
ASYM = 0.7
MIN_RANGE = 0.12
MIN_DEADZONE = 0.03
MIN_RISE = 0.10      # a calibration prompt must raise a shape at least this much to count as measured
HOLD_S = 0.5


def thresholds(strictness: float = 1.0) -> tuple[float, float]:
    """(similarity threshold, key-part fraction) for a strictness setting (0.7 lenient ... 1.3 strict)."""
    s = float(np.clip(strictness, 0.7, 1.3))
    return round(BASE_THRESHOLD + 0.25 * (s - 1.0), 3), round(BASE_GAMMA * s, 3)


@dataclass
class FaceCalibration:
    neutral: np.ndarray | None = None    # (D,) resting face
    deadzone: np.ndarray | None = None   # (D,) resting jitter subtracted before comparing
    rise: np.ndarray | None = None       # (D,) measured maximum rise above neutral, NaN where not measured
    lr_swap: bool = False                # the camera feed is mirrored relative to the user's anatomy

    @classmethod
    def from_dict(cls, d: dict | None) -> "FaceCalibration":
        if not d:
            return cls()

        def arr(k):
            v = d.get(k)
            return None if v is None else np.array([np.nan if x is None else x for x in v], float)
        return cls(neutral=arr("neutral"), deadzone=arr("deadzone"), rise=arr("rise"), lr_swap=bool(d.get("lr_swap", False)))

    def to_dict(self) -> dict:
        def out(v):
            return None if v is None else [None if not np.isfinite(x) else round(float(x), 4) for x in v]
        return {"neutral": out(self.neutral), "deadzone": out(self.deadzone), "rise": out(self.rise),
                "lr_swap": self.lr_swap, "measured": sorted(self.measured)}

    @property
    def measured(self) -> set[str]:
        if self.rise is None:
            return set()
        return {DIMS[k] for k in np.nonzero(np.isfinite(self.rise))[0]}

    def with_neutral(self, neutral: np.ndarray | None, deadzone: np.ndarray | None) -> "FaceCalibration":
        if neutral is None:
            return self
        return FaceCalibration(neutral=neutral, deadzone=deadzone, rise=self.rise, lr_swap=self.lr_swap)

    # -- derived quantities ---------------------------------------------------------------------------------
    @property
    def rest(self) -> np.ndarray:
        return REST_MEAN if self.neutral is None else self.neutral

    @property
    def dz(self) -> np.ndarray:
        return np.full(D, MIN_DEADZONE) if self.deadzone is None else np.maximum(self.deadzone, MIN_DEADZONE)

    @property
    def range(self) -> np.ndarray:
        """How far each shape can rise above this user's neutral."""
        prior = np.maximum(TYPICAL_MAX - self.rest, 0.0)
        if self.rise is None:
            return prior
        return np.where(np.isfinite(self.rise), self.rise, prior)

    def response(self, frames: np.ndarray) -> np.ndarray:
        """Raw shapes -> rise above the resting face, resting jitter removed."""
        return np.clip(np.asarray(frames, float) - self.rest - self.dz, 0.0, 1.0)

    def fraction(self, frames: np.ndarray) -> np.ndarray:
        """Raw shapes -> fraction of the way from neutral to this user's maximum (0..1)."""
        x = np.asarray(frames, float) - self.rest
        return np.clip(x / np.maximum(self.range, MIN_RANGE), 0.0, 1.0)


def neutral_from_frames(frames: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(T, D) raw frames of a relaxed face -> (neutral, deadzone). A face that is not relaxed (smiling, mouth open...)
    is clipped to the upper end of real resting faces, so it cannot hide a later expression."""
    f = np.asarray(frames, float)
    neutral = np.median(f, axis=0)
    neutral = np.minimum(neutral, np.maximum(REST_P90 + 0.1, 0.15))
    deadzone = np.maximum(np.percentile(f, 90, axis=0) - np.percentile(f, 50, axis=0), MIN_DEADZONE)
    return neutral, np.minimum(deadzone, 0.12)


@dataclass
class FaceTarget:
    """What one item asks for, in one orientation."""
    intent: np.ndarray                  # (D,) 0..1 of a full effort
    keys: list[list[int]]               # key parts (shape indices)
    gaze: bool = False                  # gaze shapes count only for gaze items

    @classmethod
    def of(cls, item, mirrored: bool = False) -> "FaceTarget":
        v = item.vector(mirrored)
        return cls(intent=v, keys=item.key_index(mirrored), gaze=bool((v[GAZE_MASK] > 0).any()))


def expected(target: FaceTarget, calib: FaceCalibration) -> np.ndarray:
    """The rise above neutral the tracker should report for this target and this user."""
    return np.where(DEAD_MASK, 0.0, target.intent * calib.range)


def similarity(e: np.ndarray, x: np.ndarray, gaze: bool = False) -> np.ndarray:
    """Similarity of response frame(s) x (..., D) with an expected response e (D,), in [0, 1]."""
    t = np.asarray(e, dtype=float)
    r = np.atleast_2d(np.asarray(x, dtype=float))
    w = WEIGHTS if gaze else np.where(GAZE_MASK, 0.0, WEIGHTS)
    num = (r * t * w).sum(-1)
    den = np.sqrt((t * t * w).sum()) * np.sqrt((r * r * w).sum(-1))
    cos = np.where(den > 1e-9, num / np.maximum(den, 1e-9), 0.0)
    active = (t > ACTIVE_TARGET)[None, :] | (r > ACTIVE_RESPONSE)
    mad = (np.abs(r - t) * w * active).sum(-1) / np.maximum((w * active).sum(-1), 1e-9)
    return np.clip(COS_WEIGHT * cos + (1 - COS_WEIGHT) * (1 - mad), 0.0, 1.0)


def key_check(target: FaceTarget, a: np.ndarray, gamma: float) -> tuple[np.ndarray, list[tuple[int, str]]]:
    """a: (..., D) fractions of range. Returns (g, failures): g >= 1 when every key part moved enough (rule b) and
    every one-sided part moved more on its side (rule c); failures lists (part index, 'weak'|'both sides') for the
    last frame."""
    a = np.atleast_2d(a)
    g = np.full(len(a), np.inf)
    fails: list[tuple[int, str]] = []
    for p, ks in enumerate(target.keys):
        frac = a[:, ks].mean(-1)
        ratio = frac / max(gamma, 1e-6)
        g = np.minimum(g, ratio)
        if ratio[-1] < 1:
            fails.append((p, "weak"))
        if len(ks) == 1:
            k = ks[0]
            m = int(MIRROR_PERM[k])
            if m != k and target.intent[m] == 0:
                # other side must stay at or below ASYM x this side
                other = a[:, m]
                sym = np.where(other > 1e-6, ASYM * a[:, k] / np.maximum(other, 1e-6), np.inf)
                g = np.minimum(g, sym)
                if sym[-1] < 1:
                    fails.append((p, "both sides"))
    return g, fails


@dataclass
class FaceScore:
    score: float
    valid: bool = True
    reason: str = ""
    matched: tuple[float, float] = (0.0, 0.0)
    similarity: float = 0.0
    missing: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    seen: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"score": round(float(self.score), 4), "valid": self.valid, "reason": self.reason,
                "matched": [round(self.matched[0], 2), round(self.matched[1], 2)],
                "similarity": round(float(self.similarity), 4), "missing": self.missing, "extra": self.extra,
                "seen": self.seen}


def _pretty(name: str) -> str:
    out = "".join(" " + c.lower() if c.isupper() else c for c in name)
    return out.strip()


def _part_name(ks: list[int]) -> str:
    names = [DIMS[k] for k in ks]
    if len(names) == 2 and names[0][:-4] == names[1][:-5] or len(names) == 2 and names[0][:-5] == names[1][:-4]:
        base = names[0][:-4] if names[0].endswith("Left") else names[0][:-5]
        return _pretty(base)
    return ", ".join(_pretty(n) for n in names)


class _Windows:
    """Moving 0.5-s averages of one response, shared by the target and the lures."""

    def __init__(self, frames: np.ndarray, times: np.ndarray, calib: FaceCalibration, hold_s: float):
        fps = (len(times) - 1) / max(times[-1] - times[0], 1e-6)
        self.win = max(1, min(len(frames), int(round(hold_s * fps))))
        c = np.cumsum(np.vstack([np.zeros((1, frames.shape[1])), frames]), axis=0)
        self.seg = (c[self.win:] - c[:-self.win]) / self.win          # (W, D) averaged raw shapes
        self.times = times
        self.x = calib.response(self.seg)
        self.a = calib.fraction(self.seg)
        self.calib = calib

    def score(self, target: FaceTarget, threshold: float, gamma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Per window: (score, similarity, gate). The score equals the similarity when every key part passes and is
        held below the threshold otherwise, so 'score >= threshold' is the pass rule."""
        sim = similarity(expected(target, self.calib), self.x, gaze=target.gaze)
        g, _ = key_check(target, self.a, gamma)
        ok = g >= 1
        s = np.where(ok, sim, np.minimum(sim * np.clip(g, 0, 1), threshold - 0.01))
        return np.clip(s, 0, 1), sim, g


def score_face(target: FaceTarget, frames: np.ndarray, times_s: np.ndarray | None = None,
               calib: FaceCalibration | None = None, *, threshold: float = BASE_THRESHOLD, gamma: float = BASE_GAMMA,
               hold_s: float = HOLD_S, lures: list[FaceTarget] | None = None) -> dict:
    """Best sustained match over the response window. ``frames`` are (T, D) raw blendshapes."""
    calib = calib or FaceCalibration()
    frames = np.asarray(frames, dtype=float)
    if frames.ndim == 2:
        keep = np.isfinite(frames).all(axis=1)
        frames = frames[keep]
        times_s = None if times_s is None else np.asarray(times_s, float)[keep]
    if frames.ndim != 2 or frames.shape[1] != D or len(frames) < 3:
        return {"target": FaceScore(0.0, valid=False, reason="no face tracked").to_dict(), "lures": []}
    times = np.arange(len(frames)) / 30.0 if times_s is None else np.asarray(times_s, float) - times_s[0]
    w = _Windows(frames, times, calib, hold_s)
    s, sim, g = w.score(target, threshold, gamma)
    j = int(np.argmax(s))
    a = w.a[j]
    _, fails = key_check(target, a[None], gamma)
    missing = [("not enough: " if why == "weak" else "both sides moved: ") + _part_name(target.keys[p])
               for p, why in fails]
    e = expected(target, calib)
    gap = w.x[j] - e
    allowed = np.ones(D, bool) if target.gaze else ~GAZE_MASK
    extra = [_pretty(DIMS[k]) for k in np.argsort(-gap)[:3] if gap[k] > 0.25 and allowed[k] and not DEAD_MASK[k]]
    seen = {DIMS[k]: round(float(a[k]), 2) for k in range(D) if a[k] >= 0.05 and not DEAD_MASK[k]
            and (target.gaze or not GAZE_MASK[k])}
    end = min(j + w.win - 1, len(times) - 1)
    res = FaceScore(float(s[j]), matched=(float(times[j]), float(times[end])), similarity=float(sim[j]),
                    missing=missing, extra=extra, seen=seen)
    lure_scores = [round(float(w.score(lt, threshold, gamma)[0].max()), 4) for lt in (lures or [])]
    return {"target": res.to_dict(), "lures": lure_scores}


def orient(frames: np.ndarray, lr_swap: bool) -> np.ndarray:
    return mirror_vec(frames) if lr_swap else np.asarray(frames, float)


def regions_of(target: dict[str, float]) -> list[str]:
    from .blendshapes import REGION
    return sorted({REGION[k] for k in target})


__all__ = ["FaceCalibration", "FaceTarget", "score_face", "similarity", "expected", "key_check", "thresholds",
           "neutral_from_frames", "orient", "BASE_THRESHOLD", "BASE_GAMMA", "MIN_RISE"]
