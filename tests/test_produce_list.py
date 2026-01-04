"""Tests for ListProxy operations in produce()."""

import pytest

from patchdiff import produce
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

    result, patches, _reverse = produce(base, recipe)

    assert result == [1, 10, 2, 3]
    assert len(patches) == 1
    assert patches[0] == {"op": "add", "path": Pointer([1]), "value": 10}


def test_list_pop():
    """Test popping from a list."""
    base = [1, 2, 3]

    def recipe(draft):
        value = draft.pop()
        assert value == 3

    result, patches, _reverse = produce(base, recipe)

    assert result == [1, 2]
    assert len(patches) == 1
    assert patches[0]["op"] == "remove"


def test_list_remove():
    """Test removing from a list."""
    base = [1, 2, 3, 2]

    def recipe(draft):
        draft.remove(2)  # Removes first occurrence

    result, patches, _reverse = produce(base, recipe)

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

    result, patches, _reverse = produce(base, recipe)

    assert result == [1, 3]
    assert len(patches) == 1
    assert patches[0] == {"op": "remove", "path": Pointer([1])}


def test_list_extend():
    """Test extending a list."""
    base = [1, 2]

    def recipe(draft):
        draft.extend([3, 4])

    result, patches, _reverse = produce(base, recipe)

    assert result == [1, 2, 3, 4]
    assert len(patches) == 2  # Two append operations


def test_list_clear():
    """Test clearing a list."""
    base = [1, 2, 3]

    def recipe(draft):
        draft.clear()

    result, patches, _reverse = produce(base, recipe)

    assert result == []
    assert len(patches) == 3  # All elements removed


def test_list_nested():
    """Test operations on nested lists."""
    base = {"items": [1, 2, 3]}

    def recipe(draft):
        draft["items"].append(4)
        draft["items"][0] = 10

    result, patches, _reverse = produce(base, recipe)

    assert result == {"items": [10, 2, 3, 4]}
    assert len(patches) == 2


def test_list_contains():
    """Test __contains__ (in operator) on list proxy."""
    base = [1, 2, 3]

    def recipe(draft):
        assert 2 in draft
        assert 5 not in draft
        draft.append(5)

    result, _patches, _reverse = produce(base, recipe)

    assert 5 in result


def test_list_len():
    """Test __len__ on list proxy."""
    base = [1, 2, 3]

    def recipe(draft):
        assert len(draft) == 3
        draft.append(4)
        assert len(draft) == 4

    result, _patches, _reverse = produce(base, recipe)

    assert len(result) == 4


def test_list_pop_with_index():
    """Test pop() with specific index."""
    base = [1, 2, 3, 4]

    def recipe(draft):
        value = draft.pop(1)
        assert value == 2

    result, patches, _reverse = produce(base, recipe)

    assert result == [1, 3, 4]
    assert len(patches) == 1
    assert patches[0]["op"] == "remove"


def test_list_pop_negative_index():
    """Test pop() with negative index."""
    base = [1, 2, 3, 4]

    def recipe(draft):
        value = draft.pop(-2)
        assert value == 3

    result, _patches, _reverse = produce(base, recipe)

    assert result == [1, 2, 4]


def test_list_getitem_slice():
    """Test __getitem__ with slice."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        sliced = draft[1:3]
        assert sliced == [2, 3]

    result, _patches, _reverse = produce(base, recipe)

    assert result == base


def test_list_setitem_slice():
    """Test __setitem__ with slice - same length replacement."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        draft[1:3] = [20, 30]

    result, patches, _reverse = produce(base, recipe)

    assert result == [1, 20, 30, 4, 5]
    # Should generate replace patches for indices 1 and 2
    assert len(patches) == 2
    assert patches[0]["op"] == "replace"
    assert patches[0]["path"].tokens == (1,)
    assert patches[0]["value"] == 20
    assert patches[1]["op"] == "replace"
    assert patches[1]["path"].tokens == (2,)
    assert patches[1]["value"] == 30


def test_list_setitem_slice_expand():
    """Test __setitem__ with slice - expanding (adding elements)."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        draft[1:3] = [20, 30, 40]

    result, patches, _reverse = produce(base, recipe)

    assert result == [1, 20, 30, 40, 4, 5]
    # Should replace 2 elements and add 1
    assert len(patches) == 3
    assert patches[0]["op"] == "replace"  # Replace index 1
    assert patches[1]["op"] == "replace"  # Replace index 2
    assert patches[2]["op"] == "add"  # Add at index 3


def test_list_setitem_slice_shrink():
    """Test __setitem__ with slice - shrinking (removing elements)."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        draft[1:4] = [20]

    result, patches, _reverse = produce(base, recipe)

    assert result == [1, 20, 5]
    # Should replace 1 element and remove 2
    assert len(patches) == 3
    assert patches[0]["op"] == "replace"  # Replace index 1
    assert patches[1]["op"] == "remove"  # Remove index 3
    assert patches[2]["op"] == "remove"  # Remove index 2


def test_list_setitem_slice_step():
    """Test __setitem__ with step slice."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        draft[::2] = [10, 30, 50]  # Replace indices 0, 2, 4

    result, patches, _reverse = produce(base, recipe)

    assert result == [10, 2, 30, 4, 50]
    # Should generate replace patches for indices 0, 2, 4
    assert len(patches) == 3
    assert all(p["op"] == "replace" for p in patches)


def test_list_delitem_slice():
    """Test __delitem__ with slice."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        del draft[1:3]

    result, patches, _reverse = produce(base, recipe)

    assert result == [1, 4, 5]
    # Should generate remove patches (in reverse order to maintain indices)
    assert len(patches) == 2
    assert patches[0]["op"] == "remove"
    assert patches[0]["path"].tokens == (2,)  # Remove 3 first
    assert patches[1]["op"] == "remove"
    assert patches[1]["path"].tokens == (1,)  # Then remove 2


def test_list_delitem_slice_step():
    """Test __delitem__ with step slice."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        del draft[::2]  # Delete indices 0, 2, 4

    result, patches, _reverse = produce(base, recipe)

    assert result == [2, 4]
    # Should generate remove patches for indices 0, 2, 4 (in reverse)
    assert len(patches) == 3
    assert all(p["op"] == "remove" for p in patches)


def test_list_index():
    """Test index() method on list proxy."""
    base = [1, 2, 3, 2, 4]

    def recipe(draft):
        idx = draft.index(2)
        assert idx == 1

    result, _patches, _reverse = produce(base, recipe)

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

    result, _patches, _reverse = produce(base, recipe)

    assert result.count(2) == 4


def test_list_reverse():
    """Test reverse() method on list proxy."""
    base = [1, 2, 3, 4]

    def recipe(draft):
        draft.reverse()

    result, _patches, _reverse = produce(base, recipe)

    assert result == [4, 3, 2, 1]


def test_list_sort():
    """Test sort() method on list proxy."""
    base = [3, 1, 4, 2]

    def recipe(draft):
        draft.sort()

    result, _patches, _reverse = produce(base, recipe)

    assert result == [1, 2, 3, 4]


def test_list_sort_reverse():
    """Test sort() with reverse parameter."""
    base = [3, 1, 4, 2]

    def recipe(draft):
        draft.sort(reverse=True)

    result, _patches, _reverse = produce(base, recipe)

    assert result == [4, 3, 2, 1]


def test_list_sort_with_key():
    """Test sort() with key function."""
    base = ["apple", "pie", "a", "cherry"]

    def recipe(draft):
        draft.sort(key=len)

    result, _patches, _reverse = produce(base, recipe)

    assert result == ["a", "pie", "apple", "cherry"]


def test_list_reversed():
    """Test __reversed__ on list proxy."""
    base = [1, 2, 3, 4]

    def recipe(draft):
        rev = list(reversed(draft))
        # Verify reversed returns elements in reverse order
        assert rev == [4, 3, 2, 1]

    result, patches, _reverse = produce(base, recipe)

    # No mutations, so no patches
    assert patches == []
    assert result == base


def test_list_copy():
    """Test copy() method on list proxy."""
    base = [1, 2, 3]

    def recipe(draft):
        copied = draft.copy()
        # Verify copy returns a real list with same contents
        assert copied == [1, 2, 3]
        assert isinstance(copied, list)
        # Verify it's a different object (not a proxy)
        copied.append(4)
        # This mutation is on the copy, not the draft

    result, patches, _reverse = produce(base, recipe)

    # No mutations to draft, so no patches
    assert patches == []
    assert result == base
