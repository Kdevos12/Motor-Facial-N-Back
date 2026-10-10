"""Minimal BVH parser + forward kinematics (numpy, vectorised over frames)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class BvhJoint:
    name: str
    offset: np.ndarray
    channels: list[str] = field(default_factory=list)
    children: list["BvhJoint"] = field(default_factory=list)
    parent: "BvhJoint | None" = None
    end_offset: np.ndarray | None = None
    channel_start: int = 0


@dataclass
class Bvh:
    root: BvhJoint
    joints: list[BvhJoint]
    frame_time: float
    motion: np.ndarray  # (F, total_channels)

    def joint(self, name: str) -> BvhJoint:
        for j in self.joints:
            if j.name == name:
                return j
        raise KeyError(name)


def parse_bvh(text: str) -> Bvh:
    tokens = text.split()
    pos = 0

    def take() -> str:
        nonlocal pos
        tok = tokens[pos]
        pos += 1
        return tok

    def expect(word: str) -> None:
        tok = take()
        if tok != word:
            raise ValueError(f"BVH: expected {word!r}, got {tok!r}")

    joints: list[BvhJoint] = []
    n_channels = 0

    def parse_joint(name: str, parent: BvhJoint | None) -> BvhJoint:
        nonlocal n_channels
        expect("{")
        expect("OFFSET")
        offset = np.array([float(take()) for _ in range(3)])
        j = BvhJoint(name=name, offset=offset, parent=parent)
        joints.append(j)
        expect("CHANNELS")
        k = int(take())
        j.channels = [take() for _ in range(k)]
        j.channel_start = n_channels
        n_channels += k
        while True:
            tok = take()
            if tok == "JOINT":
                j.children.append(parse_joint(take(), j))
            elif tok == "End":
                expect("Site")
                expect("{")
                expect("OFFSET")
                j.end_offset = np.array([float(take()) for _ in range(3)])
                expect("}")
            elif tok == "}":
                return j
            else:
                raise ValueError(f"BVH: unexpected token {tok!r}")

    expect("HIERARCHY")
    expect("ROOT")
    root = parse_joint(take(), None)
    expect("MOTION")
    expect("Frames:")
    n_frames = int(take())
    expect("Frame")
    expect("Time:")
    frame_time = float(take())
    values = np.array(tokens[pos:pos + n_frames * n_channels], dtype=float)
    if values.size != n_frames * n_channels:
        n_frames = values.size // max(n_channels, 1)
        values = values[: n_frames * n_channels]
    return Bvh(root=root, joints=joints, frame_time=frame_time, motion=values.reshape(n_frames, n_channels))


def _axis_rot(axis: str, deg: np.ndarray) -> np.ndarray:
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    o, z = np.ones_like(a), np.zeros_like(a)
    if axis == "X":
        rows = [[o, z, z], [z, c, -s], [z, s, c]]
    elif axis == "Y":
        rows = [[c, z, s], [z, o, z], [-s, z, c]]
    else:
        rows = [[c, -s, z], [s, c, z], [z, z, o]]
    return np.stack([np.stack(r, -1) for r in rows], -2)


def forward_kinematics(bvh: Bvh, frames: slice | np.ndarray | None = None) -> dict[str, np.ndarray]:
    """World positions (F, 3) of every joint, plus '<name>_end' for end sites."""
    motion = bvh.motion if frames is None else bvh.motion[frames]
    n = len(motion)
    out: dict[str, np.ndarray] = {}
    rots: dict[str, np.ndarray] = {}

    def visit(j: BvhJoint, parent_pos: np.ndarray, parent_rot: np.ndarray) -> None:
        local_t = np.broadcast_to(j.offset, (n, 3)).copy()
        local_r = np.broadcast_to(np.eye(3), (n, 3, 3)).copy()
        for k, ch in enumerate(j.channels):
            col = motion[:, j.channel_start + k]
            if ch.endswith("position"):
                local_t[:, "XYZ".index(ch[0])] += col
            else:
                local_r = local_r @ _axis_rot(ch[0], col)
        pos = parent_pos + np.einsum("fij,fj->fi", parent_rot, local_t)
        rot = parent_rot @ local_r
        out[j.name] = pos
        rots[j.name] = rot
        if j.end_offset is not None:
            out[j.name + "_end"] = pos + np.einsum("fij,j->fi", rot, j.end_offset)
        for c in j.children:
            visit(c, pos, rot)

    visit(bvh.root, np.zeros((n, 3)), np.broadcast_to(np.eye(3), (n, 3, 3)).copy())
    return out
