"""Ready-made recipes for large open motion datasets, imported locally into ~/.mfnb/packs.

They are not bundled because their licences do not allow it (non-commercial, and for
LaFAN1 no redistribution of derivatives): each user imports them for personal use.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .common import make_clips
from .generic import bvh_to_frames
from .pack import user_pack_dir, write_pack

Classified = tuple[str, str, str, int]  # category, subcategory, display name, max clips


def bandai_classify(path: Path) -> Classified | None:
    m = re.match(r"dataset-1_([a-z-]+)_([a-z-]+)_(\d+)\.bvh$", path.name)
    if not m:
        return None
    content, style = m.group(1), m.group(2).replace("-", " ")
    table = {
        "punch": ("boxing", "punches (Bandai Namco)", 6), "kick": ("kicks", "kicks (Bandai Namco)", 6),
        "slash": ("everyday & sports", "sword slashes (Bandai Namco)", 4),
        "dance-long": ("dance", "dance (Bandai Namco)", 12), "dance-short": ("dance", "dance (Bandai Namco)", 6),
        "bow": ("everyday & sports", "styled gestures (Bandai Namco)", 1),
        "bye": ("everyday & sports", "styled gestures (Bandai Namco)", 1),
        "byebye": ("everyday & sports", "styled gestures (Bandai Namco)", 1),
        "guide": ("everyday & sports", "styled gestures (Bandai Namco)", 1),
        "call": ("everyday & sports", "styled gestures (Bandai Namco)", 2),
        "respond": ("everyday & sports", "styled gestures (Bandai Namco)", 2),
    }
    if content not in table:
        return None  # locomotion does not fit a small space
    cat, sub, k = table[content]
    return cat, sub, f"{content.replace('-', ' ').capitalize()} ({style})", k


def lafan_classify(path: Path) -> Classified | None:
    m = re.match(r"([a-zA-Z]+)(\d+)_subject(\d+)\.bvh$", path.name)
    if not m:
        return None
    kind = m.group(1)
    table = {"dance": ("dance", "dance (LaFAN1)", 25), "fight": ("boxing", "fight (LaFAN1)", 25),
             "fightAndSports": ("everyday & sports", "fight & sports (LaFAN1)", 20)}
    if kind not in table:
        return None
    cat, sub, k = table[kind]
    return cat, sub, f"{kind[0].upper() + kind[1:]} {m.group(2)} (subject {m.group(3)})", k


@dataclass
class Recipe:
    name: str
    title: str
    licence: str
    fetch: Callable[[Path], Path]
    classify: Callable[[Path], Classified | None]
    pattern: str = "**/*.bvh"


def _fetch_bandai(cache: Path) -> Path:
    repo = cache / "bandai-namco-motion"
    if not (repo / ".git").exists():
        subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
                        "https://github.com/BandaiNamcoResearchInc/Bandai-Namco-Research-Motiondataset", str(repo)],
                       check=True)
    subprocess.run(["git", "-C", str(repo), "sparse-checkout", "set", "dataset/Bandai-Namco-Research-Motiondataset-1"],
                   check=True)
    return repo / "dataset" / "Bandai-Namco-Research-Motiondataset-1"


LAFAN_URL = "https://media.githubusercontent.com/media/ubisoft/ubisoft-laforge-animation-dataset/master/lafan1/lafan1.zip"
LAFAN_SHA256 = "ea918082b500a5d158e9d3aa39039df04cd42e25f5c02fe8f7e88e8e9365a977"


def _fetch_lafan(cache: Path) -> Path:
    root = cache / "lafan1"
    if not any(root.glob("**/*.bvh")):
        root.mkdir(parents=True, exist_ok=True)
        zpath = cache / "lafan1.zip"
        if not zpath.exists():
            print("Downloading LaFAN1 (144 MB)...")
            with urllib.request.urlopen(LAFAN_URL, timeout=600) as r:
                data = r.read()
            if hashlib.sha256(data).hexdigest() != LAFAN_SHA256:
                raise RuntimeError("LaFAN1 checksum mismatch")
            zpath.write_bytes(data)
        with zipfile.ZipFile(zpath) as z:
            for member in z.namelist():
                if member.endswith(".bvh") and ".." not in member:
                    (root / Path(member).name).write_bytes(z.read(member))
    return root


RECIPES = {
    "bandai": Recipe("bandai", "Bandai Namco Research Motion Dataset 1", "CC BY-NC 4.0 (Bandai Namco Research Inc.)",
                     _fetch_bandai, bandai_classify),
    "lafan1": Recipe("lafan1", "Ubisoft La Forge LaFAN1", "CC BY-NC-ND 4.0 (Ubisoft Entertainment)",
                     _fetch_lafan, lafan_classify),
}


def import_files(files: list[Path], classify: Callable[[Path], Classified | None], source: str, licence: str,
                 title: str, out: Path) -> int:
    items = []
    for f in sorted(files):
        c = classify(f)
        if c is None:
            continue
        cat, sub, name, k = c
        try:
            frames = bvh_to_frames(f.read_text(errors="replace"))
        except Exception as exc:  # one odd file should not stop an import
            print(f"  skipped {f.name}: {exc}")
            continue
        clips = make_clips(frames, id_prefix=f"{source}.{f.stem}", name=name, category=cat, subcategory=sub,
                           source=source, description=f"Motion capture: {title} ({licence}).", max_clips=k)
        print(f"  {f.name}: {len(clips)} clips ({cat})")
        items += clips
    write_pack(out, items, source=title, licence=licence)
    print(f"Wrote {len(items)} clips to {out}")
    return len(items)


def import_dataset(name: str, cache: Path) -> Path:
    r = RECIPES[name]
    root = r.fetch(cache)
    out = user_pack_dir() / f"{r.name}.pack.json.gz"
    import_files(list(root.glob(r.pattern)), r.classify, r.name, r.licence, r.title, out)
    return out
