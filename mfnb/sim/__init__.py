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


def synth_face_response(target: np.ndarray, rng: np.random.Generator, *, fps: float = 30.0,
                        effort: tuple[float, float] = (0.6, 1.0), rest: np.ndarray | None = None, noise: float = 0.03,
                        idle_before: float = 1.0, hold: float = 1.2, idle_after: float = 1.0,
                        crosstalk: float = 0.04) -> tuple[np.ndarray, np.ndarray]:
    """A person producing a facial expression as MediaPipe would report it (raw 51-dim shapes): their resting face,
    then a ramp to ``target`` (intent units, 0..1 of a full effort) at a personal effort per shape, hold, release.
    Shapes the tracker never outputs stay at 0 and each shape tops out at its typical real maximum."""
    from ..face.blendshapes import DEAD_MASK, REST_MEAN, TYPICAL_MAX
    t = np.asarray(target, dtype=float)
    base = REST_MEAN if rest is None else np.asarray(rest, float)
    eff = rng.uniform(effort[0], effort[1], t.shape)
    peak = base + t * eff * np.maximum(TYPICAL_MAX - base, 0) + np.abs(rng.normal(0, crosstalk, t.shape))
    ramp = int(0.3 * fps)
    env = np.concatenate([np.zeros(int(idle_before * fps)), np.linspace(0, 1, ramp), np.ones(int(hold * fps)),
                          np.linspace(1, 0, ramp), np.zeros(int(idle_after * fps))])
    frames = base + env[:, None] * (peak - base)[None, :] + rng.normal(0, noise, (len(env), len(t)))
    frames = np.where(DEAD_MASK, 0.0, np.clip(frames, 0, 1))
    return frames, np.arange(len(env)) / fps


def synth_face_neutral(rng: np.random.Generator, rest: np.ndarray | None = None, seconds: float = 2.0,
                       fps: float = 30.0, noise: float = 0.03) -> np.ndarray:
    """A relaxed face held still (raw 51-dim shapes)."""
    from ..face.blendshapes import DEAD_MASK, REST_MEAN
    base = REST_MEAN if rest is None else np.asarray(rest, float)
    f = base + rng.normal(0, noise, (int(seconds * fps), len(base)))
    return np.where(DEAD_MASK, 0.0, np.clip(f, 0, 1))
