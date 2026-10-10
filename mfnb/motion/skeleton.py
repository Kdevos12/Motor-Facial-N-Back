"""Canonical skeleton shared by the rig, the importers, the scorer and the web client.

Frame convention (metres): y up, x = camera right (= the subject's LEFT when they face the
camera), z = toward the camera. MediaPipe world landmarks map to it as (x, -y, -z).
"""
from __future__ import annotations

import numpy as np

JOINTS: list[str] = [
    "nose", "l_ear", "r_ear",
    "l_shoulder", "r_shoulder", "l_elbow", "r_elbow", "l_wrist", "r_wrist", "l_index", "r_index",
    "l_hip", "r_hip", "l_knee", "r_knee", "l_ankle", "r_ankle", "l_foot", "r_foot",
]
J: dict[str, int] = {name: i for i, name in enumerate(JOINTS)}
N_JOINTS = len(JOINTS)

# MediaPipe Pose landmark index for each canonical joint.
MEDIAPIPE_INDEX: list[int] = [0, 7, 8, 11, 12, 13, 14, 15, 16, 19, 20, 23, 24, 25, 26, 27, 28, 31, 32]


def _mirror_name(name: str) -> str:
    if name.startswith("l_"):
        return "r_" + name[2:]
    if name.startswith("r_"):
        return "l_" + name[2:]
    return name


MIRROR_PERM: np.ndarray = np.array([J[_mirror_name(n)] for n in JOINTS])

# Scoring bones: (name, start, end, weight). "mid_hip"/"mid_shoulder" are virtual joints.
BONES: list[tuple[str, str, str, float]] = [
    ("torso", "mid_hip", "mid_shoulder", 1.0),
    ("shoulder line", "r_shoulder", "l_shoulder", 0.8),
    ("hip line", "r_hip", "l_hip", 0.8),
    ("head", "mid_shoulder", "nose", 0.3),
    ("left upper arm", "l_shoulder", "l_elbow", 1.0),
    ("left forearm", "l_elbow", "l_wrist", 1.2),
    ("left hand", "l_wrist", "l_index", 0.3),
    ("right upper arm", "r_shoulder", "r_elbow", 1.0),
    ("right forearm", "r_elbow", "r_wrist", 1.2),
    ("right hand", "r_wrist", "r_index", 0.3),
    ("left thigh", "l_hip", "l_knee", 1.0),
    ("left shin", "l_knee", "l_ankle", 1.0),
    ("left foot", "l_ankle", "l_foot", 0.3),
    ("right thigh", "r_hip", "r_knee", 1.0),
    ("right shin", "r_knee", "r_ankle", 1.0),
    ("right foot", "r_ankle", "r_foot", 0.3),
]
LOWER_BODY_BONES = {"left thigh", "left shin", "left foot", "right thigh", "right shin", "right foot"}

# Drawing connections for the stick figure (joint index pairs).
CONNECTIONS: list[tuple[str, str]] = [
    ("l_shoulder", "r_shoulder"), ("l_hip", "r_hip"),
    ("l_shoulder", "l_hip"), ("r_shoulder", "r_hip"),
    ("l_shoulder", "l_elbow"), ("l_elbow", "l_wrist"), ("l_wrist", "l_index"),
    ("r_shoulder", "r_elbow"), ("r_elbow", "r_wrist"), ("r_wrist", "r_index"),
    ("l_hip", "l_knee"), ("l_knee", "l_ankle"), ("l_ankle", "l_foot"),
    ("r_hip", "r_knee"), ("r_knee", "r_ankle"), ("r_ankle", "r_foot"),
]


def point(seq: np.ndarray, name: str) -> np.ndarray:
    """Joint (or virtual mid joint) positions, works on (..., 19, 3) arrays."""
    if name == "mid_hip":
        return (seq[..., J["l_hip"], :] + seq[..., J["r_hip"], :]) / 2
    if name == "mid_shoulder":
        return (seq[..., J["l_shoulder"], :] + seq[..., J["r_shoulder"], :]) / 2
    return seq[..., J[name], :]


def mirror_seq(seq: np.ndarray) -> np.ndarray:
    """Mirror a (..., 19, 3) sequence across the sagittal plane: swap sides and negate x."""
    out = np.asarray(seq)[..., MIRROR_PERM, :].copy()
    out[..., 0] *= -1
    return out


def mirror_visibility(vis: np.ndarray) -> np.ndarray:
    return np.asarray(vis)[..., MIRROR_PERM].copy()


def from_mediapipe_world(landmarks33: np.ndarray) -> np.ndarray:
    """(T, 33, >=3) MediaPipe world landmarks -> (T, 19, 3) canonical."""
    lm = np.asarray(landmarks33, dtype=float)[..., MEDIAPIPE_INDEX, :3]
    return lm * np.array([1.0, -1.0, -1.0])


def meta() -> dict:
    """Skeleton description for the web client."""
    return {
        "joints": JOINTS,
        "mediapipe_index": MEDIAPIPE_INDEX,
        "connections": [[J[a], J[b]] for a, b in CONNECTIONS],
        "bones": [{"name": n, "a": a, "b": b, "weight": w} for n, a, b, w in BONES],
    }
