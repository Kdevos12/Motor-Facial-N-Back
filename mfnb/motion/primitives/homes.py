"""Home poses shared by composable primitives (all full poses).

IK targets are side-relative [out, up, fwd] metres: arm targets are wrist offsets from the
shoulder (chest frame), leg targets are ankle offsets from the hip (pelvis frame).
"""
from __future__ import annotations

from .dsl import full

NEUTRAL = full({})

# Orthodox boxing / kickboxing guard: left side forward.
GUARD = full({
    "yaw": -30, "pitch": 5, "head_pitch": -5,
    "l_leg_ik": [0.06, -0.80, 0.22], "r_leg_ik": [0.10, -0.80, -0.24],
    "l_arm_ik": ([-0.10, 0.08, 0.30], "down+0.3out"),
    "r_arm_ik": ([-0.16, 0.14, 0.17], "down+0.3out"),
})

# Taekwondo sparring stance (kyorugi junbi): more side-on, hands lower.
TKD_STANCE = full({
    "yaw": -55, "pitch": 3,
    "l_leg_ik": [0.0, -0.80, 0.28], "r_leg_ik": [0.12, -0.80, -0.28],
    "l_arm_ik": ([-0.06, -0.08, 0.34], "down+0.3out"),
    "r_arm_ik": ([-0.14, -0.10, 0.20], "down+0.3out"),
})

# Taekwondo ready stance (naranhi seogi junbi): fists in front of the belt.
TKD_READY = full({
    "l_leg_ik": [0.12, -0.83, 0.0], "r_leg_ik": [0.12, -0.83, 0.0],
    "l_arm_ik": ([-0.08, -0.40, 0.17], "out+0.3down"),
    "r_arm_ik": ([-0.08, -0.40, 0.17], "out+0.3down"),
})

# Karate ready (yoi).
KARATE_YOI = full({
    "l_leg_ik": [0.12, -0.83, 0.0], "r_leg_ik": [0.12, -0.83, 0.0],
    "l_arm_ik": ([-0.04, -0.44, 0.12], "out+0.3down"),
    "r_arm_ik": ([-0.04, -0.44, 0.12], "out+0.3down"),
})

# Karate front stance (zenkutsu dachi), left forward, left fist forward, right fist at hip.
ZENKUTSU = full({
    "yaw": -10,
    "l_leg_ik": [0.06, -0.72, 0.42], "r_leg_ik": [0.10, -0.72, -0.44],
    "l_arm_ik": ([-0.12, -0.06, 0.42], "down+0.3out"),
    "r_arm_ik": ([0.0, -0.40, -0.04], "back+0.3out"),
})

# Wrestling stance: crouched, staggered, hands forward.
WRESTLE = full({
    "yaw": -20, "pitch": 30, "head_pitch": 22,
    "l_leg_ik": [0.12, -0.62, 0.25], "r_leg_ik": [0.14, -0.62, -0.25],
    "l_arm_ik": ([-0.08, -0.14, 0.38], "down+0.2out"),
    "r_arm_ik": ([-0.08, -0.18, 0.32], "down+0.2out"),
})

# Judo natural stance with grips (right-handed: right lapel, left sleeve).
JUDO = full({
    "yaw": 10,
    "l_leg_ik": [0.12, -0.82, -0.05], "r_leg_ik": [0.12, -0.82, 0.10],
    "l_arm_ik": ([0.04, -0.16, 0.40], "down+0.3out"),
    "r_arm_ik": ([-0.12, -0.02, 0.38], "down+0.3out"),
})

# Clinch / Thai plum position: both hands behind an imaginary neck.
CLINCH = full({
    "pitch": 10,
    "l_leg_ik": [0.10, -0.80, 0.10], "r_leg_ik": [0.10, -0.80, -0.10],
    "l_arm_ik": ([-0.16, 0.08, 0.40], "down+0.4out"),
    "r_arm_ik": ([-0.16, 0.08, 0.40], "down+0.4out"),
})

# Tai chi wuji: feet shoulder width, soft knees.
WUJI = full({
    "l_leg_ik": [0.12, -0.80, 0.0], "r_leg_ik": [0.12, -0.80, 0.0],
    "l_arm_ik": ([0.05, -0.50, 0.08], "back+0.3out"),
    "r_arm_ik": ([0.05, -0.50, 0.08], "back+0.3out"),
})

# Qigong horse stance with fists at the waist.
HORSE = full({
    "l_leg_ik": ([0.28, -0.68, 0.0], "fwd+0.7out"), "r_leg_ik": ([0.28, -0.68, 0.0], "fwd+0.7out"),
    "l_arm_ik": ([0.0, -0.40, 0.04], "back+0.3out"),
    "r_arm_ik": ([0.0, -0.40, 0.04], "back+0.3out"),
})

HOMES = {
    "neutral": NEUTRAL, "guard": GUARD, "tkd_stance": TKD_STANCE, "tkd_ready": TKD_READY,
    "karate_yoi": KARATE_YOI, "zenkutsu": ZENKUTSU, "wrestle": WRESTLE, "judo": JUDO,
    "clinch": CLINCH, "wuji": WUJI, "horse": HORSE,
}
