"""Core tests for produce() function - complex scenarios and edge cases."""

import pytest

from patchdiff import apply, produce


def assert_patches_work(base, recipe):
    """Helper to verify that patches and reverse patches work correctly.

    This applies the recipe, then verifies:
    1. Applying patches to base produces the result
    2. Applying reverse patches to result produces the base
    """
    import copy

    base_copy = copy.deepcopy(base)

    result, patches, reverse = produce(base, recipe)

    # Verify patches transform base to result
    applied = apply(base_copy, patches)
    assert applied == result, f"Patches failed: {patches}"

    # Verify reverse patches transform result back to base
    reverted = apply(result, reverse)
    assert reverted == base_copy, f"Reverse patches failed: {reverse}"

    return result, patches, reverse


def test_deeply_nested_mutation():
    """Test mutations on deeply nested structures."""
    base = {"a": {"b": {"c": [1, 2, 3]}}}

    def recipe(draft):
        draft["a"]["b"]["c"].append(4)
        draft["a"]["b"]["d"] = "new"

    result, patches, _reverse = produce(base, recipe)

    assert result == {"a": {"b": {"c": [1, 2, 3, 4], "d": "new"}}}
    assert len(patches) == 2


def test_mixed_operations():
    """Test mixed operations across different types."""
    base = {"users": [{"name": "Alice", "tags": {"python", "js"}}]}

    def recipe(draft):
        draft["users"][0]["name"] = "Bob"
        draft["users"][0]["tags"].add("rust")
        draft["users"].append({"name": "Charlie", "tags": set()})

    result, patches, _reverse = produce(base, recipe)

    assert result["users"][0]["name"] == "Bob"
    assert "rust" in result["users"][0]["tags"]
    assert len(result["users"]) == 2
    assert len(patches) == 3


def test_original_unchanged():
    """Test that the original object is not mutated."""
    base = {"a": 1, "b": [1, 2], "c": {3, 4}}

    def recipe(draft):
        draft["a"] = 10
        draft["b"].append(3)
        draft["c"].add(5)

    result, _patches, _reverse = produce(base, recipe)

    # Original should be unchanged
    assert base == {"a": 1, "b": [1, 2], "c": {3, 4}}
    # Result should have mutations
    assert result == {"a": 10, "b": [1, 2, 3], "c": {3, 4, 5}}


def test_patches_apply_correctly():
    """Test that generated patches can be applied using apply()."""
    base = {"count": 0, "items": []}

    def recipe(draft):
        draft["count"] = 5
        draft["items"].extend([1, 2, 3])

    result, patches, _reverse = produce(base, recipe)

    # Apply patches to base should give us the result
    applied = apply(base, patches)
    assert applied == result


def test_reverse_patches_work():
    """Test that reverse patches correctly undo changes."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        draft["a"] = 10
        draft["c"] = 3
        del draft["b"]

    result, _patches, reverse = produce(base, recipe)

    # Apply reverse patches to result should give us base
    reverted = apply(result, reverse)
    assert reverted == base


def test_empty_recipe():
    """Test produce with no mutations."""
    base = {"a": 1}

    def recipe(draft):
        pass  # No mutations

    result, patches, reverse = produce(base, recipe)

    assert result == base
    assert patches == []
    assert reverse == []


def test_unsupported_type():
    """Test produce with unsupported base type."""
    base = "string"

    def recipe(draft):
        pass

    with pytest.raises(TypeError):
        produce(base, recipe)


def test_reading_nested_values():
    """Test that reading nested values works correctly."""
    base = {"user": {"name": "Alice", "age": 30}}

    def recipe(draft):
        # Read nested value
        name = draft["user"]["name"]
        assert name == "Alice"
        # Modify based on read value
        draft["user"]["name"] = name.upper()

    result, _patches, _reverse = produce(base, recipe)

    assert result["user"]["name"] == "ALICE"


def test_no_patch_for_same_value_dict():
    """Test that setting a dict value to the same value produces no patch."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        draft["a"] = 1  # Same value

    result, patches, reverse = produce(base, recipe)

    assert result == {"a": 1, "b": 2}
    assert patches == [], f"Expected no patches, got {patches}"
    assert reverse == []


def test_no_patch_for_same_value_list():
    """Test that setting a list item to the same value produces no patch."""
    base = [1, 2, 3]

    def recipe(draft):
        draft[1] = 2  # Same value

    result, patches, reverse = produce(base, recipe)

    assert result == [1, 2, 3]
    assert patches == [], f"Expected no patches, got {patches}"
    assert reverse == []


def test_no_patch_for_same_nested_value():
    """Test that setting a nested value to the same value produces no patch."""
    base = {"user": {"name": "Alice", "age": 30}}

    def recipe(draft):
        draft["user"]["name"] = "Alice"  # Same value
        draft["user"]["age"] = 30  # Same value

    result, patches, reverse = produce(base, recipe)

    assert result == base
    assert patches == [], f"Expected no patches, got {patches}"
    assert reverse == []


def test_no_patch_for_update_with_same_values():
    """Test that dict.update() with same values produces no patches."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        draft.update({"a": 1, "b": 2})  # Same values

    result, patches, reverse = produce(base, recipe)

    assert result == base
    assert patches == [], f"Expected no patches, got {patches}"
    assert reverse == []


def test_no_patch_for_list_slice_same_values():
    """Test that slice assignment with same values produces no patches."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        draft[1:3] = [2, 3]  # Same values

    result, patches, reverse = produce(base, recipe)

    assert result == base
    assert patches == [], f"Expected no patches, got {patches}"
    assert reverse == []


def test_partial_patch_for_mixed_changes():
    """Test that only actual changes produce patches."""
    base = {"a": 1, "b": 2, "c": 3}

    def recipe(draft):
        draft["a"] = 1  # Same value - no patch
        draft["b"] = 20  # Different value - should patch
        draft["c"] = 3  # Same value - no patch

    result, patches, _reverse = produce(base, recipe)

    assert result == {"a": 1, "b": 20, "c": 3}
    assert len(patches) == 1
    assert patches[0]["op"] == "replace"
    assert patches[0]["path"].tokens == ("b",)
    assert patches[0]["value"] == 20


# =============================================================================
# Tests verifying patches and reverse patches actually work when applied
# =============================================================================


def test_dict_operations_patches_apply():
    """Test that dict operation patches can be applied correctly."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        draft["a"] = 10  # replace
        draft["c"] = 3  # add
        del draft["b"]  # remove

    assert_patches_work(base, recipe)


def test_dict_update_patches_apply():
    """Test that dict.update() patches can be applied correctly."""
    base = {"a": 1}

    def recipe(draft):
        draft.update({"b": 2, "c": 3})

    assert_patches_work(base, recipe)


def test_dict_pop_patches_apply():
    """Test that dict.pop() patches can be applied correctly."""
    base = {"a": 1, "b": 2, "c": 3}

    def recipe(draft):
        draft.pop("b")

    assert_patches_work(base, recipe)


def test_dict_clear_patches_apply():
    """Test that dict.clear() patches can be applied correctly."""
    base = {"a": 1, "b": 2, "c": 3}

    def recipe(draft):
        draft.clear()

    assert_patches_work(base, recipe)


def test_list_append_patches_apply():
    """Test that list.append() patches can be applied correctly."""
    base = [1, 2, 3]

    def recipe(draft):
        draft.append(4)
        draft.append(5)

    assert_patches_work(base, recipe)


def test_list_insert_patches_apply():
    """Test that list.insert() patches can be applied correctly."""
    base = [1, 2, 3]

    def recipe(draft):
        draft.insert(1, 10)

    assert_patches_work(base, recipe)


def test_list_pop_patches_apply():
    """Test that list.pop() patches can be applied correctly."""
    base = [1, 2, 3, 4]

    def recipe(draft):
        draft.pop()
        draft.pop(0)

    assert_patches_work(base, recipe)


def test_list_remove_patches_apply():
    """Test that list.remove() patches can be applied correctly."""
    base = [1, 2, 3, 2, 4]

    def recipe(draft):
        draft.remove(2)

    assert_patches_work(base, recipe)


def test_list_setitem_patches_apply():
    """Test that list setitem patches can be applied correctly."""
    base = [1, 2, 3]

    def recipe(draft):
        draft[0] = 10
        draft[-1] = 30

    assert_patches_work(base, recipe)


def test_list_delitem_patches_apply():
    """Test that list delitem patches can be applied correctly."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        del draft[2]

    assert_patches_work(base, recipe)


def test_list_extend_patches_apply():
    """Test that list.extend() patches can be applied correctly."""
    base = [1, 2]

    def recipe(draft):
        draft.extend([3, 4, 5])

    assert_patches_work(base, recipe)


def test_list_clear_patches_apply():
    """Test that list.clear() patches can be applied correctly."""
    base = [1, 2, 3]

    def recipe(draft):
        draft.clear()

    assert_patches_work(base, recipe)


def test_list_slice_setitem_patches_apply():
    """Test that list slice assignment patches can be applied correctly."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        draft[1:3] = [20, 30, 40]

    assert_patches_work(base, recipe)


def test_list_slice_delitem_patches_apply():
    """Test that list slice deletion patches can be applied correctly."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        del draft[1:4]

    assert_patches_work(base, recipe)


def test_list_reverse_patches_apply():
    """Test that list.reverse() patches can be applied correctly."""
    base = [1, 2, 3, 4]

    def recipe(draft):
        draft.reverse()

    assert_patches_work(base, recipe)


def test_list_sort_patches_apply():
    """Test that list.sort() patches can be applied correctly."""
    base = [3, 1, 4, 1, 5, 9, 2, 6]

    def recipe(draft):
        draft.sort()

    assert_patches_work(base, recipe)


def test_set_add_patches_apply():
    """Test that set.add() patches can be applied correctly."""
    base = {1, 2, 3}

    def recipe(draft):
        draft.add(4)
        draft.add(5)

    assert_patches_work(base, recipe)


def test_set_remove_patches_apply():
    """Test that set.remove() patches can be applied correctly."""
    base = {1, 2, 3, 4}

    def recipe(draft):
        draft.remove(2)

    assert_patches_work(base, recipe)


def test_set_discard_patches_apply():
    """Test that set.discard() patches can be applied correctly."""
    base = {1, 2, 3}

    def recipe(draft):
        draft.discard(2)
        draft.discard(10)  # Not present, should be no-op

    assert_patches_work(base, recipe)


def test_set_clear_patches_apply():
    """Test that set.clear() patches can be applied correctly."""
    base = {1, 2, 3}

    def recipe(draft):
        draft.clear()

    assert_patches_work(base, recipe)


def test_set_update_patches_apply():
    """Test that set.update() patches can be applied correctly."""
    base = {1, 2}

    def recipe(draft):
        draft.update({3, 4, 5})

    assert_patches_work(base, recipe)


def test_set_operators_patches_apply():
    """Test that set operator patches can be applied correctly."""
    base = {1, 2, 3, 4}

    def recipe(draft):
        draft |= {5, 6}  # union
        draft -= {1}  # difference
        draft &= {2, 3, 5, 6}  # intersection

    assert_patches_work(base, recipe)


def test_nested_operations_patches_apply():
    """Test that nested structure patches can be applied correctly."""
    base = {
        "users": [
            {"name": "Alice", "tags": {1, 2}},
            {"name": "Bob", "tags": {3, 4}},
        ],
        "count": 2,
    }

    def recipe(draft):
        draft["users"][0]["name"] = "Alicia"
        draft["users"][0]["tags"].add(5)
        draft["users"].append({"name": "Charlie", "tags": set()})
        draft["count"] = 3

    assert_patches_work(base, recipe)


def test_complex_list_operations_patches_apply():
    """Test complex list operations produce correct patches."""
    base = [{"id": 1}, {"id": 2}, {"id": 3}]

    def recipe(draft):
        draft[0]["id"] = 10
        draft.pop(1)
        draft.append({"id": 4})

    assert_patches_work(base, recipe)
