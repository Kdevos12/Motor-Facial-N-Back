"""Import any BVH file: joints are recognised from their names (Mixamo, CMU, Bandai Namco,
LaFAN1/Ubisoft, Rokoko and most rigs), the up axis and handedness are detected."""
from __future__ import annotations

import re

import numpy as np

from ..library import FPS
from ..skeleton import J, N_JOINTS
from .bvh import Bvh, forward_kinematics, parse_bvh
from .common import scale_to_standard

PARTS = {
    "shoulder": [r"^upperarm$", r"^arm$", r"^shldr$", r"^shoulder$"],
    "elbow": [r"^lowerarm$", r"^forearm$", r"^elbow$"],
    "wrist": [r"^hand$", r"^wrist$"],
    "hip": [r"^upperleg$", r"^upleg$", r"^thigh$", r"^hip$"],
    "knee": [r"^lowerleg$", r"^leg$", r"^shin$", r"^knee$", r"^calf$"],
    "ankle": [r"^foot$", r"^ankle$"],
    "toe": [r"^toebase$", r"^toes?$", r"^toe\w*$"],
    "index": [r"^(hand)?index\w*$"],
}
CANON = {"shoulder": "shoulder", "elbow": "elbow", "wrist": "wrist", "hip": "hip", "knee": "knee", "ankle": "ankle"}


def split_side(name: str) -> tuple[str | None, str]:
    """('l' | 'r' | None, normalised base name)."""
    n = name.split(":")[-1]
    side = None
    low = n.lower()
    for pre, sd in (("left", "l"), ("right", "r")):
        if low.startswith(pre):
            side, n = sd, n[len(pre):]
            break
        if low.endswith(pre):
            side, n = sd, n[: -len(pre)]
            break
    if side is None:
        m = re.match(r"^([lLrR])[_.\s]?(?=[A-Z_.])(.+)$", n)
        if m and (n[1].isupper() or n[1] in "_. "):
            side, n = m.group(1).lower(), m.group(2)
        else:
            m = re.match(r"^(.+?)[_.\s]([lLrR])$", n)
            if m:
                side, n = m.group(2).lower(), m.group(1)
    base = re.sub(r"[^a-z]", "", n.lower())
    return side, base


def auto_map(bvh: Bvh) -> dict[str, str]:
    """Canonical joint (and 'head', 'neck', toe/index tips) -> BVH joint or '<joint>_end'."""
    info = [(j, *split_side(j.name)) for j in bvh.joints]
    out: dict[str, str] = {}
    for side in ("l", "r"):
        for part, patterns in PARTS.items():
            found = None
            for pat in patterns:
                for j, sd, base in info:
                    if sd == side and re.match(pat, base) and not (part == "hip" and j.parent is None):
                        found = j
                        break
                if found:
                    break
            if found is None:
                continue
            if part in CANON:
                out[f"{side}_{CANON[part]}"] = found.name
            elif part == "toe":
                out[f"{side}_foot"] = found.name + "_end" if found.end_offset is not None else found.name
            elif part == "index":
                deepest = found
                while deepest.children:
                    deepest = deepest.children[0]
                out[f"{side}_index"] = deepest.name + "_end" if deepest.end_offset is not None else deepest.name
    for side in ("l", "r"):
        if f"{side}_foot" not in out and f"{side}_ankle" in out:
            ank = bvh.joint(out[f"{side}_ankle"])
            if ank.end_offset is not None:
                out[f"{side}_foot"] = ank.name + "_end"
    for j, sd, base in info:
        if sd is None and base == "head":
            out["head"] = j.name
            if j.end_offset is not None:
                out["head_top"] = j.name + "_end"
        if sd is None and base in ("neck", "neck1") and "neck" not in out:
            out["neck"] = j.name
    required = [f"{s}_{p}" for s in "lr" for p in CANON.values()] + ["head"]
    missing = [r for r in required if r not in out]
    if missing:
        raise ValueError(f"could not recognise joints: {missing}")
    return out


def to_canonical_generic(pos: dict[str, np.ndarray], mapping: dict[str, str]) -> np.ndarray:
    n = len(pos[mapping["head"]])
    out = np.zeros((n, N_JOINTS, 3))
    for side in ("l", "r"):
        for p in ("shoulder", "elbow", "wrist", "hip", "knee", "ankle"):
            out[:, J[f"{side}_{p}"]] = pos[mapping[f"{side}_{p}"]]
        wrist, elbow = out[:, J[f"{side}_wrist"]], out[:, J[f"{side}_elbow"]]
        key = mapping.get(f"{side}_index")
        out[:, J[f"{side}_index"]] = pos[key] if key in pos else wrist + (wrist - elbow) * 0.55
        ankle, knee = out[:, J[f"{side}_ankle"]], out[:, J[f"{side}_knee"]]
        key = mapping.get(f"{side}_foot")
        if key in pos:
            out[:, J[f"{side}_foot"]] = pos[key]
        else:
            out[:, J[f"{side}_foot"]] = ankle + 0.4 * np.linalg.norm(ankle - knee, axis=-1, keepdims=True) * [0, -0.3, 1]
    up_axis = _detect_up(out)
    out = _to_y_up(out, up_axis)
    head = _to_y_up(pos[mapping["head"]][:, None], up_axis)[:, 0]
    top = _to_y_up(pos[mapping["head_top"]][:, None], up_axis)[:, 0] if "head_top" in mapping else None
    mid_sh = (out[:, J["l_shoulder"]] + out[:, J["r_shoulder"]]) / 2
    head_up = (top - head) if top is not None else (head - mid_sh)
    head_up /= np.maximum(np.linalg.norm(head_up, axis=-1, keepdims=True), 1e-9)
    hip_vec = out[:, J["l_hip"]] - out[:, J["r_hip"]]
    fwd = np.cross(hip_vec, [0.0, 1.0, 0.0])
    fwd -= np.sum(fwd * head_up, -1, keepdims=True) * head_up
    fwd /= np.maximum(np.linalg.norm(fwd, axis=-1, keepdims=True), 1e-9)
    lateral = np.cross(head_up, fwd)
    unit = np.linalg.norm(out[:, J["l_knee"]] - out[:, J["l_hip"]], axis=-1, keepdims=True) / 0.43
    out[:, J["nose"]] = head + unit * (0.07 * head_up + 0.10 * fwd)
    out[:, J["l_ear"]] = head + unit * (0.06 * head_up + 0.075 * lateral)
    out[:, J["r_ear"]] = head + unit * (0.06 * head_up - 0.075 * lateral)
    out = scale_to_standard(out)
    # handedness: toes must point the same way as the body faces
    toes = (out[:, J["l_foot"]] - out[:, J["l_ankle"]]) + (out[:, J["r_foot"]] - out[:, J["r_ankle"]])
    if np.mean(np.sum(toes * fwd, -1)) < 0:
        out[..., 0] *= -1
    return out


def _detect_up(frames: np.ndarray) -> tuple[int, float]:
    """Axis (0/1/2) pointing from the feet to the shoulders, and its sign."""
    span = np.median((frames[:, J["l_shoulder"]] + frames[:, J["r_shoulder"]]) / 2
                     - (frames[:, J["l_ankle"]] + frames[:, J["r_ankle"]]) / 2, axis=0)
    axis = int(np.argmax(np.abs(span)))
    return axis, float(np.sign(span[axis]) or 1.0)


def _to_y_up(a: np.ndarray, up: tuple[int, float]) -> np.ndarray:
    axis, sign = up
    if axis == 1:
        return a * np.array([1.0, sign, sign])  # y-down: rotate 180 degrees about x
    if axis == 2:  # z-up -> y-up (rotation about x keeps handedness)
        return np.stack([a[..., 0], sign * a[..., 2], -sign * a[..., 1]], -1)
    return np.stack([-sign * a[..., 1], sign * a[..., 0], a[..., 2]], -1)  # x-up


def bvh_to_frames(text: str) -> np.ndarray:
    bvh = parse_bvh(text)
    step = max(1, int(round(1.0 / (bvh.frame_time * FPS))))
    mapping = auto_map(bvh)
    return to_canonical_generic(forward_kinematics(bvh, slice(0, None, step)), mapping)
