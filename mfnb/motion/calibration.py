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


def calibrate(items: list, n_neg: int = 10, seed: int = 0, progress=None, pool: list | None = None,
              framing: str = "full") -> dict[str, dict]:
    """Thresholds for ``items``; near-miss negatives are drawn from ``pool`` (default: items).
    framing 'upper' scores the arms and trunk only, for the upper-body moves, against upper-body near-misses
    (the only ones a waist-up block can show); its keys get an '_upper' suffix."""
    rng = np.random.default_rng(seed)
    by_cat: dict[str, list] = {}
    pool = pool or items
    if framing == "upper":
        items = [it for it in items if it.body_part == "upper"]
        pool = [it for it in pool if it.body_part == "upper"]
    sfx = "" if framing == "full" else f"_{framing}"
    for it in pool:
        by_cat.setdefault(it.category, []).append(it)
    out = {}
    for k, it in enumerate(items):
        cands = [o for o in by_cat.get(it.category, []) if o.id != it.id] or [o for o in pool if o.id != it.id]
        picks = [cands[i] for i in rng.choice(len(cands), min(n_neg, len(cands)), replace=False)]
        neg = []
        for o in picks:
            f, t = synth_response(o.frames, rng, style_m=0.03)
            neg.append(score_motor([it.frames], ResponseInput(f, t), static=it.static, framing=framing)["target"]["score"])
        thr = float(np.clip(max(DEFAULT_THRESHOLD, np.percentile(neg, 90) + 0.05), DEFAULT_THRESHOLD, MAX_THRESHOLD))
        mirror = None
        if it.sided:
            f, t = synth_response(mirror_seq(it.frames), rng, style_m=0.03)
            mirror = score_motor([it.frames], ResponseInput(f, t), static=it.static, framing=framing)["target"]["score"]
        out[it.id] = {f"threshold{sfx}": round(thr, 3),
                      f"chiral{sfx}": bool(it.sided and mirror is not None and mirror < thr),
                      f"mirror_score{sfx}": None if mirror is None else round(float(mirror), 3)}
        if progress and k % 50 == 0:
            progress(k, len(items))
    return out


def calibrate_all(items: list, pool: list, progress=None) -> dict[str, dict]:
    """Full-body and upper-body thresholds, merged per item."""
    out = calibrate(items, progress=progress, pool=pool)
    for iid, d in calibrate(items, progress=progress, pool=pool, framing="upper").items():
        out.setdefault(iid, {}).update(d)
    return out


def user_calibration_file() -> Path:
    from ..config import home
    return home() / "calibration.json"


def load_calibration(path: Path | None = None) -> dict[str, dict]:
    """Bundled thresholds, overlaid with the user's (imported clips) unless a path is given."""
    paths = [path] if path else [CALIBRATION_FILE, user_calibration_file()]
    out: dict[str, dict] = {}
    for p in paths:
        if p.exists():
            out.update(json.loads(p.read_text()))
    return out


def save_calibration(data: dict, path: Path | None = None) -> None:
    path = path or CALIBRATION_FILE
    path.write_text(json.dumps(data, indent=0, sort_keys=True))


def merge_calibration(path: Path, data: dict) -> None:
    """Add or replace keys of existing entries (e.g. upper-body thresholds) without touching the others."""
    old = json.loads(path.read_text()) if path.exists() else {}
    for iid, d in data.items():
        old.setdefault(iid, {}).update(d)
    save_calibration(old, path)
