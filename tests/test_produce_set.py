"""Tests for SetProxy operations in produce()."""

import pytest

from patchdiff import apply, produce
from patchdiff.pointer import Pointer


def test_set_add():
    """Test adding to a set."""
    base = {1, 2, 3}

    def recipe(draft):
        draft.add(4)

    result, patches, reverse = produce(base, recipe)

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

    result, patches, reverse = produce(base, recipe)

    assert result == {1, 3}
    assert len(patches) == 1  # Only removal of 2


def test_set_update():
    """Test updating a set."""
    base = {1, 2}

    def recipe(draft):
        draft.update({3, 4})

    result, patches, reverse = produce(base, recipe)

    assert result == {1, 2, 3, 4}
    assert len(patches) == 2


def test_set_clear():
    """Test clearing a set."""
    base = {1, 2, 3}

    def recipe(draft):
        draft.clear()

    result, patches, reverse = produce(base, recipe)

    assert result == set()
    assert len(patches) == 3


def test_set_contains():
    """Test __contains__ (in operator) on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        assert 2 in draft
        assert 5 not in draft
        draft.add(5)

    result, patches, reverse = produce(base, recipe)

    assert 5 in result


def test_set_len():
    """Test __len__ on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        assert len(draft) == 3
        draft.add(4)
        assert len(draft) == 4

    result, patches, reverse = produce(base, recipe)

    assert len(result) == 4


def test_set_pop_non_empty():
    """Test pop() on non-empty set."""
    base = {1, 2, 3}

    def recipe(draft):
        value = draft.pop()
        assert value in {1, 2, 3}

    result, patches, reverse = produce(base, recipe)

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

    result, patches, reverse = produce(base, recipe)

    assert result == {1, 2, 3}  # Original unchanged by union


def test_set_intersection():
    """Test intersection() method on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        result = draft.intersection({2, 3, 4})
        assert result == {2, 3}

    result, patches, reverse = produce(base, recipe)

    assert result == {1, 2, 3}  # Original unchanged


def test_set_difference():
    """Test difference() method on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        result = draft.difference({2, 4})
        assert result == {1, 3}

    result, patches, reverse = produce(base, recipe)

    assert result == {1, 2, 3}  # Original unchanged


def test_set_symmetric_difference():
    """Test symmetric_difference() method on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        result = draft.symmetric_difference({2, 3, 4})
        assert result == {1, 4}

    result, patches, reverse = produce(base, recipe)

    assert result == {1, 2, 3}  # Original unchanged


def test_set_update_inplace_operator():
    """Test |= operator on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        draft |= {3, 4, 5}

    result, patches, reverse = produce(base, recipe)

    assert result == {1, 2, 3, 4, 5}
    assert len(patches) == 2  # Added 4 and 5


def test_set_intersection_update():
    """Test &= operator on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        draft &= {2, 3, 4}

    result, patches, reverse = produce(base, recipe)

    assert result == {2, 3}
    assert len(patches) == 1  # Removed 1


def test_set_difference_update():
    """Test -= operator on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        draft -= {2, 4}

    result, patches, reverse = produce(base, recipe)

    assert result == {1, 3}
    assert len(patches) == 1  # Removed 2


def test_set_symmetric_difference_update():
    """Test ^= operator on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        draft ^= {2, 3, 4}

    result, patches, reverse = produce(base, recipe)

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

    result, patches, reverse = produce(base, recipe)

    assert result == base


def test_set_isdisjoint():
    """Test isdisjoint() method on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        assert draft.isdisjoint({4, 5, 6})
        assert not draft.isdisjoint({2, 4})

    result, patches, reverse = produce(base, recipe)

    assert result == base


def test_set_issubset():
    """Test issubset() method on set proxy."""
    base = {1, 2}

    def recipe(draft):
        assert draft.issubset({1, 2, 3})
        assert not draft.issubset({1})

    result, patches, reverse = produce(base, recipe)

    assert result == base


def test_set_issuperset():
    """Test issuperset() method on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        assert draft.issuperset({1, 2})
        assert not draft.issuperset({1, 2, 4})

    result, patches, reverse = produce(base, recipe)

    assert result == base


def test_set_copy():
    """Test copy() method on set proxy."""
    base = {1, 2, 3}

    def recipe(draft):
        copied = draft.copy()
        assert copied == {1, 2, 3}
        assert isinstance(copied, set)

    result, patches, reverse = produce(base, recipe)

    assert result == base
