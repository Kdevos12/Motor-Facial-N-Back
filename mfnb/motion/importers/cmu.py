"""Import clips from the CMU Graphics Lab Motion Capture Database.

Source: BVH conversions in the MIT-licensed GitHub mirror ``adventuring/mocap``. CMU terms:
free to use, including in products, but the data itself may not be resold.

Pipeline: BVH -> canonical 19 joints (metres, facing the camera) -> 30 fps -> segmentation at
rest pauses (long stretches split into windows) -> space/motion filters -> tagged items.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..library import FPS, MotionItem
from ..skeleton import J, N_JOINTS
from .bvh import forward_kinematics, parse_bvh
from .common import face_camera, make_clips, scale_to_standard, segment  # noqa: F401  (re-exported for tests)
from .pack import DATA_DIR, write_pack

REPO = "https://github.com/adventuring/mocap"

# Canonical joint <- BVH joint (this mirror's naming).
JOINT_MAP = {
    "l_shoulder": "lShldr", "r_shoulder": "rShldr", "l_elbow": "lForeArm", "r_elbow": "rForeArm",
    "l_wrist": "lHand", "r_wrist": "rHand", "l_index": "lIndex2_end", "r_index": "rIndex2_end",
    "l_hip": "lThigh", "r_hip": "rThigh", "l_knee": "lShin", "r_knee": "rShin",
    "l_ankle": "lFoot", "r_ankle": "rFoot", "l_foot": "lFoot_end", "r_foot": "rFoot_end",
}


@dataclass
class Source:
    path: str              # path in the repo
    category: str
    subcategory: str
    name: str
    max_clips: int = 6


def _s(directory, files, category, sub, name, max_clips=6):
    return [Source(f"CMU/{directory}/{f}.bvh", category, sub, name, max_clips) for f in files]


CURATED: list[Source] = [
    *_s("12.tai-chi,walk", ["12_04.tai-chi"], "tai chi & qigong", "tai chi (mocap)", "Tai chi form", 30),
    *_s("144.punching-female", ["144_20.Punch-Sequence", "144_21.Punch-Sequence001", "144_13.Left-Punch-Sequence001",
                                "144_14.Left-Punch-Sequence002"], "boxing", "punch sequences (mocap)", "Punch sequence", 8),
    *_s("144.punching-female", ["144_05.Front-Kicking", "144_06.Front-Kicking001", "144_09.Left-Front-Kicking",
                                "144_10.Left-Front-Kicking001"], "kicks", "front kicks (mocap)", "Front kicking", 6),
    *_s("144.punching-female", ["144_07.Left-Blocks", "144_08.Left-Blocks001", "144_26.Right-Blocks",
                                "144_27.Right-Blocks001"], "evasion", "blocks (mocap)", "Blocks", 6),
    *_s("144.punching-female", ["144_11.Left-Lunges", "144_17.Lunges", "144_18.Lunges001"], "fitness",
        "lunges (mocap)", "Lunges", 4),
    *_s("144.punching-female", ["144_22.Reach-Left001", "144_24.Reach-Right"], "everyday & sports", "reaching (mocap)",
        "Reach", 4),
    *_s("14.various-everyday-behaviors", ["14_01.boxing", "14_02.boxing", "14_03.boxing"], "boxing",
        "shadow boxing (mocap)", "Shadow boxing", 8),
    *_s("13.various-everyday-behaviors", ["13_17.boxing", "13_18.boxing"], "boxing", "shadow boxing (mocap)",
        "Shadow boxing", 8),
    *_s("80.assorted-motions", ["80_10.boxing"], "boxing", "shadow boxing (mocap)", "Shadow boxing", 8),
    *_s("135.Martial-Arts-Walks", ["135_01.Bassai", "135_02.Empi", "135_06.Heiansyodan"], "karate", "kata (mocap)",
        "Kata fragment", 10),
    *_s("135.Martial-Arts-Walks", ["135_05.Gedanbarai", "135_09.Oiduki", "135_10.Syutouuke"], "karate",
        "basics (mocap)", "Karate basics", 6),
    *_s("135.Martial-Arts-Walks", ["135_04.Front-Kick", "135_07.Mawashigeri", "135_11.Yokogeri"], "kicks",
        "karate kicks (mocap)", "Karate kicks", 6),
    *_s("74.kicks-and-walking-on-slopes", ["74_03.kick", "74_04.kick", "74_05.kick", "74_06.kick"], "kicks",
        "kicks (mocap)", "Kick", 4),
    *_s("42.stretch", ["42_01.stretch-rotate-head,shoulders,arms,legs"], "fitness", "stretching (mocap)", "Stretch", 20),
    *_s("14.various-everyday-behaviors", ["14_06.jumping-jacks,jog,squats,side-twists,stretches",
                                          "14_14.jumping-jacks,jog,squats,side-twists,stretches"], "fitness",
        "warm-up (mocap)", "Warm-up", 12),
    *_s("94.indian-dance", [f"94_{k:02d}.Unknown" for k in range(1, 17)], "dance", "indian dance (mocap)",
        "Indian dance", 4),
    *_s("93.Charleston-Dance", ["93_03.charleston-01", "93_08.xtra-fancY-charleston"], "dance", "charleston (mocap)",
        "Charleston", 8),
    *_s("15.various-everyday-behaviors,dance-moves",
        ["15_04.wash-windows,paint-hand-signals-dance-Egyptian-walk,the-Dive,the-Twist,the-Cabbage-Patch-boxing",
         "15_05.wash-windows,paint-hand-signals-dance-Egyptian-walk,the-Dive,the-Twist,the-Cabbage-Patch-boxing"],
        "dance", "party dances (mocap)", "Party dance & gestures", 12),
    *_s("63.golf", ["63_01.Swing", "63_02", "63_03"], "everyday & sports", "golf (mocap)", "Golf swing", 3),
    *_s("124.Sports-Related-Motions", ["124_01.Baseball-Pitch", "124_03.Basketball-Shoot", "124_07.Baseball-Swing",
                                       "124_09.Frisbee", "124_12.Underhand-Toss"], "everyday & sports",
        "sports (mocap)", "Sports motion", 3),
    *_s("80.assorted-motions", ["80_13.drumming", "80_12.fishing", "80_14.teaching", "80_03.shooting-a-gun",
                                "80_02.chopping-onions"], "everyday & sports", "gestures (mocap)", "Everyday gesture", 3),
    *_s("2.various-expressions-and-human-behaviors", ["02_05.punch-strike"], "boxing", "strikes (mocap)",
        "Punch & strike", 6),
    *_s("2.various-expressions-and-human-behaviors", ["02_07.swordplay", "02_08.swordplay"], "everyday & sports",
        "swordplay (mocap)", "Swordplay", 6),
    *_s("24.nursery-rhymes", ["24_01.nursery-rhyme-[I-m-a-little-teapot...]"], "everyday & sports",
        "nursery rhymes (mocap)", "Nursery rhyme gestures", 6),
]


def to_canonical(pos: dict[str, np.ndarray]) -> np.ndarray:
    n = len(next(iter(pos.values())))
    out = np.zeros((n, N_JOINTS, 3))
    for cj, bj in JOINT_MAP.items():
        out[:, J[cj]] = pos[bj]
    head = pos["head"]
    le, re_ = pos["leftEye"], pos["rightEye"]
    eyes = (le + re_) / 2
    lateral = le - re_
    lateral /= np.maximum(np.linalg.norm(lateral, axis=-1, keepdims=True), 1e-9)
    fwd = eyes - head
    fwd -= np.sum(fwd * lateral, -1, keepdims=True) * lateral
    fwd /= np.maximum(np.linalg.norm(fwd, axis=-1, keepdims=True), 1e-9)
    scale_hint = np.linalg.norm(pos["lShin"] - pos["lThigh"], axis=-1, keepdims=True)
    out[:, J["nose"]] = eyes - 0.08 * scale_hint * np.array([0, 1, 0]) + 0.05 * scale_hint * fwd
    out[:, J["l_ear"]] = head + lateral * 0.2 * scale_hint + 0.1 * scale_hint * np.array([0, 1, 0])
    out[:, J["r_ear"]] = head - lateral * 0.2 * scale_hint + 0.1 * scale_hint * np.array([0, 1, 0])
    return scale_to_standard(out)


def clips_from_bvh(text: str, src: Source, trial: str) -> list[MotionItem]:
    bvh = parse_bvh(text)
    step = max(1, int(round(1.0 / (bvh.frame_time * FPS))))
    frames = to_canonical(forward_kinematics(bvh, slice(0, None, step)))
    return make_clips(frames, id_prefix=f"cmu.{trial}", name=f"{src.name} (CMU {trial})", category=src.category,
                      subcategory=src.subcategory, source="cmu",
                      description=f"Motion capture: CMU Graphics Lab database, trial {trial}.", max_clips=src.max_clips)


def fetch_repo(cache: Path, paths: list[str], progress=print) -> Path:
    """Sparse, blob-filtered clone of the BVH mirror; only the needed files are downloaded."""
    repo = cache / "adventuring-mocap"
    if not (repo / ".git").exists():
        cache.mkdir(parents=True, exist_ok=True)
        progress(f"Cloning {REPO} (sparse)...")
        subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", REPO, str(repo)], check=True)
    dirs = sorted({str(Path(p).parent) for p in paths})
    subprocess.run(["git", "-C", str(repo), "sparse-checkout", "set", *dirs], check=True)
    return repo


def import_cmu(args) -> int:
    from ... import config
    sources = CURATED
    if args.subjects:
        wanted = {s.strip() for s in args.subjects.split(",")}
        sources = [s for s in CURATED if re.match(r"CMU/(\d+)\.", s.path).group(1) in wanted]
    root = Path(args.source) if args.source else fetch_repo(config.home() / "cache", [s.path for s in sources])
    items: list[MotionItem] = []
    for src in sources:
        p = root / src.path
        if not p.exists():
            print(f"  missing {src.path}, skipped")
            continue
        trial = Path(src.path).name.split(".")[0]
        clips = clips_from_bvh(p.read_text(errors="replace"), src, trial)
        print(f"  {trial}: {len(clips)} clips ({src.category})")
        items += clips
    out = Path(args.out) if args.out else DATA_DIR / "cmu.pack.json.gz"
    write_pack(out, items, source="CMU Graphics Lab Motion Capture Database (mocap.cs.cmu.edu), BVH via "
               "github.com/adventuring/mocap", licence="CMU: free to use, may not be resold; mirror: MIT")
    print(f"Wrote {len(items)} clips to {out}. Run `mfnb calibrate --bundled` to refresh the acceptance thresholds.")
    return 0
