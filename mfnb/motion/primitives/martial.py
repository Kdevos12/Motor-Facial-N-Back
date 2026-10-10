"""Taekwondo and karate basics, adapted to a 2-3 m^2 space (techniques done in place)."""
from __future__ import annotations

from .dsl import Primitive, full, posture, seq, strike
from .homes import KARATE_YOI, TKD_READY, TKD_STANCE, ZENKUTSU

# Stances (left foot forward where asymmetric).
AP_SEOGI = {"yaw": -5, "l_leg_ik": [0.08, -0.82, 0.22], "r_leg_ik": [0.10, -0.82, -0.22]}
AP_KUBI = {"yaw": -8, "l_leg_ik": [0.08, -0.70, 0.40], "r_leg_ik": [0.12, -0.70, -0.46]}
DWIT_KUBI = {"yaw": -70, "l_leg_ik": [0.0, -0.76, 0.32], "r_leg_ik": ([0.12, -0.70, -0.12], "fwd+0.6out")}
JUCHUM = {"l_leg_ik": ([0.30, -0.66, 0.0], "fwd+0.7out"), "r_leg_ik": ([0.30, -0.66, 0.0], "fwd+0.7out")}
BEOM = {"yaw": -30, "l_leg_ik": [0.04, -0.66, 0.28], "l_foot": "down+0.6fwd", "r_leg_ik": [0.10, -0.68, -0.08]}
HIP_FIST_L = {"l_arm_ik": ([0.0, -0.40, -0.04], "back+0.3out")}
HIP_FIST_R = {"r_arm_ik": ([0.0, -0.40, -0.04], "back+0.3out")}


def _t(id_, name, keys, sub, home="tkd_ready", **kw):
    return Primitive(f"tkd.{id_}", name, "taekwondo", sub, keys, home=home, **kw)


def _kr(id_, name, keys, sub, home="zenkutsu", **kw):
    return Primitive(f"karate.{id_}", name, "karate", sub, keys, home=home, **kw)


def tkd_primitives() -> list[Primitive]:
    r, s = TKD_READY, TKD_STANCE
    out = [
        _t("ap_seogi", "Walking stance (ap seogi)", posture(full(AP_SEOGI, HIP_FIST_L, HIP_FIST_R)), "stances",
           static=True, stance_based=True),
        _t("ap_kubi", "Front stance (ap kubi)", posture(full(AP_KUBI, HIP_FIST_R,
           {"l_arm_ik": ([-0.10, -0.06, 0.42], "down+0.3out")})), "stances", static=True, stance_based=True,
           flexibility="medium"),
        _t("dwit_kubi", "Back stance (dwit kubi) with knife-hand guard", posture(full(DWIT_KUBI, {
            "twist": 25, "l_arm_ik": ([0.0, 0.02, 0.42], "down+0.3out"), "r_arm_ik": ([-0.20, -0.18, 0.20], "down+0.3out")})),
           "stances", static=True, stance_based=True, flexibility="medium"),
        _t("juchum_seogi", "Horse-riding stance (juchum seogi)", posture(full(JUCHUM, {
            "l_arm_ik": ([-0.12, -0.04, 0.44], "down+0.3out"), "r_arm_ik": ([-0.12, -0.04, 0.44], "down+0.3out")})),
           "stances", static=True, flexibility="medium"),
        _t("beom_seogi", "Tiger stance (beom seogi)", posture(full(BEOM, {
            "l_arm_ik": ([-0.06, -0.02, 0.40], "down+0.3out"), "r_arm_ik": ([-0.16, -0.20, 0.22], "down+0.3out")})),
           "stances", static=True, stance_based=True),
        # Blocks (makki) from the ready stance into a walking stance.
        _t("arae_makki", "Low block (arae makki)", seq(r, [
            (0.25, {**AP_SEOGI, "l_arm_ik": ([-0.20, 0.10, 0.10], "down+0.3out"),
                    "r_arm_ik": ([-0.10, -0.30, 0.30], "down+0.3out")}),
            (0.25, {"l_upper_arm": "down+0.5fwd+0.2out", "l_forearm": "down+0.6fwd+0.1out", **HIP_FIST_R}),
            (0.25, {})], back=0.4), "blocks", stance_based=True),
        _t("momtong_an_makki", "Inside middle block (momtong an makki)", seq(r, [
            (0.22, {**AP_SEOGI, "r_arm_ik": ([0.10, 0.10, 0.10], "down+0.5out")}),
            (0.25, {"twist": 15, "r_upper_arm": "down+0.6fwd+0.3out", "r_forearm": "up+0.25fwd+0.25in", **HIP_FIST_L}),
            (0.25, {})], back=0.4), "blocks", stance_based=True),
        _t("momtong_bakkat_makki", "Outside middle block (momtong bakkat makki)", seq(r, [
            (0.22, {**AP_SEOGI, "l_arm_ik": ([-0.25, -0.15, 0.25], "down+0.3out")}),
            (0.25, {"twist": -15, "l_upper_arm": "down+0.4fwd+0.6out", "l_forearm": "up+0.3fwd", **HIP_FIST_R}),
            (0.25, {})], back=0.4), "blocks", stance_based=True),
        _t("olgul_makki", "Rising block (olgul makki)", seq(r, [
            (0.22, {**AP_SEOGI, "l_arm_ik": ([-0.15, -0.20, 0.30], "down+0.3out")}),
            (0.25, {"l_upper_arm": "up+0.5fwd+0.5out", "l_forearm": "in+0.25up+0.2fwd", **HIP_FIST_R}),
            (0.25, {})], back=0.4), "blocks", stance_based=True),
        _t("sonnal_makki", "Knife-hand guarding block (sonnal makki)", seq(r, [
            (0.25, {**DWIT_KUBI, "l_arm_ik": ([0.10, 0.20, -0.10], "down+0.3out"),
                    "r_arm_ik": ([0.0, 0.10, -0.10], "down+0.3out")}),
            (0.3, {"twist": 25, "l_arm_ik": ([0.0, 0.02, 0.42], "down+0.3out"),
                   "r_arm_ik": ([-0.20, -0.18, 0.20], "down+0.3out")}),
            (0.25, {})], back=0.45), "blocks", stance_based=True, flexibility="medium", complexity=3),
        _t("hecheo_makki", "Wedge block (hecheo makki)", seq(r, [
            (0.22, {**AP_KUBI, "l_arm_ik": ([-0.25, -0.20, 0.25], "down+0.3out"),
                    "r_arm_ik": ([-0.25, -0.20, 0.25], "down+0.3out")}),
            (0.28, {"l_upper_arm": "out+0.3fwd+0.2down", "l_forearm": "up+0.2fwd",
                    "r_upper_arm": "out+0.3fwd+0.2down", "r_forearm": "up+0.2fwd"}),
            (0.25, {})], back=0.4), "blocks", stance_based=True, flexibility="medium"),
        # Punches and strikes.
        _t("momtong_jireugi", "Middle punch (momtong jireugi)", seq(r, [
            (0.2, {**AP_SEOGI, **HIP_FIST_R, "l_arm_ik": ([-0.12, -0.10, 0.40], "down+0.3out")}),
            (0.22, {"twist": 20, "r_upper_arm": "@fwd+0.12down+0.22in", "r_forearm": "@fwd+0.1down+0.2in", **HIP_FIST_L}),
            (0.2, {})], back=0.4), "punches", stance_based=True),
        _t("dubeon_jireugi", "Double punch (dubeon jireugi)", seq(r, [
            (0.2, {**AP_KUBI, **HIP_FIST_L, **HIP_FIST_R}),
            (0.18, {"twist": -15, "l_upper_arm": "@fwd+0.1down+0.25in", "l_forearm": "@fwd+0.1down+0.2in"}),
            (0.18, {"twist": 15, **HIP_FIST_L, "r_upper_arm": "@fwd+0.1down+0.25in", "r_forearm": "@fwd+0.1down+0.2in"}),
            (0.2, {})], back=0.4), "punches", stance_based=True, complexity=3, flexibility="medium"),
        _t("olgul_jireugi", "High punch (olgul jireugi)", seq(r, [
            (0.2, {**AP_SEOGI, **HIP_FIST_R}),
            (0.22, {"twist": 20, "r_upper_arm": "@fwd+0.25up+0.22in", "r_forearm": "@fwd+0.22up+0.2in", **HIP_FIST_L}),
            (0.2, {})], back=0.4), "punches", stance_based=True),
        _t("sonnal_mok_chigi", "Knife-hand neck strike (sonnal mok chigi)", seq(r, [
            (0.25, {**AP_KUBI, "r_arm_ik": ([0.05, 0.25, -0.10], "down+0.4out")}),
            (0.25, {"twist": 25, "r_upper_arm": "out+0.6fwd+0.1up", "r_forearm": "in+0.7fwd", **HIP_FIST_L}),
            (0.2, {})], back=0.4), "strikes", stance_based=True, flexibility="medium"),
        _t("palkup_dollyo_chigi", "Turning elbow strike (palkup dollyo chigi)", seq(r, [
            (0.22, {**AP_KUBI, **HIP_FIST_L}),
            (0.25, {"twist": 35, "r_upper_arm": "out+0.45fwd+0.1up", "r_forearm": "in+0.1back"}),
            (0.2, {})], back=0.4), "strikes", stance_based=True, flexibility="medium"),
        _t("deung_jumeok", "Backfist strike (deung jumeok ap chigi)", seq(r, [
            (0.22, {**AP_SEOGI, "l_arm_ik": ([-0.25, 0.15, 0.12], "down+0.4out")}),
            (0.22, {"l_upper_arm": "@fwd+0.3up+0.05out", "l_forearm": "@fwd+0.5up", **HIP_FIST_R}),
            (0.2, {})], back=0.4), "strikes", stance_based=True),
        # Kicks from the sparring stance (kyorugi).
        _t("ap_chagi", "Front kick (ap chagi)", seq(s, [
            (0.2, {"yaw": -20, "r_thigh": "@fwd+0.35up", "r_shin": "@down+0.15back"}),
            (0.14, {"r_thigh": "@fwd+0.2up", "r_shin": "@fwd+0.1up", "r_foot": "@fwd+0.4up"}),
            (0.06, {}), (0.16, {"r_thigh": "@fwd+0.35up", "r_shin": "@down+0.15back"})], back=0.3),
           "kicks", home="tkd_stance", stance_based=True, flexibility="medium"),
        _t("ap_ollyeo_chagi", "Front rising kick (ap ollyeo chagi)", seq(s, [
            (0.3, {"yaw": -20, "pitch": -8, "r_thigh": "@fwd+1.1up", "r_shin": "@fwd+1.2up"}), (0.05, {})],
            back=0.35), "kicks", home="tkd_stance", stance_based=True, flexibility="high"),
        _t("dollyo_chagi", "Roundhouse kick (dollyo chagi)", seq(s, [
            (0.2, {"yaw": -15, "r_thigh": "@0.5fwd+0.7out+0.1down", "r_shin": "@back+0.5down+0.2out"}),
            (0.18, {"yaw": 60, "pitch": -15, "roll": 12, "r_thigh": "@fwd+0.05down+0.25in", "r_shin": "@fwd+0.1up+0.2in",
                    "r_foot": "@fwd+0.3in"}),
            (0.08, {}), (0.2, {"yaw": -15, "r_thigh": "@0.5fwd+0.7out+0.1down", "r_shin": "@back+0.5down+0.2out"})],
            back=0.3), "kicks", home="tkd_stance", stance_based=True, flexibility="medium", complexity=3),
        _t("bandal_chagi", "Half-moon kick (bandal chagi)", seq(s, [
            (0.2, {"yaw": -25, "r_thigh": "@0.7fwd+0.5out+0.2up", "r_shin": "@down+0.4back"}),
            (0.16, {"yaw": 20, "pitch": -10, "r_thigh": "@fwd+0.1down+0.15in", "r_shin": "@fwd+0.1in"}),
            (0.08, {}), (0.18, {"yaw": -25, "r_thigh": "@0.7fwd+0.5out+0.2up", "r_shin": "@down+0.4back"})],
            back=0.3), "kicks", home="tkd_stance", stance_based=True, flexibility="medium", complexity=3),
        _t("yeop_chagi", "Side kick (yeop chagi)", seq(s, [
            (0.22, {"yaw": -85, "l_thigh": "@fwd+0.15up+0.2in", "l_shin": "@down+0.4back"}),
            (0.18, {"roll": 25, "l_thigh": "@fwd+0.1down", "l_shin": "@fwd", "l_foot": "@0.6in+down"}),
            (0.1, {}), (0.2, {"roll": 0, "l_thigh": "@fwd+0.15up+0.2in", "l_shin": "@down+0.4back"})], back=0.3),
           "kicks", home="tkd_stance", stance_based=True, flexibility="medium", complexity=3),
        _t("mireo_chagi", "Push kick (mireo chagi)", seq(s, [
            (0.2, {"l_thigh": "@fwd+0.3up", "l_shin": "@down+0.1back"}),
            (0.18, {"pitch": -12, "l_thigh": "@fwd+0.05down", "l_shin": "@fwd+0.1up"}),
            (0.1, {}), (0.2, {"pitch": 0, "l_thigh": "@fwd+0.3up", "l_shin": "@down+0.1back"})], back=0.3),
           "kicks", home="tkd_stance", stance_based=True),
        _t("naeryo_chagi", "Axe kick (naeryo chagi)", seq(s, [
            (0.3, {"yaw": -20, "pitch": -10, "r_thigh": "@fwd+1.2up+0.1out", "r_shin": "@fwd+1.3up"}),
            (0.22, {"pitch": -4, "r_thigh": "@fwd+0.2down", "r_shin": "@fwd+0.6down"}), (0.06, {})], back=0.3),
           "kicks", home="tkd_stance", stance_based=True, flexibility="high", complexity=3),
        _t("bakkat_chagi", "Outward crescent kick (bakkat chagi)", seq(s, [
            (0.18, {"yaw": -15, "r_thigh": "@fwd+0.3up+0.4in", "r_shin": "@fwd+0.4up+0.3in"}),
            (0.22, {"r_thigh": "@fwd+0.4up+0.4out", "r_shin": "@fwd+0.4up+0.5out"}),
            (0.15, {"r_thigh": "down+0.2out", "r_shin": "down"})], back=0.3),
           "kicks", home="tkd_stance", stance_based=True, flexibility="high", complexity=3),
        _t("an_chagi", "Inward crescent kick (an chagi)", seq(s, [
            (0.18, {"yaw": -15, "r_thigh": "@fwd+0.3up+0.4out", "r_shin": "@fwd+0.4up+0.4out"}),
            (0.22, {"r_thigh": "@fwd+0.4up+0.4in", "r_shin": "@fwd+0.4up+0.5in"}),
            (0.15, {"r_thigh": "down+0.2back", "r_shin": "down"})], back=0.3),
           "kicks", home="tkd_stance", stance_based=True, flexibility="medium", complexity=3),
        _t("kyorugi_punch", "Sparring body punch (momtong jireugi)", strike(s, {
            "twist": 40, "pitch": 8, "r_upper_arm": "@fwd+0.2down+0.2in", "r_forearm": "@fwd+0.15down+0.15in"}),
           "punches", home="tkd_stance", stance_based=True),
    ]
    return out


def karate_primitives() -> list[Primitive]:
    z, y = ZENKUTSU, KARATE_YOI
    KIBA = {"l_leg_ik": ([0.30, -0.64, 0.0], "fwd+0.7out"), "r_leg_ik": ([0.30, -0.64, 0.0], "fwd+0.7out")}
    KOKUTSU = {"yaw": -70, "l_leg_ik": [0.0, -0.76, 0.34], "r_leg_ik": ([0.12, -0.70, -0.14], "fwd+0.6out")}
    return [
        _kr("zenkutsu_dachi", "Front stance (zenkutsu dachi)", posture(z), "stances", static=True,
            stance_based=True, flexibility="medium"),
        _kr("kiba_dachi", "Horse stance (kiba dachi)", posture(full(KIBA, HIP_FIST_L, HIP_FIST_R)), "stances",
            static=True, flexibility="medium"),
        _kr("kokutsu_dachi", "Back stance (kokutsu dachi)", posture(full(KOKUTSU, {
            "twist": 20, "l_arm_ik": ([0.0, 0.0, 0.42], "down+0.3out"), "r_arm_ik": ([-0.20, -0.18, 0.18], "down+0.3out")})),
            "stances", static=True, stance_based=True, flexibility="medium"),
        _kr("gedan_barai", "Downward block (gedan barai)", seq(z, [
            (0.25, {"l_arm_ik": ([-0.20, 0.10, 0.10], "down+0.3out"), "r_arm_ik": ([-0.10, -0.30, 0.30], "down+0.3out")}),
            (0.25, {"l_upper_arm": "down+0.5fwd+0.25out", "l_forearm": "down+0.6fwd+0.15out", **HIP_FIST_R}),
            (0.25, {})], back=0.4), "blocks", stance_based=True),
        _kr("age_uke", "Rising block (age uke)", seq(z, [
            (0.22, {"l_arm_ik": ([-0.15, -0.20, 0.30], "down+0.3out")}),
            (0.25, {"l_upper_arm": "up+0.5fwd+0.5out", "l_forearm": "in+0.25up+0.2fwd"}),
            (0.25, {})], back=0.4), "blocks", stance_based=True),
        _kr("soto_uke", "Outside block (soto uke)", seq(z, [
            (0.22, {"l_arm_ik": ([0.20, 0.15, -0.05], "down+0.5out")}),
            (0.25, {"twist": 15, "l_upper_arm": "down+0.6fwd+0.1out", "l_forearm": "up+0.25fwd+0.3in"}),
            (0.25, {})], back=0.4), "blocks", stance_based=True),
        _kr("uchi_uke", "Inside block (uchi uke)", seq(z, [
            (0.22, {"l_arm_ik": ([-0.25, -0.15, 0.20], "down+0.3out")}),
            (0.25, {"twist": -15, "l_upper_arm": "down+0.4fwd+0.6out", "l_forearm": "up+0.3fwd"}),
            (0.25, {})], back=0.4), "blocks", stance_based=True),
        _kr("shuto_uke", "Knife-hand block (shuto uke)", seq(z, [
            (0.25, {**KOKUTSU, "l_arm_ik": ([0.10, 0.20, -0.10], "down+0.3out"), "r_arm_ik": ([0.0, 0.1, -0.1], "down")}),
            (0.3, {"twist": 20, "l_arm_ik": ([0.0, 0.0, 0.42], "down+0.3out"), "r_arm_ik": ([-0.20, -0.18, 0.18], "down+0.3out")}),
            (0.25, {})], back=0.45), "blocks", stance_based=True, flexibility="medium", complexity=3),
        _kr("gyaku_zuki", "Reverse punch (gyaku zuki)", seq(z, [
            (0.22, {"twist": 30, "yaw": 10, "r_upper_arm": "@fwd+0.12down+0.22in", "r_forearm": "@fwd+0.1down+0.2in",
                    **HIP_FIST_L}), (0.15, {})], back=0.4), "punches", stance_based=True),
        _kr("kizami_zuki", "Jab punch (kizami zuki)", seq(z, [
            (0.18, {"twist": -15, "pitch": 6, "l_upper_arm": "@fwd+0.05up+0.1in", "l_forearm": "@fwd+0.05up+0.08in"}),
            (0.12, {})], back=0.3), "punches", stance_based=True),
        _kr("oi_zuki", "Stepping punch (oi zuki, in place)", seq(y, [
            (0.3, {"yaw": -8, "l_leg_ik": [0.06, -0.72, 0.42], "r_leg_ik": [0.10, -0.72, -0.44], "z": 0.15,
                   **HIP_FIST_R, "l_arm_ik": ([-0.12, -0.06, 0.42], "down+0.3out")}),
            (0.22, {"twist": 25, "r_upper_arm": "@fwd+0.12down+0.22in", "r_forearm": "@fwd+0.1down+0.2in",
                    **HIP_FIST_L}),
            (0.2, {})], back=0.5), "punches", home="karate_yoi", stance_based=True, complexity=3,
            flexibility="medium"),
        _kr("mae_geri", "Front kick (mae geri)", seq(z, [
            (0.22, {"r_thigh": "@fwd+0.35up", "r_shin": "@down+0.15back"}),
            (0.14, {"r_thigh": "@fwd+0.25up", "r_shin": "@fwd+0.05up", "r_foot": "@fwd+0.3up"}),
            (0.06, {}), (0.16, {"r_thigh": "@fwd+0.35up", "r_shin": "@down+0.15back"})], back=0.35),
            "kicks", stance_based=True, flexibility="medium"),
        _kr("yoko_geri", "Side snap kick (yoko geri keage)", seq(z, [
            (0.22, {"yaw": -80, "l_thigh": "@fwd+0.15up+0.2in", "l_shin": "@down+0.4back"}),
            (0.15, {"roll": 20, "l_thigh": "@fwd+0.05down", "l_shin": "@fwd+0.2up"}),
            (0.08, {}), (0.18, {"roll": 0, "l_thigh": "@fwd+0.15up+0.2in", "l_shin": "@down+0.4back"})], back=0.35),
            "kicks", stance_based=True, flexibility="medium", complexity=3),
        _kr("mawashi_geri", "Roundhouse kick (mawashi geri)", seq(z, [
            (0.22, {"yaw": 0, "r_thigh": "@0.5fwd+0.7out", "r_shin": "@back+0.5down+0.2out"}),
            (0.18, {"yaw": 60, "pitch": -12, "roll": 10, "r_thigh": "@fwd+0.05down+0.25in", "r_shin": "@fwd+0.1up+0.2in"}),
            (0.08, {}), (0.2, {"yaw": 0, "r_thigh": "@0.5fwd+0.7out", "r_shin": "@back+0.5down+0.2out"})], back=0.35),
            "kicks", stance_based=True, flexibility="medium", complexity=3),
        _kr("empi_uchi", "Elbow strike (empi uchi)", seq(z, [
            (0.24, {"twist": 35, "r_upper_arm": "out+0.45fwd+0.1up", "r_forearm": "in+0.1back", **HIP_FIST_L}),
            (0.15, {})], back=0.4), "strikes", stance_based=True),
        _kr("uraken_uchi", "Backfist (uraken uchi)", seq(z, [
            (0.2, {"l_arm_ik": ([-0.25, 0.15, 0.12], "down+0.4out")}),
            (0.2, {"l_upper_arm": "@fwd+0.3up+0.05out", "l_forearm": "@fwd+0.5up"}), (0.15, {})], back=0.4),
            "strikes", stance_based=True),
        _kr("tettsui", "Hammer fist (tettsui uchi)", seq(z, [
            (0.25, {"l_upper_arm": "up+0.4out+0.2back", "l_forearm": "up+0.5in"}),
            (0.22, {"l_upper_arm": "fwd+0.4out", "l_forearm": "fwd+0.4down"}), (0.15, {})], back=0.4),
            "strikes", stance_based=True),
        _kr("nukite", "Spear hand (nukite)", seq(z, [
            (0.22, {"twist": 30, "r_upper_arm": "@fwd+0.05down+0.22in", "r_forearm": "@fwd+0.2in",
                    "l_arm_ik": ([-0.25, -0.15, 0.30], "down+0.3out")}), (0.15, {})], back=0.4),
            "strikes", stance_based=True),
        _kr("kiba_zuki", "Punch in horse stance (kiba dachi zuki)", seq(full(KIBA, HIP_FIST_L, HIP_FIST_R), [
            (0.22, {"r_upper_arm": "@fwd+0.12down+0.22in", "r_forearm": "@fwd+0.1down+0.2in"}),
            (0.1, {}), (0.22, {**HIP_FIST_R, "l_upper_arm": "@fwd+0.12down+0.22in", "l_forearm": "@fwd+0.1down+0.2in"}),
            (0.1, {})], back=0.35), "punches", home=None, flexibility="medium", complexity=3),
    ]


def primitives() -> list[Primitive]:
    return tkd_primitives() + karate_primitives()


COMBOS = [
    ["tkd.arae_makki", "tkd.momtong_jireugi"], ["tkd.momtong_an_makki", "tkd.momtong_jireugi"],
    ["tkd.olgul_makki", "tkd.momtong_jireugi"], ["tkd.arae_makki", "tkd.dubeon_jireugi"],
    ["tkd.sonnal_makki", "tkd.momtong_jireugi"], ["tkd.momtong_bakkat_makki", "tkd.deung_jumeok"],
    ["tkd.arae_makki", "tkd.olgul_makki", "tkd.momtong_jireugi"],
    ["tkd.ap_chagi", "tkd.kyorugi_punch"], ["tkd.dollyo_chagi", "tkd.kyorugi_punch"],
    ["tkd.bandal_chagi", "tkd.dollyo_chagi"], ["tkd.mireo_chagi", "tkd.dollyo_chagi"],
    ["tkd.ap_chagi", "tkd.yeop_chagi"], ["tkd.kyorugi_punch", "tkd.bandal_chagi"],
    ["tkd.an_chagi", "tkd.kyorugi_punch"], ["tkd.mireo_chagi", "tkd.kyorugi_punch", "tkd.dollyo_chagi"],
    ["karate.gedan_barai", "karate.gyaku_zuki"], ["karate.age_uke", "karate.gyaku_zuki"],
    ["karate.soto_uke", "karate.gyaku_zuki"], ["karate.uchi_uke", "karate.kizami_zuki", "karate.gyaku_zuki"],
    ["karate.kizami_zuki", "karate.gyaku_zuki"], ["karate.mae_geri", "karate.gyaku_zuki"],
    ["karate.gedan_barai", "karate.mae_geri", "karate.gyaku_zuki"], ["karate.age_uke", "karate.empi_uchi"],
    ["karate.uraken_uchi", "karate.gyaku_zuki"], ["karate.mawashi_geri", "karate.gyaku_zuki"],
    ["karate.shuto_uke", "karate.nukite"], ["karate.soto_uke", "karate.empi_uchi", "karate.uraken_uchi"],
]
