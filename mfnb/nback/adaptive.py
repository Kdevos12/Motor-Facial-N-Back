"""Block-level N adaptation (Jaeggi-style)."""
from __future__ import annotations

UP = 0.85
DOWN = 0.60
MIN_N = 1
MAX_N = 12


def next_n(n: int, accuracy: float | None, mode: str = "adaptive", up: float = UP, down: float = DOWN,
           min_n: int = MIN_N, max_n: int = MAX_N) -> int:
    """N for the next block. Manual mode keeps N; no valid trials keeps N."""
    if mode != "adaptive" or accuracy is None:
        return n
    if accuracy >= up:
        return min(n + 1, max_n)
    if accuracy < down:
        return max(n - 1, min_n)
    return n


def block_length(n: int, base: int = 20) -> int:
    return base + n
