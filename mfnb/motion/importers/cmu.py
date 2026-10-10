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

from ..library import FPS, MotionItem, SPACE_LIMITS, compute_metrics
from ..skeleton import J, N_JOINTS
from .bvh import forward_kinematics, parse_bvh
from .pack import DATA_DIR, write_pack

REPO = "https://github.com/adventuring/mocap"
LEG_LENGTH_M = 0.85

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
    # metres, standard leg length
    leg = np.median(np.linalg.norm(out[:, J["l_knee"]] - out[:, J["l_hip"]], axis=-1)
                    + np.linalg.norm(out[:, J["l_ankle"]] - out[:, J["l_knee"]], axis=-1))
    return out * (LEG_LENGTH_M / leg)


def face_camera(frames: np.ndarray) -> np.ndarray:
    """Recentre on the first frame's pelvis, rotate so it faces +z, put the feet on the floor."""
    f = frames.copy()
    mid = (f[0, J["l_hip"]] + f[0, J["r_hip"]]) / 2
    f[:, :, 0] -= mid[0]
    f[:, :, 2] -= mid[2]
    hip_vec = f[0, J["l_hip"]] - f[0, J["r_hip"]]
    fwd = np.cross(hip_vec, [0.0, 1.0, 0.0])
    yaw = np.arctan2(fwd[0], fwd[2])
    c, s = np.cos(-yaw), np.sin(-yaw)
    x, z = f[..., 0].copy(), f[..., 2].copy()
    f[..., 0] = c * x + s * z
    f[..., 2] = -s * x + c * z
    f[:, :, 1] -= f[:, [J["l_ankle"], J["r_ankle"], J["l_foot"], J["r_foot"]], 1].min()
    f[:, :, 1] += 0.02
    return f


def motion_energy(f: np.ndarray) -> np.ndarray:
    mid = (f[:, J["l_hip"]] + f[:, J["r_hip"]]) / 2
    rel = f - mid[:, None]
    v = np.linalg.norm(np.diff(rel, axis=0), axis=-1).sum(-1) * FPS
    v += np.linalg.norm(np.diff(mid, axis=0), axis=-1) * FPS * 3
    v = np.concatenate([[v[0]], v])
    k = max(1, int(0.25 * FPS))
    return np.convolve(v, np.ones(k) / k, mode="same")


def segment(frames: np.ndarray, min_s: float = 1.2, max_s: float = 5.0, window_s: float = 3.5) -> list[tuple[int, int]]:
    """Cut at rest pauses; long active stretches become fixed windows."""
    e = motion_energy(frames)
    active_level = np.percentile(e, 75)
    rest = e < 0.3 * active_level
    cuts = [0]
    i = 0
    n = len(e)
    while i < n:
        if rest[i]:
            j = i
            while j < n and rest[j]:
                j += 1
            if j - i >= int(0.25 * FPS):
                cuts.append((i + j) // 2)
            i = j
        else:
            i += 1
    cuts.append(n - 1)
    out = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        length = (b - a) / FPS
        if length < min_s:
            continue
        if length <= max_s:
            out.append((a, b))
        else:
            w = int(window_s * FPS)
            for s in range(a, b - int(min_s * FPS), w):
                out.append((s, min(b, s + w)))
    return out


def estimate_complexity(f: np.ndarray) -> int:
    e = motion_energy(f)
    top = e.max()
    if top <= 0:
        return 1
    peaks = [i for i in range(1, len(e) - 1) if e[i] >= e[i - 1] and e[i] > e[i + 1] and e[i] > 0.5 * top]
    merged = []
    for p in peaks:
        if not merged or p - merged[-1] > int(0.35 * FPS):
            merged.append(p)
    return int(np.clip(len(merged) + 1, 2, 5))


def estimate_flexibility(f: np.ndarray) -> str:
    angles = []
    for side in ("l", "r"):
        thigh = f[:, J[f"{side}_knee"]] - f[:, J[f"{side}_hip"]]
        cosv = -thigh[:, 1] / np.maximum(np.linalg.norm(thigh, axis=-1), 1e-9)
        angles.append(np.degrees(np.arccos(np.clip(cosv, -1, 1))))
    hip_flex = float(np.max(angles))
    mid_y = ((f[:, J["l_hip"], 1] + f[:, J["r_hip"], 1]) / 2)
    crouch = float(mid_y.max() - mid_y.min())
    if hip_flex > 95 or crouch > 0.45:
        return "high"
    if hip_flex > 65 or crouch > 0.25:
        return "medium"
    return "low"


def clips_from_bvh(text: str, src: Source, trial: str) -> list[MotionItem]:
    bvh = parse_bvh(text)
    step = max(1, int(round(1.0 / (bvh.frame_time * FPS))))
    pos = forward_kinematics(bvh, slice(0, None, step))
    frames = to_canonical(pos)
    # drop the T-pose calibration lead-in that many CMU takes start with
    arms_out = np.abs(frames[:, J["l_wrist"], 0] - frames[:, J["r_wrist"], 0]) > 1.3
    start = int(np.argmax(~arms_out)) if arms_out[:15].all() else 0
    frames = frames[start:]
    items = []
    limit_fp, limit_reach = SPACE_LIMITS["small"]
    for k, (a, b) in enumerate(segment(frames)):
        seg = face_camera(frames[a:b + 1]).astype(np.float32)
        m = compute_metrics(seg)
        dev = np.linalg.norm(seg - seg[:1], axis=-1).sum(-1)
        if dev.max() < 1.0:          # nothing happens
            continue
        if m["footprint_m"] > limit_fp or m["reach_m"] > limit_reach:
            continue
        if not np.isfinite(seg).all():
            continue
        items.append(MotionItem(
            id=f"cmu.{trial}.{k}", name=f"{src.name} (CMU {trial} #{k + 1})", category=src.category,
            subcategory=src.subcategory, complexity=estimate_complexity(seg), flexibility=estimate_flexibility(seg),
            static=False, stance_based=False, source="cmu", segments=[f"cmu.{trial}"],
            description=f"Motion capture: CMU Graphics Lab database, trial {trial}.", tags=["mocap"], frames=seg, **m))
    # keep the most varied clips of a long take
    if len(items) > src.max_clips:
        idx = np.linspace(0, len(items) - 1, src.max_clips).round().astype(int)
        items = [items[i] for i in sorted(set(idx))]
    return items


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
    print(f"Wrote {len(items)} clips to {out}. Run `mfnb calibrate` to refresh the acceptance thresholds.")
    return 0
