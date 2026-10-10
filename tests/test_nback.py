import random

import pytest

from mfnb.nback.adaptive import next_n
from mfnb.nback.plan import PlanOptions, lure_items, make_plan, resolve_targets
from mfnb.progress.mastery import ItemStats, record_attempt, record_seen, status

POOL = [f"m{i}" for i in range(40)]


def test_standard_plan_offsets_and_watch_only():
    plan = make_plan(POOL, PlanOptions(n=2, n_trials=22), random.Random(0))
    assert [t.watch_only for t in plan[:2]] == [True, True]
    assert all(not t.watch_only and [g.offset for g in t.targets] == [2] for t in plan[2:])
    tgt = resolve_targets(plan, 5)
    assert tgt == [(plan[3].item_id, False)]


def test_no_repeat_within_window():
    plan = make_plan(POOL, PlanOptions(n=3, n_trials=40), random.Random(1))
    ids = [t.item_id for t in plan]
    for i in range(len(ids)):
        assert ids[i] not in ids[max(0, i - 5):i]


def test_plan_small_pool():
    plan = make_plan(["a", "b"], PlanOptions(n=3, n_trials=12), random.Random(2))
    assert len(plan) == 12
    assert all(plan[i].item_id != plan[i - 1].item_id for i in range(1, 12))
    single = make_plan(["a"], PlanOptions(n=1, n_trials=5), random.Random(2))
    assert [t.item_id for t in single] == ["a"] * 5


def test_variable_n_offsets_within_one():
    plan = make_plan(POOL, PlanOptions(n=2, n_trials=200, variable_n=True), random.Random(3))
    offs = [t.targets[0].offset for t in plan if t.targets]
    assert set(offs) <= {1, 2, 3} and {1, 3} <= set(offs)
    for t in plan:
        for g in t.targets:
            assert 0 <= g.offset <= t.index


def test_plan_no_mirror_on_symmetric():
    chiral = set(POOL[:10])
    plan = make_plan(POOL, PlanOptions(n=1, n_trials=300, chirality_p=1.0), random.Random(4), chiral=chiral)
    for t in plan:
        for g in t.targets:
            ref = plan[t.index - g.offset]
            assert g.mirror == (ref.item_id in chiral)


def test_effective_mirror_combines_display_and_instruction():
    plan = make_plan(POOL, PlanOptions(n=1, n_trials=60, chirality_p=0.5, side_variety_p=0.5), random.Random(5),
                     chiral=set(POOL), side_variety=set(POOL))
    for t in plan[1:]:
        (item, mirror), = resolve_targets(plan, t.index)
        ref = plan[t.index - 1]
        assert item == ref.item_id and mirror == (ref.shown_mirrored != t.targets[0].mirror)


def test_stance_based_items_follow_stance():
    plan = make_plan(POOL, PlanOptions(n=1, n_trials=30, stance_mirror=True), random.Random(6), stance_based=set(POOL))
    assert all(t.shown_mirrored for t in plan)


def test_sequence_mode():
    plan = make_plan(POOL, PlanOptions(n=2, n_trials=100, sequence_p=1.0), random.Random(7))
    for t in plan[2:]:
        offs = [g.offset for g in t.targets]
        assert len(offs) == 2 and offs[1] == 2 and offs[0] in (0, 1)


def test_lures_exclude_targets():
    plan = make_plan(POOL, PlanOptions(n=2, n_trials=10), random.Random(8))
    lures = lure_items(plan, 6)
    assert (plan[4].item_id, plan[4].shown_mirrored) not in lures
    assert (plan[6].item_id, plan[6].shown_mirrored) in lures


@pytest.mark.parametrize("acc,expected", [(0.9, 3), (0.85, 3), (0.7, 2), (0.59, 1), (None, 2)])
def test_adaptation(acc, expected):
    assert next_n(2, acc) == expected
    assert next_n(2, acc, mode="manual") == 2
    assert next_n(1, 0.1) == 1


def test_mastery_progression():
    st = ItemStats()
    assert status(st) == "new"
    record_seen(st, "2026-10-01")
    assert status(st) == "seen"
    for _ in range(3):
        record_attempt(st, 0.9, True, "2026-10-01")
    assert status(st) == "learning"  # needs a second day
    record_attempt(st, 0.9, True, "2026-10-02")
    assert status(st) == "mastered"
    for _ in range(3):
        record_attempt(st, 0.2, False, "2026-10-03")
    assert status(st) == "learning"
