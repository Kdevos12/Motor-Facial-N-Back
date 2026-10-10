"""Per-item acceptance thresholds (idea from the Jackknife recogniser, reimplemented).

Each item is scored against synthetic executions of *other* items from its category; its
threshold sits above the best of those near-misses, so moves with close neighbours need a
more faithful execution, and moves with no close neighbour are not judged too harshly.
The same pass measures whether the mirrored move is distinguishable (chirality instructions
are only given for items where it is).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..sim import synth_response
from .scoring import DEFAULT_THRESHOLD, ResponseInput, score_motor
from .skeleton import mirror_seq

CALIBRATION_FILE = Path(__file__).resolve().parent / "data" / "calibration.json"
MAX_THRESHOLD = 0.75


def calibrate(items: list, n_neg: int = 10, seed: int = 0, progress=None) -> dict[str, dict]:
    rng = np.random.default_rng(seed)
    by_cat: dict[str, list] = {}
    for it in items:
        by_cat.setdefault(it.category, []).append(it)
    out = {}
    for k, it in enumerate(items):
        pool = [o for o in by_cat[it.category] if o.id != it.id] or [o for o in items if o.id != it.id]
        picks = [pool[i] for i in rng.choice(len(pool), min(n_neg, len(pool)), replace=False)]
        neg = []
        for o in picks:
            f, t = synth_response(o.frames, rng, style_m=0.03)
            neg.append(score_motor([it.frames], ResponseInput(f, t), static=it.static)["target"]["score"])
        thr = float(np.clip(max(DEFAULT_THRESHOLD, np.percentile(neg, 90) + 0.05), DEFAULT_THRESHOLD, MAX_THRESHOLD))
        mirror = None
        if it.sided:
            f, t = synth_response(mirror_seq(it.frames), rng, style_m=0.03)
            mirror = score_motor([it.frames], ResponseInput(f, t), static=it.static)["target"]["score"]
        out[it.id] = {"threshold": round(thr, 3),
                      "chiral": bool(it.sided and mirror is not None and mirror < thr),
                      "mirror_score": None if mirror is None else round(float(mirror), 3)}
        if progress and k % 50 == 0:
            progress(k, len(items))
    return out


def load_calibration(path: Path | None = None) -> dict[str, dict]:
    path = path or CALIBRATION_FILE
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_calibration(data: dict, path: Path | None = None) -> None:
    path = path or CALIBRATION_FILE
    path.write_text(json.dumps(data, indent=0, sort_keys=True))
