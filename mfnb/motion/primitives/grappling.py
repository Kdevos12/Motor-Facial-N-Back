"""Shadow grappling: solo mimicry of partner techniques (judo uchikomi, wrestling, clinch).

Full-turn throws (back to the camera) are flagged by their computed rotation; the default
versions are in-place entries turning at most ~90 degrees.
"""
from __future__ import annotations

from .dsl import Primitive, seq
from .homes import CLINCH, JUDO, WRESTLE

LEVEL = {"pitch": 38, "head_pitch": 30, "l_leg_ik": [0.12, -0.52, 0.28], "r_leg_ik": [0.14, -0.52, -0.25]}


def _g(id_, name, keys, sub, home, **kw):
    return Primitive(f"grapple.{id_}", name, "grappling", sub, keys, home=home, stance_based=True, **kw)


def primitives() -> list[Primitive]:
    w, j, c = WRESTLE, JUDO, CLINCH
    return [
        # Wrestling
        _g("level_change", "Level change", seq(w, [(0.25, LEVEL), (0.2, {})], back=0.3), "wrestling", "wrestle",
           flexibility="medium"),
        _g("penetration_step", "Penetration step (short)", seq(w, [
            (0.2, LEVEL),
            (0.3, {"z": 0.25, "pitch": 40, "l_leg_ik": [0.12, -0.40, 0.18], "r_leg_ik": [0.14, -0.40, -0.45],
                   "l_arm_ik": ([-0.10, -0.30, 0.40], "down+0.3out"), "r_arm_ik": ([-0.10, -0.30, 0.40], "down+0.3out")}),
            (0.15, {})], back=0.45), "wrestling", "wrestle", flexibility="high", complexity=3),
        _g("double_leg", "Double-leg shot (shadow)", seq(w, [
            (0.2, LEVEL),
            (0.28, {"z": 0.2, "pitch": 45, "l_leg_ik": [0.12, -0.45, 0.20], "r_leg_ik": [0.14, -0.45, -0.40],
                    "l_arm_ik": ([0.05, -0.40, 0.42], "down+0.3out"), "r_arm_ik": ([0.05, -0.40, 0.42], "down+0.3out")}),
            (0.22, {"pitch": 30, "l_arm_ik": ([-0.10, -0.45, 0.15], "out+0.3back"),
                    "r_arm_ik": ([-0.10, -0.45, 0.15], "out+0.3back")}),
            (0.1, {})], back=0.45), "wrestling", "wrestle", flexibility="high", complexity=4),
        _g("single_leg", "Single-leg grab (shadow)", seq(w, [
            (0.22, {**LEVEL, "roll": 10}),
            (0.25, {"z": 0.12, "l_arm_ik": ([0.0, -0.45, 0.40], "down+0.3out"), "r_arm_ik": ([-0.25, -0.42, 0.38], "down+0.3out")}),
            (0.25, {"pitch": 15, "head_pitch": 10, "l_leg_ik": [0.12, -0.70, 0.25], "r_leg_ik": [0.14, -0.70, -0.25],
                    "l_arm_ik": ([-0.15, -0.20, 0.20], "down+0.3out"), "r_arm_ik": ([-0.25, -0.15, 0.20], "down+0.3out")}),
            (0.1, {})], back=0.45), "wrestling", "wrestle", flexibility="medium", complexity=4),
        _g("sprawl", "Sprawl (hips back)", seq(w, [
            (0.25, {"z": -0.15, "pitch": 55, "head_pitch": 40, "l_leg_ik": [0.20, -0.70, -0.40],
                    "r_leg_ik": [0.22, -0.70, -0.55], "l_arm_ik": ([0.0, -0.40, 0.30], "out+0.3back"),
                    "r_arm_ik": ([0.0, -0.40, 0.30], "out+0.3back")}),
            (0.3, {})], back=0.4), "wrestling", "wrestle", flexibility="medium"),
        _g("snap_down", "Snap-down", seq(w, [
            (0.2, {"pitch": 15, "l_arm_ik": ([-0.15, 0.15, 0.40], "down+0.3out"), "r_arm_ik": ([-0.15, 0.15, 0.40], "down+0.3out")}),
            (0.2, {"pitch": 35, "l_arm_ik": ([-0.10, -0.42, 0.15], "out+0.3back"), "r_arm_ik": ([-0.10, -0.42, 0.15], "out+0.3back"),
                   "l_leg_ik": [0.12, -0.56, 0.20], "r_leg_ik": [0.14, -0.56, -0.30]}),
            (0.15, {})], back=0.35), "wrestling", "wrestle", complexity=3),
        _g("arm_drag", "Arm drag", seq(w, [
            (0.2, {"r_arm_ik": ([-0.40, -0.05, 0.35], "down+0.3out")}),
            (0.3, {"yaw": 25, "twist": 30, "r_arm_ik": ([0.10, -0.40, -0.05], "out+0.2back"),
                   "l_arm_ik": ([-0.05, -0.30, 0.25], "down+0.3out")}),
            (0.15, {})], back=0.4), "wrestling", "wrestle", complexity=3),
        _g("pummel", "Pummeling (swim for underhooks)", seq(w, [
            (0.25, {"pitch": 15, "r_upper_arm": "fwd+0.3in+0.2down", "r_forearm": "up+0.6fwd+0.2in"}),
            (0.25, {"r_arm_ik": ([-0.08, -0.18, 0.32], "down+0.2out"), "l_upper_arm": "fwd+0.3in+0.2down",
                    "l_forearm": "up+0.6fwd+0.2in"}),
            (0.15, {})], back=0.35), "wrestling", "wrestle", complexity=3),
        _g("collar_tie", "Collar tie and head position", seq(w, [
            (0.25, {"pitch": 18, "l_arm_ik": ([-0.20, 0.10, 0.42], "down+0.4out"), "head_yaw": -15}),
            (0.3, {})], back=0.35), "wrestling", "wrestle"),
        _g("whizzer", "Whizzer (overhook)", seq(w, [
            (0.3, {"yaw": -45, "roll": 10, "l_upper_arm": "out+0.3up+0.3fwd", "l_forearm": "down+0.6in+0.3back"}),
            (0.25, {})], back=0.35), "wrestling", "wrestle", flexibility="medium"),
        _g("hand_fight", "Hand fighting (strip the grip)", seq(w, [
            (0.18, {"l_arm_ik": ([-0.20, -0.05, 0.42], "down+0.3out")}),
            (0.18, {"l_arm_ik": ([0.15, -0.35, 0.20], "down+0.3out"), "r_arm_ik": ([-0.25, 0.0, 0.40], "down+0.3out")}),
            (0.18, {"r_arm_ik": ([0.15, -0.35, 0.20], "down+0.3out")}),
            (0.1, {})], back=0.3), "wrestling", "wrestle", complexity=3),
        # Clinch
        _g("plum_knee", "Thai clinch knee", seq(c, [
            (0.2, {"pitch": 20, "l_arm_ik": ([-0.16, -0.10, 0.40], "down+0.4out"), "r_arm_ik": ([-0.16, -0.10, 0.40], "down+0.4out")}),
            (0.22, {"r_thigh": "@fwd+0.5up", "r_shin": "@down+0.3back", "yaw": -10}),
            (0.1, {})], back=0.35), "clinch", "clinch", complexity=3),
        _g("body_lock", "Body lock", seq(c, [
            (0.3, {"pitch": 15, "l_arm_ik": ([-0.25, -0.30, 0.38], "out+0.3down"), "r_arm_ik": ([-0.25, -0.30, 0.38], "out+0.3down"),
                   "l_leg_ik": [0.12, -0.72, 0.15], "r_leg_ik": [0.12, -0.72, -0.15]}),
            (0.3, {"pitch": -10})], back=0.4), "clinch", "clinch", complexity=3),
        _g("frame_push", "Frame and push off", seq(c, [
            (0.25, {"l_arm_ik": ([-0.15, -0.05, 0.25], "down+0.3out"), "r_arm_ik": ([-0.12, 0.05, 0.22], "down+0.3out")}),
            (0.22, {"pitch": 0, "l_arm_ik": ([-0.12, -0.05, 0.50], "down+0.3out"), "r_arm_ik": ([-0.10, 0.05, 0.50], "down+0.3out"),
                    "z": -0.12}),
            (0.15, {})], back=0.4), "clinch", "clinch"),
        _g("clinch_elbow", "Clinch break elbow", seq(c, [
            (0.18, {"l_arm_ik": ([-0.10, -0.20, 0.30], "down+0.3out")}),
            (0.22, {"twist": 35, "r_upper_arm": "out+0.45fwd+0.1up", "r_forearm": "in+0.1back"}),
            (0.12, {})], back=0.35), "clinch", "clinch"),
        # Judo (right-handed)
        _g("kuzushi", "Kuzushi (break balance forward)", seq(j, [
            (0.3, {"pitch": -5, "l_arm_ik": ([0.15, -0.30, 0.10], "out+0.3back"),
                   "r_arm_ik": ([-0.10, 0.18, 0.40], "down+0.4out")}),
            (0.2, {})], back=0.4), "judo", "judo"),
        _g("seoi_nage_entry", "Seoi nage entry (90° uchikomi)", seq(j, [
            (0.2, {"yaw": 35, "r_leg_ik": [0.10, -0.80, 0.25], "l_arm_ik": ([0.15, -0.20, 0.30], "out+0.3back")}),
            (0.3, {"yaw": 95, "pitch": 30, "l_leg_ik": [0.14, -0.62, 0.0], "r_leg_ik": [0.14, -0.62, 0.0],
                   "r_upper_arm": "fwd+0.6up+0.2in", "r_forearm": "up+0.4back",
                   "l_arm_ik": ([-0.20, -0.30, 0.20], "out+0.3back")}),
            (0.15, {})], back=0.5), "judo", "judo", flexibility="medium", complexity=4),
        _g("seoi_nage_full", "Seoi nage entry (full turn)", seq(j, [
            (0.2, {"yaw": 60, "r_leg_ik": [0.10, -0.80, 0.25]}),
            (0.35, {"yaw": 180, "pitch": 32, "l_leg_ik": [0.14, -0.60, 0.0], "r_leg_ik": [0.14, -0.60, 0.0],
                    "r_upper_arm": "fwd+0.6up+0.2in", "r_forearm": "up+0.4back",
                    "l_arm_ik": ([-0.20, -0.30, 0.20], "out+0.3back")}),
            (0.15, {})], back=0.6), "judo", "judo", flexibility="medium", complexity=4, tags=("turns_away",)),
        _g("osoto_gari", "Osoto gari (major outer reap)", seq(j, [
            (0.25, {"z": 0.15, "pitch": 15, "l_leg_ik": [0.20, -0.80, 0.20], "l_arm_ik": ([0.15, -0.30, 0.10], "out+0.3back")}),
            (0.22, {"r_thigh": "fwd+0.3out", "r_shin": "down+0.2fwd"}),
            (0.25, {"pitch": 35, "r_thigh": "back+0.4up+0.1out", "r_shin": "back+0.2up",
                    "r_arm_ik": ([-0.10, 0.10, 0.45], "down+0.3out")}),
            (0.1, {})], back=0.5), "judo", "judo", flexibility="medium", complexity=4),
        _g("ouchi_gari", "Ouchi gari (major inner reap)", seq(j, [
            (0.22, {"pitch": 15, "z": 0.1}),
            (0.3, {"r_thigh": "fwd+0.25in+0.2down", "r_shin": "down+0.3in"}),
            (0.25, {"r_thigh": "down+0.3out+0.1fwd", "r_shin": "down+0.2back+0.3out", "pitch": 22}),
            (0.1, {})], back=0.45), "judo", "judo", complexity=4),
        _g("kouchi_gari", "Kouchi gari (minor inner reap)", seq(j, [
            (0.22, {"pitch": 10}), (0.25, {"r_thigh": "down+0.4fwd+0.2in", "r_shin": "down+0.3fwd+0.3in",
                                          "r_foot": "fwd+0.6in"}),
            (0.1, {})], back=0.4), "judo", "judo", complexity=3),
        _g("deashi_barai", "De-ashi barai (forward foot sweep)", seq(j, [
            (0.2, {"yaw": 20}), (0.25, {"l_thigh": "down+0.35in+0.3fwd", "l_shin": "down+0.45in+0.2fwd",
                                       "l_foot": "in+0.5fwd", "l_arm_ik": ([0.20, -0.35, 0.05], "out+0.3back")}),
            (0.1, {})], back=0.4), "judo", "judo", complexity=3),
        _g("o_goshi_entry", "O goshi entry (hip throw, 90°)", seq(j, [
            (0.22, {"yaw": 40, "r_leg_ik": [0.08, -0.80, 0.22]}),
            (0.3, {"yaw": 95, "pitch": 20, "l_leg_ik": [0.14, -0.66, 0.0], "r_leg_ik": [0.14, -0.66, 0.0],
                   "r_arm_ik": ([-0.10, -0.30, -0.25], "out+0.3down"), "l_arm_ik": ([0.0, -0.20, 0.35], "out+0.3back")}),
            (0.15, {})], back=0.5), "judo", "judo", flexibility="medium", complexity=4),
        _g("uchi_mata_entry", "Uchi mata (shadow, 90°)", seq(j, [
            (0.22, {"yaw": 45}),
            (0.3, {"yaw": 95, "pitch": 45, "r_thigh": "back+0.6up", "r_shin": "back+0.7up",
                   "l_arm_ik": ([0.15, -0.30, 0.10], "out+0.3back"), "r_arm_ik": ([-0.10, 0.0, 0.42], "down+0.3out")}),
            (0.15, {})], back=0.5), "judo", "judo", flexibility="high", complexity=4),
        _g("tai_otoshi", "Tai otoshi (body drop, 90°)", seq(j, [
            (0.25, {"yaw": 80, "pitch": 15, "l_leg_ik": [0.12, -0.66, 0.0]}),
            (0.25, {"r_thigh": "out+0.6down+0.1fwd", "r_shin": "out+0.8down",
                    "l_arm_ik": ([0.20, -0.30, 0.0], "out+0.3back")}),
            (0.15, {})], back=0.5), "judo", "judo", flexibility="medium", complexity=4),
        _g("harai_goshi", "Harai goshi (sweeping hip, 90°)", seq(j, [
            (0.22, {"yaw": 50}),
            (0.3, {"yaw": 100, "pitch": 30, "r_thigh": "back+0.2out+0.3up", "r_shin": "back+0.2out+0.3up",
                   "l_arm_ik": ([0.15, -0.30, 0.10], "out+0.3back")}),
            (0.15, {})], back=0.5), "judo", "judo", flexibility="high", complexity=4),
    ]


COMBOS = [
    ["grapple.level_change", "grapple.penetration_step"], ["grapple.collar_tie", "grapple.snap_down"],
    ["grapple.hand_fight", "grapple.single_leg"], ["grapple.snap_down", "grapple.double_leg"],
    ["grapple.pummel", "grapple.whizzer"], ["grapple.arm_drag", "grapple.single_leg"],
    ["grapple.level_change", "grapple.sprawl"], ["grapple.plum_knee", "grapple.plum_knee"],
    ["grapple.frame_push", "grapple.clinch_elbow"], ["grapple.body_lock", "grapple.plum_knee"],
    ["grapple.kuzushi", "grapple.seoi_nage_entry"], ["grapple.kouchi_gari", "grapple.seoi_nage_entry"],
    ["grapple.ouchi_gari", "grapple.osoto_gari"], ["grapple.deashi_barai", "grapple.o_goshi_entry"],
    ["grapple.kuzushi", "grapple.uchi_mata_entry"], ["grapple.kouchi_gari", "grapple.tai_otoshi"],
]
