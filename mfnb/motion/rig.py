"""Direction-based forward kinematics for procedurally authored moves.

A pose is authored as *bone directions* plus a few torso/pelvis angles:

    {"yaw": -20, "twist": 15, "pitch": 5,
     "r_upper_arm": "@fwd", "r_forearm": "@fwd", "l_upper_arm": "down+0.6fwd+0.3out", ...}

Direction strings combine the tokens ``fwd back up down out in`` with optional weights
("down+0.3fwd"). ``out``/``in`` are side-relative (away from / toward the body midline), so
the same direction reads naturally for both sides. Arm directions live in the chest frame,
leg directions in the pelvis frame; a leading ``@`` means the root frame (facing the camera),
which is handy for strikes aimed straight at the viewer whatever the stance.

Scalars (degrees): yaw (pelvis turn; + turns the body toward the subject's left, so an
orthodox guard with the left shoulder forward uses a negative yaw), twist (chest relative to
pelvis, same sign), pitch (+ leans forward), roll (+ bends toward the subject's left),
head_yaw, head_pitch (+ = chin up), head_roll. x/z: root offset in metres.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, fields

import numpy as np

from .skeleton import J, N_JOINTS

ARM_SEGMENTS = ["upper_arm", "forearm", "hand"]
LEG_SEGMENTS = ["thigh", "shin", "foot"]
SEGMENTS = [f"{s}_{seg}" for s in ("l", "r") for seg in ARM_SEGMENTS + LEG_SEGMENTS]
SCALARS = ["yaw", "twist", "pitch", "roll", "head_yaw", "head_pitch", "head_roll", "x", "z"]


@dataclass(frozen=True)
class BodyDims:
    hip_half: float = 0.10
    shoulder_half: float = 0.18
    torso: float = 0.50
    upper_arm: float = 0.29
    forearm: float = 0.26
    hand: float = 0.15
    thigh: float = 0.43
    shin: float = 0.42
    foot: float = 0.17
    ankle_height: float = 0.08

    @classmethod
    def from_dict(cls, d: dict | None) -> "BodyDims":
        if not d:
            return cls()
        names = {f.name for f in fields(cls)}
        return cls(**{k: float(v) for k, v in d.items() if k in names})


DEFAULT_BODY = BodyDims()

_AXES = {
    "fwd": (0.0, 0.0, 1.0), "back": (0.0, 0.0, -1.0),
    "up": (0.0, 1.0, 0.0), "down": (0.0, -1.0, 0.0),
    "out": (1.0, 0.0, 0.0), "in": (-1.0, 0.0, 0.0),
}
_TOKEN = re.compile(r"([+-]?)\s*(\d*\.?\d*)\s*(fwd|back|up|down|out|in)")

REST_POSE: dict = {
    "l_upper_arm": "down+0.08out", "l_forearm": "down+0.06out+0.08fwd",
    "r_upper_arm": "down+0.08out", "r_forearm": "down+0.06out+0.08fwd",
    "l_thigh": "down+0.04out", "l_shin": "down",
    "r_thigh": "down+0.04out", "r_shin": "down",
}


def parse_dir(spec) -> tuple[bool, np.ndarray]:
    """Return (root_frame, unit side-relative vector [out, up, fwd])."""
    if isinstance(spec, str):
        s = spec.strip()
        root = s.startswith("@")
        if root:
            s = s[1:]
        v = np.zeros(3)
        pos = 0
        for m in _TOKEN.finditer(s):
            if s[pos:m.start()].strip(" +"):
                raise ValueError(f"bad direction spec {spec!r}")
            sign = -1.0 if m.group(1) == "-" else 1.0
            coef = float(m.group(2)) if m.group(2) not in ("", ".") else 1.0
            v += sign * coef * np.array(_AXES[m.group(3)])
            pos = m.end()
        if s[pos:].strip() or not np.any(v):
            raise ValueError(f"bad direction spec {spec!r}")
    else:
        root = False
        v = np.asarray(spec, dtype=float)
        if v.shape != (3,) or not np.any(v):
            raise ValueError(f"bad direction vector {spec!r}")
    return root, v / np.linalg.norm(v)


def _rx(a):
    c, s = np.cos(a), np.sin(a)
    o, z = np.ones_like(a), np.zeros_like(a)
    return np.stack([np.stack([o, z, z], -1), np.stack([z, c, -s], -1), np.stack([z, s, c], -1)], -2)


def _ry(a):
    c, s = np.cos(a), np.sin(a)
    o, z = np.ones_like(a), np.zeros_like(a)
    return np.stack([np.stack([c, z, s], -1), np.stack([z, o, z], -1), np.stack([-s, z, c], -1)], -2)


def _rz(a):
    c, s = np.cos(a), np.sin(a)
    o, z = np.ones_like(a), np.zeros_like(a)
    return np.stack([np.stack([c, -s, z], -1), np.stack([s, c, z], -1), np.stack([z, z, o], -1)], -2)


def frames_from_scalars(sc: dict[str, np.ndarray]):
    """Pelvis, chest and head rotation matrices, each (T, 3, 3)."""
    d = {k: np.radians(np.asarray(sc[k], dtype=float)) for k in ("yaw", "twist", "pitch", "roll",
                                                                  "head_yaw", "head_pitch", "head_roll")}
    pelvis = _ry(d["yaw"])
    chest = _ry(d["yaw"] + d["twist"]) @ _rx(d["pitch"]) @ _rz(-d["roll"])
    head = chest @ _ry(d["head_yaw"]) @ _rx(-d["head_pitch"]) @ _rz(-d["head_roll"])
    return pelvis, chest, head


@dataclass
class ResolvedKey:
    """A keyframe with every bone direction expressed in the root (world) frame."""
    t: float
    scalars: dict[str, float]
    dirs: np.ndarray  # (len(SEGMENTS), 3)


def merge_pose(base: dict, update: dict) -> dict:
    out = dict(base)
    for k, v in update.items():
        if k not in SCALARS and k not in SEGMENTS:
            raise KeyError(f"unknown pose key {k!r}")
        out[k] = v
    return out


def resolve_pose(pose: dict, t: float = 0.0) -> ResolvedKey:
    sc = {k: float(pose.get(k, 0.0)) for k in SCALARS}
    pel, chest, _ = frames_from_scalars({k: np.array([v]) for k, v in sc.items()})
    pel, chest = pel[0], chest[0]
    dirs = np.zeros((len(SEGMENTS), 3))
    for side, sgn in (("l", 1.0), ("r", -1.0)):
        for group, frame, segs in (("arm", chest, ARM_SEGMENTS), ("leg", pel, LEG_SEGMENTS)):
            prev = None
            for seg in segs:
                name = f"{side}_{seg}"
                spec = pose.get(name)
                if spec is None:
                    if seg == "hand":
                        world = prev
                    elif seg == "foot":
                        fwd = pel @ np.array([0.0, 0.0, 1.0])
                        world = fwd + 0.35 * prev
                    else:
                        raise KeyError(f"pose missing {name}")
                else:
                    root, v = parse_dir(spec)
                    local = np.array([sgn * v[0], v[1], v[2]])
                    world = local if root else frame @ local
                world = world / np.linalg.norm(world)
                dirs[SEGMENTS.index(name)] = world
                prev = world
    return ResolvedKey(t=t, scalars=sc, dirs=dirs)


def _slerp(a: np.ndarray, b: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Slerp between unit vectors a,b (S,3) for weights w (T,) -> (T,S,3)."""
    dot = np.clip(np.sum(a * b, -1), -1.0, 1.0)
    om = np.arccos(dot)
    so = np.sin(om)
    w = w[:, None]
    small = so < 1e-4
    safe_so = np.where(small, 1.0, so)
    wa = np.where(small, 1 - w, np.sin((1 - w) * om) / safe_so)
    wb = np.where(small, w, np.sin(w * om) / safe_so)
    out = wa[..., None] * a + wb[..., None] * b
    return out / np.linalg.norm(out, axis=-1, keepdims=True)


def _ease(u: np.ndarray) -> np.ndarray:
    return u * u * (3 - 2 * u)


def interpolate(keys: list[ResolvedKey], fps: float = 30.0):
    """Sample resolved keys -> (scalars dict of (T,), dirs (T, S, 3))."""
    if not keys:
        raise ValueError("no keys")
    duration = keys[-1].t
    n = max(1, int(round(duration * fps)) + 1)
    times = np.arange(n) / fps
    sc = {k: np.zeros(n) for k in SCALARS}
    dirs = np.zeros((n, len(SEGMENTS), 3))
    if len(keys) == 1:
        for k in SCALARS:
            sc[k][:] = keys[0].scalars[k]
        dirs[:] = keys[0].dirs
        return sc, dirs
    for i in range(len(keys) - 1):
        a, b = keys[i], keys[i + 1]
        last = i == len(keys) - 2
        mask = (times >= a.t) & ((times <= b.t) if last else (times < b.t))
        if not mask.any():
            continue
        span = max(b.t - a.t, 1e-9)
        u = _ease(np.clip((times[mask] - a.t) / span, 0.0, 1.0))
        for k in SCALARS:
            sc[k][mask] = a.scalars[k] + (b.scalars[k] - a.scalars[k]) * u
        dirs[mask] = _slerp(a.dirs, b.dirs, u)
    return sc, dirs


def forward_kinematics(sc: dict[str, np.ndarray], dirs: np.ndarray, body: BodyDims = DEFAULT_BODY,
                       ground: bool = True) -> np.ndarray:
    """Scalars (T,) + world bone directions (T,S,3) -> joints (T,19,3)."""
    n = dirs.shape[0]
    pel, chest, head = frames_from_scalars(sc)
    out = np.zeros((n, N_JOINTS, 3))
    mid_hip = np.stack([np.asarray(sc["x"], float), np.full(n, 1.0), np.asarray(sc["z"], float)], -1)
    ex = np.array([1.0, 0.0, 0.0])
    ey = np.array([0.0, 1.0, 0.0])
    pel_x = pel @ ex
    chest_x = chest @ ex
    chest_y = chest @ ey
    mid_sh = mid_hip + chest_y * body.torso
    out[:, J["l_hip"]] = mid_hip + pel_x * body.hip_half
    out[:, J["r_hip"]] = mid_hip - pel_x * body.hip_half
    out[:, J["l_shoulder"]] = mid_sh + chest_x * body.shoulder_half
    out[:, J["r_shoulder"]] = mid_sh - chest_x * body.shoulder_half
    out[:, J["nose"]] = mid_sh + head @ np.array([0.0, 0.20, 0.09])
    out[:, J["l_ear"]] = mid_sh + head @ np.array([0.075, 0.19, -0.01])
    out[:, J["r_ear"]] = mid_sh + head @ np.array([-0.075, 0.19, -0.01])
    seg = {name: dirs[:, i] for i, name in enumerate(SEGMENTS)}
    for s in ("l", "r"):
        elbow = out[:, J[f"{s}_shoulder"]] + seg[f"{s}_upper_arm"] * body.upper_arm
        wrist = elbow + seg[f"{s}_forearm"] * body.forearm
        out[:, J[f"{s}_elbow"]] = elbow
        out[:, J[f"{s}_wrist"]] = wrist
        out[:, J[f"{s}_index"]] = wrist + seg[f"{s}_hand"] * body.hand
        knee = out[:, J[f"{s}_hip"]] + seg[f"{s}_thigh"] * body.thigh
        ankle = knee + seg[f"{s}_shin"] * body.shin
        out[:, J[f"{s}_knee"]] = knee
        out[:, J[f"{s}_ankle"]] = ankle
        out[:, J[f"{s}_foot"]] = ankle + seg[f"{s}_foot"] * body.foot
    if ground:
        lows = np.stack([
            out[:, J["l_ankle"], 1] - body.ankle_height, out[:, J["r_ankle"], 1] - body.ankle_height,
            out[:, J["l_foot"], 1] - 0.02, out[:, J["r_foot"], 1] - 0.02,
        ], -1).min(-1)
        out[:, :, 1] -= lows[:, None]
    return out


def sample_keys(keys: list[tuple[float, dict]], fps: float = 30.0, body: BodyDims = DEFAULT_BODY,
                base: dict | None = None) -> np.ndarray:
    """Author-level keys [(t, partial pose), ...] -> grounded joints (T, 19, 3).

    Each key's partial pose is merged onto the previous full pose (the first onto ``base``,
    default REST_POSE), so keys only list what changes.
    """
    pose = dict(REST_POSE if base is None else base)
    resolved = []
    for t, upd in keys:
        pose = merge_pose(pose, upd)
        resolved.append(resolve_pose(pose, t))
    sc, dirs = interpolate(resolved, fps)
    return forward_kinematics(sc, dirs, body)


def pose_joints(pose: dict, body: BodyDims = DEFAULT_BODY) -> np.ndarray:
    """Single full pose -> joints (19, 3)."""
    return sample_keys([(0.0, pose)], body=body)[0]
