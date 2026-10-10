"""Tai chi (Yang 24-form fragments, in place) and qigong (Ba Duan Jin)."""
from __future__ import annotations

from .dsl import Primitive, seq
from .homes import HORSE, WUJI

BOW_L = {"yaw": -15, "l_leg_ik": [0.10, -0.72, 0.30], "r_leg_ik": [0.14, -0.76, -0.25]}
BOW_R = {"yaw": 15, "r_leg_ik": [0.10, -0.72, 0.30], "l_leg_ik": [0.14, -0.76, -0.25]}
EMPTY_L = {"l_leg_ik": [0.06, -0.72, 0.28], "l_foot": "down+0.8fwd", "r_leg_ik": [0.12, -0.72, -0.05]}
CENTER = {"yaw": 0, "l_leg_ik": [0.12, -0.78, 0.0], "r_leg_ik": [0.12, -0.78, 0.0]}
HOLD_BALL_L = {"l_arm_ik": ([-0.15, 0.0, 0.30], "down+0.5out"), "r_arm_ik": ([-0.20, -0.35, 0.28], "down+0.5out")}
HOLD_BALL_R = {"r_arm_ik": ([-0.15, 0.0, 0.30], "down+0.5out"), "l_arm_ik": ([-0.20, -0.35, 0.28], "down+0.5out")}
SLOW = 1.0


def _tc(id_, name, steps, back=0.9, **kw):
    return Primitive(f"taichi.{id_}", name, "tai chi & qigong", kw.pop("sub", "tai chi"), seq(WUJI, steps, back=back),
                     home="wuji", **kw)


def _qg(id_, name, steps, home=WUJI, back=0.9, **kw):
    return Primitive(f"qigong.{id_}", name, "tai chi & qigong", "qigong (ba duan jin)", seq(home, steps, back=back),
                     home="wuji" if home is WUJI else "horse", **kw)


def primitives() -> list[Primitive]:
    return [
        _tc("commencement", "Commencement", [
            (1.0, {"l_arm_ik": ([0.0, -0.02, 0.50], "down+0.3out"), "r_arm_ik": ([0.0, -0.02, 0.50], "down+0.3out")}),
            (0.9, {"l_leg_ik": [0.12, -0.70, 0.0], "r_leg_ik": [0.12, -0.70, 0.0],
                   "l_arm_ik": ([0.0, -0.40, 0.30], "down+0.3out"), "r_arm_ik": ([0.0, -0.40, 0.30], "down+0.3out")})]),
        _tc("wild_horse_l", "Part the wild horse's mane (left)", [
            (0.8, {**HOLD_BALL_R, "yaw": 15}),
            (1.0, {**BOW_L, "twist": -10, "l_arm_ik": ([0.05, 0.12, 0.48], "down+0.4out"),
                   "r_arm_ik": ([0.10, -0.45, 0.10], "back+0.3out")})], stance_based=False, complexity=3),
        _tc("white_crane", "White crane spreads its wings", [
            (0.8, {**HOLD_BALL_R}),
            (1.0, {**EMPTY_L, "r_arm_ik": ([0.0, 0.40, 0.20], "out+0.3down"), "l_arm_ik": ([0.05, -0.48, 0.12], "back+0.3out")})],
            complexity=3),
        _tc("brush_knee_l", "Brush knee and push (left)", [
            (0.8, {"yaw": 25, "r_arm_ik": ([0.15, 0.10, -0.05], "down+0.4out"), "l_arm_ik": ([-0.25, 0.05, 0.25], "down+0.4out")}),
            (1.0, {**BOW_L, "l_arm_ik": ([0.12, -0.50, 0.15], "back+0.3out"), "r_arm_ik": ([-0.12, 0.05, 0.50], "down+0.4out")})],
            complexity=3),
        _tc("play_lute", "Play the lute (pi pa)", [
            (0.9, {**EMPTY_L, "yaw": -10, "l_arm_ik": ([-0.08, 0.10, 0.45], "down+0.4out"),
                   "r_arm_ik": ([-0.25, -0.12, 0.30], "down+0.4out")}), (0.8, {})]),
        _tc("repulse_monkey", "Repulse the monkey", [
            (0.9, {"yaw": 20, "r_arm_ik": ([0.20, 0.0, -0.20], "down+0.4out"), "l_arm_ik": ([-0.05, 0.0, 0.45], "down+0.4out")}),
            (1.0, {"yaw": 0, "r_arm_ik": ([-0.10, 0.05, 0.50], "down+0.4out"), "l_arm_ik": ([0.10, -0.45, 0.10], "back+0.3out"),
                   "l_leg_ik": [0.12, -0.74, -0.15], "r_leg_ik": [0.12, -0.76, 0.05]})], complexity=3),
        _tc("ward_off_l", "Grasp the bird's tail: ward off", [
            (0.8, {**HOLD_BALL_R}),
            (1.0, {**BOW_L, "l_arm_ik": ([-0.15, 0.0, 0.42], "out+0.4down"), "r_arm_ik": ([0.05, -0.45, 0.12], "back+0.3out")})]),
        _tc("roll_back", "Grasp the bird's tail: roll back", [
            (0.6, {**BOW_L, "l_arm_ik": ([-0.10, 0.05, 0.45], "down+0.4out"), "r_arm_ik": ([-0.20, -0.10, 0.40], "down+0.4out")}),
            (1.0, {"yaw": 30, "l_leg_ik": [0.10, -0.76, 0.20], "r_leg_ik": [0.14, -0.70, -0.22],
                   "l_arm_ik": ([-0.25, -0.10, 0.25], "down+0.4out"), "r_arm_ik": ([0.15, -0.20, 0.05], "down+0.4out")})],
            complexity=3),
        _tc("press", "Grasp the bird's tail: press", [
            (0.8, {"l_arm_ik": ([-0.20, -0.05, 0.25], "out+0.4down"), "r_arm_ik": ([-0.30, -0.05, 0.22], "down+0.4out")}),
            (0.9, {**BOW_L, "l_arm_ik": ([-0.20, -0.05, 0.45], "out+0.4down"), "r_arm_ik": ([-0.28, -0.05, 0.42], "down+0.4out")})]),
        _tc("push", "Grasp the bird's tail: push", [
            (0.8, {"l_leg_ik": [0.10, -0.76, 0.20], "r_leg_ik": [0.14, -0.70, -0.22],
                   "l_arm_ik": ([-0.10, -0.10, 0.22], "down+0.4out"), "r_arm_ik": ([-0.10, -0.10, 0.22], "down+0.4out")}),
            (1.0, {**BOW_L, "l_arm_ik": ([-0.10, 0.0, 0.48], "down+0.4out"), "r_arm_ik": ([-0.10, 0.0, 0.48], "down+0.4out")})]),
        _tc("single_whip", "Single whip", [
            (0.9, {"yaw": -40, "r_upper_arm": "out+0.6fwd", "r_forearm": "out+0.6fwd", "r_hand": "down+0.3fwd",
                   "l_arm_ik": ([-0.25, -0.20, 0.25], "down+0.4out")}),
            (1.0, {**BOW_L, "yaw": 30, "twist": 20, "l_arm_ik": ([0.0, 0.05, 0.48], "down+0.4out")})],
            complexity=3, flexibility="medium"),
        _tc("cloud_hands", "Wave hands like clouds", [
            (0.9, {"yaw": 30, "l_arm_ik": ([-0.25, 0.05, 0.35], "down+0.4out"), "r_arm_ik": ([-0.15, -0.35, 0.30], "down+0.4out")}),
            (0.9, {"yaw": -30, "r_arm_ik": ([-0.25, 0.05, 0.35], "down+0.4out"), "l_arm_ik": ([-0.15, -0.35, 0.30], "down+0.4out")}),
            (0.9, {"yaw": 30, "l_arm_ik": ([-0.25, 0.05, 0.35], "down+0.4out"), "r_arm_ik": ([-0.15, -0.35, 0.30], "down+0.4out")})],
            complexity=3),
        _tc("golden_rooster_l", "Golden rooster stands on one leg (left)", [
            (1.0, {"l_thigh": "fwd+0.15up", "l_shin": "down+0.1back", "l_foot": "down+0.5fwd",
                   "r_leg_ik": [0.10, -0.80, 0.0],
                   "l_arm_ik": ([-0.05, 0.10, 0.30], "down+0.3out"), "r_arm_ik": ([0.08, -0.45, 0.10], "back+0.3out")}),
            (0.8, {})], flexibility="medium"),
        _tc("high_pat", "High pat on horse", [
            (0.9, {**EMPTY_L, "r_arm_ik": ([-0.10, 0.15, 0.48], "down+0.4out"), "l_arm_ik": ([-0.12, -0.35, 0.25], "down+0.4out")}),
            (0.7, {})]),
        _tc("needle_sea", "Needle at the sea bottom", [
            (0.8, {"r_arm_ik": ([0.05, 0.10, 0.0], "down+0.3out")}),
            (1.0, {**EMPTY_L, "pitch": 35, "head_pitch": 15, "r_arm_ik": ([-0.12, -0.45, 0.25], "out+0.3back"),
                   "l_arm_ik": ([0.08, -0.45, 0.05], "back+0.3out")})], flexibility="medium"),
        _tc("fan_through_back", "Fan through the back", [
            (1.0, {**BOW_L, "r_arm_ik": ([0.05, 0.38, 0.20], "out+0.3down"), "l_arm_ik": ([-0.08, 0.0, 0.48], "down+0.4out")}),
            (0.7, {})]),
        _tc("shuttle_l", "Fair lady works the shuttles", [
            (0.8, {**HOLD_BALL_R}),
            (1.0, {**BOW_L, "l_arm_ik": ([-0.05, 0.40, 0.25], "out+0.3down"), "r_arm_ik": ([-0.10, 0.0, 0.48], "down+0.4out")})],
            complexity=3),
        _tc("cross_hands", "Cross hands", [
            (0.9, {"l_arm_ik": ([0.15, 0.30, 0.25], "down+0.4out"), "r_arm_ik": ([0.15, 0.30, 0.25], "down+0.4out")}),
            (1.0, {**CENTER, "l_arm_ik": ([-0.28, -0.05, 0.30], "down+0.4out"), "r_arm_ik": ([-0.24, -0.02, 0.32], "down+0.4out")})]),
        # Ba Duan Jin
        _qg("hold_heavens", "Two hands hold up the heavens", [
            (1.0, {"l_arm_ik": ([-0.15, -0.10, 0.35], "out+0.4down"), "r_arm_ik": ([-0.15, -0.10, 0.35], "out+0.4down")}),
            (1.0, {"l_upper_arm": "up+0.05in", "l_forearm": "up+0.1in", "l_hand": "in",
                   "r_upper_arm": "up+0.05in", "r_forearm": "up+0.1in", "r_hand": "in", "head_pitch": 20}),
            (0.8, {})], back=1.2),
        _qg("draw_bow_l", "Draw the bow (left)", [
            (0.8, {"l_leg_ik": ([0.28, -0.66, 0.0], "fwd+0.7out"), "r_leg_ik": ([0.28, -0.66, 0.0], "fwd+0.7out"),
                   "l_arm_ik": ([-0.30, 0.0, 0.30], "down+0.4out"), "r_arm_ik": ([-0.30, 0.0, 0.25], "down+0.4out")}),
            (1.0, {"head_yaw": 60, "l_upper_arm": "out+0.05up", "l_forearm": "out+0.1up", "l_hand": "up",
                   "r_upper_arm": "out+0.1up+0.2fwd", "r_forearm": "in+0.2fwd"}),
            (0.7, {})], back=1.0, flexibility="medium", complexity=3),
        _qg("separate_heaven_earth", "Separate heaven and earth", [
            (1.0, {"l_upper_arm": "up+0.1out", "l_forearm": "up", "l_hand": "in",
                   "r_arm_ik": ([0.05, -0.50, 0.08], "back+0.3out")}),
            (0.8, {}), (1.0, {"r_upper_arm": "up+0.1out", "r_forearm": "up", "r_hand": "in",
                              "l_arm_ik": ([0.05, -0.50, 0.08], "back+0.3out")})], back=1.0, complexity=3),
        _qg("owl_gazes_back", "Wise owl gazes backward", [
            (1.0, {"head_yaw": 70, "twist": 15, "l_upper_arm": "down+0.3out+0.2back", "r_upper_arm": "down+0.3out+0.2back"}),
            (0.6, {}), (1.0, {"head_yaw": 0, "twist": 0}),
            (1.0, {"head_yaw": -70, "twist": -15})], back=1.0, complexity=3),
        _qg("sway_head_tail", "Sway the head and shake the tail", [
            (1.0, {"pitch": 25, "roll": 20, "l_arm_ik": ([-0.10, -0.25, 0.15], "out+0.3down")}),
            (1.0, {"pitch": 35, "roll": -20}), (0.8, {"pitch": 0, "roll": 0})], home=HORSE, back=0.8,
            flexibility="medium", complexity=3),
        _qg("hold_feet", "Two hands hold the feet", [
            (1.0, {"l_upper_arm": "up", "l_forearm": "up", "r_upper_arm": "up", "r_forearm": "up"}),
            (1.4, {"pitch": 85, "head_pitch": 30, "l_upper_arm": "up+0.1fwd", "l_forearm": "up+0.1fwd",
                   "r_upper_arm": "up+0.1fwd", "r_forearm": "up+0.1fwd",
                   "l_leg_ik": [0.12, -0.84, 0.0], "r_leg_ik": [0.12, -0.84, 0.0]}),
            (0.5, {})], back=1.4, flexibility="high", complexity=3),
        _qg("angry_eyes_punch", "Punch with angry eyes", [
            (0.8, {"twist": -10, "l_upper_arm": "@fwd+0.1down+0.2in", "l_forearm": "@fwd+0.1down+0.2in"}),
            (0.6, {}), (0.8, {"twist": 10, "l_arm_ik": ([0.0, -0.40, 0.04], "back+0.3out"),
                              "r_upper_arm": "@fwd+0.1down+0.2in", "r_forearm": "@fwd+0.1down+0.2in"})],
            home=HORSE, back=0.8, flexibility="medium", complexity=3),
        _qg("bounce_toes", "Bouncing on the toes", [
            (0.7, {"l_foot": "down+0.6fwd", "r_foot": "down+0.6fwd", "head_pitch": 5}),
            (0.6, {}), (0.4, {"l_foot": "fwd+0.35down", "r_foot": "fwd+0.35down"})], back=0.4),
    ]


COMBOS = [
    ["taichi.commencement", "taichi.wild_horse_l"], ["taichi.wild_horse_l", "taichi.white_crane"],
    ["taichi.white_crane", "taichi.brush_knee_l"], ["taichi.brush_knee_l", "taichi.play_lute"],
    ["taichi.ward_off_l", "taichi.roll_back", "taichi.press", "taichi.push"],
    ["taichi.ward_off_l", "taichi.roll_back"], ["taichi.press", "taichi.push"],
    ["taichi.single_whip", "taichi.cloud_hands"], ["taichi.cloud_hands", "taichi.single_whip"],
    ["taichi.high_pat", "taichi.golden_rooster_l"], ["taichi.shuttle_l", "taichi.needle_sea", "taichi.fan_through_back"],
    ["taichi.repulse_monkey", "taichi.ward_off_l"], ["taichi.push", "taichi.cross_hands"],
    ["qigong.hold_heavens", "qigong.separate_heaven_earth"], ["qigong.draw_bow_l", "qigong.owl_gazes_back"],
    ["qigong.hold_feet", "qigong.bounce_toes"],
]
