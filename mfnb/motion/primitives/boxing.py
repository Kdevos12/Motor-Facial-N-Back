"""Boxing strikes and evasion/defense, orthodox stance (left side forward)."""
from __future__ import annotations

from .dsl import Primitive, seq, strike
from .homes import GUARD

LEAD_ARM_STRAIGHT = {"l_upper_arm": "@fwd+0.08up+0.06in", "l_forearm": "@fwd+0.06up+0.04in"}
REAR_ARM_STRAIGHT = {"r_upper_arm": "@fwd+0.08up+0.22in", "r_forearm": "@fwd+0.04up+0.14in"}
CROUCH = {"l_leg_ik": [0.06, -0.70, 0.24], "r_leg_ik": [0.10, -0.70, -0.24]}
DEEP = {"l_leg_ik": [0.08, -0.62, 0.24], "r_leg_ik": [0.12, -0.62, -0.24]}


def _b(id_, name, keys, sub="strikes", **kw):
    return Primitive(f"box.{id_}", name, "boxing", sub, keys, home="guard", stance_based=True, **kw)


def _e(id_, name, keys, **kw):
    return Primitive(f"evade.{id_}", name, "evasion", kw.pop("sub", "evasion"), keys, home="guard",
                     stance_based=True, **kw)


def primitives() -> list[Primitive]:
    g = GUARD
    p = [
        _b("jab", "Jab", strike(g, {"twist": -12, **LEAD_ARM_STRAIGHT}, t_in=0.18, hold=0.08, t_out=0.22)),
        _b("cross", "Cross", strike(g, {"twist": 45, "yaw": -12, "pitch": 8, **REAR_ARM_STRAIGHT},
                                    t_in=0.24, hold=0.1, t_out=0.3)),
        _b("lead_hook", "Lead hook", strike(g, {
            "twist": -30, "yaw": -18, "l_upper_arm": "out+0.25fwd+0.05down", "l_forearm": "in+0.35fwd"},
            t_in=0.26, hold=0.1, t_out=0.3)),
        _b("rear_hook", "Rear hook", strike(g, {
            "twist": 55, "yaw": -10, "r_upper_arm": "out+0.3fwd", "r_forearm": "in+0.3fwd"},
            t_in=0.3, hold=0.1, t_out=0.32)),
        _b("lead_uppercut", "Lead uppercut", strike(g, {
            "twist": -20, "pitch": 2, "l_upper_arm": "down+0.9fwd", "l_forearm": "up+0.45fwd+0.15in",
            **CROUCH}, t_in=0.28, hold=0.1, t_out=0.3)),
        _b("rear_uppercut", "Rear uppercut", strike(g, {
            "twist": 40, "pitch": 4, "r_upper_arm": "down+0.8fwd+0.2in", "r_forearm": "up+0.4fwd+0.2in",
            **CROUCH}, t_in=0.3, hold=0.1, t_out=0.32)),
        _b("lead_body_hook", "Lead hook to the body", strike(g, {
            "twist": -28, "pitch": 18, "roll": 8, "l_upper_arm": "out+0.4down+0.3fwd",
            "l_forearm": "in+0.45fwd+0.15down", **DEEP}, t_in=0.3, hold=0.1, t_out=0.34)),
        _b("rear_body_cross", "Cross to the body", strike(g, {
            "twist": 40, "pitch": 22, "r_upper_arm": "@fwd+0.35down+0.2in", "r_forearm": "@fwd+0.3down+0.1in",
            **DEEP}, t_in=0.3, hold=0.1, t_out=0.34)),
        _b("overhand", "Overhand", strike(g, {
            "twist": 50, "pitch": 18, "roll": 8, "r_upper_arm": "up+0.6fwd+0.3out",
            "r_forearm": "fwd+0.7down+0.3in"}, t_in=0.36, hold=0.1, t_out=0.36,
            chamber={"twist": 15, "r_upper_arm": "out+0.4up+0.2back", "r_forearm": "up+0.5fwd"},
            t_chamber=0.18), complexity=3),
        _b("lead_elbow", "Lead horizontal elbow", strike(g, {
            "twist": -35, "l_upper_arm": "out+0.4fwd+0.1up", "l_forearm": "in+0.15back"},
            t_in=0.24, hold=0.1, t_out=0.3), sub="elbows"),
        _b("rear_elbow", "Rear horizontal elbow", strike(g, {
            "twist": 55, "r_upper_arm": "out+0.45fwd+0.1up", "r_forearm": "in+0.15back"},
            t_in=0.26, hold=0.1, t_out=0.3), sub="elbows"),
        _b("rear_up_elbow", "Rear upward elbow", strike(g, {
            "twist": 35, "pitch": -5, "r_upper_arm": "up+0.5fwd+0.2in", "r_forearm": "down+0.3in+0.2back",
            **CROUCH}, t_in=0.28, hold=0.12, t_out=0.3), sub="elbows"),
        _b("lead_backfist", "Lead backfist", strike(g, {
            "twist": -15, "l_upper_arm": "@fwd+0.25up+0.05out", "l_forearm": "@fwd+0.45up"},
            t_in=0.2, hold=0.08, t_out=0.25,
            chamber={"l_upper_arm": "fwd+0.2in", "l_forearm": "in+0.5up"}, t_chamber=0.15)),
        _b("double_jab", "Double jab", seq(g, [
            (0.18, {"twist": -12, **LEAD_ARM_STRAIGHT}), (0.16, {"twist": -4,
             "l_upper_arm": "@fwd+0.3down", "l_forearm": "@fwd+0.4up"}),
            (0.16, {"twist": -12, **LEAD_ARM_STRAIGHT}), (0.08, {})], back=0.22), complexity=3),
        _b("rear_shovel", "Rear shovel hook", strike(g, {
            "twist": 40, "pitch": 10, "r_upper_arm": "down+0.6fwd+0.4out", "r_forearm": "up+0.6fwd+0.5in",
            **CROUCH}, t_in=0.3, hold=0.1, t_out=0.32)),
    ]
    e = [
        _e("slip_left", "Slip left", seq(g, [(0.22, {"roll": 16, "pitch": 12, "twist": -8, **CROUCH}),
                                             (0.12, {})], back=0.26)),
        _e("slip_right", "Slip right", seq(g, [(0.22, {"roll": -16, "pitch": 12, "twist": 18, **CROUCH}),
                                               (0.12, {})], back=0.26)),
        _e("roll_lr", "Roll under (left to right)", seq(g, [
            (0.2, {"roll": 14, "pitch": 14, **CROUCH}), (0.22, {"roll": 0, "pitch": 26, **DEEP}),
            (0.22, {"roll": -14, "pitch": 14, **CROUCH})], back=0.3), complexity=3),
        _e("roll_rl", "Roll under (right to left)", seq(g, [
            (0.2, {"roll": -14, "pitch": 14, **CROUCH}), (0.22, {"roll": 0, "pitch": 26, **DEEP}),
            (0.22, {"roll": 14, "pitch": 14, **CROUCH})], back=0.3), complexity=3),
        _e("pull_back", "Pull back", seq(g, [(0.22, {
            "pitch": -14, "yaw": -40, "l_leg_ik": [0.06, -0.83, 0.22], "r_leg_ik": [0.10, -0.74, -0.24]}),
            (0.15, {})], back=0.28)),
        _e("duck", "Duck", seq(g, [(0.25, {"pitch": 16, **DEEP}), (0.15, {})], back=0.3)),
        _e("shoulder_roll", "Shoulder roll", seq(g, [(0.24, {
            "twist": -38, "roll": -6, "pitch": 6,
            "l_arm_ik": ([0.02, -0.40, 0.18], "down+0.5out"),
            "r_arm_ik": ([-0.10, 0.12, 0.10], "down+0.3out")}), (0.15, {})], back=0.28)),
        _e("parry", "Rear hand parry", seq(g, [(0.15, {"r_arm_ik": ([-0.30, 0.10, 0.28], "down+0.3out")}),
                                               (0.08, {})], back=0.2), sub="blocks"),
        _e("catch", "Catch the jab", seq(g, [(0.15, {"r_arm_ik": ([-0.20, 0.16, 0.30], "down+0.3out")}),
                                             (0.1, {})], back=0.2), sub="blocks"),
        _e("high_guard", "High guard block", seq(g, [(0.2, {
            "pitch": 8, "head_pitch": -12,
            "l_arm_ik": ([-0.08, 0.32, 0.16], "down+0.6out"), "r_arm_ik": ([-0.10, 0.32, 0.14], "down+0.6out")}),
            (0.25, {})], back=0.25), sub="blocks"),
        _e("elbow_block", "Elbow block to the body", seq(g, [(0.2, {
            "pitch": 10, "roll": 6, "twist": -10, **CROUCH,
            "l_arm_ik": ([-0.02, -0.12, 0.16], "down"), "r_arm_ik": ([-0.10, 0.06, 0.12], "down+0.3out")}),
            (0.2, {})], back=0.25), sub="blocks"),
        _e("cross_guard", "Cross guard", seq(g, [(0.2, {
            "l_arm_ik": ([-0.30, 0.10, 0.25], "down+0.3out"), "r_arm_ik": ([-0.30, 0.04, 0.27], "down+0.3out")}),
            (0.2, {})], back=0.25), sub="blocks"),
        _e("step_back", "Step back (pendulum)", seq(g, [(0.2, {"z": -0.2, "pitch": 0}), (0.15, {})], back=0.25),
           sub="footwork"),
        _e("pivot", "Lead foot pivot", seq(g, [(0.3, {"yaw": -75, "twist": 10}), (0.15, {})], back=0.3),
           sub="footwork"),
        _e("lean_left", "Lean left (lateral)", seq(g, [(0.25, {"roll": 22, "x": 0.08, **CROUCH}), (0.12, {})],
                                                    back=0.25)),
        _e("lean_right", "Lean right (lateral)", seq(g, [(0.25, {"roll": -22, "x": -0.08, **CROUCH}),
                                                       (0.12, {})], back=0.25)),
    ]
    return p + e


# Classic boxing combos by primitive id, used by the composer.
COMBOS = [
    ["box.jab", "box.cross"], ["box.jab", "box.jab", "box.cross"], ["box.jab", "box.cross", "box.lead_hook"],
    ["box.jab", "box.cross", "box.lead_hook", "box.cross"], ["box.jab", "box.rear_uppercut", "box.lead_hook"],
    ["box.lead_hook", "box.cross"], ["box.cross", "box.lead_hook", "box.cross"],
    ["box.jab", "box.cross", "box.lead_body_hook"], ["box.jab", "box.rear_body_cross", "box.lead_hook"],
    ["box.lead_uppercut", "box.rear_hook"], ["box.jab", "evade.slip_right", "box.cross"],
    ["evade.slip_left", "box.cross"], ["evade.slip_right", "box.lead_hook"],
    ["evade.roll_lr", "box.lead_hook"], ["evade.roll_rl", "box.cross"],
    ["evade.pull_back", "box.cross"], ["evade.parry", "box.cross"], ["evade.catch", "box.jab", "box.cross"],
    ["box.jab", "box.cross", "evade.roll_lr", "box.cross"], ["evade.shoulder_roll", "box.cross"],
    ["box.double_jab", "box.cross"], ["box.jab", "box.overhand"], ["evade.duck", "box.rear_uppercut"],
    ["evade.high_guard", "box.lead_hook", "box.cross"], ["box.lead_elbow", "box.rear_elbow"],
    ["box.jab", "box.cross", "evade.slip_left", "box.cross"], ["evade.step_back", "box.cross"],
    ["evade.pivot", "box.cross"], ["evade.lean_left", "box.rear_hook"], ["evade.lean_right", "box.lead_hook"],
]
