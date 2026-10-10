"""Application logic behind the API: blocks, scoring, progress, calibration, dashboard."""
from __future__ import annotations

import datetime as dt
import json
import random
from collections import defaultdict

import numpy as np

from ..face.blendshapes import D as FACE_D
from ..face.blendshapes import DIMS as FACE_DIMS
from ..face.blendshapes import IDX as FACE_IDX
from ..face.blendshapes import MIRROR_PERM, from_mediapipe
from ..face.expressions import FaceLibrary, get_face_library
from ..face.scoring import MIN_RISE, FaceCalibration, FaceTarget, neutral_from_frames, orient, score_face, thresholds
from ..motion.library import MotionLibrary, get_library
from ..motion.rig import DEFAULT_BODY, BodyDims
from ..motion.scoring import ResponseInput, Tolerance, View, estimate_view, judge, score_motor
from ..motion.skeleton import J
from ..nback.adaptive import next_n
from ..nback.plan import PlanOptions, TrialPlan, lure_items, make_plan, resolve_targets
from ..progress.mastery import ItemStats, record_attempt, record_seen, status
from ..storage.db import Store

MODALITIES = ("motor", "facial")
VIEW_WARN_YAW, VIEW_WARN_TILT, VIEW_MAX_YAW = 45.0, 30.0, 70.0
FACE_STIM_S = 2.4  # neutral -> expression -> hold -> neutral
# Face calibration prompts -> the shapes each one measures (the shapes it is about, not its side effects).
CALIBRATION_PROMPTS = {
    "smile": ["mouthSmileLeft", "mouthSmileRight"],
    "brows_up": ["browInnerUp", "browOuterUpLeft", "browOuterUpRight"],
    "frown": ["browDownLeft", "browDownRight"],
    "eyes_closed": ["eyeBlinkLeft", "eyeBlinkRight"],
    "jaw_open": ["jawOpen"],
    "pucker": ["mouthPucker"],
    "upper_lip": ["mouthUpperUpLeft", "mouthUpperUpRight"],
    "mouth_frown": ["mouthFrownLeft", "mouthFrownRight"],
    "funnel": ["mouthFunnel"],
    "lips_press": ["mouthPressLeft", "mouthPressRight"],
    "lips_roll": ["mouthRollLower", "mouthRollUpper"],
    "jaw_left": ["jawLeft"],
    "mouth_left": ["mouthLeft"],
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

    @staticmethod
    def framing(settings: dict, overrides: dict | None = None) -> str:
        f = {**settings["motor"], **(overrides or {})}.get("framing", "full")
        return f if f in ("full", "upper") else "full"

    def motor_pool(self, prof: dict, overrides: dict | None = None, camera_yaw_deg: float | None = None):
        s = prof["settings"]
        ms = {**s["motor"], **(overrides or {})}
        if camera_yaw_deg is None:
            camera_yaw_deg = float((prof["calibration"].get("view") or {}).get("yaw_deg", 0.0))
        return self.motor.filter(categories=ms.get("categories") or None, complexity=tuple(ms.get("complexity", (1, 5))),
                                 flexibility=s["flexibility"], space=s["space"], allow_turn_away=s["allow_turn_away"],
                                 exclude=self.store.exclusions(prof["id"], "motor"), sources=ms.get("sources") or None,
                                 framing=self.framing(s, overrides), camera_yaw_deg=camera_yaw_deg)

    def measure_view(self, pid: int, rest: dict, framing: str) -> tuple[View, str | None]:
        """Camera angle from ~2 s of the user relaxed and facing the screen. Too oblique a camera is refused."""
        f = np.asarray(rest.get("frames", []), dtype=float)
        if f.ndim != 3 or f.shape[1:] != (19, 3) or len(f) < 10 or not np.isfinite(f).all():
            raise ServiceError("You were not tracked while standing still: step back into view and try again.")
        vis = rest.get("visibility")
        view = estimate_view(f, None if vis is None else np.asarray(vis, float), framing)
        yaw, tilt = abs(view.yaw_deg), view.tilt_deg
        side = "left" if view.yaw_deg > 0 else "right"
        if yaw > VIEW_MAX_YAW:
            raise ServiceError(f"The camera sees you from about {yaw:.0f}° to your {side}. Place it within 45° of "
                               "straight in front of you, and face the screen while it measures.")
        warning = None
        if yaw > VIEW_WARN_YAW or tilt > VIEW_WARN_TILT:
            warning = (f"The camera is about {yaw:.0f}° to your {side} and tilted {tilt:.0f}°. Scoring corrects for "
                       "it, but tracking is more reliable within 30° and with the camera around chest height.")
        self.store.set_calibration(pid, "view", view.to_dict())
        return view, warning

    def face_calibration(self, prof: dict) -> FaceCalibration:
        return FaceCalibration.from_dict(prof["calibration"].get("face"))

    def face_pool(self, prof: dict, overrides: dict | None = None):
        fs = {**prof["settings"]["facial"], **(overrides or {})}
        return self.face.filter(categories=fs.get("categories") or None, complexity=tuple(fs.get("complexity", (1, 5))),
                                exclude=self.store.exclusions(prof["id"], "facial"),
                                measured=self.face_calibration(prof).measured)

    # -- blocks ------------------------------------------------------------------------
    def start_block(self, pid: int, modality: str, n: int | None = None, overrides: dict | None = None,
                    seed: int | None = None, face_neutral: list | None = None, view_rest: dict | None = None) -> dict:
        if modality not in MODALITIES:
            raise ServiceError(f"unknown modality {modality}")
        prof = self._profile(pid)
        s = prof["settings"]
        ms = {**s[modality], **(overrides or {})}
        n = int(ms["n"] if n is None else n)
        if n < 0 or n > 12:
            raise ServiceError("N must be between 0 and 12")
        rng = random.Random(seed)
        view, view_warning = None, None
        if modality == "motor":
            framing = self.framing(s, overrides)
            if view_rest is not None:
                view, view_warning = self.measure_view(pid, view_rest, framing)
            pool = self.motor_pool(prof, overrides, None if view is None else view.yaw_deg)
            opts = PlanOptions(n=n, n_trials=int(ms["block_base"]) + n, variable_n=bool(ms.get("variable_n")),
                               chirality_p=float(ms.get("chirality_p", 0.0)), sequence_p=float(ms.get("sequence_p", 0.0)),
                               stance_mirror=s["stance"] == "southpaw")
            kw = dict(chiral={i.id for i in pool if self.motor.chiral(i.id, framing)},
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
        if view is not None:
            config["view"] = view.to_dict()
            config["view_warning"] = view_warning
        if modality == "facial" and face_neutral is not None:
            # the resting face of this session (lighting, camera and posture change from day to day)
            try:
                neutral, deadzone = neutral_from_frames(self._face_frames(face_neutral, self.face_calibration(prof).lr_swap))
                config["face_neutral"] = np.round(neutral, 4).tolist()
                config["face_deadzone"] = np.round(deadzone, 4).tolist()
            except ServiceError:
                pass   # face not tracked during the capture: fall back to the calibration's resting face
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
        cfg = block["config"]
        return {"block_id": bid, "modality": modality, "n": block["n"], "trials": trials, "items": items,
                "status": block["status"], "settings": cfg["settings"],
                "framing": self.framing(cfg["settings"], cfg.get("overrides")) if modality == "motor" else None,
                "view": cfg.get("view"), "view_warning": cfg.get("view_warning")}

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
            cfg = block["config"]
            framing = self.framing(cfg["settings"], cfg.get("overrides"))
            view = View.from_dict(cfg.get("view"))
            res = score_motor([self.motor.frames(i, m) for i, m in targets],
                              ResponseInput(frames, None if times is None else np.asarray(times, float),
                                            None if vis is None else np.asarray(vis, float)),
                              static=len(targets) == 1 and self.motor.get(targets[0][0]).static,
                              tolerance=Tolerance(strictness=float(s["strictness"]), flexibility=s["flexibility"]),
                              lures=[self.motor.frames(i, m) for i, m in lures],
                              lure_static=[self.motor.get(i).static for i, _ in lures], framing=framing, view=view)
            threshold = float(np.mean([self.motor.threshold(i, framing) for i, _ in targets]))
            names = {i: self.motor.get(i).name for i, _ in lures}
        else:
            calib = self.face_calibration(prof)
            try:
                frames = self._face_frames(payload.get("frames", []), calib.lr_swap)
            except ServiceError:
                return self._invalid(bid, idx, plan, targets, "no face tracked")
            cfg = block["config"]
            if cfg.get("face_neutral") is not None:
                calib = calib.with_neutral(np.asarray(cfg["face_neutral"], float),
                                           None if cfg.get("face_deadzone") is None else np.asarray(cfg["face_deadzone"], float))
            (tid, tm), = targets
            times = payload.get("times")
            threshold, gamma = thresholds(float(s["strictness"]))
            res = score_face(FaceTarget.of(self.face.get(tid), tm), frames,
                             None if times is None else np.asarray(times, float), calib=calib, threshold=threshold,
                             gamma=gamma, lures=[FaceTarget.of(self.face.get(i), m) for i, m in lures])
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
                "missing": tres.get("missing", []),
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
        valid = [t for t in trials if t["valid"] and t["score"] is not None]
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
    def calibrate_body(self, pid: int, frames: list, framing: str = "full") -> dict:
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
        if framing == "upper":   # legs out of the picture: keep the default proportions for them
            for k in ("thigh", "shin", "foot"):
                measured[k] = default[k]
        dims = {k: round(float(np.clip(v, 0.5 * default[k], 1.6 * default[k])), 3) for k, v in measured.items()}
        dims["ankle_height"] = default["ankle_height"]
        BodyDims.from_dict(dims)
        self.store.set_calibration(pid, "body", dims)
        return dims

    @staticmethod
    def _face_frames(x, lr_swap: bool = False) -> np.ndarray:
        """(T, 52) MediaPipe scores or (T, 51) shapes -> (T, 51) shapes in the user's own left/right."""
        try:
            a = np.asarray(x, dtype=float)
        except (TypeError, ValueError):
            raise ServiceError("face frames must be numbers") from None
        if a.ndim != 2 or a.shape[1] not in (FACE_D, FACE_D + 1) or len(a) < 3:
            raise ServiceError("face frames must be (T, 52) or (T, 51)")
        a = from_mediapipe(a) if a.shape[1] == FACE_D + 1 else a
        a = a[np.isfinite(a).all(axis=1)]          # frames the browser could not fill
        if len(a) < 3:
            raise ServiceError("no face tracked")
        return orient(np.clip(a, 0.0, 1.0), lr_swap)

    @staticmethod
    def wink_side(neutral: np.ndarray, wink_left: np.ndarray) -> str:
        """'normal' when a left wink closes the left eye, 'mirrored' when it closes the right one (the camera feed is
        mirrored), 'unclear' otherwise (both eyes, or barely moved)."""
        rise = np.percentile(wink_left, 90, axis=0) - neutral
        dl, dr = rise[FACE_IDX["eyeBlinkLeft"]], rise[FACE_IDX["eyeBlinkRight"]]
        if dl - dr >= 0.15 and dl >= 0.20:
            return "normal"
        if dr - dl >= 0.15 and dr >= 0.20:
            return "mirrored"
        return "unclear"

    def calibrate_face(self, pid: int, neutral: list, prompts: dict[str, list] | None = None,
                       wink_left: list | None = None) -> dict:
        """Resting face, how far each prompted movement goes on this face, and a left/right check."""
        raw_neutral = self._face_frames(neutral)
        side = "skipped"
        if wink_left is not None:
            side = self.wink_side(np.median(raw_neutral, axis=0), self._face_frames(wink_left))
        lr_swap = side == "mirrored"
        neutral_v, deadzone = neutral_from_frames(orient(raw_neutral, lr_swap))
        rise = np.full(FACE_D, np.nan)
        for prompt, frames in (prompts or {}).items():
            if prompt not in CALIBRATION_PROMPTS:
                continue
            a = self._face_frames(frames, lr_swap)
            for name in CALIBRATION_PROMPTS[prompt]:
                k = FACE_IDX[name]
                r = float(np.percentile(a[:, k], 90) - neutral_v[k])
                if r >= MIN_RISE:
                    rise[k] = r
                    m = int(MIRROR_PERM[k])
                    if m != k and FACE_DIMS[m] not in CALIBRATION_PROMPTS[prompt] and np.isnan(rise[m]):
                        rise[m] = r   # one-sided prompt (jaw to the left): assume the other side moves as far
        cal = FaceCalibration(neutral=neutral_v, deadzone=deadzone, rise=rise, lr_swap=lr_swap).to_dict()
        cal["side_check"] = side
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
