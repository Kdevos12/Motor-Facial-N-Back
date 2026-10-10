"""Bundled packs of imported clips (see ``mfnb import-cmu``)."""
from __future__ import annotations

import base64
import gzip
import json
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def encode_frames(frames: np.ndarray) -> str:
    """(T,19,3) metres -> base64 of int16 millimetres."""
    mm = np.clip(np.round(np.asarray(frames) * 1000.0), -32768, 32767).astype("<i2")
    return base64.b64encode(mm.tobytes()).decode("ascii")


def decode_frames(data: str, n_frames: int) -> np.ndarray:
    mm = np.frombuffer(base64.b64decode(data), dtype="<i2").reshape(n_frames, 19, 3)
    return (mm.astype(np.float32) / 1000.0)


def write_pack(path: Path, items: list, source: str, licence: str) -> None:
    payload = {"source": source, "licence": licence, "items": []}
    for it in items:
        meta = it.meta()
        meta["n_frames"] = int(len(it.frames))
        meta["frames"] = encode_frames(it.frames)
        payload["items"].append(meta)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))


def read_pack(path: Path) -> list:
    from ..library import MotionItem
    with gzip.open(path, "rt", encoding="utf-8") as f:
        payload = json.load(f)
    out = []
    for meta in payload["items"]:
        frames = decode_frames(meta.pop("frames"), meta.pop("n_frames"))
        out.append(MotionItem(**meta, frames=frames))
    return out


def user_pack_dir() -> Path:
    from ...config import home
    d = home() / "packs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_packs(directory: Path | None = None, include_user: bool = True) -> list:
    """Bundled packs, plus the user's own imports (~/.mfnb/packs) unless a directory is given."""
    dirs = [directory] if directory else [DATA_DIR] + ([user_pack_dir()] if include_user else [])
    items, seen = [], set()
    for d in dirs:
        for p in sorted(d.glob("*.pack.json.gz")):
            for it in read_pack(p):
                if it.id not in seen:
                    seen.add(it.id)
                    items.append(it)
    return items
