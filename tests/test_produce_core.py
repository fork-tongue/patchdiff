"""Core tests for produce() function - complex scenarios and edge cases."""

import pytest

from patchdiff import apply, produce
from patchdiff.pointer import Pointer


def test_deeply_nested_mutation():
    """Test mutations on deeply nested structures."""
    base = {"a": {"b": {"c": [1, 2, 3]}}}

    def recipe(draft):
        draft["a"]["b"]["c"].append(4)
        draft["a"]["b"]["d"] = "new"

    result, patches, reverse = produce(base, recipe)

    assert result == {"a": {"b": {"c": [1, 2, 3, 4], "d": "new"}}}
    assert len(patches) == 2


def test_mixed_operations():
    """Test mixed operations across different types."""
    base = {"users": [{"name": "Alice", "tags": {"python", "js"}}]}

    def recipe(draft):
        draft["users"][0]["name"] = "Bob"
        draft["users"][0]["tags"].add("rust")
        draft["users"].append({"name": "Charlie", "tags": set()})

    result, patches, reverse = produce(base, recipe)

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

    result, patches, reverse = produce(base, recipe)

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

    result, patches, reverse = produce(base, recipe)

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

    result, patches, reverse = produce(base, recipe)

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

    result, patches, reverse = produce(base, recipe)

    assert result["user"]["name"] == "ALICE"
