"""Core tests for produce() function - complex scenarios and edge cases."""

import pytest

from patchdiff import apply, produce


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
