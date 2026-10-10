"""The 52 MediaPipe Face Landmarker blendshapes (ARKit-style names)."""
from __future__ import annotations

import numpy as np

NAMES: list[str] = [
    "_neutral", "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight",
    "cheekPuff", "cheekSquintLeft", "cheekSquintRight", "eyeBlinkLeft", "eyeBlinkRight", "eyeLookDownLeft",
    "eyeLookDownRight", "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft", "eyeLookOutRight", "eyeLookUpLeft",
    "eyeLookUpRight", "eyeSquintLeft", "eyeSquintRight", "eyeWideLeft", "eyeWideRight", "jawForward", "jawLeft",
    "jawOpen", "jawRight", "mouthClose", "mouthDimpleLeft", "mouthDimpleRight", "mouthFrownLeft",
    "mouthFrownRight", "mouthFunnel", "mouthLeft", "mouthLowerDownLeft", "mouthLowerDownRight", "mouthPressLeft",
    "mouthPressRight", "mouthPucker", "mouthRight", "mouthRollLower", "mouthRollUpper", "mouthShrugLower",
    "mouthShrugUpper", "mouthSmileLeft", "mouthSmileRight", "mouthStretchLeft", "mouthStretchRight",
    "mouthUpperUpLeft", "mouthUpperUpRight", "noseSneerLeft", "noseSneerRight",
]
# Scoring uses every shape but the neutral one.
DIMS: list[str] = NAMES[1:]
D = len(DIMS)
IDX: dict[str, int] = {n: i for i, n in enumerate(DIMS)}


def _mirror_name(n: str) -> str:
    for a, b in (("Left", "Right"), ("Right", "Left")):
        if n.endswith(a):
            return n[: -len(a)] + b
    return n


MIRROR_PERM = np.array([IDX[_mirror_name(n)] for n in DIMS])

REGION = {}
for n in DIMS:
    if n.startswith("brow"):
        REGION[n] = "brows"
    elif n.startswith("eyeLook"):
        REGION[n] = "gaze"
    elif n.startswith("eye"):
        REGION[n] = "eyes"
    elif n.startswith(("cheek", "nose")):
        REGION[n] = "cheeks & nose"
    elif n.startswith("jaw"):
        REGION[n] = "jaw"
    else:
        REGION[n] = "mouth"
WEIGHTS = np.array([0.5 if REGION[n] == "gaze" else (0.3 if n == "mouthClose" else 1.0) for n in DIMS])


def vec(d: dict[str, float]) -> np.ndarray:
    v = np.zeros(D)
    for k, x in d.items():
        v[IDX[k]] = x
    return v


def mirror_vec(v: np.ndarray) -> np.ndarray:
    return np.asarray(v)[..., MIRROR_PERM]


def from_mediapipe(scores52: np.ndarray, lr_swap: bool = False) -> np.ndarray:
    """(T, 52) MediaPipe scores in NAMES order -> (T, D) without the neutral shape."""
    out = np.asarray(scores52, dtype=float)[..., 1:]
    return mirror_vec(out) if lr_swap else out
