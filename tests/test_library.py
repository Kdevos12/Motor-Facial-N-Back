import numpy as np
import pytest

from mfnb.motion.library import CATEGORIES, get_library
from mfnb.motion.primitives.dsl import FLEX


@pytest.fixture(scope="module")
def lib():
    return get_library()


def test_library_size_and_categories(lib):
    items = list(lib.items.values())
    primitives = [i for i in items if len(i.segments) == 1 and i.source == "procedural"]
    assert len(primitives) >= 150
    assert len(items) >= 500
    assert set(CATEGORIES) <= {i.category for i in items}
    # the categories the user asked for explicitly
    for cat in ("evasion", "taekwondo", "grappling"):
        assert sum(1 for i in items if i.category == cat) >= 20


def test_items_are_well_formed(lib):
    for it in lib.items.values():
        assert it.frames is not None and it.frames.shape[1:] == (19, 3), it.id
        assert np.isfinite(it.frames).all(), it.id
        assert 1 <= it.complexity <= 5, it.id
        assert it.flexibility in FLEX, it.id
        assert it.duration_s > 0.5, it.id
        assert it.category in CATEGORIES, it.id
        # nothing floats or sinks: the lowest foot point stays near the floor
        assert abs(float(it.frames[:, [15, 16, 17, 18], 1].min())) < 0.1, it.id


def test_no_spinning_or_high_kicks_by_default(lib):
    default = lib.filter(flexibility="medium")
    assert all(i.facing_away_deg <= 100 for i in default)
    assert all(i.flexibility != "high" for i in default)
    # head height ~1.6 m: no kick above it
    for it in lib.items.values():
        if it.category in ("kicks", "taekwondo"):
            assert float(it.frames[:, [17, 18], 1].max()) < 1.75, it.id


def test_small_space_filter_keeps_most_items(lib):
    small = lib.filter(space="small")
    assert len(small) > 0.9 * len(lib)
    assert all(i.footprint_m <= 0.75 for i in small)


def test_combos_chain_primitives(lib):
    combo = lib.get("combo.jab+cross")
    assert combo.segments == ["box.jab", "box.cross"]
    assert combo.complexity >= 3
    jab, cross = lib.get("box.jab"), lib.get("box.cross")
    # each item carries the same stillness padding at both ends
    from mfnb.motion.library import PAD_S
    expected = jab.duration_s + cross.duration_s - 2 * PAD_S
    assert abs(combo.duration_s - expected) < 0.1


def test_filter_respects_exclusions_and_complexity(lib):
    some = lib.filter(categories=["boxing"], complexity=(2, 2), exclude={"box.jab"})
    assert some and all(i.category == "boxing" and i.complexity == 2 for i in some)
    assert "box.jab" not in {i.id for i in some}
