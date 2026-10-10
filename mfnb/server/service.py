"""Application logic behind the API: blocks, scoring, progress, calibration, dashboard."""
from __future__ import annotations

import datetime as dt
import json
import random
from collections import defaultdict

import numpy as np

from ..face.blendshapes import D as FACE_D
from ..face.blendshapes import IDX as FACE_IDX
from ..face.blendshapes import from_mediapipe, mirror_vec
from ..face.expressions import FaceLibrary, get_face_library
from ..face.scoring import FaceCalibration, score_face
from ..motion.library import MotionLibrary, get_library
from ..motion.rig import DEFAULT_BODY, BodyDims
from ..motion.scoring import ResponseInput, Tolerance, judge, score_motor
from ..motion.skeleton import J
from ..nback.adaptive import next_n
from ..nback.plan import PlanOptions, TrialPlan, lure_items, make_plan, resolve_targets
from ..progress.mastery import ItemStats, record_attempt, record_seen, status
from ..storage.db import Store

MODALITIES = ("motor", "facial")
FACE_STIM_S = 2.4  # neutral -> expression -> hold -> neutral
GAIN_GROUPS = {
    "smile": ["mouthSmileLeft", "mouthSmileRight", "cheekSquintLeft", "cheekSquintRight"],
    "brows_up": ["browInnerUp", "browOuterUpLeft", "browOuterUpRight"],
    "frown": ["browDownLeft", "browDownRight"],
    "jaw_open": ["jawOpen", "mouthLowerDownLeft", "mouthLowerDownRight"],
    "pucker": ["mouthPucker", "mouthFunnel"],
}


class ServiceError(ValueError):
    pass


def today() -> str:
    return dt.date.today().isoformat()


def instruction_text(targets: list[dict]) -> str:
    def one(t):
        base = "copy it now" if t["offset"] == 0 else f"{t['offset']}-back"
        return base + (" · switch sides" if t["mirror"] else "")
    if not targets:
        return "watch"
    if len(targets) == 1:
        return one(targets[0])
    return " then ".join(one(t) for t in targets)


class Trainer:
    def __init__(self, store: Store, motor: MotionLibrary | None = None, face: FaceLibrary | None = None):
        self.store = store
        self.motor = motor or get_library()
        self.face = face or get_face_library()

    # -- helpers -----------------------------------------------------------------------
    def _profile(self, pid: int) -> dict:
        prof = self.store.get_profile(pid)
        if prof is None:
            raise ServiceError(f"unknown profile {pid}")
        return prof

    def motor_item_payload(self, item_id: str, with_frames: bool = True) -> dict:
        it = self.motor.get(item_id)
        d = it.meta()
        if with_frames:
            d["frames"] = np.round(it.frames, 3).tolist()
            d["fps"] = 30
        return d

    def face_item_payload(self, item_id: str) -> dict:
        d = self.face.get(item_id).meta()
        d["duration_s"] = FACE_STIM_S
        return d

    def motor_pool(self, prof: dict, overrides: dict | None = None):
        s = prof["settings"]
        ms = {**s["motor"], **(overrides or {})}
        return self.motor.filter(categories=ms.get("categories") or None, complexity=tuple(ms.get("complexity", (1, 5))),
                                 flexibility=s["flexibility"], space=s["space"], allow_turn_away=s["allow_turn_away"],
                                 exclude=self.store.exclusions(prof["id"], "motor"), sources=ms.get("sources") or None)

    def face_pool(self, prof: dict, overrides: dict | None = None):
        fs = {**prof["settings"]["facial"], **(overrides or {})}
        return self.face.filter(categories=fs.get("categories") or None, complexity=tuple(fs.get("complexity", (1, 5))),
                                exclude=self.store.exclusions(prof["id"], "facial"))

    # -- blocks ------------------------------------------------------------------------
    def start_block(self, pid: int, modality: str, n: int | None = None, overrides: dict | None = None,
                    seed: int | None = None) -> dict:
        if modality not in MODALITIES:
            raise ServiceError(f"unknown modality {modality}")
        prof = self._profile(pid)
        s = prof["settings"]
        ms = {**s[modality], **(overrides or {})}
        n = int(ms["n"] if n is None else n)
        if n < 0 or n > 12:
            raise ServiceError("N must be between 0 and 12")
        rng = random.Random(seed)
        if modality == "motor":
            pool = self.motor_pool(prof, overrides)
            opts = PlanOptions(n=n, n_trials=int(ms["block_base"]) + n, variable_n=bool(ms.get("variable_n")),
                               chirality_p=float(ms.get("chirality_p", 0.0)), sequence_p=float(ms.get("sequence_p", 0.0)),
                               stance_mirror=s["stance"] == "southpaw")
            kw = dict(chiral={i.id for i in pool if i.chiral},
                      side_variety={i.id for i in pool if i.sided and not i.stance_based},
                      stance_based={i.id for i in pool if i.stance_based})
        else:
            pool = self.face_pool(prof, overrides)
            opts = PlanOptions(n=n, n_trials=int(ms["block_base"]) + n)
            kw = dict(side_variety={i.id for i in pool if i.sided})
        if len(pool) < 2:
            raise ServiceError("Fewer than 2 items match your filters: widen the categories or complexity range.")
        plan = make_plan([i.id for i in pool], opts, rng, **kw)
        config = {"settings": s, "overrides": overrides or {}, "pool_size": len(pool)}
        bid = self.store.create_block(pid, modality, n, config, [t.to_dict() for t in plan], today())
        return self.block_payload(bid)

    def block_payload(self, bid: int) -> dict:
        block = self.store.get_block(bid)
        if block is None:
            raise ServiceError(f"unknown block {bid}")
        plan = [TrialPlan.from_dict(d) for d in block["plan"]]
        modality = block["modality"]
        trials = []
        for t in plan:
            resolved = resolve_targets(plan, t.index)
            targets = [{"offset": g.offset, "mirror": g.mirror, "item_id": i, "effective_mirror": m}
                       for g, (i, m) in zip(t.targets, resolved)]
            trials.append({"index": t.index, "item_id": t.item_id, "shown_mirrored": t.shown_mirrored,
                           "watch_only": t.watch_only, "targets": targets, "instruction": instruction_text(targets)})
        ids = sorted({t.item_id for t in plan})
        if modality == "motor":
            items = {i: self.motor_item_payload(i) for i in ids}
        else:
            items = {i: self.face_item_payload(i) for i in ids}
        return {"block_id": bid, "modality": modality, "n": block["n"], "trials": trials, "items": items,
                "status": block["status"], "settings": block["config"]["settings"]}

    def submit_response(self, bid: int, idx: int, payload: dict) -> dict:
        block = self.store.get_block(bid)
        if block is None:
            raise ServiceError(f"unknown block {bid}")
        if block["status"] != "running":
            raise ServiceError("block already finished")
        plan = [TrialPlan.from_dict(d) for d in block["plan"]]
        if not 0 <= idx < len(plan):
            raise ServiceError("trial index out of range")
        if plan[idx].watch_only:
            raise ServiceError("this trial has no response")
        prof = self._profile(block["profile_id"])
        s = prof["settings"]
        targets = resolve_targets(plan, idx)
        lures = lure_items(plan, idx)
        if block["modality"] == "motor":
            frames = np.asarray(payload.get("frames", []), dtype=float)
            if frames.ndim != 3 or frames.shape[1:] != (19, 3):
                return self._invalid(bid, idx, plan, targets, "no tracking data")
            vis = payload.get("visibility")
            times = payload.get("times")
            res = score_motor([self.motor.frames(i, m) for i, m in targets],
                              ResponseInput(frames, None if times is None else np.asarray(times, float),
                                            None if vis is None else np.asarray(vis, float)),
                              static=len(targets) == 1 and self.motor.get(targets[0][0]).static,
                              tolerance=Tolerance(strictness=float(s["strictness"]), flexibility=s["flexibility"]),
                              lures=[self.motor.frames(i, m) for i, m in lures],
                              lure_static=[self.motor.get(i).static for i, _ in lures])
            threshold = float(np.mean([self.motor.get(i).threshold for i, _ in targets]))
            names = {i: self.motor.get(i).name for i, _ in lures}
        else:
            frames = np.asarray(payload.get("frames", []), dtype=float)
            calib = FaceCalibration.from_dict(prof["calibration"].get("face"))
            if frames.ndim == 2 and frames.shape[1] == 52:
                frames = from_mediapipe(frames, calib.lr_swap)
            if frames.ndim != 2 or frames.shape[1] != FACE_D:
                return self._invalid(bid, idx, plan, targets, "no face tracked")
            (tid, tm), = targets
            times = payload.get("times")
            res = score_face(self.face.get(tid).vector(tm), frames, None if times is None else np.asarray(times, float),
                             calib=calib, lures=[self.face.get(i).vector(m) for i, m in lures])
            threshold = self.face.get(tid).threshold
            names = {i: self.face.get(i).name for i, _ in lures}
        tres = res["target"]
        valid = bool(tres["valid"])
        correct, confused_idx = judge(tres["score"], res["lures"], threshold) if valid else (None, None)
        confused = lures[confused_idx][0] if confused_idx is not None else None
        result = {**tres, "threshold": round(threshold, 3), "lure_scores": res["lures"],
                  "lures": [{"item_id": i, "mirrored": m, "name": names[i]} for i, m in lures]}
        response = {k: payload.get(k) for k in ("frames", "visibility", "times") if payload.get(k) is not None}
        self.store.save_trial(bid, idx, plan[idx].item_id, [[i, m] for i, m in targets], tres["score"], correct,
                              valid, confused, result, response)
        if valid:
            day = today()
            stats = self.store.get_stats(block["profile_id"], block["modality"])
            for i, _ in targets:
                st = record_attempt(ItemStats.from_dict(stats.get(i)), float(tres["score"]), bool(correct), day)
                self.store.put_stats(block["profile_id"], block["modality"], i, st.to_dict())
        return {"index": idx, "score": tres["score"], "valid": valid, "reason": tres.get("reason", ""),
                "correct": correct, "threshold": round(threshold, 3),
                "confused_with": None if confused is None else {"item_id": confused, "name": names[confused]}}

    def _invalid(self, bid, idx, plan, targets, reason):
        self.store.save_trial(bid, idx, plan[idx].item_id, [[i, m] for i, m in targets], 0.0, None, False, None,
                              {"score": 0.0, "valid": False, "reason": reason}, None)
        return {"index": idx, "score": 0.0, "valid": False, "reason": reason, "correct": None, "confused_with": None}

    def finish_block(self, bid: int) -> dict:
        block = self.store.get_block(bid)
        if block is None:
            raise ServiceError(f"unknown block {bid}")
        prof = self._profile(block["profile_id"])
        trials = self.store.list_trials(bid)
        valid = [t for t in trials if t["valid"]]
        acc = float(np.mean([bool(t["correct"]) for t in valid])) if valid else None
        mean_score = float(np.mean([t["score"] for t in valid])) if valid else None
        mode = prof["settings"]["n_mode"]
        nxt = next_n(block["n"], acc, mode=mode) if block["n"] >= 1 else block["n"]
        if block["status"] == "running":
            self.store.finish_block(bid, acc, mean_score, nxt)
            stats = self.store.get_stats(prof["id"], block["modality"])
            day = today()
            for t in block["plan"]:
                st = record_seen(ItemStats.from_dict(stats.get(t["item_id"])), day)
                stats[t["item_id"]] = st.to_dict()
                self.store.put_stats(prof["id"], block["modality"], t["item_id"], stats[t["item_id"]])
            if mode == "adaptive":
                self.store.update_profile(prof["id"], settings={block["modality"]: {"n": nxt}})
        return {"block_id": bid, "modality": block["modality"], "n": block["n"], "accuracy": acc,
                "mean_score": mean_score, "next_n": nxt, "n_valid": len(valid),
                "n_correct": sum(1 for t in valid if t["correct"]), "n_mode": mode}

    def block_report(self, bid: int) -> dict:
        payload = self.block_payload(bid)
        block = self.store.get_block(bid)
        payload["trials_results"] = self.store.list_trials(bid, with_responses=True)
        payload["summary"] = {k: block[k] for k in ("accuracy", "mean_score", "next_n", "started_at", "finished_at", "day")}
        return payload

    # -- calibration -------------------------------------------------------------------
    def calibrate_body(self, pid: int, frames: list) -> dict:
        f = np.asarray(frames, dtype=float)
        if f.ndim != 3 or f.shape[1:] != (19, 3) or len(f) < 10:
            raise ServiceError("need at least 10 frames of 19 joints")

        def seg(a, b):
            return float(np.median(np.linalg.norm(f[:, J[a]] - f[:, J[b]], axis=-1)))

        def both(a, b):
            return (seg(f"l_{a}", f"l_{b}") + seg(f"r_{a}", f"r_{b}")) / 2

        mid_sh = (f[:, J["l_shoulder"]] + f[:, J["r_shoulder"]]) / 2
        mid_hip = (f[:, J["l_hip"]] + f[:, J["r_hip"]]) / 2
        measured = {
            "shoulder_half": seg("l_shoulder", "r_shoulder") / 2, "hip_half": seg("l_hip", "r_hip") / 2,
            "torso": float(np.median(np.linalg.norm(mid_sh - mid_hip, axis=-1))),
            "upper_arm": both("shoulder", "elbow"), "forearm": both("elbow", "wrist"), "hand": both("wrist", "index"),
            "thigh": both("hip", "knee"), "shin": both("knee", "ankle"), "foot": both("ankle", "foot"),
        }
        default = DEFAULT_BODY.__dict__
        dims = {k: round(float(np.clip(v, 0.5 * default[k], 1.6 * default[k])), 3) for k, v in measured.items()}
        dims["ankle_height"] = default["ankle_height"]
        BodyDims.from_dict(dims)
        self.store.set_calibration(pid, "body", dims)
        return dims

    def calibrate_face(self, pid: int, neutral: list, prompts: dict[str, list] | None = None,
                       wink_left: list | None = None) -> dict:
        def arr(x):
            a = np.asarray(x, dtype=float)
            if a.ndim != 2 or a.shape[1] not in (FACE_D, FACE_D + 1) or len(a) < 3:
                raise ServiceError("face frames must be (T, 52) or (T, 51)")
            return a[:, 1:] if a.shape[1] == FACE_D + 1 else a
        raw_neutral = arr(neutral)
        lr_swap = False
        if wink_left is not None:
            w = arr(wink_left)
            lr_swap = bool(np.percentile(w[:, FACE_IDX["eyeBlinkRight"]], 90) >
                           np.percentile(w[:, FACE_IDX["eyeBlinkLeft"]], 90))

        def orient(a):
            return mirror_vec(a) if lr_swap else a
        neutral_v = np.median(orient(raw_neutral), axis=0)
        gain = np.ones(FACE_D)
        for group, frames in (prompts or {}).items():
            if group not in GAIN_GROUPS:
                continue
            a = orient(arr(frames))
            for name in GAIN_GROUPS[group]:
                k = FACE_IDX[name]
                peak = float(np.percentile(a[:, k], 90) - neutral_v[k])
                gain[k] = float(np.clip(0.85 / max(peak, 0.1), 0.8, 3.0))
        cal = {"neutral": np.round(neutral_v, 4).tolist(), "gain": np.round(gain, 3).tolist(), "lr_swap": lr_swap}
        self.store.set_calibration(pid, "face", cal)
        return cal

    # -- progress & dashboard ------------------------------------------------------------
    def item_progress(self, pid: int, modality: str) -> list[dict]:
        stats = self.store.get_stats(pid, modality)
        lib = self.motor if modality == "motor" else self.face
        out = []
        for iid, st in stats.items():
            if iid not in lib.items:
                continue
            it = lib.get(iid)
            out.append({"item_id": iid, "name": it.name, "category": it.category, "complexity": it.complexity,
                        **ItemStats.from_dict(st).to_dict()})
        return sorted(out, key=lambda d: (d["status"] != "mastered", -(d["ewma"] or 0)))

    def dashboard(self, pid: int) -> dict:
        prof = self._profile(pid)
        blocks = [b for b in self.store.list_blocks(pid) if b["status"] == "finished"]
        days = sorted({b["day"] for b in blocks})
        streak = 0
        d = dt.date.today()
        day_set = set(days)
        if d.isoformat() not in day_set:
            d -= dt.timedelta(days=1)
        while d.isoformat() in day_set:
            streak += 1
            d -= dt.timedelta(days=1)
        minutes = sum(((b["finished_at"] or b["started_at"]) - b["started_at"]) / 60 for b in blocks)
        out = {"profile": {"id": pid, "name": prof["name"]},
               "totals": {"blocks": len(blocks), "minutes": round(minutes, 1), "days": len(days), "streak": streak},
               "modalities": {}}
        for m in MODALITIES:
            mb = sorted([b for b in blocks if b["modality"] == m], key=lambda b: b["started_at"])
            progress = self.item_progress(pid, m)
            lib = self.motor if m == "motor" else self.face
            by_cat: dict[str, dict[str, int]] = defaultdict(lambda: {"mastered": 0, "learning": 0, "seen": 0, "total": 0})
            for it in lib.items.values():
                by_cat[it.category]["total"] += 1
            for p in progress:
                if p["status"] in ("mastered", "learning", "seen"):
                    by_cat[p["category"]][p["status"]] += 1
            cat_acc: dict[str, list[int]] = defaultdict(list)
            for t in self.store.trials_for_profile(pid, m):
                if t["valid"] and t["correct"] is not None and t["item_id"] in lib.items:
                    for iid, _ in json.loads(t["targets"]):
                        if iid in lib.items:
                            cat_acc[lib.get(iid).category].append(int(t["correct"]))
            out["modalities"][m] = {
                "current_n": prof["settings"][m]["n"],
                "best_n": max([b["n"] for b in mb if (b["accuracy"] or 0) >= 0.6], default=None),
                "history": [{"block_id": b["id"], "day": b["day"], "n": b["n"], "accuracy": b["accuracy"],
                             "mean_score": b["mean_score"], "started_at": b["started_at"]} for b in mb],
                "mastery": {c: v for c, v in sorted(by_cat.items())},
                "mastered": [p for p in progress if p["status"] == "mastered"],
                "learning": [p for p in progress if p["status"] == "learning"][:50],
                "category_accuracy": {c: round(float(np.mean(v)), 3) for c, v in sorted(cat_acc.items())},
                "counts": {s_: sum(1 for p in progress if p["status"] == s_) for s_ in ("mastered", "learning", "seen")},
                "library_size": len(lib),
            }
        out["recent"] = [{"block_id": b["id"], "modality": b["modality"], "day": b["day"], "n": b["n"],
                          "accuracy": b["accuracy"], "next_n": b["next_n"]} for b in blocks[:12]]
        return out
