"""Paths and default profile settings."""
from __future__ import annotations

import copy
import os
from pathlib import Path

DEFAULT_PORT = 8765


def home() -> Path:
    p = Path(os.environ.get("MFNB_HOME", "~/.mfnb")).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_path() -> Path:
    return home() / "mfnb.db"


def assets_dir() -> Path:
    p = home() / "assets"
    p.mkdir(parents=True, exist_ok=True)
    return p


DEFAULT_SETTINGS: dict = {
    # body & space
    "flexibility": "medium",          # low / medium / high (lower body)
    "space": "small",                 # small (2-3 m^2) / medium / large
    "allow_turn_away": False,         # techniques that turn the back to the camera
    "stance": "orthodox",             # orthodox / southpaw (mirrors stance-based moves)
    # display
    "view": "mirror",                 # mirror / facing / back
    "camera_yaw": 25,                 # stick figure camera angle (degrees)
    "side_view": True,                # small side-view inset
    "show_names": False,              # show move names during the block
    "show_self_view": True,           # webcam preview during the response
    "sound": True,
    # pacing & tolerance
    "playback_speed": 1.0,            # stimulus speed (0.5 - 1.5)
    "stimulus_repeats": 1,
    "response_multiplier": 2.5,       # response window = multiplier x stimulus (2.0 - 3.0)
    "response_min_extra_s": 3.0,      # ... and at least stimulus + this
    "iti_s": 1.5,                     # pause between trials
    "strictness": 1.0,                # 0.7 lenient ... 1.3 strict
    "n_mode": "adaptive",             # adaptive / manual
    "motor": {"n": 1, "block_base": 20, "categories": [], "complexity": [1, 3], "variable_n": False,
              "chirality_p": 0.0, "sequence_p": 0.0, "sources": []},
    "facial": {"n": 1, "block_base": 20, "categories": [], "complexity": [1, 3]},
}


def merge_settings(base: dict, update: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (update or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge_settings(out[k], v)
        else:
            out[k] = v
    return out
