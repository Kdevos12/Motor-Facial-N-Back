"""Static postures (yoga, martial, gestures) and everyday / sports gestures."""
from __future__ import annotations

from .dsl import Primitive, posture, seq
from .homes import GUARD, NEUTRAL

HANDS_HIPS = {"l_arm_ik": ([0.0, -0.42, 0.0], "out+0.4back"), "r_arm_ik": ([0.0, -0.42, 0.0], "out+0.4back")}
PRAYER = {"l_arm_ik": ([-0.17, -0.12, 0.24], "down+0.5out"), "r_arm_ik": ([-0.17, -0.12, 0.24], "down+0.5out")}
ARMS_UP = {"l_upper_arm": "up+0.1out", "l_forearm": "up+0.1out", "r_upper_arm": "up+0.1out", "r_forearm": "up+0.1out"}
ARMS_OUT = {"l_upper_arm": "out", "l_forearm": "out", "r_upper_arm": "out", "r_forearm": "out"}


def _p(id_, name, pose, sub, flex="low", **kw):
    return Primitive(f"pose.{id_}", name, "static postures", sub, posture(pose), static=True, flexibility=flex, **kw)


def _ev(id_, name, steps, sub, back=0.45, home=NEUTRAL, **kw):
    return Primitive(f"daily.{id_}", name, "everyday & sports", sub, seq(home, steps, back=back),
                     home="neutral" if home is NEUTRAL else "guard", **kw)


def postures() -> list[Primitive]:
    return [
        _p("mountain", "Mountain pose", {**ARMS_UP, "head_pitch": 10}, "yoga"),
        _p("tree_l", "Tree pose (standing on right leg)", {"l_thigh": "down+0.5out+0.2fwd", "l_shin": "in+0.4down",
                                                           "r_leg_ik": [0.0, -0.84, 0.0], **PRAYER}, "yoga", "medium"),
        _p("warrior1_l", "Warrior I (left forward)", {"yaw": -10, "l_leg_ik": [0.10, -0.55, 0.45], "r_leg_ik": [0.12, -0.55, -0.55],
                                                      "pitch": -5, **ARMS_UP}, "yoga", "medium"),
        _p("warrior2_l", "Warrior II (left forward)", {"yaw": -80, "head_yaw": 75, "l_leg_ik": ([0.0, -0.55, 0.50], "fwd+0.3out"),
                                                       "r_leg_ik": ([0.20, -0.58, -0.50], "fwd+0.6out"),
                                                       "l_upper_arm": "@fwd", "l_forearm": "@fwd",
                                                       "r_upper_arm": "@back", "r_forearm": "@back"}, "yoga", "medium"),
        _p("triangle_l", "Triangle pose", {"yaw": -80, "roll": 55, "l_leg_ik": [0.0, -0.75, 0.45],
                                           "r_leg_ik": ([0.25, -0.75, -0.40], "fwd+0.6out"), "l_upper_arm": "down",
                                           "l_forearm": "down", "r_upper_arm": "up", "r_forearm": "up"}, "yoga", "high"),
        _p("chair", "Chair pose", {"pitch": 25, "l_leg_ik": [0.05, -0.55, 0.15], "r_leg_ik": [0.05, -0.55, 0.15], **ARMS_UP},
           "yoga", "medium"),
        _p("goddess", "Goddess pose", {"l_leg_ik": ([0.34, -0.58, 0.0], "fwd+0.8out"), "r_leg_ik": ([0.34, -0.58, 0.0], "fwd+0.8out"),
                                       "l_upper_arm": "out", "l_forearm": "up", "r_upper_arm": "out", "r_forearm": "up"},
           "yoga", "medium"),
        _p("star", "Star pose", {"l_leg_ik": [0.32, -0.78, 0.0], "r_leg_ik": [0.32, -0.78, 0.0],
                                 "l_upper_arm": "up+0.8out", "l_forearm": "up+0.8out",
                                 "r_upper_arm": "up+0.8out", "r_forearm": "up+0.8out"}, "yoga"),
        _p("warrior3_l", "Warrior III (on left leg)", {"pitch": 80, "head_pitch": 60, "r_thigh": "back+0.05up", "r_shin": "back+0.05up",
                                                       "r_foot": "down", "l_leg_ik": [0.0, -0.84, 0.0],
                                                       "l_upper_arm": "up", "l_forearm": "up", "r_upper_arm": "up", "r_forearm": "up"},
           "yoga", "high"),
        _p("dancer_l", "Dancer pose (on left leg)", {"pitch": 35, "r_thigh": "back+0.4up", "r_shin": "up+0.5back",
                                                     "r_arm_ik": ([0.0, -0.10, -0.55], "out+0.2down"), "l_upper_arm": "@fwd+0.4up",
                                                     "l_forearm": "@fwd+0.4up", "l_leg_ik": [0.0, -0.84, 0.0]}, "yoga", "high"),
        _p("crescent_lunge", "Crescent lunge", {"l_leg_ik": [0.10, -0.50, 0.45], "r_leg_ik": [0.12, -0.50, -0.62],
                                                "r_foot": "back+0.7down", **ARMS_UP}, "yoga", "high"),
        _p("eagle", "Eagle pose (arms and legs wrapped)", {"pitch": 10, "l_leg_ik": [-0.05, -0.62, 0.20],
                                                           "r_thigh": "fwd+0.5down+0.5in", "r_shin": "down+0.5in+0.2back",
                                                           "l_arm_ik": ([-0.25, 0.12, 0.30], "down"), "r_arm_ik": ([-0.20, 0.15, 0.30], "down")},
           "yoga", "high"),
        _p("t_pose", "T pose", {**ARMS_OUT}, "gestures"),
        _p("y_pose", "Y pose", {"l_upper_arm": "up+0.5out", "l_forearm": "up+0.5out", "r_upper_arm": "up+0.5out",
                                "r_forearm": "up+0.5out"}, "gestures"),
        _p("hands_hips", "Hands on hips", {**HANDS_HIPS}, "gestures"),
        _p("arms_crossed", "Arms crossed", {"l_arm_ik": ([-0.32, -0.25, 0.22], "down+0.3out"),
                                            "r_arm_ik": ([-0.30, -0.22, 0.26], "down+0.3out")}, "gestures"),
        _p("superhero", "Superhero stance", {"l_leg_ik": [0.25, -0.82, 0.0], "r_leg_ik": [0.25, -0.82, 0.0], **HANDS_HIPS,
                                             "head_pitch": 10}, "gestures"),
        _p("thinker", "The thinker (standing)", {"l_arm_ik": ([-0.15, 0.10, 0.14], "down"), "r_arm_ik": ([-0.25, -0.25, 0.22], "down+0.3out"),
                                                 "head_pitch": -10}, "gestures"),
        _p("double_biceps", "Double biceps", {"l_upper_arm": "out+0.1up", "l_forearm": "up+0.2in",
                                              "r_upper_arm": "out+0.1up", "r_forearm": "up+0.2in"}, "gestures"),
        _p("archer", "Archer pose", {"yaw": -80, "head_yaw": 75, "l_upper_arm": "@fwd+0.05up", "l_forearm": "@fwd+0.05up",
                                     "r_upper_arm": "@fwd", "r_forearm": "@back", "l_leg_ik": [0.0, -0.80, 0.30],
                                     "r_leg_ik": [0.15, -0.80, -0.25]}, "gestures"),
        _p("liberty", "Statue of Liberty", {"r_upper_arm": "up+0.1out", "r_forearm": "up", "l_arm_ik": ([-0.25, -0.15, 0.20], "down+0.3out")},
           "gestures"),
        _p("stop_sign", "Stop sign", {"r_upper_arm": "@fwd", "r_forearm": "@fwd+0.1up", "r_hand": "up"}, "gestures"),
        _p("flamingo_l", "Flamingo (on left leg)", {"r_thigh": "down+0.1fwd", "r_shin": "back+0.9up",
                                                    "l_leg_ik": [0.0, -0.84, 0.0], **ARMS_OUT},
           "balance", "medium"),
        _p("knee_up_hold", "Knee up hold (on left leg)", {"r_thigh": "fwd+0.1up", "r_shin": "down", "l_leg_ik": [0.0, -0.84, 0.0],
                                                          **HANDS_HIPS}, "balance"),
        _p("airplane", "Airplane (on left leg)", {"pitch": 60, "head_pitch": 45, "r_thigh": "back+0.5up", "r_shin": "back+0.5up",
                                                  "l_leg_ik": [0.0, -0.84, 0.0], **ARMS_OUT}, "balance", "high"),
        _p("guard_hold", "Fighting guard (hold)", GUARD, "martial", stance_based=True),
        _p("crane_kungfu", "Kung fu crane stance", {"r_thigh": "fwd+0.2up", "r_shin": "down+0.1back", "l_leg_ik": [0.0, -0.80, 0.0],
                                                    "r_upper_arm": "up+0.4out", "r_forearm": "up+0.3out", "r_hand": "down+0.3fwd",
                                                    "l_upper_arm": "out+0.2down", "l_forearm": "out", "l_hand": "down"},
           "martial", "medium"),
        _p("tiger_claw", "Tiger claw stance", {"yaw": -20, "l_leg_ik": [0.08, -0.62, 0.35], "r_leg_ik": [0.14, -0.62, -0.35],
                                               "l_arm_ik": ([-0.05, 0.10, 0.42], "down+0.3out"), "l_hand": "@fwd+0.4up",
                                               "r_arm_ik": ([-0.05, -0.30, 0.30], "down+0.3out"), "r_hand": "@fwd+0.4down"},
           "martial", "medium"),
        _p("cat_stance", "Cat stance (neko ashi dachi)", {"yaw": -30, "l_leg_ik": [0.04, -0.66, 0.28], "l_foot": "down+0.6fwd",
                                                          "r_leg_ik": [0.10, -0.68, -0.08],
                                                          "l_arm_ik": ([-0.06, 0.0, 0.40], "down+0.3out"),
                                                          "r_arm_ik": ([-0.16, -0.20, 0.22], "down+0.3out")}, "martial"),
        _p("prayer", "Prayer hands", {**PRAYER}, "gestures"),
    ]


def gestures() -> list[Primitive]:
    return [
        _ev("wave", "Wave hello", [(0.3, {"r_upper_arm": "out+0.6up", "r_forearm": "up+0.3in"}),
                                   (0.25, {"r_forearm": "up+0.4out"}), (0.25, {"r_forearm": "up+0.3in"}),
                                   (0.25, {"r_forearm": "up+0.4out"})], "gestures", complexity=3),
        _ev("salute", "Military salute", [(0.35, {"r_arm_ik": ([-0.12, 0.25, 0.08], "out"), "head_pitch": 5}), (0.5, {})], "gestures"),
        _ev("point_forward", "Point forward", [(0.3, {"r_upper_arm": "@fwd+0.1in", "r_forearm": "@fwd+0.1in"}), (0.4, {})], "gestures"),
        _ev("come_here", "Beckon (come here)", [(0.3, {"r_upper_arm": "@fwd+0.3down", "r_forearm": "@fwd+0.2up", "r_hand": "up+0.3fwd"}),
                                                (0.2, {"r_forearm": "up+0.4back", "r_hand": "back"}),
                                                (0.2, {"r_forearm": "@fwd+0.2up", "r_hand": "up+0.3fwd"}),
                                                (0.2, {"r_forearm": "up+0.4back", "r_hand": "back"})], "gestures", complexity=3),
        _ev("shrug", "Shrug", [(0.35, {"head_pitch": -5, "l_upper_arm": "down+0.3out", "l_forearm": "out+0.6fwd",
                                       "r_upper_arm": "down+0.3out", "r_forearm": "out+0.6fwd", "head_roll": 10}), (0.4, {})],
            "gestures"),
        _ev("facepalm", "Facepalm", [(0.35, {"r_arm_ik": ([-0.18, 0.16, 0.12], "down+0.2out"), "head_pitch": -15}), (0.5, {})],
            "gestures"),
        _ev("scratch_head", "Scratch head", [(0.35, {"r_arm_ik": ([-0.10, 0.30, 0.0], "out+0.3fwd"), "head_roll": -8}),
                                             (0.2, {"r_arm_ik": ([-0.13, 0.30, 0.02], "out+0.3fwd")}),
                                             (0.2, {"r_arm_ik": ([-0.10, 0.30, 0.0], "out+0.3fwd")})], "gestures"),
        _ev("check_watch", "Check your watch", [(0.35, {"l_arm_ik": ([-0.15, -0.10, 0.30], "down+0.3out"), "head_pitch": -20}),
                                                (0.5, {})], "gestures"),
        _ev("phone_call", "Phone call", [(0.4, {"r_arm_ik": ([-0.07, 0.18, 0.0], "down+0.3fwd"), "head_roll": -10}), (0.6, {})],
            "gestures"),
        _ev("drink", "Drink from a glass", [(0.4, {"r_arm_ik": ([-0.12, 0.05, 0.28], "down+0.3out")}),
                                            (0.4, {"r_arm_ik": ([-0.15, 0.14, 0.12], "down+0.3out"), "head_pitch": 25}),
                                            (0.3, {"head_pitch": 0, "r_arm_ik": ([-0.12, 0.05, 0.28], "down+0.3out")})],
            "gestures", complexity=3),
        _ev("clap", "Clap above the head", [(0.3, {"l_arm_ik": ([-0.15, 0.48, 0.10], "out"), "r_arm_ik": ([-0.15, 0.48, 0.10], "out")}),
                                            (0.15, {"l_arm_ik": ([-0.05, 0.45, 0.10], "out"), "r_arm_ik": ([-0.05, 0.45, 0.10], "out")}),
                                            (0.15, {"l_arm_ik": ([-0.15, 0.48, 0.10], "out"), "r_arm_ik": ([-0.15, 0.48, 0.10], "out")})],
            "gestures"),
        _ev("bow", "Bow", [(0.6, {"pitch": 40, "head_pitch": -10}), (0.4, {})], "gestures", back=0.6),
        _ev("look_around", "Look around", [(0.5, {"head_yaw": 70, "twist": 15}), (0.6, {"head_yaw": -70, "twist": -15}),
                                           (0.4, {"head_yaw": 0, "twist": 0})], "gestures", complexity=3),
        _ev("stretch_yawn", "Stretch and yawn", [(0.6, {"l_upper_arm": "up+0.3out", "l_forearm": "up+0.3out",
                                                        "r_upper_arm": "up+0.3out", "r_forearm": "up+0.3out", "pitch": -8,
                                                        "head_pitch": 20}), (0.6, {})], "gestures", back=0.6),
        # Sports
        _ev("golf_swing", "Golf swing", [
            (0.2, {"pitch": 30, "l_leg_ik": [0.16, -0.76, 0.0], "r_leg_ik": [0.16, -0.76, 0.0],
                   "l_arm_ik": ([-0.12, -0.50, 0.15], "out+0.3back"), "r_arm_ik": ([-0.16, -0.48, 0.15], "out+0.3back")}),
            (0.6, {"twist": 70, "l_arm_ik": ([-0.38, 0.10, 0.12], "down"), "r_arm_ik": ([-0.10, 0.18, 0.05], "down")}),
            (0.3, {"twist": -60, "pitch": 15, "l_arm_ik": ([-0.05, 0.20, 0.10], "down"), "r_arm_ik": ([-0.38, 0.12, 0.12], "down")})],
            "sports", back=0.6, complexity=4, flexibility="medium"),
        _ev("tennis_forehand", "Tennis forehand", [
            (0.4, {"twist": 45, "r_upper_arm": "out+0.3back+0.1down", "r_forearm": "out+0.4back"}),
            (0.3, {"twist": -40, "r_upper_arm": "@fwd+0.4in+0.1up", "r_forearm": "@in+0.4up+0.3fwd"})], "sports", complexity=3),
        _ev("tennis_backhand", "Tennis backhand (two hands)", [
            (0.4, {"twist": -50, "l_arm_ik": ([0.10, -0.25, -0.10], "down+0.3out"), "r_arm_ik": ([-0.35, -0.25, 0.0], "down+0.3out")}),
            (0.3, {"twist": 45, "l_arm_ik": ([-0.35, 0.10, 0.20], "down+0.3out"), "r_arm_ik": ([0.05, 0.15, 0.30], "down+0.3out")})],
            "sports", complexity=3),
        _ev("tennis_serve", "Tennis serve", [
            (0.4, {"l_upper_arm": "up+0.2fwd", "l_forearm": "up", "r_upper_arm": "out+0.3up", "r_forearm": "back+0.5down", "pitch": -10}),
            (0.3, {"r_upper_arm": "up+0.3fwd", "r_forearm": "up+0.4fwd", "l_upper_arm": "down+0.3in", "l_forearm": "down", "pitch": 15})],
            "sports", complexity=3),
        _ev("baseball_swing", "Baseball swing", [
            (0.4, {"twist": 50, "l_arm_ik": ([-0.30, 0.15, 0.10], "down"), "r_arm_ik": ([-0.05, 0.20, 0.05], "down"),
                   "l_leg_ik": [0.16, -0.76, 0.0], "r_leg_ik": [0.16, -0.76, 0.0]}),
            (0.25, {"twist": -50, "l_arm_ik": ([0.10, 0.05, 0.35], "down+0.3out"), "r_arm_ik": ([-0.30, 0.05, 0.30], "down+0.3out")})],
            "sports", complexity=3),
        _ev("baseball_pitch", "Baseball pitch (no step)", [
            (0.4, {"l_thigh": "fwd+0.2up", "l_shin": "down", "twist": 30, "r_upper_arm": "down+0.4back"}),
            (0.3, {"l_thigh": "down+0.3fwd", "l_shin": "down", "r_upper_arm": "out+0.3up+0.3back", "r_forearm": "up+0.4back"}),
            (0.25, {"twist": -40, "pitch": 25, "r_upper_arm": "@fwd+0.3down+0.2in", "r_forearm": "@fwd+0.5down+0.4in"})],
            "sports", complexity=4, flexibility="medium"),
        _ev("basketball_shot", "Basketball shot", [
            (0.4, {"l_leg_ik": [0.10, -0.66, 0.05], "r_leg_ik": [0.10, -0.66, 0.05], "r_arm_ik": ([-0.10, 0.20, 0.10], "down"),
                   "l_arm_ik": ([-0.20, 0.20, 0.15], "down+0.3out")}),
            (0.3, {**{"l_leg_ik": [0.10, -0.84, 0.0], "r_leg_ik": [0.10, -0.84, 0.0]}, "r_upper_arm": "up+0.4fwd",
                   "r_forearm": "up+0.5fwd", "r_hand": "fwd+0.3down"})], "sports", complexity=3),
        _ev("volleyball_set", "Volleyball set", [
            (0.4, {"l_arm_ik": ([-0.12, 0.30, 0.10], "out+0.3down"), "r_arm_ik": ([-0.12, 0.30, 0.10], "out+0.3down"),
                   "l_leg_ik": [0.12, -0.70, 0.0], "r_leg_ik": [0.12, -0.70, 0.0]}),
            (0.3, {"l_arm_ik": ([-0.10, 0.52, 0.05], "out"), "r_arm_ik": ([-0.10, 0.52, 0.05], "out"),
                   "l_leg_ik": [0.12, -0.84, 0.0], "r_leg_ik": [0.12, -0.84, 0.0]})], "sports", complexity=3),
        _ev("volleyball_dig", "Volleyball dig", [
            (0.4, {"pitch": 25, "l_leg_ik": [0.20, -0.60, 0.05], "r_leg_ik": [0.20, -0.60, 0.05],
                   "l_arm_ik": ([-0.18, -0.38, 0.38], "out+0.3down"), "r_arm_ik": ([-0.18, -0.38, 0.38], "out+0.3down")}),
            (0.25, {"l_arm_ik": ([-0.18, -0.15, 0.48], "out+0.3down"), "r_arm_ik": ([-0.18, -0.15, 0.48], "out+0.3down")})],
            "sports", complexity=3, flexibility="medium"),
        _ev("archery", "Archery draw", [
            (0.5, {"yaw": -70, "head_yaw": 65, "l_upper_arm": "@fwd+0.05up", "l_forearm": "@fwd+0.05up",
                   "r_upper_arm": "@fwd+0.05up", "r_forearm": "@fwd"}),
            (0.6, {"r_forearm": "@back+0.1in"}), (0.3, {"r_upper_arm": "@back+0.2out", "r_forearm": "@back+0.2out"})],
            "sports", complexity=3),
        _ev("fishing_cast", "Fishing cast", [
            (0.4, {"r_upper_arm": "fwd+0.3up+0.2out", "r_forearm": "up+0.3back"}),
            (0.3, {"r_upper_arm": "@fwd+0.2up", "r_forearm": "@fwd+0.1up", "pitch": 8})], "sports"),
        _ev("axe_chop", "Axe chop", [
            (0.5, {"l_arm_ik": ([-0.15, 0.45, 0.05], "out"), "r_arm_ik": ([-0.10, 0.48, 0.05], "out"), "pitch": -5}),
            (0.3, {"pitch": 40, "l_arm_ik": ([-0.15, -0.45, 0.30], "out+0.3down"), "r_arm_ik": ([-0.10, -0.40, 0.35], "out+0.3down"),
                   "l_leg_ik": [0.18, -0.70, 0.0], "r_leg_ik": [0.18, -0.70, 0.0]})], "sports", back=0.5, complexity=3),
        _ev("bowling", "Bowling (short step)", [
            (0.4, {"r_upper_arm": "back+0.4down", "r_forearm": "back+0.3down", "pitch": 10}),
            (0.4, {"z": 0.15, "pitch": 30, "l_leg_ik": [0.05, -0.62, 0.30], "r_leg_ik": [-0.05, -0.62, -0.35],
                   "r_upper_arm": "@fwd+0.4down", "r_forearm": "@fwd+0.2down", "l_upper_arm": "out+0.3down"})],
            "sports", back=0.6, complexity=3, flexibility="medium"),
        _ev("drumming", "Drumming", [
            (0.2, {"l_arm_ik": ([-0.10, -0.20, 0.30], "down+0.3out"), "r_arm_ik": ([-0.10, 0.05, 0.25], "down+0.3out")}),
            (0.2, {"l_arm_ik": ([-0.10, 0.05, 0.25], "down+0.3out"), "r_arm_ik": ([-0.10, -0.20, 0.30], "down+0.3out")}),
            (0.2, {"l_arm_ik": ([-0.10, -0.20, 0.30], "down+0.3out"), "r_arm_ik": ([-0.10, 0.05, 0.25], "down+0.3out")})],
            "gestures", complexity=3),
    ]


def primitives() -> list[Primitive]:
    return postures() + gestures()


COMBOS = [
    ["daily.wave", "daily.salute"], ["daily.point_forward", "daily.come_here"], ["daily.shrug", "daily.facepalm"],
    ["daily.check_watch", "daily.phone_call"], ["daily.drink", "daily.stretch_yawn"], ["daily.bow", "daily.wave"],
    ["daily.golf_swing", "daily.clap"], ["daily.tennis_forehand", "daily.tennis_backhand"],
    ["daily.tennis_serve", "daily.tennis_forehand"], ["daily.basketball_shot", "daily.clap"],
    ["daily.volleyball_dig", "daily.volleyball_set"], ["daily.baseball_swing", "daily.point_forward"],
    ["daily.archery", "daily.look_around"], ["daily.axe_chop", "daily.stretch_yawn"], ["daily.fishing_cast", "daily.scratch_head"],
]
