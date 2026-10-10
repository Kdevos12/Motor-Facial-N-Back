"""Small authoring DSL for procedural primitives.

A primitive's ``keys`` are ``[(t_seconds, partial_pose), ...]``. The first key of a
composable primitive is its full *home* pose and the last key returns to it, which lets the
composer chain primitives that share a home.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..rig import REST_POSE, merge_pose

FLEX = ("low", "medium", "high")


@dataclass
class Primitive:
    id: str
    name: str
    category: str
    subcategory: str
    keys: list[tuple[float, dict]]
    home: str | None = None
    complexity: int = 2
    flexibility: str = "low"
    static: bool = False
    stance_based: bool = False
    composable: bool = True
    description: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if self.flexibility not in FLEX:
            raise ValueError(f"{self.id}: bad flexibility {self.flexibility}")
        if self.static:
            self.composable = False
            self.complexity = 1


def full(*parts: dict, base: dict | None = None) -> dict:
    """Merge partial poses onto REST (or ``base``) into a full pose."""
    pose = dict(REST_POSE if base is None else base)
    for p in parts:
        pose = merge_pose(pose, p)
    return pose


def seq(home: dict, steps: list[tuple[float, dict]], back: float | None = 0.35,
        start: float = 0.0) -> list[tuple[float, dict]]:
    """Keys from ``home``: each step is (duration_to_reach, partial pose). Ends back home unless
    ``back`` is None. A step whose pose is an empty dict is a hold."""
    keys: list[tuple[float, dict]] = [(start, home)]
    t = start
    for dt, pose in steps:
        t += dt
        keys.append((round(t, 4), pose))
    if back is not None:
        t += back
        keys.append((round(t, 4), home))
    return keys


def strike(home: dict, peak: dict, t_in: float = 0.28, hold: float = 0.12, t_out: float = 0.32,
           chamber: dict | None = None, t_chamber: float = 0.22) -> list[tuple[float, dict]]:
    steps = []
    if chamber is not None:
        steps.append((t_chamber, chamber))
    steps += [(t_in, peak), (hold, {})]
    if chamber is not None:
        steps.append((t_chamber, chamber))
    return seq(home, steps, back=t_out)


def posture(pose: dict, t_in: float = 1.0, hold: float = 1.8) -> list[tuple[float, dict]]:
    """Static posture: rest -> pose -> hold."""
    return [(0.0, {}), (t_in, pose), (t_in + hold, {})]


def repeat(steps: list[tuple[float, dict]], n: int) -> list[tuple[float, dict]]:
    return [s for _ in range(n) for s in steps]
