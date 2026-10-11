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

# ---- what MediaPipe 0.10 actually outputs on real faces ------------------------------------------------------
# Measured with the Face Landmarker (VIDEO and IMAGE mode give the same values within 0.02) on 165 posed photos of
# 15 people (Yale Face Database: each person's own neutral, happy, surprised, sad, sleepy and wink photos) and 436
# in-the-wild expression photos. TYPICAL_MAX is max(p95, p90 of the best-matching posed expression).
# Left/right pairs are averaged: the model is symmetric, the photo sets are not.
_TYPICAL_MAX = {
    "browDownLeft": 0.624, "browDownRight": 0.648, "browInnerUp": 0.756, "browOuterUpLeft": 0.806,
    "browOuterUpRight": 0.707, "cheekPuff": 0.002, "cheekSquintLeft": 0.000, "cheekSquintRight": 0.000,
    "eyeBlinkLeft": 0.696, "eyeBlinkRight": 0.682, "eyeLookDownLeft": 0.742, "eyeLookDownRight": 0.738,
    "eyeLookInLeft": 0.628, "eyeLookInRight": 0.842, "eyeLookOutLeft": 0.840, "eyeLookOutRight": 0.618,
    "eyeLookUpLeft": 0.468, "eyeLookUpRight": 0.432, "eyeSquintLeft": 0.751, "eyeSquintRight": 0.675,
    "eyeWideLeft": 0.134, "eyeWideRight": 0.122, "jawForward": 0.006, "jawLeft": 0.165, "jawOpen": 0.524,
    "jawRight": 0.157, "mouthClose": 0.014, "mouthDimpleLeft": 0.107, "mouthDimpleRight": 0.117,
    "mouthFrownLeft": 0.274, "mouthFrownRight": 0.277, "mouthFunnel": 0.029, "mouthLeft": 0.099,
    "mouthLowerDownLeft": 0.802, "mouthLowerDownRight": 0.834, "mouthPressLeft": 0.292, "mouthPressRight": 0.267,
    "mouthPucker": 0.631, "mouthRight": 0.502, "mouthRollLower": 0.186, "mouthRollUpper": 0.180,
    "mouthShrugLower": 0.346, "mouthShrugUpper": 0.100, "mouthSmileLeft": 0.911, "mouthSmileRight": 0.905,
    "mouthStretchLeft": 0.493, "mouthStretchRight": 0.448, "mouthUpperUpLeft": 0.442, "mouthUpperUpRight": 0.501,
    "noseSneerLeft": 0.000, "noseSneerRight": 0.000,
}
# Resting face (in-the-wild neutral photos): mean, and 90th percentile.
_REST_MEAN = {
    "browDownLeft": 0.176, "browDownRight": 0.187, "browInnerUp": 0.072, "browOuterUpLeft": 0.135,
    "browOuterUpRight": 0.100, "eyeBlinkLeft": 0.130, "eyeBlinkRight": 0.112, "eyeLookDownLeft": 0.170,
    "eyeLookDownRight": 0.174, "eyeLookInLeft": 0.130, "eyeLookInRight": 0.193, "eyeLookOutLeft": 0.203,
    "eyeLookOutRight": 0.141, "eyeLookUpLeft": 0.164, "eyeLookUpRight": 0.155, "eyeSquintLeft": 0.414,
    "eyeSquintRight": 0.308, "eyeWideLeft": 0.017, "eyeWideRight": 0.018, "jawLeft": 0.012, "jawOpen": 0.070,
    "jawRight": 0.003, "mouthClose": 0.005, "mouthDimpleLeft": 0.016, "mouthDimpleRight": 0.011,
    "mouthFrownLeft": 0.016, "mouthFrownRight": 0.017, "mouthFunnel": 0.006, "mouthLeft": 0.012,
    "mouthLowerDownLeft": 0.050, "mouthLowerDownRight": 0.059, "mouthPressLeft": 0.056, "mouthPressRight": 0.076,
    "mouthPucker": 0.081, "mouthRight": 0.006, "mouthRollLower": 0.051, "mouthRollUpper": 0.070,
    "mouthShrugLower": 0.047, "mouthShrugUpper": 0.018, "mouthSmileLeft": 0.043, "mouthSmileRight": 0.045,
    "mouthStretchLeft": 0.023, "mouthStretchRight": 0.030, "mouthUpperUpLeft": 0.008, "mouthUpperUpRight": 0.009,
}
_REST_P90 = {
    "browDownLeft": 0.489, "browDownRight": 0.532, "browInnerUp": 0.199, "browOuterUpLeft": 0.460,
    "browOuterUpRight": 0.313, "eyeBlinkLeft": 0.236, "eyeBlinkRight": 0.240, "eyeLookDownLeft": 0.464,
    "eyeLookDownRight": 0.451, "eyeLookInLeft": 0.460, "eyeLookInRight": 0.544, "eyeLookOutLeft": 0.501,
    "eyeLookOutRight": 0.412, "eyeLookUpLeft": 0.395, "eyeLookUpRight": 0.373, "eyeSquintLeft": 0.674,
    "eyeSquintRight": 0.554, "eyeWideLeft": 0.040, "eyeWideRight": 0.042, "jawLeft": 0.017, "jawOpen": 0.228,
    "jawRight": 0.002, "mouthClose": 0.012, "mouthDimpleLeft": 0.041, "mouthDimpleRight": 0.027,
    "mouthFrownLeft": 0.034, "mouthFrownRight": 0.038, "mouthFunnel": 0.012, "mouthLeft": 0.011,
    "mouthLowerDownLeft": 0.140, "mouthLowerDownRight": 0.171, "mouthPressLeft": 0.144, "mouthPressRight": 0.205,
    "mouthPucker": 0.281, "mouthRight": 0.011, "mouthRollLower": 0.162, "mouthRollUpper": 0.180,
    "mouthShrugLower": 0.080, "mouthShrugUpper": 0.037, "mouthSmileLeft": 0.113, "mouthSmileRight": 0.116,
    "mouthStretchLeft": 0.062, "mouthStretchRight": 0.093, "mouthUpperUpLeft": 0.014, "mouthUpperUpRight": 0.019,
}


def _symmetric(d: dict[str, float]) -> np.ndarray:
    v = np.array([d.get(n, 0.0) for n in DIMS])
    return (v + v[MIRROR_PERM]) / 2


TYPICAL_MAX = _symmetric(_TYPICAL_MAX)
REST_MEAN = _symmetric(_REST_MEAN)
REST_P90 = _symmetric(_REST_P90)
# Never output by the model (max below 0.02 over 600 real faces): kept in targets so the avatar can draw them,
# ignored by scoring.
DEAD = frozenset({"cheekPuff", "cheekSquintLeft", "cheekSquintRight", "jawForward", "noseSneerLeft", "noseSneerRight"})
# Real but never measured on a deliberate performance: an expression can rely on these only once the user's face
# calibration has shown that the tracker sees them on this face.
UNVERIFIED = frozenset({"jawLeft", "jawRight", "mouthLeft", "mouthRight", "mouthFunnel", "mouthRollLower",
                        "mouthRollUpper", "mouthPressLeft", "mouthPressRight", "mouthFrownLeft", "mouthFrownRight"})
DEAD_MASK = np.array([n in DEAD for n in DIMS])
GAZE_MASK = np.array([REGION[n] == "gaze" for n in DIMS])
UNVERIFIED_MASK = np.array([n in UNVERIFIED for n in DIMS])
# Too weak to be a key part of an expression unless the user's calibration measured it (eyeWide, dimples...).
WEAK_MASK = (TYPICAL_MAX < 0.25) & ~DEAD_MASK
WEIGHTS = np.array([0.0 if n in DEAD else 0.5 if REGION[n] == "gaze" else (0.3 if n == "mouthClose" else 1.0)
                    for n in DIMS])
BASE_NAME = [n[:-4] if n.endswith("Left") else n[:-5] if n.endswith("Right") else n for n in DIMS]


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


def can_be_key(name: str) -> bool:
    """A shape that can define an expression (dead and weak shapes cannot, unverified ones can once measured)."""
    return name not in DEAD and (name in UNVERIFIED or not WEAK_MASK[IDX[name]])


def keyable_without_calibration(name: str) -> bool:
    return can_be_key(name) and name not in UNVERIFIED
