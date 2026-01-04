"""Tests for ListProxy operations in produce()."""

import pytest

from patchdiff import apply, produce
from patchdiff.pointer import Pointer


def test_list_append():
    """Test appending to a list."""
    base = [1, 2, 3]

    def recipe(draft):
        draft.append(4)

    result, patches, reverse = produce(base, recipe)

    assert result == [1, 2, 3, 4]
    assert len(patches) == 1
    assert patches[0] == {"op": "add", "path": Pointer(["-"]), "value": 4}
    assert len(reverse) == 1
    assert reverse[0] == {"op": "remove", "path": Pointer(["-"])}


def test_list_insert():
    """Test inserting into a list."""
    base = [1, 2, 3]

    def recipe(draft):
        draft.insert(1, 10)

    result, patches, reverse = produce(base, recipe)

    assert result == [1, 10, 2, 3]
    assert len(patches) == 1
    assert patches[0] == {"op": "add", "path": Pointer([1]), "value": 10}


def test_list_pop():
    """Test popping from a list."""
    base = [1, 2, 3]

    def recipe(draft):
        value = draft.pop()
        assert value == 3

    result, patches, reverse = produce(base, recipe)

    assert result == [1, 2]
    assert len(patches) == 1
    assert patches[0]["op"] == "remove"


def test_list_remove():
    """Test removing from a list."""
    base = [1, 2, 3, 2]

    def recipe(draft):
        draft.remove(2)  # Removes first occurrence

    result, patches, reverse = produce(base, recipe)

    assert result == [1, 3, 2]
    assert len(patches) == 1


def test_list_setitem():
    """Test setting an item in a list."""
    base = [1, 2, 3]

    def recipe(draft):
        draft[1] = 20

    result, patches, reverse = produce(base, recipe)

    assert result == [1, 20, 3]
    assert len(patches) == 1
    assert patches[0] == {"op": "replace", "path": Pointer([1]), "value": 20}
    assert reverse[0] == {"op": "replace", "path": Pointer([1]), "value": 2}


def test_list_delitem():
    """Test deleting an item from a list."""
    base = [1, 2, 3]

    def recipe(draft):
        del draft[1]

    result, patches, reverse = produce(base, recipe)

    assert result == [1, 3]
    assert len(patches) == 1
    assert patches[0] == {"op": "remove", "path": Pointer([1])}


def test_list_extend():
    """Test extending a list."""
    base = [1, 2]

    def recipe(draft):
        draft.extend([3, 4])

    result, patches, reverse = produce(base, recipe)

    assert result == [1, 2, 3, 4]
    assert len(patches) == 2  # Two append operations


def test_list_clear():
    """Test clearing a list."""
    base = [1, 2, 3]

    def recipe(draft):
        draft.clear()

    result, patches, reverse = produce(base, recipe)

    assert result == []
    assert len(patches) == 3  # All elements removed


def test_list_nested():
    """Test operations on nested lists."""
    base = {"items": [1, 2, 3]}

    def recipe(draft):
        draft["items"].append(4)
        draft["items"][0] = 10

    result, patches, reverse = produce(base, recipe)

    assert result == {"items": [10, 2, 3, 4]}
    assert len(patches) == 2


def test_list_contains():
    """Test __contains__ (in operator) on list proxy."""
    base = [1, 2, 3]

    def recipe(draft):
        assert 2 in draft
        assert 5 not in draft
        draft.append(5)

    result, patches, reverse = produce(base, recipe)

    assert 5 in result


def test_list_len():
    """Test __len__ on list proxy."""
    base = [1, 2, 3]

    def recipe(draft):
        assert len(draft) == 3
        draft.append(4)
        assert len(draft) == 4

    result, patches, reverse = produce(base, recipe)

    assert len(result) == 4


def test_list_pop_with_index():
    """Test pop() with specific index."""
    base = [1, 2, 3, 4]

    def recipe(draft):
        value = draft.pop(1)
        assert value == 2

    result, patches, reverse = produce(base, recipe)

    assert result == [1, 3, 4]
    assert len(patches) == 1
    assert patches[0]["op"] == "remove"


def test_list_pop_negative_index():
    """Test pop() with negative index."""
    base = [1, 2, 3, 4]

    def recipe(draft):
        value = draft.pop(-2)
        assert value == 3

    result, patches, reverse = produce(base, recipe)

    assert result == [1, 2, 4]


def test_list_getitem_slice():
    """Test __getitem__ with slice."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        sliced = draft[1:3]
        assert sliced == [2, 3]

    result, patches, reverse = produce(base, recipe)

    assert result == base


def test_list_setitem_slice():
    """Test __setitem__ with slice."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        draft[1:3] = [20, 30]

    result, patches, reverse = produce(base, recipe)

    assert result == [1, 20, 30, 4, 5]


def test_list_delitem_slice():
    """Test __delitem__ with slice."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        del draft[1:3]

    result, patches, reverse = produce(base, recipe)

    assert result == [1, 4, 5]


def test_list_index():
    """Test index() method on list proxy."""
    base = [1, 2, 3, 2, 4]

    def recipe(draft):
        idx = draft.index(2)
        assert idx == 1

    result, patches, reverse = produce(base, recipe)

    assert result == base


def test_list_index_not_found():
    """Test index() with value not in list."""
    base = [1, 2, 3]

    def recipe(draft):
        draft.index(5)

    with pytest.raises(ValueError):
        produce(base, recipe)


def test_list_count():
    """Test count() method on list proxy."""
    base = [1, 2, 3, 2, 4, 2]

    def recipe(draft):
        count = draft.count(2)
        assert count == 3
        draft.append(2)

    result, patches, reverse = produce(base, recipe)

    assert result.count(2) == 4


def test_list_reverse():
    """Test reverse() method on list proxy."""
    base = [1, 2, 3, 4]

    def recipe(draft):
        draft.reverse()

    result, patches, reverse = produce(base, recipe)

    assert result == [4, 3, 2, 1]


def test_list_sort():
    """Test sort() method on list proxy."""
    base = [3, 1, 4, 2]

    def recipe(draft):
        draft.sort()

    result, patches, reverse = produce(base, recipe)

    assert result == [1, 2, 3, 4]


def test_list_sort_reverse():
    """Test sort() with reverse parameter."""
    base = [3, 1, 4, 2]

    def recipe(draft):
        draft.sort(reverse=True)

    result, patches, reverse = produce(base, recipe)

    assert result == [4, 3, 2, 1]


def test_list_sort_with_key():
    """Test sort() with key function."""
    base = ["apple", "pie", "a", "cherry"]

    def recipe(draft):
        draft.sort(key=len)

    result, patches, reverse = produce(base, recipe)

    assert result == ["a", "pie", "apple", "cherry"]


def test_list_reversed():
    """Test __reversed__ on list proxy."""
    base = [1, 2, 3, 4]

    def recipe(draft):
        rev = list(reversed(draft))
        assert rev == [4, 3, 2, 1]

    result, patches, reverse = produce(base, recipe)

    assert result == base


def test_list_copy():
    """Test copy() method on list proxy."""
    base = [1, 2, 3]

    def recipe(draft):
        copied = draft.copy()
        assert copied == [1, 2, 3]
        assert isinstance(copied, list)

    result, patches, reverse = produce(base, recipe)

    assert result == base
