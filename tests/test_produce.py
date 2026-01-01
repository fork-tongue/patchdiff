"""Tests for proxy-based patch generation."""

import pytest

from patchdiff import apply, produce
from patchdiff.pointer import Pointer


class TestProduceDictOperations:
    """Test produce() with dict operations."""

    def test_add_key(self):
        """Test adding a new key to a dict."""
        base = {"a": 1}

        def recipe(draft):
            draft["b"] = 2

        result, patches, reverse = produce(base, recipe)

        assert result == {"a": 1, "b": 2}
        assert len(patches) == 1
        assert patches[0] == {"op": "add", "path": Pointer(["b"]), "value": 2}
        assert len(reverse) == 1
        assert reverse[0] == {"op": "remove", "path": Pointer(["b"])}

    def test_remove_key(self):
        """Test removing a key from a dict."""
        base = {"a": 1, "b": 2}

        def recipe(draft):
            del draft["b"]

        result, patches, reverse = produce(base, recipe)

        assert result == {"a": 1}
        assert len(patches) == 1
        assert patches[0] == {"op": "remove", "path": Pointer(["b"])}
        assert len(reverse) == 1
        assert reverse[0] == {"op": "add", "path": Pointer(["b"]), "value": 2}

    def test_replace_value(self):
        """Test replacing a value in a dict."""
        base = {"a": 1}

        def recipe(draft):
            draft["a"] = 2

        result, patches, reverse = produce(base, recipe)

        assert result == {"a": 2}
        assert len(patches) == 1
        assert patches[0] == {"op": "replace", "path": Pointer(["a"]), "value": 2}
        assert len(reverse) == 1
        assert reverse[0] == {"op": "replace", "path": Pointer(["a"]), "value": 1}

    def test_multiple_operations(self):
        """Test multiple operations on a dict."""
        base = {"a": 1, "b": 2}

        def recipe(draft):
            draft["a"] = 10
            draft["c"] = 3
            del draft["b"]

        result, patches, reverse = produce(base, recipe)

        assert result == {"a": 10, "c": 3}
        assert len(patches) == 3

    def test_nested_dict(self):
        """Test operations on nested dicts."""
        base = {"user": {"name": "Alice", "age": 30}}

        def recipe(draft):
            draft["user"]["age"] = 31
            draft["user"]["city"] = "NYC"

        result, patches, reverse = produce(base, recipe)

        assert result == {"user": {"name": "Alice", "age": 31, "city": "NYC"}}
        assert len(patches) == 2
        # Check that patches have correct nested paths
        age_patch = next(p for p in patches if "age" in p["path"].tokens)
        assert age_patch["path"] == Pointer(["user", "age"])
        assert age_patch["value"] == 31

    def test_dict_pop(self):
        """Test dict.pop() operation."""
        base = {"a": 1, "b": 2}

        def recipe(draft):
            value = draft.pop("b")
            assert value == 2

        result, patches, reverse = produce(base, recipe)

        assert result == {"a": 1}
        assert len(patches) == 1
        assert patches[0]["op"] == "remove"

    def test_dict_update(self):
        """Test dict.update() operation."""
        base = {"a": 1}

        def recipe(draft):
            draft.update({"b": 2, "c": 3})

        result, patches, reverse = produce(base, recipe)

        assert result == {"a": 1, "b": 2, "c": 3}
        assert len(patches) == 2

    def test_dict_setdefault(self):
        """Test dict.setdefault() operation."""
        base = {"a": 1}

        def recipe(draft):
            draft.setdefault("b", 2)
            draft.setdefault("a", 10)  # Should not change

        result, patches, reverse = produce(base, recipe)

        assert result == {"a": 1, "b": 2}
        assert len(patches) == 1  # Only "b" was added

    def test_dict_clear(self):
        """Test dict.clear() operation."""
        base = {"a": 1, "b": 2, "c": 3}

        def recipe(draft):
            draft.clear()

        result, patches, reverse = produce(base, recipe)

        assert result == {}
        assert len(patches) == 3  # All keys removed


class TestProduceListOperations:
    """Test produce() with list operations."""

    def test_append(self):
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

    def test_insert(self):
        """Test inserting into a list."""
        base = [1, 2, 3]

        def recipe(draft):
            draft.insert(1, 10)

        result, patches, reverse = produce(base, recipe)

        assert result == [1, 10, 2, 3]
        assert len(patches) == 1
        assert patches[0] == {"op": "add", "path": Pointer([1]), "value": 10}

    def test_pop(self):
        """Test popping from a list."""
        base = [1, 2, 3]

        def recipe(draft):
            value = draft.pop()
            assert value == 3

        result, patches, reverse = produce(base, recipe)

        assert result == [1, 2]
        assert len(patches) == 1
        assert patches[0]["op"] == "remove"

    def test_remove(self):
        """Test removing from a list."""
        base = [1, 2, 3, 2]

        def recipe(draft):
            draft.remove(2)  # Removes first occurrence

        result, patches, reverse = produce(base, recipe)

        assert result == [1, 3, 2]
        assert len(patches) == 1

    def test_setitem(self):
        """Test setting an item in a list."""
        base = [1, 2, 3]

        def recipe(draft):
            draft[1] = 20

        result, patches, reverse = produce(base, recipe)

        assert result == [1, 20, 3]
        assert len(patches) == 1
        assert patches[0] == {"op": "replace", "path": Pointer([1]), "value": 20}
        assert reverse[0] == {"op": "replace", "path": Pointer([1]), "value": 2}

    def test_delitem(self):
        """Test deleting an item from a list."""
        base = [1, 2, 3]

        def recipe(draft):
            del draft[1]

        result, patches, reverse = produce(base, recipe)

        assert result == [1, 3]
        assert len(patches) == 1
        assert patches[0] == {"op": "remove", "path": Pointer([1])}

    def test_extend(self):
        """Test extending a list."""
        base = [1, 2]

        def recipe(draft):
            draft.extend([3, 4])

        result, patches, reverse = produce(base, recipe)

        assert result == [1, 2, 3, 4]
        assert len(patches) == 2  # Two append operations

    def test_clear(self):
        """Test clearing a list."""
        base = [1, 2, 3]

        def recipe(draft):
            draft.clear()

        result, patches, reverse = produce(base, recipe)

        assert result == []
        assert len(patches) == 3  # All elements removed

    def test_nested_list(self):
        """Test operations on nested lists."""
        base = {"items": [1, 2, 3]}

        def recipe(draft):
            draft["items"].append(4)
            draft["items"][0] = 10

        result, patches, reverse = produce(base, recipe)

        assert result == {"items": [10, 2, 3, 4]}
        assert len(patches) == 2


class TestProduceSetOperations:
    """Test produce() with set operations."""

    def test_add(self):
        """Test adding to a set."""
        base = {1, 2, 3}

        def recipe(draft):
            draft.add(4)

        result, patches, reverse = produce(base, recipe)

        assert result == {1, 2, 3, 4}
        assert len(patches) == 1
        assert patches[0] == {"op": "add", "path": Pointer(["-"]), "value": 4}

    def test_remove(self):
        """Test removing from a set."""
        base = {1, 2, 3}

        def recipe(draft):
            draft.remove(2)

        result, patches, reverse = produce(base, recipe)

        assert result == {1, 3}
        assert len(patches) == 1
        assert patches[0] == {"op": "remove", "path": Pointer([2])}
        assert reverse[0] == {"op": "add", "path": Pointer([2]), "value": 2}

    def test_discard(self):
        """Test discarding from a set."""
        base = {1, 2, 3}

        def recipe(draft):
            draft.discard(2)
            draft.discard(10)  # Doesn't raise error

        result, patches, reverse = produce(base, recipe)

        assert result == {1, 3}
        assert len(patches) == 1  # Only removal of 2

    def test_update(self):
        """Test updating a set."""
        base = {1, 2}

        def recipe(draft):
            draft.update({3, 4})

        result, patches, reverse = produce(base, recipe)

        assert result == {1, 2, 3, 4}
        assert len(patches) == 2

    def test_clear(self):
        """Test clearing a set."""
        base = {1, 2, 3}

        def recipe(draft):
            draft.clear()

        result, patches, reverse = produce(base, recipe)

        assert result == set()
        assert len(patches) == 3


class TestProduceComplexScenarios:
    """Test produce() with complex nested structures."""

    def test_deeply_nested_mutation(self):
        """Test mutations on deeply nested structures."""
        base = {"a": {"b": {"c": [1, 2, 3]}}}

        def recipe(draft):
            draft["a"]["b"]["c"].append(4)
            draft["a"]["b"]["d"] = "new"

        result, patches, reverse = produce(base, recipe)

        assert result == {"a": {"b": {"c": [1, 2, 3, 4], "d": "new"}}}
        assert len(patches) == 2

    def test_mixed_operations(self):
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

    def test_original_unchanged(self):
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

    def test_patches_apply_correctly(self):
        """Test that generated patches can be applied using apply()."""
        base = {"count": 0, "items": []}

        def recipe(draft):
            draft["count"] = 5
            draft["items"].extend([1, 2, 3])

        result, patches, reverse = produce(base, recipe)

        # Apply patches to base should give us the result
        applied = apply(base, patches)
        assert applied == result

    def test_reverse_patches_work(self):
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


class TestProduceEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_recipe(self):
        """Test produce with no mutations."""
        base = {"a": 1}

        def recipe(draft):
            pass  # No mutations

        result, patches, reverse = produce(base, recipe)

        assert result == base
        assert patches == []
        assert reverse == []

    def test_unsupported_type(self):
        """Test produce with unsupported base type."""
        base = "string"

        def recipe(draft):
            pass

        with pytest.raises(TypeError):
            produce(base, recipe)

    def test_reading_nested_values(self):
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

    def test_iterating_over_proxy(self):
        """Test that we can iterate over proxy objects."""
        base = {"a": 1, "b": 2, "c": 3}

        def recipe(draft):
            total = sum(draft.values())
            draft["total"] = total

        result, patches, reverse = produce(base, recipe)

        assert result["total"] == 6
