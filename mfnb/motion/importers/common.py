"""Shared steps for turning long mocap takes into library clips."""
from __future__ import annotations

import numpy as np

from ..library import FPS, SPACE_LIMITS, MotionItem, compute_metrics
from ..skeleton import J

LEG_LENGTH_M = 0.85
FEET = [J["l_ankle"], J["r_ankle"], J["l_foot"], J["r_foot"]]


def scale_to_standard(frames: np.ndarray) -> np.ndarray:
    leg = np.median(np.linalg.norm(frames[:, J["l_knee"]] - frames[:, J["l_hip"]], axis=-1)
                    + np.linalg.norm(frames[:, J["l_ankle"]] - frames[:, J["l_knee"]], axis=-1))
    return frames * (LEG_LENGTH_M / max(leg, 1e-9))


def face_camera(frames: np.ndarray) -> np.ndarray:
    """Recentre on the first frame's pelvis, rotate so it faces +z, put the feet on the floor."""
    f = frames.copy()
    mid = (f[0, J["l_hip"]] + f[0, J["r_hip"]]) / 2
    f[:, :, 0] -= mid[0]
    f[:, :, 2] -= mid[2]
    hip_vec = f[0, J["l_hip"]] - f[0, J["r_hip"]]
    fwd = np.cross(hip_vec, [0.0, 1.0, 0.0])
    yaw = np.arctan2(fwd[0], fwd[2])
    c, s = np.cos(-yaw), np.sin(-yaw)
    x, z = f[..., 0].copy(), f[..., 2].copy()
    f[..., 0] = c * x + s * z
    f[..., 2] = -s * x + c * z
    f[:, :, 1] -= f[:, FEET, 1].min()
    f[:, :, 1] += 0.02
    return f


def motion_energy(f: np.ndarray) -> np.ndarray:
    mid = (f[:, J["l_hip"]] + f[:, J["r_hip"]]) / 2
    rel = f - mid[:, None]
    v = np.linalg.norm(np.diff(rel, axis=0), axis=-1).sum(-1) * FPS
    v += np.linalg.norm(np.diff(mid, axis=0), axis=-1) * FPS * 3
    v = np.concatenate([[v[0]], v])
    k = max(1, int(0.25 * FPS))
    return np.convolve(v, np.ones(k) / k, mode="same")


def segment(frames: np.ndarray, min_s: float = 1.2, max_s: float = 5.0, window_s: float = 3.5) -> list[tuple[int, int]]:
    """Cut at rest pauses; long active stretches become fixed windows."""
    e = motion_energy(frames)
    active_level = np.percentile(e, 75)
    rest = e < 0.3 * active_level
    cuts = [0]
    i = 0
    n = len(e)
    while i < n:
        if rest[i]:
            j = i
            while j < n and rest[j]:
                j += 1
            if j - i >= int(0.25 * FPS):
                cuts.append((i + j) // 2)
            i = j
        else:
            i += 1
    cuts.append(n - 1)
    out = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        length = (b - a) / FPS
        if length < min_s:
            continue
        if length <= max_s:
            out.append((a, b))
        else:
            w = int(window_s * FPS)
            for s in range(a, b - int(min_s * FPS), w):
                out.append((s, min(b, s + w)))
    return out


def estimate_complexity(f: np.ndarray) -> int:
    e = motion_energy(f)
    top = e.max()
    if top <= 0:
        return 1
    peaks = [i for i in range(1, len(e) - 1) if e[i] >= e[i - 1] and e[i] > e[i + 1] and e[i] > 0.5 * top]
    merged: list[int] = []
    for p in peaks:
        if not merged or p - merged[-1] > int(0.35 * FPS):
            merged.append(p)
    return int(np.clip(len(merged) + 1, 2, 5))


def estimate_flexibility(f: np.ndarray) -> str:
    angles = []
    for side in ("l", "r"):
        thigh = f[:, J[f"{side}_knee"]] - f[:, J[f"{side}_hip"]]
        cosv = -thigh[:, 1] / np.maximum(np.linalg.norm(thigh, axis=-1), 1e-9)
        angles.append(np.degrees(np.arccos(np.clip(cosv, -1, 1))))
    hip_flex = float(np.max(angles))
    mid_y = (f[:, J["l_hip"], 1] + f[:, J["r_hip"], 1]) / 2
    crouch = float(mid_y.max() - mid_y.min())
    if hip_flex > 95 or crouch > 0.45:
        return "high"
    if hip_flex > 65 or crouch > 0.25:
        return "medium"
    return "low"


def make_clips(frames: np.ndarray, *, id_prefix: str, name: str, category: str, subcategory: str, source: str,
               description: str, max_clips: int = 6, space: str = "small", tags: list[str] | None = None) -> list[MotionItem]:
    """Segment a canonical 30 fps take into tagged clips that fit the training space."""
    # drop a T-pose calibration lead-in
    arms_out = np.abs(frames[:, J["l_wrist"], 0] - frames[:, J["r_wrist"], 0]) > 1.3
    if len(arms_out) > 15 and arms_out[:15].all():
        frames = frames[int(np.argmax(~arms_out)):]
    limit_fp, limit_reach = SPACE_LIMITS[space]
    items = []
    for k, (a, b) in enumerate(segment(frames)):
        seg = face_camera(frames[a:b + 1]).astype(np.float32)
        if not np.isfinite(seg).all():
            continue
        dev = np.linalg.norm(seg - seg[:1], axis=-1).sum(-1)
        if dev.max() < 1.0:
            continue
        m = compute_metrics(seg)
        if m["footprint_m"] > limit_fp or m["reach_m"] > limit_reach:
            continue
        items.append(MotionItem(
            id=f"{id_prefix}.{k}", name=f"{name} #{k + 1}", category=category, subcategory=subcategory,
            complexity=estimate_complexity(seg), flexibility=estimate_flexibility(seg), static=False,
            stance_based=False, source=source, segments=[id_prefix], description=description,
            tags=list(tags or ["mocap"]), frames=seg, **m))
    if len(items) > max_clips:
        idx = np.linspace(0, len(items) - 1, max_clips).round().astype(int)
        items = [items[i] for i in sorted(set(idx))]
    return items
