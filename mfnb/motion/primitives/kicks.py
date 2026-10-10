"""Kicks and knees from the orthodox guard. Low and mid height only, no spinning kicks."""
from __future__ import annotations

from .dsl import Primitive, seq
from .homes import GUARD

ARMS_TIGHT = {"l_arm_ik": ([-0.12, 0.10, 0.26], "down+0.3out"), "r_arm_ik": ([-0.16, 0.14, 0.15], "down+0.3out")}
REAR_ARM_SWING = {"r_upper_arm": "down+0.4back+0.2out", "r_forearm": "down+0.3back"}
LEAD_ARM_SWING = {"l_upper_arm": "down+0.4back+0.2out", "l_forearm": "down+0.3back"}


def _k(id_, name, steps, flex="low", sub="kicks", back=0.35, **kw):
    return Primitive(f"kick.{id_}", name, "kicks", sub, seq(GUARD, steps, back=back), home="guard",
                     flexibility=flex, stance_based=True, **kw)


def primitives() -> list[Primitive]:
    return [
        _k("rear_low_round", "Rear low roundhouse (leg kick)", [
            (0.22, {"yaw": 5, "r_thigh": "@0.5fwd+0.6out+0.5down", "r_shin": "@back+0.8down+0.2out"}),
            (0.2, {"yaw": 55, "pitch": -8, "roll": 6, "r_thigh": "@fwd+0.45down+0.25in", "r_shin": "@fwd+0.55down+0.2in",
                   **REAR_ARM_SWING}),
            (0.1, {}), (0.22, {"yaw": 5, "r_thigh": "@0.5fwd+0.6out+0.5down", "r_shin": "@back+0.8down+0.2out",
                               **ARMS_TIGHT})], flex="low", complexity=3),
        _k("rear_mid_round", "Rear body roundhouse", [
            (0.22, {"yaw": 10, "r_thigh": "@0.5fwd+0.7out+0.2down", "r_shin": "@back+0.6down+0.2out"}),
            (0.2, {"yaw": 70, "pitch": -14, "roll": 12, "r_thigh": "@fwd+0.1down+0.25in", "r_shin": "@fwd+0.05up+0.2in",
                   **REAR_ARM_SWING}),
            (0.1, {}), (0.22, {"yaw": 10, "r_thigh": "@0.5fwd+0.7out+0.2down", "r_shin": "@back+0.6down+0.2out",
                               **ARMS_TIGHT})], flex="medium", complexity=3),
        _k("lead_low_round", "Lead low roundhouse", [
            (0.2, {"yaw": -50, "l_thigh": "@0.4fwd+0.7out+0.5down", "l_shin": "@back+0.8down"}),
            (0.2, {"yaw": -95, "pitch": -8, "roll": -6, "l_thigh": "@fwd+0.45down+0.3in", "l_shin": "@fwd+0.55down+0.25in",
                   **LEAD_ARM_SWING}),
            (0.1, {}), (0.2, {"yaw": -50, "l_thigh": "@0.4fwd+0.7out+0.5down", "l_shin": "@back+0.8down"})],
           flex="low", complexity=3),
        _k("lead_teep", "Lead teep (push kick)", [
            (0.2, {"l_thigh": "@fwd+0.2up", "l_shin": "@down+0.2fwd", **ARMS_TIGHT}),
            (0.18, {"pitch": -14, "l_thigh": "@fwd+0.15down", "l_shin": "@fwd+0.1up"}),
            (0.1, {}), (0.18, {"pitch": 0, "l_thigh": "@fwd+0.2up", "l_shin": "@down+0.2fwd"})], flex="low"),
        _k("rear_teep", "Rear teep (push kick)", [
            (0.22, {"yaw": -5, "r_thigh": "@fwd+0.25up", "r_shin": "@down+0.1fwd", **ARMS_TIGHT}),
            (0.18, {"pitch": -14, "r_thigh": "@fwd+0.1down", "r_shin": "@fwd+0.12up"}),
            (0.1, {}), (0.2, {"pitch": 0, "r_thigh": "@fwd+0.25up", "r_shin": "@down+0.1fwd"})], flex="low"),
        _k("rear_front_kick", "Rear front snap kick", [
            (0.2, {"yaw": -10, "r_thigh": "@fwd+0.35up", "r_shin": "@down+0.15back", **ARMS_TIGHT}),
            (0.14, {"pitch": -6, "r_thigh": "@fwd+0.25up", "r_shin": "@fwd+0.05up", "r_foot": "@fwd+0.3up"}),
            (0.06, {}), (0.16, {"pitch": 0, "r_thigh": "@fwd+0.35up", "r_shin": "@down+0.15back"})], flex="medium"),
        _k("lead_side_kick", "Lead low side kick", [
            (0.22, {"yaw": -85, "l_thigh": "@fwd+0.1up+0.2in", "l_shin": "@down+0.3back", **ARMS_TIGHT}),
            (0.18, {"roll": 18, "l_thigh": "@fwd+0.35down", "l_shin": "@fwd+0.3down", "l_foot": "@0.5in+down"}),
            (0.1, {}), (0.2, {"roll": 0, "l_thigh": "@fwd+0.1up+0.2in", "l_shin": "@down+0.3back"})],
           flex="medium", complexity=3),
        _k("rear_knee", "Rear straight knee", [
            (0.25, {"yaw": -10, "pitch": -6, "r_thigh": "@fwd+0.45up", "r_shin": "@down+0.35back",
                    "l_arm_ik": ([-0.14, -0.18, 0.40], "down+0.3out"), "r_arm_ik": ([-0.14, -0.18, 0.40], "down+0.3out")}),
            (0.12, {})], back=0.3, sub="knees"),
        _k("lead_knee", "Lead straight knee", [
            (0.25, {"yaw": -35, "pitch": -6, "l_thigh": "@fwd+0.45up", "l_shin": "@down+0.35back",
                    "l_arm_ik": ([-0.14, -0.18, 0.40], "down+0.3out"), "r_arm_ik": ([-0.14, -0.18, 0.40], "down+0.3out")}),
            (0.12, {})], back=0.3, sub="knees"),
        _k("rear_side_knee", "Rear diagonal knee", [
            (0.28, {"yaw": 30, "pitch": -4, "roll": 8, "r_thigh": "@fwd+0.35up+0.35out", "r_shin": "@down+0.3back+0.3in",
                    "l_arm_ik": ([-0.10, 0.0, 0.40], "down+0.3out"), "r_arm_ik": ([-0.20, 0.0, 0.36], "down+0.3out")}),
            (0.12, {})], back=0.3, sub="knees", flex="medium"),
        _k("lead_check", "Lead leg check", [
            (0.2, {"yaw": -45, "l_thigh": "@0.8fwd+0.3up+0.5out", "l_shin": "@down+0.1fwd", **ARMS_TIGHT}),
            (0.25, {})], back=0.25, sub="defense"),
        _k("lead_oblique", "Lead oblique kick (stomp)", [
            (0.2, {"yaw": -60, "l_thigh": "@fwd+0.25up", "l_shin": "@down+0.2back", **ARMS_TIGHT}),
            (0.16, {"pitch": -10, "l_thigh": "@fwd+0.55down", "l_shin": "@fwd+0.75down", "l_foot": "@out+0.3down"}),
            (0.1, {}), (0.2, {"pitch": 0, "l_thigh": "@fwd+0.25up", "l_shin": "@down+0.2back"})]),
        _k("switch_kick", "Switch kick (body)", [
            (0.18, {"yaw": 0, "l_leg_ik": [0.10, -0.80, -0.22], "r_leg_ik": [0.06, -0.80, 0.22]}),
            (0.2, {"yaw": -10, "l_thigh": "@0.4fwd+0.7out+0.2down", "l_shin": "@back+0.6down"}),
            (0.2, {"yaw": -95, "pitch": -12, "roll": -10, "l_thigh": "@fwd+0.1down+0.25in", "l_shin": "@fwd+0.05up+0.2in",
                   **LEAD_ARM_SWING}),
            (0.1, {}), (0.22, {"yaw": -30, "l_thigh": "@0.4fwd+0.7out+0.2down", "l_shin": "@back+0.6down"})],
           flex="medium", complexity=4),
        _k("knee_lift", "Knee lift (balance)", [
            (0.35, {"l_thigh": "fwd+0.1up", "l_shin": "down", **ARMS_TIGHT}), (0.6, {})], back=0.35, sub="knees"),
    ]


COMBOS = [
    ["box.jab", "box.cross", "kick.rear_low_round"], ["box.jab", "kick.rear_mid_round"],
    ["kick.lead_teep", "box.cross"], ["box.jab", "box.cross", "kick.lead_knee"],
    ["kick.lead_check", "box.cross"], ["box.cross", "box.lead_hook", "kick.rear_low_round"],
    ["kick.lead_teep", "box.jab", "box.cross"], ["box.jab", "kick.rear_knee"],
    ["kick.switch_kick", "box.cross"], ["kick.lead_oblique", "box.cross", "box.lead_hook"],
    ["box.jab", "box.rear_uppercut", "kick.lead_knee"], ["evade.slip_right", "box.lead_hook", "kick.rear_low_round"],
    ["kick.rear_teep", "box.jab"], ["box.lead_hook", "kick.rear_mid_round"], ["kick.lead_low_round", "box.cross"],
    ["box.jab", "box.cross", "kick.lead_side_kick"], ["kick.rear_front_kick", "box.cross"],
]
