"""Fitness, calisthenics and mobility drills that fit a small space."""
from __future__ import annotations

from .dsl import Primitive, seq
from .homes import NEUTRAL

WIDE = {"l_leg_ik": [0.14, -0.82, 0.0], "r_leg_ik": [0.14, -0.82, 0.0]}
SQUAT = {"pitch": 30, "head_pitch": 20, "l_leg_ik": ([0.16, -0.48, 0.10], "fwd+0.3out"),
         "r_leg_ik": ([0.16, -0.48, 0.10], "fwd+0.3out"),
         "l_upper_arm": "@fwd+0.1up", "l_forearm": "@fwd+0.1up", "r_upper_arm": "@fwd+0.1up", "r_forearm": "@fwd+0.1up"}
ARMS_OUT = {"l_upper_arm": "out", "l_forearm": "out", "r_upper_arm": "out", "r_forearm": "out"}
ARMS_UP = {"l_upper_arm": "up+0.1out", "l_forearm": "up+0.1out", "r_upper_arm": "up+0.1out", "r_forearm": "up+0.1out"}
HANDS_HIPS = {"l_arm_ik": ([0.0, -0.42, 0.0], "out+0.4back"), "r_arm_ik": ([0.0, -0.42, 0.0], "out+0.4back")}
HANDS_HEAD = {"l_arm_ik": ([-0.12, 0.22, -0.08], "out+0.3fwd"), "r_arm_ik": ([-0.12, 0.22, -0.08], "out+0.3fwd")}


def _f(id_, name, steps, sub="strength", back=0.6, **kw):
    return Primitive(f"fit.{id_}", name, "fitness", sub, seq(NEUTRAL, steps, back=back), home="neutral", **kw)


def primitives() -> list[Primitive]:
    return [
        _f("squat", "Bodyweight squat", [(0.9, SQUAT), (0.3, {})], back=0.9, flexibility="medium"),
        _f("sumo_squat", "Sumo squat", [(0.9, {"pitch": 10, "l_leg_ik": ([0.32, -0.56, 0.0], "fwd+0.8out"),
                                              "r_leg_ik": ([0.32, -0.56, 0.0], "fwd+0.8out"),
                                              "l_arm_ik": ([-0.18, -0.15, 0.28], "down+0.3out"),
                                              "r_arm_ik": ([-0.18, -0.15, 0.28], "down+0.3out")}), (0.3, {})],
           back=0.9, flexibility="medium"),
        _f("lunge_fwd", "Forward lunge", [(0.8, {"z": 0.2, "l_leg_ik": [0.08, -0.55, 0.42], "r_leg_ik": [0.10, -0.55, -0.45],
                                                 "r_foot": "back+0.6down", **HANDS_HIPS}), (0.3, {})],
           back=0.8, flexibility="medium"),
        _f("reverse_lunge", "Reverse lunge", [(0.8, {"z": -0.15, "r_leg_ik": [0.08, -0.55, -0.48],
                                                     "l_leg_ik": [0.10, -0.55, 0.35], "r_foot": "back+0.6down",
                                                     **HANDS_HIPS}), (0.3, {})], back=0.8, flexibility="medium"),
        _f("lateral_lunge", "Lateral lunge", [(0.8, {"x": 0.15, "pitch": 15, "l_leg_ik": ([0.40, -0.55, 0.05], "fwd+0.5out"),
                                                     "r_leg_ik": [0.30, -0.78, 0.0],
                                                     "l_arm_ik": ([-0.25, -0.25, 0.30], "down+0.3out"),
                                                     "r_arm_ik": ([-0.25, -0.25, 0.30], "down+0.3out")}), (0.3, {})],
           back=0.8, flexibility="medium"),
        _f("curtsy_lunge", "Curtsy lunge", [(0.8, {"r_leg_ik": [-0.20, -0.58, -0.35], "l_leg_ik": [0.10, -0.58, 0.15],
                                                   "yaw": 10, **HANDS_HIPS}), (0.3, {})], back=0.8, flexibility="high"),
        _f("good_morning", "Good morning (hip hinge)", [(0.9, {"pitch": 60, "head_pitch": 25, **HANDS_HEAD,
                                                               "l_leg_ik": [0.10, -0.80, -0.05], "r_leg_ik": [0.10, -0.80, -0.05]}),
                                                        (0.3, {})], back=0.9, flexibility="medium"),
        _f("side_bend", "Standing side bend", [(0.9, {"roll": -28, "l_upper_arm": "up+0.3in", "l_forearm": "in+0.6up",
                                                      "r_arm_ik": ([0.0, -0.42, 0.0], "out+0.4back"), **WIDE}),
                                               (0.5, {})], back=0.9, sub="mobility"),
        _f("torso_twist", "Torso twist", [(0.6, {"twist": 45, **ARMS_OUT, **WIDE}), (0.6, {"twist": -45}), (0.4, {"twist": 0})],
           sub="mobility", complexity=3),
        _f("windmill", "Windmill toe touch", [(0.6, {**ARMS_OUT, "l_leg_ik": [0.28, -0.78, 0.0], "r_leg_ik": [0.28, -0.78, 0.0]}),
                                              (0.8, {"pitch": 70, "twist": 45, "head_pitch": 20}),
                                              (0.6, {"pitch": 0, "twist": 0})], sub="mobility", flexibility="high", complexity=3),
        _f("arm_circles", "Big arm circles", [(0.35, {"l_upper_arm": "fwd", "l_forearm": "fwd", "r_upper_arm": "fwd", "r_forearm": "fwd"}),
                                              (0.35, ARMS_UP), (0.35, {"l_upper_arm": "back+0.3out", "l_forearm": "back+0.3out",
                                                                       "r_upper_arm": "back+0.3out", "r_forearm": "back+0.3out"}),
                                              (0.35, {"l_upper_arm": "down", "l_forearm": "down", "r_upper_arm": "down",
                                                      "r_forearm": "down"})], sub="mobility", complexity=3),
        _f("shoulder_press", "Shoulder press", [(0.5, {"l_upper_arm": "out", "l_forearm": "up", "r_upper_arm": "out",
                                                       "r_forearm": "up"}), (0.5, ARMS_UP), (0.5, {"l_upper_arm": "out",
                                                       "l_forearm": "up", "r_upper_arm": "out", "r_forearm": "up"})]),
        _f("lateral_raise", "Lateral raise", [(0.7, {**ARMS_OUT}), (0.3, {})]),
        _f("front_raise", "Front raise", [(0.7, {"l_upper_arm": "fwd", "l_forearm": "fwd", "r_upper_arm": "fwd", "r_forearm": "fwd"}),
                                          (0.3, {})]),
        _f("biceps_curl", "Biceps curl", [(0.6, {"l_forearm": "up+0.4fwd", "r_forearm": "up+0.4fwd"}), (0.2, {})]),
        _f("triceps_ext", "Overhead triceps extension", [(0.6, {"l_upper_arm": "up+0.1in", "l_forearm": "back+0.6down+0.2in",
                                                                "r_upper_arm": "up+0.1in", "r_forearm": "back+0.6down+0.2in"}),
                                                         (0.5, {"l_forearm": "up", "r_forearm": "up"}),
                                                         (0.5, {"l_forearm": "back+0.6down+0.2in", "r_forearm": "back+0.6down+0.2in"})],
           complexity=3),
        _f("upright_row", "Upright row", [(0.6, {"l_upper_arm": "out+0.1up", "l_forearm": "in+0.5down",
                                                 "r_upper_arm": "out+0.1up", "r_forearm": "in+0.5down"}), (0.2, {})]),
        _f("standing_crunch", "Standing cross crunch", [(0.6, {**HANDS_HEAD, "twist": 30, "pitch": 15,
                                                               "r_thigh": "fwd+0.3up+0.2in", "r_shin": "down+0.1back"}),
                                                        (0.2, {})], back=0.6, flexibility="medium"),
        _f("high_knees", "High knees (in place)", [
            (0.25, {"l_thigh": "fwd+0.1up", "l_shin": "down", "r_arm_ik": ([-0.05, 0.05, 0.25], "down+0.3out")}),
            (0.25, {"l_thigh": "down", "l_shin": "down", "r_thigh": "fwd+0.1up", "r_shin": "down", "r_arm_ik": ([0.05, -0.45, 0.0], "back+0.3out"),
                    "l_arm_ik": ([-0.05, 0.05, 0.25], "down+0.3out")}),
            (0.25, {"r_thigh": "down", "r_shin": "down", "l_thigh": "fwd+0.1up", "l_shin": "down",
                    "l_arm_ik": ([0.05, -0.45, 0.0], "back+0.3out"), "r_arm_ik": ([-0.05, 0.05, 0.25], "down+0.3out")})],
           sub="cardio", back=0.3, complexity=3, flexibility="medium"),
        _f("butt_kicks", "Butt kicks (in place)", [(0.25, {"l_shin": "up+0.4back"}), (0.25, {"l_shin": "down", "r_shin": "up+0.4back"}),
                                                    (0.25, {"r_shin": "down", "l_shin": "up+0.4back"})], sub="cardio", back=0.3,
           complexity=3),
        _f("hip_abduction", "Standing hip abduction", [(0.6, {"l_thigh": "down+0.6out", "l_shin": "down+0.6out", "roll": -8,
                                                              **HANDS_HIPS}), (0.3, {})], back=0.6),
        _f("step_jack", "Step jack", [(0.35, {"l_leg_ik": [0.35, -0.80, 0.0], **ARMS_UP}), (0.35, {"l_leg_ik": [0.08, -0.84, 0.0],
                                                                                                 "l_upper_arm": "down", "l_forearm": "down",
                                                                                                 "r_upper_arm": "down", "r_forearm": "down"}),
                                      (0.35, {"r_leg_ik": [0.35, -0.80, 0.0], **ARMS_UP})], sub="cardio", back=0.4, complexity=3),
        _f("wood_chop", "Wood chop (high to low)", [(0.6, {"twist": 35, "l_arm_ik": ([-0.30, 0.35, 0.25], "down+0.3out"),
                                                           "r_arm_ik": ([-0.05, 0.38, 0.25], "down+0.3out")}),
                                                    (0.6, {"twist": -35, "pitch": 30, "l_arm_ik": ([0.0, -0.50, 0.15], "down+0.3out"),
                                                           "r_arm_ik": ([-0.36, -0.45, 0.15], "down+0.3out"),
                                                           "l_leg_ik": [0.14, -0.66, 0.0], "r_leg_ik": [0.14, -0.66, 0.0]})],
           sub="strength", complexity=3, flexibility="medium"),
        _f("halo", "Halo", [(0.4, {"l_arm_ik": ([-0.25, 0.30, 0.05], "out+0.3fwd"), "r_arm_ik": ([-0.10, 0.32, 0.12], "out+0.3fwd")}),
                            (0.4, {"l_arm_ik": ([-0.12, 0.30, -0.12], "out+0.3fwd"), "r_arm_ik": ([-0.22, 0.30, -0.10], "out+0.3fwd")}),
                            (0.4, {"l_arm_ik": ([-0.10, 0.32, 0.12], "out+0.3fwd"), "r_arm_ik": ([-0.25, 0.30, 0.05], "out+0.3fwd")})],
           sub="mobility", complexity=3),
        _f("ytw", "Y-T-W raises", [(0.5, {"pitch": 40, "l_upper_arm": "up+0.6out+0.3fwd", "l_forearm": "up+0.6out+0.3fwd",
                                          "r_upper_arm": "up+0.6out+0.3fwd", "r_forearm": "up+0.6out+0.3fwd"}),
                                   (0.5, {"l_upper_arm": "out", "l_forearm": "out", "r_upper_arm": "out", "r_forearm": "out"}),
                                   (0.5, {"l_upper_arm": "out+0.4down+0.3back", "l_forearm": "up+0.6out",
                                          "r_upper_arm": "out+0.4down+0.3back", "r_forearm": "up+0.6out"})],
           sub="mobility", complexity=4),
        _f("calf_raise", "Calf raise", [(0.5, {"l_foot": "down+0.5fwd", "r_foot": "down+0.5fwd", **HANDS_HIPS}), (0.4, {})],
           back=0.5),
        _f("knee_hug", "Standing knee hug", [(0.6, {"l_thigh": "fwd+0.6up", "l_shin": "down+0.4back",
                                                    "l_arm_ik": ([-0.10, -0.40, 0.35], "out+0.3down"),
                                                    "r_arm_ik": ([-0.30, -0.40, 0.35], "out+0.3down")}), (0.6, {})],
           sub="mobility", back=0.6, flexibility="medium"),
        _f("quad_stretch", "Standing quad stretch", [(0.7, {"l_thigh": "down+0.1back", "l_shin": "up+0.15back",
                                                            "l_arm_ik": ([0.05, -0.62, -0.20], "out+0.3back"),
                                                            "r_upper_arm": "out+0.2up", "r_forearm": "out+0.2up"}), (0.8, {})],
           sub="mobility", back=0.7, flexibility="medium"),
    ]


COMBOS = [
    ["fit.squat", "fit.shoulder_press"], ["fit.lunge_fwd", "fit.torso_twist"], ["fit.biceps_curl", "fit.shoulder_press"],
    ["fit.lateral_raise", "fit.front_raise"], ["fit.reverse_lunge", "fit.knee_hug"], ["fit.step_jack", "fit.squat"],
    ["fit.high_knees", "fit.butt_kicks"], ["fit.side_bend", "fit.torso_twist"], ["fit.good_morning", "fit.calf_raise"],
    ["fit.wood_chop", "fit.halo"], ["fit.sumo_squat", "fit.upright_row"], ["fit.lateral_lunge", "fit.standing_crunch"],
    ["fit.arm_circles", "fit.ytw"], ["fit.squat", "fit.lunge_fwd", "fit.reverse_lunge"],
]
