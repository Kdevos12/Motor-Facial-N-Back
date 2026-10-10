"""Facial response scoring on calibrated blendshapes."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .blendshapes import D, DIMS, REGION, WEIGHTS

COS_WEIGHT = 0.7
ACTIVE_TARGET = 0.05
ACTIVE_RESPONSE = 0.3


@dataclass
class FaceCalibration:
    neutral: np.ndarray | None = None   # (D,) resting face
    gain: np.ndarray | None = None      # (D,) per-shape gain so a full effort reaches ~1
    lr_swap: bool = False               # MediaPipe left/right convention vs the user's anatomy

    @classmethod
    def from_dict(cls, d: dict | None) -> "FaceCalibration":
        if not d:
            return cls()
        return cls(neutral=None if d.get("neutral") is None else np.asarray(d["neutral"], float),
                   gain=None if d.get("gain") is None else np.asarray(d["gain"], float),
                   lr_swap=bool(d.get("lr_swap", False)))

    def apply(self, frames: np.ndarray) -> np.ndarray:
        x = np.asarray(frames, dtype=float)
        if self.neutral is not None:
            x = x - self.neutral
        if self.gain is not None:
            x = x * self.gain
        return np.clip(x, 0.0, 1.0)


def similarity(target: np.ndarray, resp: np.ndarray) -> np.ndarray:
    """Similarity of response frame(s) (..., D) with one target (D,) in [0, 1]."""
    t = np.asarray(target, dtype=float)
    r = np.atleast_2d(np.asarray(resp, dtype=float))
    w = WEIGHTS
    num = (r * t * w).sum(-1)
    den = np.sqrt((t * t * w).sum()) * np.sqrt((r * r * w).sum(-1))
    cos = np.where(den > 1e-9, num / np.maximum(den, 1e-9), 0.0)
    active = (t > ACTIVE_TARGET)[None, :] | (r > ACTIVE_RESPONSE)
    diff = np.abs(r - t) * w
    mad = (diff * active).sum(-1) / np.maximum((w * active).sum(-1), 1e-9)
    return np.clip(COS_WEIGHT * cos + (1 - COS_WEIGHT) * (1 - mad), 0.0, 1.0)


@dataclass
class FaceScore:
    score: float
    valid: bool = True
    reason: str = ""
    matched: tuple[float, float] = (0.0, 0.0)
    missing: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"score": round(float(self.score), 4), "valid": self.valid, "reason": self.reason,
                "matched": [round(self.matched[0], 2), round(self.matched[1], 2)],
                "missing": self.missing, "extra": self.extra}


def _pretty(name: str) -> str:
    out = "".join(" " + c.lower() if c.isupper() else c for c in name)
    return out.strip()


def score_face(target: np.ndarray, frames: np.ndarray, times_s: np.ndarray | None = None,
               calib: FaceCalibration | None = None, hold_s: float = 0.5,
               lures: list[np.ndarray] | None = None) -> dict:
    """Best sustained match over the response window. ``frames`` are (T, D) raw blendshapes."""
    calib = calib or FaceCalibration()
    frames = np.asarray(frames, dtype=float)
    if frames.ndim != 2 or frames.shape[1] != D or len(frames) < 3:
        return {"target": FaceScore(0.0, valid=False, reason="no face tracked").to_dict(), "lures": []}
    times = np.arange(len(frames)) / 30.0 if times_s is None else np.asarray(times_s, float) - times_s[0]
    fps = (len(times) - 1) / max(times[-1] - times[0], 1e-6)
    win = max(1, min(len(frames), int(round(hold_s * fps))))
    resp = calib.apply(frames)
    kernel = np.ones(win) / win

    def best(t: np.ndarray) -> tuple[float, int]:
        sims = np.convolve(similarity(t, resp), kernel, mode="valid")
        j = int(np.argmax(sims))
        return float(sims[j]), j

    s, j = best(target)
    seg = resp[j:j + win].mean(0)
    gap = target - seg
    missing = [_pretty(DIMS[k]) for k in np.argsort(-gap)[:3] if gap[k] > 0.25]
    extra = [_pretty(DIMS[k]) for k in np.argsort(gap)[:3] if gap[k] < -0.3]
    res = FaceScore(s, matched=(float(times[j]), float(times[min(j + win, len(times) - 1)])),
                    missing=missing, extra=extra)
    lure_scores = [round(best(l)[0], 4) for l in (lures or [])]
    return {"target": res.to_dict(), "lures": lure_scores}


def regions_of(target: dict[str, float]) -> list[str]:
    return sorted({REGION[k] for k in target})
