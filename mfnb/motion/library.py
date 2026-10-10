"""Motion library: procedural primitives + composed combos (+ imported clips), with tags."""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from functools import lru_cache

import numpy as np

from .primitives import boxing, dance, everyday, fitness, grappling, kicks, martial, taichi
from .primitives.dsl import FLEX, Primitive
from .rig import sample_keys
from .skeleton import J, mirror_seq

FPS = 30
PAD_S = 0.35  # stillness shown before and after each move so the stance is readable
CATEGORIES = [
    "static postures", "boxing", "evasion", "kicks", "taekwondo", "karate", "grappling",
    "tai chi & qigong", "dance", "fitness", "everyday & sports",
]
SPACE_LIMITS = {  # (max stepping footprint, max reach) in metres
    "small": (0.75, 1.3),   # ~2-3 m^2 (about 1.5 m x 1.7 m)
    "medium": (1.0, 1.6),
    "large": (3.0, 3.0),
}


@dataclass
class MotionItem:
    id: str
    name: str
    category: str
    subcategory: str
    complexity: int
    flexibility: str
    static: bool
    stance_based: bool
    source: str
    segments: list[str]
    duration_s: float = 0.0
    footprint_m: float = 0.0
    reach_m: float = 0.0
    rotation_deg: float = 0.0
    facing_away_deg: float = 0.0
    sided: bool = True
    body_part: str = "upper"
    description: str = ""
    tags: list[str] = field(default_factory=list)
    threshold: float = 0.45   # per-item acceptance threshold (see calibration.py)
    chiral: bool = False      # mirrored version is distinguishable -> "switch sides" allowed
    threshold_upper: float | None = None   # the same when only the upper body is scored (framing 'upper')
    chiral_upper: bool | None = None
    heading_min_deg: float | None = None   # signed facing range during the move (0 = facing the screen)
    heading_max_deg: float | None = None
    frames: np.ndarray | None = field(default=None, repr=False, compare=False)

    def meta(self) -> dict:
        d = asdict(self)
        d.pop("frames")
        return d


def compute_metrics(frames: np.ndarray) -> dict:
    mid_hip = (frames[:, J["l_hip"]] + frames[:, J["r_hip"]]) / 2
    origin = mid_hip[0, [0, 2]]
    horiz = frames[:, :, [0, 2]] - origin
    ankles = frames[:, [J["l_ankle"], J["r_ankle"]]]
    grounded = ankles[:, :, 1] < 0.18
    ank_d = np.linalg.norm(ankles[:, :, [0, 2]] - origin, axis=-1)
    hip_d = np.linalg.norm(mid_hip[:, [0, 2]] - origin, axis=-1)
    footprint = max(float(hip_d.max()), float(ank_d[grounded].max()) if grounded.any() else 0.0)
    reach = float(np.linalg.norm(horiz, axis=-1).max())
    yaw = heading_track(frames)
    rotation = float(np.degrees(np.abs(yaw - yaw[0]).max()))
    facing = float(np.degrees(np.abs(yaw).max()))
    mirror_err = float(np.linalg.norm(frames - mirror_seq(frames), axis=-1).mean())
    rel = frames - mid_hip[:, None, :]
    def moved(names):
        idx = [J[n] for n in names]
        return float(np.linalg.norm(rel[:, idx] - rel[:1, idx], axis=-1).max())
    arms = moved(["l_wrist", "r_wrist", "l_elbow", "r_elbow"])
    legs = moved(["l_ankle", "r_ankle", "l_knee", "r_knee"])
    crouch = float(mid_hip[:, 1].max() - mid_hip[:, 1].min())
    uses_legs = legs > 0.15 or crouch > 0.12
    uses_arms = arms > 0.15
    body_part = "full" if (uses_legs and uses_arms) else ("lower" if uses_legs else "upper")
    return {
        "duration_s": round((len(frames) - 1) / FPS, 3),
        "footprint_m": round(footprint, 3), "reach_m": round(reach, 3),
        "rotation_deg": round(rotation, 1), "facing_away_deg": round(facing, 1),
        "sided": mirror_err > 0.03, "body_part": body_part,
        "heading_min_deg": round(float(np.degrees(yaw.min())), 1), "heading_max_deg": round(float(np.degrees(yaw.max())), 1),
    }


def heading_track(frames: np.ndarray) -> np.ndarray:
    """Facing angle (rad, unwrapped) of the hips per frame: 0 = facing the screen, positive = turned to the left."""
    hip_vec = frames[:, J["l_hip"]] - frames[:, J["r_hip"]]
    fwd = np.cross(hip_vec, [0.0, 1.0, 0.0])
    return np.unwrap(np.arctan2(fwd[:, 0], fwd[:, 2]))


def _all_primitives() -> list[Primitive]:
    mods = [everyday, boxing, kicks, martial, grappling, taichi, dance, fitness]
    prims = [p for m in mods for p in m.primitives()]
    ids = [p.id for p in prims]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate primitive ids: {sorted(dupes)}")
    return prims


def _curated_combos() -> list[tuple[str, list[str]]]:
    out = []
    for c in boxing.COMBOS:
        out.append(("evasion" if any(s.startswith("evade.") for s in c) else "boxing", c))
    out += [("kicks", c) for c in kicks.COMBOS]
    out += [("taekwondo" if c[0].startswith("tkd.") else "karate", c) for c in martial.COMBOS]
    out += [("grappling", c) for c in grappling.COMBOS]
    out += [("tai chi & qigong", c) for c in taichi.COMBOS]
    out += [("dance", c) for c in dance.COMBOS]
    out += [("fitness", c) for c in fitness.COMBOS]
    out += [("everyday & sports", c) for c in everyday.COMBOS]
    return out


def combine_keys(prims: list[Primitive]) -> list[tuple[float, dict]]:
    keys = list(prims[0].keys)
    for p in prims[1:]:
        t0 = keys[-1][0]
        keys += [(round(t0 + t, 4), pose) for t, pose in p.keys[1:]]
    return keys


def _random_combos(prims: list[Primitive], per_category: dict[str, int], seed: int = 7,
                   existing: set[tuple[str, ...]] = frozenset()) -> list[tuple[str, list[str]]]:
    rng = random.Random(seed)
    out = []
    seen = set(existing)
    for cat, n in per_category.items():
        pool = [p for p in prims if p.category == cat and p.composable and p.home]
        groups: dict[str, list[Primitive]] = {}
        for p in pool:
            groups.setdefault(p.home, []).append(p)
        groups = {h: g for h, g in groups.items() if len(g) >= 3}
        if not groups:
            continue
        tries = 0
        made = 0
        while made < n and tries < n * 30:
            tries += 1
            g = rng.choice(list(groups.values()))
            k = rng.choices([2, 3, 4], weights=[5, 4, 1])[0]
            combo = tuple(p.id for p in rng.sample(g, min(k, len(g))))
            if combo in seen:
                continue
            seen.add(combo)
            out.append((cat, list(combo)))
            made += 1
    return out


RANDOM_COMBOS_PER_CATEGORY = {
    "boxing": 25, "evasion": 10, "kicks": 25, "taekwondo": 25, "karate": 20, "grappling": 20,
    "tai chi & qigong": 15, "dance": 30, "fitness": 25, "everyday & sports": 15,
}


def _item_from(prims: list[Primitive], category: str | None = None, cid: str | None = None) -> MotionItem:
    keys = prims[0].keys if len(prims) == 1 else combine_keys(prims)
    frames = sample_keys(keys, fps=FPS).astype(np.float32)
    if not prims[0].static:
        pad = int(round(PAD_S * FPS))
        frames = np.concatenate([np.repeat(frames[:1], pad, 0), frames, np.repeat(frames[-1:], pad, 0)])
    flex = max((p.flexibility for p in prims), key=FLEX.index)
    if len(prims) == 1:
        p = prims[0]
        complexity, name, sub = p.complexity, p.name, p.subcategory
        cat, desc, tags = p.category, p.description, list(p.tags)
    else:
        complexity = min(5, max(max(p.complexity for p in prims), len(prims) + 1))
        name = " + ".join(p.name for p in prims)
        sub, cat, desc = "combos", category or prims[0].category, ""
        tags = sorted({t for p in prims for t in p.tags})
    item = MotionItem(
        id=cid or prims[0].id, name=name, category=cat, subcategory=sub, complexity=complexity,
        flexibility=flex, static=prims[0].static and len(prims) == 1,
        stance_based=any(p.stance_based for p in prims), source="procedural",
        segments=[p.id for p in prims], description=desc, tags=tags, frames=frames,
    )
    for k, v in compute_metrics(frames).items():
        setattr(item, k, v)
    return item


class MotionLibrary:
    def __init__(self, items: list[MotionItem]):
        self.items: dict[str, MotionItem] = {}
        for it in items:
            if it.id in self.items:
                raise ValueError(f"duplicate item id {it.id}")
            if it.heading_min_deg is None and it.frames is not None:   # packs written before these fields
                yaw = np.degrees(heading_track(np.asarray(it.frames, float)))
                it.heading_min_deg, it.heading_max_deg = round(float(yaw.min()), 1), round(float(yaw.max()), 1)
            self.items[it.id] = it

    def __len__(self) -> int:
        return len(self.items)

    def get(self, item_id: str) -> MotionItem:
        return self.items[item_id]

    def frames(self, item_id: str, mirrored: bool = False) -> np.ndarray:
        f = self.items[item_id].frames
        return mirror_seq(f) if mirrored else f

    def filter(self, *, categories: list[str] | None = None, complexity: tuple[int, int] = (1, 5),
               flexibility: str = "high", space: str = "small", allow_turn_away: bool = False,
               exclude: set[str] | frozenset = frozenset(), sources: list[str] | None = None,
               framing: str = "full", camera_yaw_deg: float = 0.0) -> list[MotionItem]:
        """``framing`` 'upper' keeps the moves done with the arms and trunk only. ``camera_yaw_deg`` is where the
        camera sees the user from (measured at the start of a block): 'turning the back to the camera' is judged
        from the camera, not from the screen."""
        max_fp, max_reach = SPACE_LIMITS.get(space, SPACE_LIMITS["small"])
        flex_level = FLEX.index(flexibility)
        out = []
        for it in self.items.values():
            if categories and it.category not in categories:
                continue
            if not (complexity[0] <= it.complexity <= complexity[1]):
                continue
            if FLEX.index(it.flexibility) > flex_level:
                continue
            if it.footprint_m > max_fp or it.reach_m > max_reach:
                continue
            if framing == "upper" and it.body_part != "upper":
                continue
            if not allow_turn_away and self.away_from_camera(it, camera_yaw_deg) > 100:
                continue
            if it.id in exclude:
                continue
            if sources and it.source not in sources:
                continue
            out.append(it)
        return out

    @staticmethod
    def away_from_camera(it: MotionItem, camera_yaw_deg: float = 0.0) -> float:
        """Largest angle (deg) between the user's front and the camera during the move."""
        lo = it.heading_min_deg if it.heading_min_deg is not None else -it.facing_away_deg
        hi = it.heading_max_deg if it.heading_max_deg is not None else it.facing_away_deg
        return max(abs(camera_yaw_deg + lo), abs(camera_yaw_deg + hi))

    def threshold(self, item_id: str, framing: str = "full") -> float:
        it = self.items[item_id]
        return it.threshold_upper if framing == "upper" and it.threshold_upper is not None else it.threshold

    def chiral(self, item_id: str, framing: str = "full") -> bool:
        it = self.items[item_id]
        return bool(it.chiral_upper) if framing == "upper" and it.chiral_upper is not None else it.chiral

    def stats(self) -> dict:
        cats: dict[str, int] = {}
        for it in self.items.values():
            cats[it.category] = cats.get(it.category, 0) + 1
        return {"total": len(self.items), "categories": cats}


def build_procedural() -> list[MotionItem]:
    prims = _all_primitives()
    by_id = {p.id: p for p in prims}
    items = [_item_from([p]) for p in prims]
    curated = _curated_combos()
    existing = {tuple(c) for _, c in curated}
    randoms = _random_combos(prims, RANDOM_COMBOS_PER_CATEGORY, existing=existing)
    seen_ids = set()
    for cat, combo in curated + randoms:
        cid = "combo." + "+".join(s.split(".", 1)[1] for s in combo)
        if cid in seen_ids:
            cid = f"{cid}.{len(seen_ids)}"
        seen_ids.add(cid)
        items.append(_item_from([by_id[s] for s in combo], category=cat, cid=cid))
    return items


def apply_calibration(items: list[MotionItem], calib: dict[str, dict]) -> None:
    for it in items:
        c = calib.get(it.id)
        if c:
            it.threshold = float(c["threshold"])
            it.chiral = bool(c["chiral"])
            if "threshold_upper" in c:
                it.threshold_upper = float(c["threshold_upper"])
                it.chiral_upper = bool(c["chiral_upper"])
        else:
            it.chiral = it.sided


@lru_cache(maxsize=2)
def get_library(include_imported: bool = True) -> MotionLibrary:
    from .calibration import load_calibration
    items = build_procedural()
    if include_imported:
        from .importers.pack import load_packs
        items += load_packs()
    apply_calibration(items, load_calibration())
    return MotionLibrary(items)
