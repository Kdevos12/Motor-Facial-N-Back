"""Synthetic responses: used by tests, threshold calibration and the camera-less demo mode."""
from __future__ import annotations

import numpy as np


def synth_response(target: np.ndarray, rng: np.random.Generator, *, fps: float = 30.0, speed: float | None = None,
                   noise_m: float = 0.025, depth_noise_m: float = 0.06, amplitude: float = 0.9, style_m: float = 0.0,
                   idle_before: float = 1.0, idle_after: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """Imitate a person reproducing ``target`` (T,19,3 @30fps): idle time, tempo change with a
    smooth warp, reduced amplitude, position jitter and noisier depth. Returns (frames, times_s)."""
    speed = float(rng.uniform(0.75, 1.35)) if speed is None else speed
    n = len(target)
    out_n = max(2, int(round(n / speed)))
    u = np.linspace(0, 1, out_n)
    warp = u + 0.06 * np.sin(2 * np.pi * u) * rng.uniform(-1, 1)
    src = np.clip(warp, 0, 1) * (n - 1)
    lo = np.floor(src).astype(int)
    hi = np.minimum(lo + 1, n - 1)
    a = (src - lo)[:, None, None]
    move = target[lo] * (1 - a) + target[hi] * a
    rest = target[0]
    move = rest + (move - rest) * amplitude
    pre = np.repeat(target[:1], int(idle_before * fps), 0)
    post = np.repeat(target[-1:], int(idle_after * fps), 0)
    frames = np.concatenate([pre, move, post])
    jitter = rng.normal(0, 1, frames.shape) * np.array([noise_m, noise_m, depth_noise_m])
    kernel = np.ones(3) / 3
    for j in range(frames.shape[1]):
        for c in range(3):
            jitter[:, j, c] = np.convolve(jitter[:, j, c], kernel, mode="same")
    frames = frames + jitter
    if style_m > 0:
        # personal style: a constant offset per joint plus a slow drift (elbows a bit higher,
        # stance a bit narrower...), which shows up as 10-25 degree bone deviations
        offset = rng.normal(0, style_m, (1, frames.shape[1], 3)) * np.array([1.0, 1.0, 1.5])
        drift = np.cumsum(rng.normal(0, style_m * 0.05, frames.shape), axis=0)
        frames = frames + offset + drift - drift.mean(0)
    times = np.arange(len(frames)) / fps
    return frames, times


def synth_face_response(target: np.ndarray, rng: np.random.Generator, *, fps: float = 30.0, gain_spread: float = 0.25,
                        noise: float = 0.04, idle_before: float = 1.0, hold: float = 1.2,
                        idle_after: float = 1.0, crosstalk: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    """A person producing a facial expression: neutral, ramp, hold, release (raw 51-dim shapes)."""
    t = np.asarray(target, dtype=float)
    gains = np.clip(rng.normal(1.0, gain_spread, t.shape), 0.4, 1.4)
    peak = np.clip(t * gains + np.abs(rng.normal(0, crosstalk, t.shape)), 0, 1)
    ramp = int(0.3 * fps)
    env = np.concatenate([np.zeros(int(idle_before * fps)), np.linspace(0, 1, ramp), np.ones(int(hold * fps)),
                          np.linspace(1, 0, ramp), np.zeros(int(idle_after * fps))])
    frames = np.clip(env[:, None] * peak[None, :] + np.abs(rng.normal(0, noise, (len(env), len(t)))), 0, 1)
    return frames, np.arange(len(env)) / fps
