"""Tests for SetProxy operations in produce()."""

import pytest

from patchdiff import produce
from patchdiff.pointer import Pointer


def test_set_add():
    """Test adding to a set."""
    base = {1, 2, 3}

    def recipe(draft):
        draft.add(4)

    result, patches, _reverse = produce(base, recipe)

    assert result == {1, 2, 3, 4}
    assert len(patches) == 1
    assert patches[0] == {"op": "add", "path": Pointer(["-"]), "value": 4}


def test_set_remove():
    """Test removing from a set."""
    base = {1, 2, 3}

    def recipe(draft):
        draft.remove(2)

    result, patches, reverse = produce(base, recipe)

    assert result == {1, 3}
    assert len(patches) == 1
    assert patches[0] == {"op": "remove", "path": Pointer([2])}
    assert reverse[0] == {"op": "add", "path": Pointer([2]), "value": 2}


def test_set_discard():
    """Test discarding from a set."""
    base = {1, 2, 3}

    def recipe(draft):
        draft.discard(2)
        draft.discard(10)  # Doesn't raise error

    result, patches, _reverse = produce(base, recipe)

    assert result == {1, 3}
    assert len(patches) == 1  # Only removal of 2


def test_set_update():
    """Test updating a set."""
    base = {1, 2}

    def recipe(draft):
        draft.update({3, 4})

    result, patches, _reverse = produce(base, recipe)

    assert result == {1, 2, 3, 4}
    assert len(patches) == 2


def test_set_clear():
    """Test clearing a set."""
    base = {1, 2, 3}

    def recipe(draft):
        draft.clear()

    result, patches, _reverse = produce(base, recipe)

    assert result == set()
    assert len(patches) == 3


def test_set_contains():
    """Test __contains__ (in operator) on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        assert 2 in draft
        assert 5 not in draft
        draft.add(5)

    result, _patches, _reverse = produce(base, recipe)

    assert 5 in result


def test_set_len():
    """Test __len__ on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        assert len(draft) == 3
        draft.add(4)
        assert len(draft) == 4

    result, _patches, _reverse = produce(base, recipe)

    assert len(result) == 4


def test_set_pop_non_empty():
    """Test pop() on non-empty set."""
    base = {1, 2, 3}

    def recipe(draft):
        value = draft.pop()
        assert value in {1, 2, 3}

    result, patches, _reverse = produce(base, recipe)

    assert len(result) == 2
    assert len(patches) == 1
    assert patches[0]["op"] == "remove"


def test_set_pop_empty():
    """Test pop() on empty set raises KeyError."""
    base = set()

    def recipe(draft):
        draft.pop()

    with pytest.raises(KeyError):
        produce(base, recipe)


def test_set_remove_not_found():
    """Test remove() with value not in set raises KeyError."""
    base = {1, 2, 3}

    def recipe(draft):
        draft.remove(5)

    with pytest.raises(KeyError):
        produce(base, recipe)


def test_set_union():
    """Test union() method on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        result = draft.union({3, 4, 5})
        assert result == {1, 2, 3, 4, 5}

    result, _patches, _reverse = produce(base, recipe)

    assert result == {1, 2, 3}  # Original unchanged by union


def test_set_intersection():
    """Test intersection() method on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        result = draft.intersection({2, 3, 4})
        assert result == {2, 3}

    result, _patches, _reverse = produce(base, recipe)

    assert result == {1, 2, 3}  # Original unchanged


def test_set_difference():
    """Test difference() method on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        result = draft.difference({2, 4})
        assert result == {1, 3}

    result, _patches, _reverse = produce(base, recipe)

    assert result == {1, 2, 3}  # Original unchanged


def test_set_symmetric_difference():
    """Test symmetric_difference() method on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        result = draft.symmetric_difference({2, 3, 4})
        assert result == {1, 4}

    result, _patches, _reverse = produce(base, recipe)

    assert result == {1, 2, 3}  # Original unchanged


def test_set_update_inplace_operator():
    """Test |= operator on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        draft |= {3, 4, 5}

    result, patches, _reverse = produce(base, recipe)

    assert result == {1, 2, 3, 4, 5}
    assert len(patches) == 2  # Added 4 and 5


def test_set_intersection_update():
    """Test &= operator on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        draft &= {2, 3, 4}

    result, patches, _reverse = produce(base, recipe)

    assert result == {2, 3}
    assert len(patches) == 1  # Removed 1


def test_set_difference_update():
    """Test -= operator on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        draft -= {2, 4}

    result, patches, _reverse = produce(base, recipe)

    assert result == {1, 3}
    assert len(patches) == 1  # Removed 2


def test_set_symmetric_difference_update():
    """Test ^= operator on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        draft ^= {2, 3, 4}

    result, patches, _reverse = produce(base, recipe)

    assert result == {1, 4}
    assert len(patches) == 3  # Removed 2, 3, added 4


def test_set_iter():
    """Test iterating over set."""
    base = {1, 2, 3}

    def recipe(draft):
        values = []
        for value in draft:
            values.append(value)
        assert set(values) == {1, 2, 3}

    result, _patches, _reverse = produce(base, recipe)

    assert result == base


def test_set_isdisjoint():
    """Test isdisjoint() method on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        # Verify isdisjoint works correctly
        assert draft.isdisjoint({4, 5, 6}) is True
        assert draft.isdisjoint({2, 4}) is False

    result, patches, _reverse = produce(base, recipe)

    # No mutations, so no patches
    assert patches == []
    assert result == base


def test_set_issubset():
    """Test issubset() method on set proxy."""
    base = {1, 2}

    def recipe(draft):
        # Verify issubset works correctly
        assert draft.issubset({1, 2, 3}) is True
        assert draft.issubset({1}) is False

    result, patches, _reverse = produce(base, recipe)

    # No mutations, so no patches
    assert patches == []
    assert result == base


def test_set_issuperset():
    """Test issuperset() method on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        # Verify issuperset works correctly
        assert draft.issuperset({1, 2}) is True
        assert draft.issuperset({1, 2, 4}) is False

    result, patches, _reverse = produce(base, recipe)

    # No mutations, so no patches
    assert patches == []
    assert result == base


def test_set_copy():
    """Test copy() method on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        copied = draft.copy()
        # Verify copy returns a real set with same contents
        assert copied == {1, 2, 3}
        assert isinstance(copied, set)
        # Verify it's a different object (not a proxy)
        copied.add(4)
        # This mutation is on the copy, not the draft

    result, patches, _reverse = produce(base, recipe)

    # No mutations to draft, so no patches
    assert patches == []
    assert result == base


def test_set_add_existing():
    """Test add() with existing element (no-op)."""
    base = {1, 2, 3}

    def recipe(draft):
        draft.add(2)  # Already exists

    result, patches, _reverse = produce(base, recipe)

    assert result == {1, 2, 3}
    assert len(patches) == 0  # No change


def test_set_update_no_args():
    """Test update() with no arguments (no-op)."""
    base = {1, 2, 3}

    def recipe(draft):
        draft.update()

    result, patches, _reverse = produce(base, recipe)

    assert result == {1, 2, 3}
    assert len(patches) == 0


def test_set_update_multiple_iterables():
    """Test update() with multiple iterables."""
    base = {1, 2}

    def recipe(draft):
        draft.update({3, 4}, [5, 6], (7, 8))

    result, patches, _reverse = produce(base, recipe)

    assert result == {1, 2, 3, 4, 5, 6, 7, 8}
    assert len(patches) == 6  # Added 6 new elements


def test_set_update_with_empty():
    """Test update() with empty iterable (no-op)."""
    base = {1, 2, 3}

    def recipe(draft):
        draft.update([])

    result, patches, _reverse = produce(base, recipe)

    assert result == {1, 2, 3}
    assert len(patches) == 0


def test_set_clear_empty():
    """Test clear() on already empty set."""
    base = set()

    def recipe(draft):
        draft.clear()

    result, patches, _reverse = produce(base, recipe)

    assert result == set()
    assert len(patches) == 0


def test_set_union_no_args():
    """Test union() with no arguments (returns copy)."""
    base = {1, 2, 3}

    def recipe(draft):
        result_set = draft.union()
        assert result_set == {1, 2, 3}
        assert isinstance(result_set, set)

    result, _patches, _reverse = produce(base, recipe)

    assert result == base


def test_set_union_multiple_iterables():
    """Test union() with multiple iterables."""
    base = {1, 2}

    def recipe(draft):
        result_set = draft.union({3, 4}, [5, 6])
        assert result_set == {1, 2, 3, 4, 5, 6}

    result, _patches, _reverse = produce(base, recipe)

    assert result == base  # union doesn't mutate


def test_set_intersection_no_args():
    """Test intersection() with no arguments (returns copy)."""
    base = {1, 2, 3}

    def recipe(draft):
        result_set = draft.intersection()
        assert result_set == {1, 2, 3}

    result, _patches, _reverse = produce(base, recipe)

    assert result == base


def test_set_intersection_multiple_iterables():
    """Test intersection() with multiple iterables."""
    base = {1, 2, 3, 4, 5}

    def recipe(draft):
        result_set = draft.intersection({2, 3, 4, 6}, [3, 4, 5, 7])
        assert result_set == {3, 4}  # Common to all

    result, _patches, _reverse = produce(base, recipe)

    assert result == base


def test_set_difference_no_args():
    """Test difference() with no arguments (returns copy)."""
    base = {1, 2, 3}

    def recipe(draft):
        result_set = draft.difference()
        assert result_set == {1, 2, 3}

    result, _patches, _reverse = produce(base, recipe)

    assert result == base


def test_set_difference_multiple_iterables():
    """Test difference() with multiple iterables."""
    base = {1, 2, 3, 4, 5}

    def recipe(draft):
        result_set = draft.difference({2, 3}, [4])
        assert result_set == {1, 5}

    result, _patches, _reverse = produce(base, recipe)

    assert result == base


def test_set_isdisjoint_with_empty():
    """Test isdisjoint() with empty set."""
    base = {1, 2, 3}

    def recipe(draft):
        # Empty sets are disjoint with all sets
        assert draft.isdisjoint(set()) is True
        assert draft.isdisjoint([]) is True

    result, _patches, _reverse = produce(base, recipe)

    assert result == base


def test_set_issubset_empty():
    """Test that empty set is subset of all sets."""
    base = set()

    def recipe(draft):
        # Empty set is subset of any set
        assert draft.issubset({1, 2, 3}) is True
        assert draft.issubset(set()) is True

    result, _patches, _reverse = produce(base, recipe)

    assert result == set()


def test_set_issubset_self():
    """Test that set is subset of itself."""
    base = {1, 2, 3}

    def recipe(draft):
        assert draft.issubset({1, 2, 3}) is True

    result, _patches, _reverse = produce(base, recipe)

    assert result == base


def test_set_issuperset_empty():
    """Test that all sets are superset of empty set."""
    base = {1, 2, 3}

    def recipe(draft):
        # All sets are superset of empty set
        assert draft.issuperset(set()) is True
        assert draft.issuperset([]) is True

    result, _patches, _reverse = produce(base, recipe)

    assert result == base


def test_set_issuperset_self():
    """Test that set is superset of itself."""
    base = {1, 2, 3}

    def recipe(draft):
        assert draft.issuperset({1, 2, 3}) is True

    result, _patches, _reverse = produce(base, recipe)

    assert result == base


def test_set_difference_update_method():
    """Test difference_update() method on set proxy."""
    base = {1, 2, 3, 4}

    def recipe(draft):
        draft.difference_update({2, 4})

    result, patches, _reverse = produce(base, recipe)

    assert result == {1, 3}
    assert len(patches) == 2


def test_set_intersection_update_method():
    """Test intersection_update() method on set proxy."""
    base = {1, 2, 3, 4}

    def recipe(draft):
        draft.intersection_update({2, 3, 5})

    result, patches, _reverse = produce(base, recipe)

    assert result == {2, 3}
    assert len(patches) == 2  # Removed 1 and 4


def test_set_symmetric_difference_update_method():
    """Test symmetric_difference_update() method on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        draft.symmetric_difference_update({2, 3, 4})

    result, patches, _reverse = produce(base, recipe)

    assert result == {1, 4}
    assert len(patches) == 3  # Removed 2, 3, added 4


def test_set_or_operator():
    """Test | operator (union) returns new set, not a proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        new = draft | {3, 4, 5}
        assert isinstance(new, set)
        assert new == {1, 2, 3, 4, 5}

    _result, patches, _reverse = produce(base, recipe)

    assert patches == []


def test_set_and_operator():
    """Test & operator (intersection) returns new set."""
    base = {1, 2, 3}

    def recipe(draft):
        new = draft & {2, 3, 4}
        assert isinstance(new, set)
        assert new == {2, 3}

    _result, patches, _reverse = produce(base, recipe)

    assert patches == []


def test_set_sub_operator():
    """Test - operator (difference) returns new set."""
    base = {1, 2, 3}

    def recipe(draft):
        new = draft - {2, 4}
        assert isinstance(new, set)
        assert new == {1, 3}

    _result, patches, _reverse = produce(base, recipe)

    assert patches == []


def test_set_xor_operator():
    """Test ^ operator (symmetric difference) returns new set."""
    base = {1, 2, 3}

    def recipe(draft):
        new = draft ^ {2, 3, 4}
        assert isinstance(new, set)
        assert new == {1, 4}

    _result, patches, _reverse = produce(base, recipe)

    assert patches == []


def test_set_eq():
    """Test __eq__ on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        assert draft == {1, 2, 3}
        assert not (draft == {1, 2})

    produce(base, recipe)


def test_set_ne():
    """Test __ne__ on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        assert draft != {1, 2}
        assert not (draft != {1, 2, 3})

    produce(base, recipe)


def test_set_bool():
    """Test __bool__ on set proxy."""

    def recipe_empty(draft):
        assert not draft

    def recipe_full(draft):
        assert draft

    produce(set(), recipe_empty)
    produce({1}, recipe_full)


def test_set_le_lt_ge_gt():
    """Test comparison operators on set proxy (subset/superset)."""
    base = {1, 2, 3}

    def recipe(draft):
        assert draft <= {1, 2, 3, 4}  # subset
        assert draft <= {1, 2, 3}  # equal is also <=
        assert draft < {1, 2, 3, 4}  # proper subset
        assert not (draft < {1, 2, 3})  # not proper subset of equal
        assert draft >= {1, 2}  # superset
        assert draft > {1, 2}  # proper superset

    produce(base, recipe)
