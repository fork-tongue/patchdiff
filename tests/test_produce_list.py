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
    # Reverse patch uses actual index (3) instead of "-" for correct application
    assert reverse[0] == {"op": "remove", "path": Pointer([3])}


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


def test_list_negative_index_nested_mutation():
    """Test that negative indices generate correct paths for nested mutations.

    This tests a bug where accessing nested structures via negative indices
    would cache the proxy with the negative index and generate incorrect paths.
    For example, draft[-1]["name"] = "new" on a 3-element list should generate
    a path of [2, "name"], not [-1, "name"].
    """
    base = [{"name": "first"}, {"name": "second"}, {"name": "third"}]

    def recipe(draft):
        # Access via negative index and mutate nested structure
        draft[-1]["name"] = "THIRD"
        draft[-2]["name"] = "SECOND"

    result, patches, _reverse = produce(base, recipe)

    assert result == [{"name": "first"}, {"name": "SECOND"}, {"name": "THIRD"}]
    assert len(patches) == 2

    # Verify paths use positive indices, not negative
    # draft[-1] on a 3-element list should resolve to index 2
    # draft[-2] on a 3-element list should resolve to index 1
    patch_paths = [tuple(p["path"].tokens) for p in patches]
    assert (2, "name") in patch_paths, f"Expected (2, 'name') in {patch_paths}"
    assert (1, "name") in patch_paths, f"Expected (1, 'name') in {patch_paths}"

    # Verify no negative indices in paths
    for patch in patches:
        for token in patch["path"].tokens:
            if isinstance(token, int):
                assert token >= 0, (
                    f"Found negative index {token} in path {patch['path']}"
                )


def test_list_negative_index_cache_consistency():
    """Test that accessing same element via positive and negative index returns same proxy.

    If we access draft[2] and draft[-1] on a 3-element list, both should
    refer to the same underlying element and mutations should be consistent.
    """
    base = [{"a": 1}, {"b": 2}, {"c": 3}]

    def recipe(draft):
        # Access via negative index first
        draft[-1]["c"] = 30
        # Access via positive index - should see the mutation
        assert draft[2]["c"] == 30
        # Mutate via positive index
        draft[2]["d"] = 4
        # Verify via negative index
        assert draft[-1]["d"] == 4

    result, patches, _reverse = produce(base, recipe)

    assert result[2] == {"c": 30, "d": 4}
    # All paths should use positive indices
    for patch in patches:
        for token in patch["path"].tokens:
            if isinstance(token, int):
                assert token >= 0, (
                    f"Found negative index {token} in path {patch['path']}"
                )


def test_list_slice_returns_wrapped_nested_structures():
    """Test that slicing a list returns wrapped proxies for nested structures.

    When accessing a slice of a list containing nested dicts/lists/sets,
    mutations to those nested structures should be tracked and generate patches.
    """
    base = [{"a": 1}, {"b": 2}, {"c": 3}, {"d": 4}]

    def recipe(draft):
        # Get a slice of the list
        sliced = draft[1:3]
        # sliced should be [{"b": 2}, {"c": 3}]
        # Mutate a nested structure obtained from the slice
        sliced[0]["b"] = 20
        sliced[1]["c"] = 30

    result, patches, _reverse = produce(base, recipe)

    # Verify the mutations took effect
    assert result == [{"a": 1}, {"b": 20}, {"c": 30}, {"d": 4}]

    # Verify patches were generated for the nested mutations
    assert len(patches) == 2
    patch_paths = [tuple(p["path"].tokens) for p in patches]
    assert (1, "b") in patch_paths, f"Expected (1, 'b') in {patch_paths}"
    assert (2, "c") in patch_paths, f"Expected (2, 'c') in {patch_paths}"


def test_list_slice_nested_list_mutation():
    """Test that slicing works with nested lists."""
    base = [[1, 2], [3, 4], [5, 6]]

    def recipe(draft):
        sliced = draft[0:2]
        sliced[0].append(99)
        sliced[1][0] = 30

    result, patches, _reverse = produce(base, recipe)

    assert result == [[1, 2, 99], [30, 4], [5, 6]]
    assert len(patches) == 2


def test_list_slice_with_step_nested_mutation():
    """Test that slicing with step returns wrapped nested structures."""
    base = [{"a": 1}, {"b": 2}, {"c": 3}, {"d": 4}, {"e": 5}]

    def recipe(draft):
        # Get every other element: indices 0, 2, 4
        sliced = draft[::2]
        sliced[0]["a"] = 10  # Mutate index 0
        sliced[2]["e"] = 50  # Mutate index 4

    result, patches, _reverse = produce(base, recipe)

    assert result == [{"a": 10}, {"b": 2}, {"c": 3}, {"d": 4}, {"e": 50}]
    assert len(patches) == 2
    patch_paths = [tuple(p["path"].tokens) for p in patches]
    assert (0, "a") in patch_paths
    assert (4, "e") in patch_paths


def test_list_setitem_negative_index():
    """Test that __setitem__ with negative index generates correct path.

    Setting draft[-1] = value on a 3-element list should generate a patch
    with path [2], not [-1].
    """
    base = [1, 2, 3]

    def recipe(draft):
        draft[-1] = 30
        draft[-2] = 20

    result, patches, _reverse = produce(base, recipe)

    assert result == [1, 20, 30]
    assert len(patches) == 2

    # Verify paths use positive indices
    patch_paths = [tuple(p["path"].tokens) for p in patches]
    assert (2,) in patch_paths, f"Expected (2,) in {patch_paths}"
    assert (1,) in patch_paths, f"Expected (1,) in {patch_paths}"

    # Verify no negative indices in paths
    for patch in patches:
        for token in patch["path"].tokens:
            if isinstance(token, int):
                assert token >= 0, (
                    f"Found negative index {token} in path {patch['path']}"
                )


def test_list_delitem_negative_index():
    """Test that __delitem__ with negative index generates correct path.

    Deleting draft[-1] on a 3-element list should generate a patch
    with path [2], not [-1].
    """
    base = [1, 2, 3, 4]

    def recipe(draft):
        del draft[-1]  # Delete 4, which is at index 3

    result, patches, _reverse = produce(base, recipe)

    assert result == [1, 2, 3]
    assert len(patches) == 1
    assert patches[0]["op"] == "remove"

    # Verify path uses positive index (3, not -1)
    assert patches[0]["path"].tokens == (3,), (
        f"Expected (3,), got {patches[0]['path'].tokens}"
    )


def test_list_delitem_negative_index_multiple():
    """Test multiple deletions with negative indices."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        del draft[-1]  # Delete 5 at index 4
        del draft[-2]  # Delete 3 at index 2 (list is now [1,2,3,4])

    result, patches, _reverse = produce(base, recipe)

    assert result == [1, 2, 4]
    assert len(patches) == 2

    # First deletion should be at index 4
    assert patches[0]["path"].tokens == (4,)
    # Second deletion should be at index 2 (after first deletion, list is [1,2,3,4])
    assert patches[1]["path"].tokens == (2,)


def test_list_setitem_negative_index_nested():
    """Test that __setitem__ with negative index works for nested structure replacement."""
    base = [{"a": 1}, {"b": 2}, {"c": 3}]

    def recipe(draft):
        draft[-1] = {"c": 30}

    result, patches, _reverse = produce(base, recipe)

    assert result == [{"a": 1}, {"b": 2}, {"c": 30}]
    assert len(patches) == 1
    assert patches[0]["path"].tokens == (2,)
    assert patches[0]["op"] == "replace"


def test_list_directly_containing_sets():
    """Test that sets directly inside lists are properly wrapped and tracked."""
    base = [{1, 2, 3}, {4, 5, 6}]

    def recipe(draft):
        # Access the sets directly in the list and mutate them
        draft[0].add(10)
        draft[1].remove(5)

    result, patches, _reverse = produce(base, recipe)

    assert result[0] == {1, 2, 3, 10}
    assert result[1] == {4, 6}
    assert len(patches) == 2


def test_list_containing_set_nested_mutation():
    """Test that sets nested inside lists are properly wrapped and tracked."""
    base = [{"tags": {1, 2, 3}}, {"tags": {4, 5}}]

    def recipe(draft):
        # Access the set inside the list and mutate it
        draft[0]["tags"].add(10)
        draft[1]["tags"].remove(4)

    result, patches, _reverse = produce(base, recipe)

    assert result[0]["tags"] == {1, 2, 3, 10}
    assert result[1]["tags"] == {4, 5} - {4}
    assert len(patches) == 2


def test_list_setitem_invalidates_proxy_cache():
    """Test that __setitem__ invalidates the proxy cache for nested structures."""
    base = [{"a": 1}, {"b": 2}]

    def recipe(draft):
        # Access nested to create a proxy cache entry
        _ = draft[0]["a"]
        # Replace the nested structure entirely
        draft[0] = {"c": 3}
        # Access again - should get new structure, not cached proxy
        assert dict(draft[0]) == {"c": 3}

    result, _patches, _reverse = produce(base, recipe)

    assert result == [{"c": 3}, {"b": 2}]


def test_list_setitem_slice_step_length_mismatch():
    """Test that step slice assignment raises ValueError on length mismatch."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        # Try to assign 2 values to 3 positions (indices 0, 2, 4)
        draft[::2] = [10, 20]  # This should fail

    with pytest.raises(ValueError, match="attempt to assign sequence of size 2"):
        produce(base, recipe)


def test_list_insert_at_beginning():
    """Test insert() at index 0 (beginning)."""
    base = [1, 2, 3]

    def recipe(draft):
        draft.insert(0, 0)

    result, patches, _reverse = produce(base, recipe)

    assert result == [0, 1, 2, 3]
    assert len(patches) == 1
    assert patches[0]["op"] == "add"
    assert patches[0]["path"].tokens == (0,)


def test_list_insert_beyond_length():
    """Test insert() with index > len (appends to end)."""
    base = [1, 2, 3]

    def recipe(draft):
        draft.insert(100, 4)

    result, patches, _reverse = produce(base, recipe)

    assert result == [1, 2, 3, 4]
    # Should add at the end
    assert len(patches) == 1


def test_list_insert_negative_index():
    """Test insert() with negative index."""
    base = [1, 2, 3]

    def recipe(draft):
        draft.insert(-1, 99)  # Insert before last element

    result, _patches, _reverse = produce(base, recipe)

    assert result == [1, 2, 99, 3]


def test_list_insert_large_negative_index():
    """Test insert() with large negative index (inserts at beginning)."""
    base = [1, 2, 3]

    def recipe(draft):
        draft.insert(-100, 0)

    result, _patches, _reverse = produce(base, recipe)

    assert result == [0, 1, 2, 3]


def test_list_pop_empty():
    """Test pop() on empty list raises IndexError."""
    base = []

    def recipe(draft):
        draft.pop()

    with pytest.raises(IndexError, match="list index out of range"):
        produce(base, recipe)


def test_list_pop_out_of_range():
    """Test pop() with out-of-range index raises IndexError."""
    base = [1, 2, 3]

    def recipe(draft):
        draft.pop(10)

    with pytest.raises(IndexError, match="list index out of range"):
        produce(base, recipe)


def test_list_remove_not_found():
    """Test remove() with element not in list raises ValueError."""
    base = [1, 2, 3]

    def recipe(draft):
        draft.remove(99)

    with pytest.raises(ValueError, match="not in list"):
        produce(base, recipe)


def test_list_remove_first_occurrence():
    """Test remove() removes only first occurrence."""
    base = [1, 2, 3, 2, 4]

    def recipe(draft):
        draft.remove(2)

    result, patches, _reverse = produce(base, recipe)

    assert result == [1, 3, 2, 4]  # First 2 removed
    assert len(patches) == 1


def test_list_extend_with_tuple():
    """Test extend() with tuple."""
    base = [1, 2]

    def recipe(draft):
        draft.extend((3, 4, 5))

    result, patches, _reverse = produce(base, recipe)

    assert result == [1, 2, 3, 4, 5]
    assert len(patches) == 3


def test_list_extend_with_empty():
    """Test extend() with empty iterable (no-op)."""
    base = [1, 2, 3]

    def recipe(draft):
        draft.extend([])

    result, patches, _reverse = produce(base, recipe)

    assert result == [1, 2, 3]
    assert len(patches) == 0


def test_list_clear_empty():
    """Test clear() on already empty list."""
    base = []

    def recipe(draft):
        draft.clear()

    result, patches, _reverse = produce(base, recipe)

    assert result == []
    assert len(patches) == 0


def test_list_reverse_empty():
    """Test reverse() on empty list."""
    base = []

    def recipe(draft):
        draft.reverse()

    result, patches, _reverse = produce(base, recipe)

    assert result == []
    assert len(patches) == 0


def test_list_reverse_single_element():
    """Test reverse() on single-element list."""
    base = [1]

    def recipe(draft):
        draft.reverse()

    result, patches, _reverse = produce(base, recipe)

    assert result == [1]
    assert len(patches) == 0


def test_list_sort_empty():
    """Test sort() on empty list."""
    base = []

    def recipe(draft):
        draft.sort()

    result, patches, _reverse = produce(base, recipe)

    assert result == []
    assert len(patches) == 0


def test_list_sort_single_element():
    """Test sort() on single-element list."""
    base = [1]

    def recipe(draft):
        draft.sort()

    result, patches, _reverse = produce(base, recipe)

    assert result == [1]
    assert len(patches) == 0


def test_list_sort_with_key_and_reverse():
    """Test sort() with both key and reverse parameters."""
    base = ["apple", "pie", "a", "longer"]

    def recipe(draft):
        draft.sort(key=len, reverse=True)

    result, patches, _reverse = produce(base, recipe)

    assert result == ["longer", "apple", "pie", "a"]
    # Should have patches for changed positions
    assert len(patches) > 0


def test_list_index_with_start():
    """Test index() with start parameter."""
    base = [1, 2, 3, 2, 4]

    def recipe(draft):
        # Find first 2
        idx1 = draft.index(2)
        assert idx1 == 1

        # Find second 2 by starting search after first
        idx2 = draft.index(2, 2)
        assert idx2 == 3

    result, _patches, _reverse = produce(base, recipe)

    assert result == base


def test_list_index_with_start_and_end():
    """Test index() with start and end parameters."""
    base = [1, 2, 3, 4, 5, 2, 6]

    def recipe(draft):
        # Search for 2 in slice [0:4]
        idx1 = draft.index(2, 0, 4)
        assert idx1 == 1

        # Search for 2 in slice [4:] - should find the second 2
        idx2 = draft.index(2, 4)
        assert idx2 == 5

    result, _patches, _reverse = produce(base, recipe)

    assert result == base


def test_list_index_with_negative_indices():
    """Test index() with negative start/end indices."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        # Search last 3 elements
        idx = draft.index(4, -3)
        assert idx == 3

    result, _patches, _reverse = produce(base, recipe)

    assert result == base


def test_list_count_not_in_list():
    """Test count() with element not in list returns 0."""
    base = [1, 2, 3]

    def recipe(draft):
        c = draft.count(99)
        assert c == 0

    result, _patches, _reverse = produce(base, recipe)

    assert result == base


def test_list_count_empty_list():
    """Test count() on empty list returns 0."""
    base = []

    def recipe(draft):
        c = draft.count(1)
        assert c == 0

    result, _patches, _reverse = produce(base, recipe)

    assert result == []


def test_list_iter_returns_proxied_nested():
    """Test that __iter__ returns proxied nested objects."""
    base = [{"x": 1}, {"x": 2}]

    def recipe(draft):
        for item in draft:
            item["x"] = 99

    result, patches, _reverse = produce(base, recipe)

    assert result == [{"x": 99}, {"x": 99}]
    assert len(patches) == 2


def test_list_reversed_returns_proxied_nested():
    """Test that __reversed__ returns proxied nested objects."""
    base = [{"x": 1}, {"x": 2}]

    def recipe(draft):
        for item in reversed(draft):
            item["x"] = 99

    result, patches, _reverse = produce(base, recipe)

    assert result == [{"x": 99}, {"x": 99}]
    assert len(patches) == 2


def test_list_iadd_operator():
    """Test += operator (in-place add, like extend) on list proxy."""
    base = [1, 2]

    def recipe(draft):
        draft += [3, 4]

    result, patches, _reverse = produce(base, recipe)

    assert result == [1, 2, 3, 4]
    assert len(patches) == 2


def test_list_imul_operator():
    """Test *= operator (in-place repeat) on list proxy."""
    base = [1, 2]

    def recipe(draft):
        draft *= 3

    result, patches, _reverse = produce(base, recipe)

    assert result == [1, 2, 1, 2, 1, 2]
    assert len(patches) == 4  # 4 new elements added


def test_list_imul_zero():
    """Test *= 0 clears the list."""
    base = [1, 2, 3]

    def recipe(draft):
        draft *= 0

    result, patches, _reverse = produce(base, recipe)

    assert result == []
    assert len(patches) == 3  # 3 elements removed


def test_list_add_operator():
    """Test + operator returns new list, not a proxy."""
    base = [1, 2]

    def recipe(draft):
        new = draft + [3, 4]
        assert isinstance(new, list)
        assert new == [1, 2, 3, 4]

    result, patches, _reverse = produce(base, recipe)

    assert patches == []


def test_list_mul_operator():
    """Test * operator returns new list, not a proxy."""
    base = [1, 2]

    def recipe(draft):
        new = draft * 3
        assert isinstance(new, list)
        assert new == [1, 2, 1, 2, 1, 2]

    result, patches, _reverse = produce(base, recipe)

    assert patches == []


def test_list_rmul_operator():
    """Test reverse * operator (int * list) returns new list."""
    base = [1, 2]

    def recipe(draft):
        new = 3 * draft
        assert isinstance(new, list)
        assert new == [1, 2, 1, 2, 1, 2]

    result, patches, _reverse = produce(base, recipe)

    assert patches == []


def test_list_eq():
    """Test __eq__ on list proxy."""
    base = [1, 2, 3]

    def recipe(draft):
        assert draft == [1, 2, 3]
        assert not (draft == [1, 2])

    produce(base, recipe)


def test_list_ne():
    """Test __ne__ on list proxy."""
    base = [1, 2, 3]

    def recipe(draft):
        assert draft != [1, 2]
        assert not (draft != [1, 2, 3])

    produce(base, recipe)


def test_list_bool():
    """Test __bool__ on list proxy."""

    def recipe_empty(draft):
        assert not draft

    def recipe_full(draft):
        assert draft

    produce([], recipe_empty)
    produce([1], recipe_full)


def test_list_lt_le_gt_ge():
    """Test comparison operators on list proxy."""
    base = [1, 2, 3]

    def recipe(draft):
        assert draft < [1, 2, 4]
        assert draft <= [1, 2, 3]
        assert draft > [1, 2, 2]
        assert draft >= [1, 2, 3]

    produce(base, recipe)
