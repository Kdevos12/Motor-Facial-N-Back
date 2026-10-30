"""Pure-Python subsequence DTW for environments without dtaidistance's C extension."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class _Match:
    path: list[tuple[int, int]]


@dataclass
class _Alignment:
    path: list[tuple[int, int]]

    def best_match(self) -> _Match:
        return _Match(self.path)


def subsequence_alignment(
    query: np.ndarray, series: np.ndarray, penalty: float = 0.1, use_c: bool = False
) -> _Alignment:
    """Return the minimum-cost path matching all of query to any part of series."""
    query = np.asarray(query, dtype=np.double)
    series = np.asarray(series, dtype=np.double)
    penalty = penalty ** 2
    rows, cols = len(query), len(series)
    costs = np.full((rows + 1, cols + 1), np.inf)
    costs[0, :] = 0.0

    for i in range(rows):
        for j in range(cols):
            local = float(np.sum((query[i] - series[j]) ** 2))
            previous = (costs[i, j], costs[i, j + 1] + penalty, costs[i + 1, j] + penalty)
            if previous[0] < previous[1] and previous[0] < previous[2]:
                best = previous[0]
            elif previous[1] < previous[2]:
                best = previous[1]
            else:
                best = previous[2]
            costs[i + 1, j + 1] = local + best

    for candidate in np.argsort(costs[rows, 1:], kind="stable") + 1:
        i, j = rows, int(candidate)
        path = [(i - 1, j - 1)]
        while i > 0 and j > 0:
            previous = (costs[i - 1, j - 1], costs[i - 1, j] + penalty, costs[i, j - 1] + penalty)
            if previous[0] <= previous[1] and previous[0] <= previous[2]:
                i, j = i - 1, j - 1
            elif previous[1] < previous[2]:
                i -= 1
            else:
                j -= 1
            path.append((i - 1, j - 1))
        path.pop()
        path.reverse()
        if path and path[-1][1] - path[0][1] + 1 >= 2:
            return _Alignment(path)
    raise ValueError("No matching subsequence found.")
