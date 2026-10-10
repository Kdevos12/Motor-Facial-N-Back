"""In-place dance moves, party dances and ballet basics."""
from __future__ import annotations

from .dsl import Primitive, posture, seq
from .homes import NEUTRAL

ARMS_UP_V = {"l_upper_arm": "up+0.45out", "l_forearm": "up+0.5out", "r_upper_arm": "up+0.45out", "r_forearm": "up+0.5out"}
HANDS_HEAD = {"l_arm_ik": ([-0.16, 0.30, 0.02], "out+0.3up"), "r_arm_ik": ([-0.16, 0.30, 0.02], "out+0.3up")}
HANDS_HIPS = {"l_arm_ik": ([0.0, -0.42, 0.0], "out+0.4back"), "r_arm_ik": ([0.0, -0.42, 0.0], "out+0.4back")}
SOFT = {"l_leg_ik": [0.08, -0.78, 0.0], "r_leg_ik": [0.08, -0.78, 0.0]}
PLIE_1 = {"l_leg_ik": ([0.12, -0.68, 0.04], "out+0.6fwd"), "r_leg_ik": ([0.12, -0.68, 0.04], "out+0.6fwd")}
PLIE_2 = {"l_leg_ik": ([0.30, -0.66, 0.0], "out+0.6fwd"), "r_leg_ik": ([0.30, -0.66, 0.0], "out+0.6fwd")}
FIRST_ARMS = {"l_arm_ik": ([-0.15, -0.35, 0.30], "out+0.3down"), "r_arm_ik": ([-0.15, -0.35, 0.30], "out+0.3down")}
SECOND_ARMS = {"l_upper_arm": "out+0.15down+0.15fwd", "l_forearm": "out+0.2down+0.3fwd",
               "r_upper_arm": "out+0.15down+0.15fwd", "r_forearm": "out+0.2down+0.3fwd"}
FIFTH_ARMS = {"l_arm_ik": ([-0.12, 0.40, 0.12], "out+0.3fwd"), "r_arm_ik": ([-0.12, 0.40, 0.12], "out+0.3fwd")}


def _d(id_, name, steps, sub="party & pop", back=0.4, **kw):
    return Primitive(f"dance.{id_}", name, "dance", sub, seq(NEUTRAL, steps, back=back), home="neutral", **kw)


def _ds(id_, name, pose, sub, **kw):
    return Primitive(f"dance.{id_}", name, "dance", sub, posture(pose), static=True, **kw)


def primitives() -> list[Primitive]:
    return [
        _d("ymca_y", "YMCA: Y", [(0.35, ARMS_UP_V), (0.4, {})], sub="ymca"),
        _d("ymca_m", "YMCA: M", [(0.35, HANDS_HEAD), (0.4, {})], sub="ymca"),
        _d("ymca_c", "YMCA: C", [(0.35, {"roll": 10, "l_upper_arm": "up+0.5out", "l_forearm": "in+0.6up",
                                         "r_upper_arm": "out+0.3up", "r_forearm": "in+0.4up"}), (0.4, {})],
           sub="ymca"),
        _d("ymca_a", "YMCA: A", [(0.35, {"l_arm_ik": ([-0.14, 0.48, 0.05], "out"), "r_arm_ik": ([-0.14, 0.48, 0.05], "out")}),
                                 (0.4, {})], sub="ymca"),
        _d("macarena_arms", "Macarena arms", [
            (0.3, {"l_upper_arm": "@fwd+0.05in", "l_forearm": "@fwd+0.05in"}),
            (0.3, {"r_upper_arm": "@fwd+0.05in", "r_forearm": "@fwd+0.05in"}),
            (0.3, {"l_arm_ik": ([-0.36, 0.0, 0.10], "down+0.3out")}),
            (0.3, {"r_arm_ik": ([-0.36, 0.0, 0.10], "down+0.3out")}),
            (0.3, {"l_arm_ik": ([-0.12, 0.25, -0.08], "out+0.3up")}), (0.3, {"r_arm_ik": ([-0.12, 0.25, -0.08], "out+0.3up")}),
            (0.3, HANDS_HIPS)], complexity=5),
        _d("disco_point", "Disco point", [
            (0.3, {"yaw": -15, "r_upper_arm": "up+0.4in+0.2fwd", "r_forearm": "up+0.4in+0.2fwd",
                   "l_arm_ik": ([0.0, -0.40, 0.0], "out+0.4back"), "r_leg_ik": [0.20, -0.82, 0.05]}),
            (0.3, {"r_upper_arm": "down+0.5out+0.2fwd", "r_forearm": "down+0.6out+0.2fwd"}),
            (0.3, {"r_upper_arm": "up+0.4in+0.2fwd", "r_forearm": "up+0.4in+0.2fwd"})], complexity=3),
        _d("dab", "Dab", [(0.3, {"pitch": 15, "head_pitch": -25, "head_yaw": 30, "roll": 10,
                                 "l_upper_arm": "fwd+0.4in+0.3up", "l_forearm": "in+0.4up+0.2back",
                                 "r_upper_arm": "out+0.6up", "r_forearm": "out+0.6up"}), (0.4, {})]),
        _d("floss", "Floss (simplified)", [
            (0.25, {"twist": 15, "l_upper_arm": "down+0.4in+0.3fwd", "l_forearm": "down+0.5in+0.3fwd",
                    "r_upper_arm": "down+0.4out+0.3back", "r_forearm": "down+0.5out+0.3back"}),
            (0.25, {"twist": -15, "l_upper_arm": "down+0.4out+0.3back", "l_forearm": "down+0.5out+0.3back",
                    "r_upper_arm": "down+0.4in+0.3fwd", "r_forearm": "down+0.5in+0.3fwd"}),
            (0.25, {"twist": 15, "l_upper_arm": "down+0.4in+0.3fwd", "l_forearm": "down+0.5in+0.3fwd",
                    "r_upper_arm": "down+0.4out+0.3back", "r_forearm": "down+0.5out+0.3back"})], complexity=3),
        _d("step_touch", "Step touch with claps", [
            (0.3, {"x": 0.18, "l_leg_ik": [0.20, -0.80, 0.0], "r_leg_ik": [0.0, -0.82, 0.0],
                   "l_arm_ik": ([-0.20, -0.05, 0.30], "down+0.4out"), "r_arm_ik": ([-0.20, -0.05, 0.30], "down+0.4out")}),
            (0.3, {"x": -0.18, "r_leg_ik": [0.20, -0.80, 0.0], "l_leg_ik": [0.0, -0.82, 0.0]}),
            (0.3, {"x": 0.0, **SOFT})], complexity=3),
        _d("twist", "The Twist", [
            (0.3, {"yaw": 30, "twist": -40, "l_leg_ik": [0.10, -0.70, 0.0], "r_leg_ik": [0.10, -0.70, 0.0],
                   "l_arm_ik": ([0.05, -0.15, 0.25], "out+0.3down"), "r_arm_ik": ([0.05, -0.15, 0.25], "out+0.3down")}),
            (0.3, {"yaw": -30, "twist": 40}), (0.3, {"yaw": 30, "twist": -40})], flexibility="medium", complexity=3),
        _d("jazz_hands", "Jazz hands", [(0.3, {"l_upper_arm": "out+0.3up+0.2fwd", "l_forearm": "up+0.3out+0.2fwd",
                                               "r_upper_arm": "out+0.3up+0.2fwd", "r_forearm": "up+0.3out+0.2fwd", **SOFT}),
                                        (0.5, {})]),
        _d("robot_arms", "Robot arms", [
            (0.25, {"l_upper_arm": "out", "l_forearm": "up", "r_upper_arm": "out", "r_forearm": "down"}),
            (0.25, {"l_forearm": "down", "r_forearm": "up"}),
            (0.25, {"head_yaw": 45, "l_upper_arm": "fwd", "l_forearm": "fwd", "r_upper_arm": "down", "r_forearm": "fwd"}),
            (0.25, {"head_yaw": 0})], complexity=4),
        _d("vogue_frame", "Vogue frame", [
            (0.3, {"l_arm_ik": ([-0.25, 0.25, 0.20], "out+0.3down"), "r_arm_ik": ([-0.30, 0.0, 0.20], "out+0.3down")}),
            (0.3, {"l_arm_ik": ([-0.30, 0.0, 0.20], "out+0.3down"), "r_arm_ik": ([-0.25, 0.25, 0.20], "out+0.3down")}),
            (0.3, {"l_arm_ik": ([-0.18, 0.40, 0.02], "out"), "r_arm_ik": ([-0.18, 0.40, 0.02], "out")})], complexity=4),
        _d("sprinkler", "The Sprinkler", [
            (0.3, {"l_arm_ik": ([-0.15, 0.25, -0.08], "out+0.3up"), "r_upper_arm": "@fwd+0.4in", "r_forearm": "@fwd+0.4in",
                   "twist": 30}),
            (0.25, {"twist": 10}), (0.25, {"twist": -10}), (0.25, {"twist": -30})], complexity=3),
        _d("lasso", "Lasso", [
            (0.25, {"r_upper_arm": "up+0.3out", "r_forearm": "out+0.6up+0.3fwd", "l_arm_ik": ([0.0, -0.4, 0.0], "out+0.4back")}),
            (0.25, {"r_forearm": "fwd+0.6up+0.3in"}), (0.25, {"r_forearm": "in+0.6up+0.3back"}),
            (0.25, {"r_forearm": "back+0.6up+0.3out"})], complexity=3),
        _d("raise_roof", "Raise the roof", [
            (0.25, {"l_arm_ik": ([-0.05, 0.20, 0.10], "out+0.4down"), "r_arm_ik": ([-0.05, 0.20, 0.10], "out+0.4down"), **SOFT}),
            (0.25, {"l_arm_ik": ([-0.05, 0.42, 0.10], "out+0.4down"), "r_arm_ik": ([-0.05, 0.42, 0.10], "out+0.4down")}),
            (0.25, {"l_arm_ik": ([-0.05, 0.20, 0.10], "out+0.4down"), "r_arm_ik": ([-0.05, 0.20, 0.10], "out+0.4down")}),
            (0.25, {"l_arm_ik": ([-0.05, 0.42, 0.10], "out+0.4down"), "r_arm_ik": ([-0.05, 0.42, 0.10], "out+0.4down")})],
           complexity=3),
        _d("hip_sway", "Hip sway with arm wave", [
            (0.4, {"roll": -10, "x": 0.06, "l_upper_arm": "out+0.4up", "l_forearm": "out+0.1down"}),
            (0.4, {"roll": 10, "x": -0.06, "l_upper_arm": "out+0.2down", "l_forearm": "out+0.4up",
                   "r_upper_arm": "out+0.4up", "r_forearm": "out+0.1down"}),
            (0.4, {"roll": 0, "x": 0.0})], complexity=3),
        _d("body_roll", "Body roll", [
            (0.3, {"pitch": -10, "head_pitch": 15}), (0.3, {"pitch": 15, "head_pitch": -10, **SOFT}),
            (0.3, {"pitch": 25, "l_leg_ik": [0.08, -0.70, 0.0], "r_leg_ik": [0.08, -0.70, 0.0]}),
            (0.3, {"pitch": 0, "head_pitch": 0})], complexity=3, flexibility="medium"),
        _d("running_man", "Running man (in place)", [
            (0.25, {"l_thigh": "fwd+0.1up", "l_shin": "down", "r_leg_ik": [0.10, -0.78, -0.10],
                    "l_arm_ik": ([-0.05, 0.05, 0.30], "down+0.3out"), "r_arm_ik": ([0.05, -0.30, -0.10], "down+0.3out")}),
            (0.25, {"l_leg_ik": [0.10, -0.78, -0.10], "r_thigh": "fwd+0.1up", "r_shin": "down",
                    "r_arm_ik": ([-0.05, 0.05, 0.30], "down+0.3out"), "l_arm_ik": ([0.05, -0.30, -0.10], "down+0.3out")}),
            (0.25, {"l_thigh": "fwd+0.1up", "l_shin": "down", "r_leg_ik": [0.10, -0.78, -0.10],
                    "l_arm_ik": ([-0.05, 0.05, 0.30], "down+0.3out"), "r_arm_ik": ([0.05, -0.30, -0.10], "down+0.3out")})],
           flexibility="medium", complexity=4),
        _d("charleston", "Charleston kick", [
            (0.3, {"r_thigh": "down+0.5fwd", "r_shin": "down+0.6fwd", "l_upper_arm": "fwd+0.3down", "r_upper_arm": "back+0.3down"}),
            (0.3, {"r_thigh": "down+0.3back", "r_shin": "back+0.6down", "l_upper_arm": "back+0.3down", "r_upper_arm": "fwd+0.3down",
                   "pitch": 10}),
            (0.3, {"r_thigh": "down+0.5fwd", "r_shin": "down+0.6fwd", "l_upper_arm": "fwd+0.3down", "r_upper_arm": "back+0.3down",
                   "pitch": 0})], complexity=4, flexibility="medium", sub="swing"),
        _d("salsa_basic", "Salsa basic (in place)", [
            (0.3, {"l_leg_ik": [0.08, -0.80, 0.18], "r_leg_ik": [0.08, -0.82, -0.05], "roll": 5,
                   "l_arm_ik": ([-0.05, -0.20, 0.25], "down+0.3out"), "r_arm_ik": ([-0.05, -0.20, 0.25], "down+0.3out")}),
            (0.3, {**SOFT, "roll": 0}), (0.3, {"r_leg_ik": [0.08, -0.80, -0.18], "l_leg_ik": [0.08, -0.82, 0.05], "roll": -5})],
           complexity=3, sub="latin"),
        _d("chicken_dance", "Chicken dance", [
            (0.25, {"l_arm_ik": ([-0.10, 0.0, 0.35], "down+0.3out"), "r_arm_ik": ([-0.10, 0.0, 0.35], "down+0.3out")}),
            (0.25, {"l_arm_ik": ([0.05, -0.20, 0.0], "out+0.6up"), "r_arm_ik": ([0.05, -0.20, 0.0], "out+0.6up")}),
            (0.3, {"l_leg_ik": [0.10, -0.62, 0.05], "r_leg_ik": [0.10, -0.62, 0.05], "pitch": 15}),
            (0.25, {**SOFT, "pitch": 0, "l_arm_ik": ([-0.25, -0.10, 0.30], "down+0.3out"),
                    "r_arm_ik": ([-0.25, -0.10, 0.30], "down+0.3out")})], complexity=4),
        _d("cabbage_patch", "Cabbage patch", [
            (0.3, {"l_arm_ik": ([-0.20, -0.10, 0.30], "down+0.3out"), "r_arm_ik": ([-0.20, -0.20, 0.35], "down+0.3out"), "yaw": 15}),
            (0.3, {"l_arm_ik": ([-0.10, -0.20, 0.40], "down+0.3out"), "r_arm_ik": ([-0.10, -0.10, 0.28], "down+0.3out"), "yaw": -15}),
            (0.3, {"l_arm_ik": ([-0.20, -0.10, 0.30], "down+0.3out"), "r_arm_ik": ([-0.20, -0.20, 0.35], "down+0.3out"), "yaw": 15})],
           complexity=3),
        _d("egyptian", "Egyptian arms", [
            (0.35, {"l_upper_arm": "out", "l_forearm": "up", "r_upper_arm": "out", "r_forearm": "down",
                    "head_yaw": 30}), (0.35, {"l_forearm": "down", "r_forearm": "up", "head_yaw": -30})], complexity=3),
        # Ballet
        _ds("first_position", "Ballet first position", {**PLIE_1, "l_leg_ik": ([0.06, -0.84, 0.03], "out+fwd"),
                                                        "r_leg_ik": ([0.06, -0.84, 0.03], "out+fwd"), **FIRST_ARMS}, "ballet"),
        _ds("second_position", "Ballet second position", {"l_leg_ik": [0.25, -0.80, 0.0], "r_leg_ik": [0.25, -0.80, 0.0],
                                                          **SECOND_ARMS}, "ballet"),
        _ds("fifth_arms", "Arms in fifth position (en haut)", {**FIFTH_ARMS}, "ballet"),
        _d("plie_first", "Plié in first position", [(0.8, {**PLIE_1, **SECOND_ARMS}), (0.4, {})], sub="ballet", back=0.8,
           flexibility="medium"),
        _d("plie_second", "Grand plié in second position", [(0.9, {**PLIE_2, **SECOND_ARMS}), (0.4, {})], sub="ballet",
           back=0.9, flexibility="medium"),
        _d("port_de_bras", "Port de bras (1st - 2nd - 5th)", [(0.6, FIRST_ARMS), (0.6, SECOND_ARMS), (0.6, FIFTH_ARMS)],
           sub="ballet", back=0.8, complexity=4),
        _d("releve", "Relevé", [(0.6, {"l_foot": "down+0.5fwd", "r_foot": "down+0.5fwd", **FIFTH_ARMS}), (0.6, {})],
           sub="ballet", back=0.6),
        _d("tendu", "Battement tendu (front)", [(0.5, {"r_thigh": "down+0.35fwd", "r_shin": "down+0.35fwd",
                                                       "r_foot": "down+0.8fwd", **SECOND_ARMS}), (0.3, {})], sub="ballet"),
        _d("passe", "Passé (retiré)", [(0.6, {"r_thigh": "fwd+0.2down+0.5out", "r_shin": "down+0.4in+0.3back", **FIFTH_ARMS}),
                                       (0.6, {})], sub="ballet", back=0.6, flexibility="medium"),
        _d("arabesque", "Low arabesque", [(0.8, {"pitch": 15, "r_thigh": "back+0.6down", "r_shin": "back+0.5down",
                                                 "r_foot": "back+0.3down", "l_upper_arm": "@fwd+0.2up",
                                                 "l_forearm": "@fwd+0.2up", "r_upper_arm": "out+0.2back"}), (0.8, {})],
           sub="ballet", back=0.8, flexibility="medium"),
    ]


COMBOS = [
    ["dance.ymca_y", "dance.ymca_m", "dance.ymca_c", "dance.ymca_a"], ["dance.ymca_y", "dance.ymca_m"],
    ["dance.ymca_c", "dance.ymca_a"], ["dance.disco_point", "dance.hip_sway"], ["dance.dab", "dance.floss"],
    ["dance.raise_roof", "dance.jazz_hands"], ["dance.robot_arms", "dance.egyptian"], ["dance.twist", "dance.charleston"],
    ["dance.vogue_frame", "dance.body_roll"], ["dance.sprinkler", "dance.lasso"], ["dance.step_touch", "dance.cabbage_patch"],
    ["dance.salsa_basic", "dance.hip_sway"], ["dance.running_man", "dance.raise_roof"],
    ["dance.plie_first", "dance.releve"], ["dance.tendu", "dance.passe"], ["dance.port_de_bras", "dance.plie_second"],
    ["dance.plie_first", "dance.tendu", "dance.arabesque"], ["dance.chicken_dance", "dance.twist"],
]
