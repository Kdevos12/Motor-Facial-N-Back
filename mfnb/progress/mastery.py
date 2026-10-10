"""Per-item progress and mastery status."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

ALPHA = 0.3
MASTERED_SUCCESSES = 3
MASTERED_EWMA = 0.8
MASTERED_DAYS = 2


@dataclass
class ItemStats:
    seen: int = 0
    attempts: int = 0
    successes: int = 0
    ewma: float | None = None
    best: float = 0.0
    first_seen: str | None = None
    last_seen: str | None = None
    success_days: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = status(self)
        return d

    @classmethod
    def from_dict(cls, d: dict | None) -> "ItemStats":
        if not d:
            return cls()
        d = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**d)


def record_seen(st: ItemStats, day: str) -> ItemStats:
    st.seen += 1
    st.first_seen = st.first_seen or day
    st.last_seen = day
    return st


def record_attempt(st: ItemStats, score: float, success: bool, day: str, alpha: float = ALPHA) -> ItemStats:
    st.attempts += 1
    st.ewma = score if st.ewma is None else (1 - alpha) * st.ewma + alpha * score
    st.best = max(st.best, score)
    st.first_seen = st.first_seen or day
    st.last_seen = day
    if success:
        st.successes += 1
        if day not in st.success_days:
            st.success_days.append(day)
    return st


def status(st: ItemStats) -> str:
    if st.successes >= MASTERED_SUCCESSES and (st.ewma or 0) >= MASTERED_EWMA and len(st.success_days) >= MASTERED_DAYS:
        return "mastered"
    if st.successes >= 1:
        return "learning"
    if st.seen or st.attempts:
        return "seen"
    return "new"
