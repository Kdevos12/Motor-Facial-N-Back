"""Block plans for the recall N-back: which item each trial shows and what to perform."""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field


@dataclass
class Target:
    offset: int            # perform the item shown `offset` trials ago (0 = the one just shown)
    mirror: bool = False   # "switch sides": perform the mirror of what was shown


@dataclass
class TrialPlan:
    index: int
    item_id: str
    shown_mirrored: bool = False
    targets: list[Target] = field(default_factory=list)

    @property
    def watch_only(self) -> bool:
        return not self.targets

    def to_dict(self) -> dict:
        d = asdict(self)
        d["watch_only"] = self.watch_only
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "TrialPlan":
        return cls(index=d["index"], item_id=d["item_id"], shown_mirrored=d.get("shown_mirrored", False),
                   targets=[Target(**t) for t in d.get("targets", [])])


@dataclass
class PlanOptions:
    n: int
    n_trials: int
    variable_n: bool = False        # offset = N +/- 1 on some trials
    variable_n_p: float = 0.35
    chirality_p: float = 0.0        # probability of a "switch sides" instruction (chiral items only)
    sequence_p: float = 0.0         # probability of "do N-k then N" (experimental)
    side_variety_p: float = 0.5     # show non-stance sided items in their mirrored variant sometimes
    stance_mirror: bool = False     # southpaw: show stance-based items mirrored


def _pick_item(pool: list[str], recent: list[str], rng: random.Random) -> str:
    fresh = [p for p in pool if p not in recent]
    if fresh:
        return rng.choice(fresh)
    if len(pool) > 1 and recent:
        return rng.choice([p for p in pool if p != recent[-1]])
    return rng.choice(pool)


def make_plan(pool: list[str], opts: PlanOptions, rng: random.Random, *, chiral: set[str] = frozenset(),
              side_variety: set[str] = frozenset(), stance_based: set[str] = frozenset()) -> list[TrialPlan]:
    """Generate a block.

    Items never repeat within the N+2 most recent trials when the pool allows it. Trials
    before the first possible target are watch-only.
    """
    if not pool:
        raise ValueError("empty item pool")
    if opts.n < 0 or opts.n_trials <= opts.n:
        raise ValueError("need n >= 0 and more trials than n")
    window = opts.n + 2
    trials: list[TrialPlan] = []
    for t in range(opts.n_trials):
        recent = [tr.item_id for tr in trials[-window:]] if window else []
        item = _pick_item(pool, recent, rng)
        if item in stance_based:
            shown_mirrored = opts.stance_mirror
        elif item in side_variety:
            shown_mirrored = rng.random() < opts.side_variety_p
        else:
            shown_mirrored = False
        trial = TrialPlan(index=t, item_id=item, shown_mirrored=shown_mirrored)
        if t >= opts.n:
            offsets = [opts.n]
            if opts.sequence_p and opts.n >= 1 and rng.random() < opts.sequence_p:
                k = rng.choice([k for k in (1, 2) if opts.n - k >= 0])
                offsets = [opts.n - k, opts.n]
            elif opts.variable_n and rng.random() < opts.variable_n_p:
                choices = [d for d in (-1, 1) if 0 <= opts.n + d <= t and opts.n + d != opts.n]
                if choices:
                    offsets = [opts.n + rng.choice(choices)]
            targets = []
            for off in offsets:
                ref = trials[t - off] if off > 0 else trial
                mirror = ref.item_id in chiral and rng.random() < opts.chirality_p
                targets.append(Target(offset=off, mirror=mirror))
            trial.targets = targets
        trials.append(trial)
    return trials


def resolve_targets(plan: list[TrialPlan], index: int) -> list[tuple[str, bool]]:
    """(item_id, effective_mirror) for each target of trial ``index``: what to perform."""
    trial = plan[index]
    out = []
    for tg in trial.targets:
        ref = plan[index - tg.offset]
        out.append((ref.item_id, ref.shown_mirrored != tg.mirror))
    return out


def lure_items(plan: list[TrialPlan], index: int, span: int = 3) -> list[tuple[str, bool]]:
    """Other recently shown items (as shown) the user might perform by mistake."""
    targets = {(i, m) for i, m in resolve_targets(plan, index)}
    out = []
    lo = max(0, index - max((t.offset for t in plan[index].targets), default=0) - span)
    for k in range(lo, index + 1):
        cand = (plan[k].item_id, plan[k].shown_mirrored)
        if cand not in targets and cand not in out:
            out.append(cand)
    return out
