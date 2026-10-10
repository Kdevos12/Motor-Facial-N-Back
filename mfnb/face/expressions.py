"""Facial expression library: action atoms, emotions, asymmetric expressions and combinations."""
from __future__ import annotations

import itertools
import random
from dataclasses import asdict, dataclass, field
from functools import lru_cache

import numpy as np

from .blendshapes import DIMS, IDX, mirror_vec, vec

FACE_CATEGORIES = ["emotions", "upper face", "lower face", "gaze", "asymmetric", "combinations"]


@dataclass
class FaceItem:
    id: str
    name: str
    category: str
    complexity: int
    target: dict[str, float]
    sided: bool = False
    regions: list[str] = field(default_factory=list)
    threshold: float = 0.62

    def vector(self, mirrored: bool = False) -> np.ndarray:
        v = vec(self.target)
        return mirror_vec(v) if mirrored else v

    def meta(self) -> dict:
        return asdict(self)


def _both(base: str, x: float) -> dict[str, float]:
    return {f"{base}Left": x, f"{base}Right": x}


# Atoms: (id, name, region, shapes, sided)
UPPER = [
    ("brows_raise", "Raise both eyebrows", {"browInnerUp": 0.8, **_both("browOuterUp", 0.8)}, False),
    ("inner_brows", "Raise inner eyebrows (worried)", {"browInnerUp": 0.9}, False),
    ("frown_brows", "Frown (lower the brows)", _both("browDown", 0.8), False),
    ("brow_left", "Raise the left eyebrow only", {"browOuterUpLeft": 0.9, "browInnerUp": 0.25, "browDownRight": 0.2}, True),
    ("eyes_wide", "Open the eyes wide", _both("eyeWide", 0.8), False),
    ("eyes_squint", "Squint", {**_both("eyeSquint", 0.7), **_both("cheekSquint", 0.3)}, False),
    ("eyes_closed", "Close both eyes", _both("eyeBlink", 0.95), False),
    ("wink_left", "Wink with the left eye", {"eyeBlinkLeft": 0.95, "cheekSquintLeft": 0.3, "eyeSquintLeft": 0.2}, True),
]
GAZE = [
    ("look_left", "Look to your left", {"eyeLookOutLeft": 0.7, "eyeLookInRight": 0.7}, True),
    ("look_up", "Look up", _both("eyeLookUp", 0.7), False),
    ("look_down", "Look down", _both("eyeLookDown", 0.7), False),
]
LOWER = [
    ("smile", "Closed smile", {**_both("mouthSmile", 0.8), **_both("cheekSquint", 0.3)}, False),
    ("big_smile", "Big open smile", {**_both("mouthSmile", 0.9), **_both("cheekSquint", 0.5), "jawOpen": 0.35,
                                    **_both("mouthUpperUp", 0.3)}, False),
    ("smirk_left", "Half smile (left corner)", {"mouthSmileLeft": 0.8, "mouthDimpleLeft": 0.3, "cheekSquintLeft": 0.2}, True),
    ("mouth_frown", "Mouth corners down", {**_both("mouthFrown", 0.7), "mouthShrugLower": 0.3}, False),
    ("pucker", "Pucker (kiss)", {"mouthPucker": 0.9}, False),
    ("funnel", "Round 'O' lips", {"mouthFunnel": 0.8, "jawOpen": 0.25}, False),
    ("jaw_open", "Open the jaw", {"jawOpen": 0.8, **_both("mouthLowerDown", 0.3)}, False),
    ("jaw_left", "Jaw to your left", {"jawLeft": 0.7}, True),
    ("mouth_left", "Mouth to your left", {"mouthLeft": 0.8}, True),
    ("lips_press", "Press the lips", {**_both("mouthPress", 0.7), "mouthClose": 0.3}, False),
    ("lips_roll", "Roll the lips in", {"mouthRollLower": 0.7, "mouthRollUpper": 0.7}, False),
    ("cheek_puff", "Puff the cheeks", {"cheekPuff": 0.9, "mouthClose": 0.3}, False),
    ("nose_wrinkle", "Wrinkle the nose", {**_both("noseSneer", 0.7), **_both("mouthUpperUp", 0.3)}, False),
    ("snarl_left", "Snarl (left upper lip)", {"mouthUpperUpLeft": 0.8, "noseSneerLeft": 0.5}, True),
    ("grimace", "Grimace (stretch the lips)", {**_both("mouthStretch", 0.7), **_both("mouthLowerDown", 0.4)}, False),
    ("jaw_forward", "Jaw forward", {"jawForward": 0.7}, False),
    ("pout", "Pout", {"mouthShrugLower": 0.6, "mouthShrugUpper": 0.4, "mouthPucker": 0.3}, False),
]
EMOTIONS = [
    ("happy", "Happiness", {**_both("mouthSmile", 0.8), **_both("cheekSquint", 0.5), **_both("eyeSquint", 0.3)}, False, 2),
    ("sad", "Sadness", {"browInnerUp": 0.7, **_both("mouthFrown", 0.6), "mouthShrugLower": 0.3}, False, 2),
    ("surprise", "Surprise", {"browInnerUp": 0.8, **_both("browOuterUp", 0.8), **_both("eyeWide", 0.7), "jawOpen": 0.6}, False, 3),
    ("fear", "Fear", {"browInnerUp": 0.8, **_both("browOuterUp", 0.4), **_both("eyeWide", 0.7),
                      **_both("mouthStretch", 0.6), "jawOpen": 0.2}, False, 3),
    ("anger", "Anger", {**_both("browDown", 0.8), **_both("eyeSquint", 0.4), **_both("mouthPress", 0.5),
                        **_both("noseSneer", 0.2)}, False, 3),
    ("disgust", "Disgust", {**_both("noseSneer", 0.8), **_both("mouthUpperUp", 0.6), **_both("browDown", 0.4),
                            **_both("eyeSquint", 0.3)}, False, 3),
    ("contempt", "Contempt", {"mouthSmileLeft": 0.5, "mouthDimpleLeft": 0.4, "eyeSquintLeft": 0.2}, True, 3),
    ("skeptical", "Skepticism", {"browOuterUpLeft": 0.8, "browDownRight": 0.4, **_both("mouthPress", 0.3)}, True, 4),
    ("confused", "Confusion", {"browInnerUp": 0.4, "browDownLeft": 0.5, "mouthLeft": 0.4}, True, 4),
    ("worried", "Worry", {"browInnerUp": 0.8, **_both("mouthStretch", 0.3), **_both("mouthPress", 0.3)}, False, 3),
    ("determined", "Determination", {**_both("browDown", 0.5), **_both("mouthPress", 0.7), "jawForward": 0.2}, False, 3),
    ("pain", "Pain", {**_both("browDown", 0.6), **_both("eyeSquint", 0.8), **_both("cheekSquint", 0.6),
                      **_both("mouthStretch", 0.6), **_both("noseSneer", 0.4)}, False, 4),
    ("flirty", "Flirty wink", {"eyeBlinkLeft": 0.9, "mouthSmileLeft": 0.7, "cheekSquintLeft": 0.4}, True, 4),
    ("shocked", "Shock", {"browInnerUp": 1.0, **_both("browOuterUp", 0.9), **_both("eyeWide", 1.0), "jawOpen": 0.9}, False, 3),
    ("laughing", "Laughing", {**_both("mouthSmile", 0.9), **_both("cheekSquint", 0.7), **_both("eyeSquint", 0.6),
                              "jawOpen": 0.6}, False, 3),
    ("smug", "Smugness", {**_both("mouthSmile", 0.5), **_both("eyeSquint", 0.3), **_both("mouthPress", 0.3)}, False, 3),
    ("thinking", "Thinking", {**_both("eyeLookUp", 0.6), "mouthLeft": 0.4, "browOuterUpLeft": 0.4}, True, 4),
    ("kissy", "Kissy face", {"mouthPucker": 0.9, **_both("eyeBlink", 0.8)}, False, 3),
    ("sulking", "Sulking", {"mouthShrugLower": 0.6, **_both("mouthFrown", 0.4), **_both("browDown", 0.3)}, False, 3),
    ("bored", "Boredom", {**_both("eyeBlink", 0.45), **_both("mouthPress", 0.2), "mouthShrugLower": 0.2}, False, 3),
]
INCOMPATIBLE = {
    frozenset({"eyes_closed", "look_left"}), frozenset({"eyes_closed", "look_up"}), frozenset({"eyes_closed", "look_down"}),
    frozenset({"eyes_wide", "eyes_squint"}), frozenset({"frown_brows", "brows_raise"}),
}


def _region_of(target: dict[str, float]) -> list[str]:
    from .blendshapes import REGION
    return sorted({REGION[k] for k in target})


def _merge(*dicts: dict[str, float]) -> dict[str, float]:
    out: dict[str, float] = {}
    for d in dicts:
        for k, v in d.items():
            out[k] = max(out.get(k, 0.0), v)
    return out


def build_items(seed: int = 11, n_triples: int = 60) -> list[FaceItem]:
    items: list[FaceItem] = []
    for cat, atoms in (("upper face", UPPER), ("gaze", GAZE), ("lower face", LOWER)):
        for aid, name, shapes, sided in atoms:
            items.append(FaceItem(f"face.{aid}", name, "asymmetric" if sided and cat != "gaze" else cat,
                                  2 if sided else 1, shapes, sided))
    for eid, name, shapes, sided, cx in EMOTIONS:
        items.append(FaceItem(f"emo.{eid}", name, "emotions", cx, shapes, sided))
    upper = [a for a in UPPER] + [g for g in GAZE]
    for (ua, un, us, uside), (la, ln, ls, lside) in itertools.product(upper, LOWER):
        if frozenset({ua, la}) in INCOMPATIBLE:
            continue
        sided = uside or lside
        items.append(FaceItem(f"combo.{ua}+{la}", f"{un} + {ln.lower()}", "combinations", 4 if sided else 3,
                              _merge(us, ls), sided))
    rng = random.Random(seed)
    seen = set()
    while len(seen) < n_triples:
        u1, u2 = rng.sample(UPPER, 2)
        lo = rng.choice(LOWER)
        key = (u1[0], u2[0], lo[0])
        if frozenset({u1[0], u2[0]}) in INCOMPATIBLE or key in seen or (u2[0], u1[0], lo[0]) in seen:
            continue
        if {u1[0], u2[0]} & {"eyes_closed", "wink_left"} and {u1[0], u2[0]} & {"eyes_wide", "eyes_squint"}:
            continue
        seen.add(key)
        sided = u1[3] or u2[3] or lo[3]
        items.append(FaceItem(f"combo.{u1[0]}+{u2[0]}+{lo[0]}", f"{u1[1]} + {u2[1].lower()} + {lo[1].lower()}",
                              "combinations", 5, _merge(u1[2], u2[2], lo[2]), sided))
    for it in items:
        it.regions = _region_of(it.target)
    return items


class FaceLibrary:
    def __init__(self, items: list[FaceItem]):
        self.items = {it.id: it for it in items}
        if len(self.items) != len(items):
            raise ValueError("duplicate face item ids")
        self._calibrate_thresholds()

    def __len__(self) -> int:
        return len(self.items)

    def get(self, item_id: str) -> FaceItem:
        return self.items[item_id]

    def _calibrate_thresholds(self) -> None:
        """Per-item threshold above the similarity of the closest *other* expression."""
        from .scoring import similarity
        ids = list(self.items)
        mat = np.stack([self.items[i].vector() for i in ids])
        for k, iid in enumerate(ids):
            others = np.delete(mat, k, axis=0)
            sims = similarity(mat[k], others)
            near = float(np.sort(sims)[-3:].mean())
            self.items[iid].threshold = round(float(np.clip(near + 0.05, 0.62, 0.85)), 3)

    def filter(self, categories: list[str] | None = None, complexity: tuple[int, int] = (1, 5),
               exclude: set[str] | frozenset = frozenset()) -> list[FaceItem]:
        return [it for it in self.items.values()
                if (not categories or it.category in categories)
                and complexity[0] <= it.complexity <= complexity[1] and it.id not in exclude]

    def stats(self) -> dict:
        cats: dict[str, int] = {}
        for it in self.items.values():
            cats[it.category] = cats.get(it.category, 0) + 1
        return {"total": len(self.items), "categories": cats}


@lru_cache(maxsize=1)
def get_face_library() -> FaceLibrary:
    return FaceLibrary(build_items())


__all__ = ["FaceItem", "FaceLibrary", "get_face_library", "FACE_CATEGORIES", "DIMS", "IDX"]
