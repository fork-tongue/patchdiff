"""Tests for proxy-based patch generation."""

import pytest

from patchdiff import apply, produce
from patchdiff.pointer import Pointer


# Dict operations


def test_dict_add_key():
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


def test_dict_remove_key():
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


def test_dict_replace_value():
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


def test_dict_multiple_operations():
    """Test multiple operations on a dict."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        draft["a"] = 10
        draft["c"] = 3
        del draft["b"]

    result, patches, reverse = produce(base, recipe)

    assert result == {"a": 10, "c": 3}
    assert len(patches) == 3


def test_dict_nested():
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


def test_dict_pop():
    """Test dict.pop() operation."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        value = draft.pop("b")
        assert value == 2

    result, patches, reverse = produce(base, recipe)

    assert result == {"a": 1}
    assert len(patches) == 1
    assert patches[0]["op"] == "remove"


def test_dict_update():
    """Test dict.update() operation."""
    base = {"a": 1}

    def recipe(draft):
        draft.update({"b": 2, "c": 3})

    result, patches, reverse = produce(base, recipe)

    assert result == {"a": 1, "b": 2, "c": 3}
    assert len(patches) == 2


def test_dict_setdefault():
    """Test dict.setdefault() operation."""
    base = {"a": 1}

    def recipe(draft):
        draft.setdefault("b", 2)
        draft.setdefault("a", 10)  # Should not change

    result, patches, reverse = produce(base, recipe)

    assert result == {"a": 1, "b": 2}
    assert len(patches) == 1  # Only "b" was added


def test_dict_clear():
    """Test dict.clear() operation."""
    base = {"a": 1, "b": 2, "c": 3}

    def recipe(draft):
        draft.clear()

    result, patches, reverse = produce(base, recipe)

    assert result == {}
    assert len(patches) == 3  # All keys removed


# List operations


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


# Set operations


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


# Complex scenarios


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


# Edge cases


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


def test_iterating_over_proxy():
    """Test that we can iterate over proxy objects."""
    base = {"a": 1, "b": 2, "c": 3}

    def recipe(draft):
        total = sum(draft.values())
        draft["total"] = total

    result, patches, reverse = produce(base, recipe)

    assert result["total"] == 6


# Additional DictProxy tests


def test_dict_contains():
    """Test __contains__ (in operator) on dict proxy."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        assert "a" in draft
        assert "c" not in draft
        draft["c"] = 3

    result, patches, reverse = produce(base, recipe)

    assert result == {"a": 1, "b": 2, "c": 3}


def test_dict_len():
    """Test __len__ on dict proxy."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        assert len(draft) == 2
        draft["c"] = 3
        assert len(draft) == 3

    result, patches, reverse = produce(base, recipe)

    assert len(result) == 3


def test_dict_keys():
    """Test keys() method on dict proxy."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        keys = list(draft.keys())
        assert "a" in keys
        assert "b" in keys
        draft["c"] = 3

    result, patches, reverse = produce(base, recipe)

    assert "c" in result.keys()


def test_dict_items():
    """Test items() method on dict proxy."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        items = list(draft.items())
        assert ("a", 1) in items
        draft["c"] = 3

    result, patches, reverse = produce(base, recipe)

    assert ("c", 3) in result.items()


def test_dict_get_existing_key():
    """Test get() with existing key."""
    base = {"a": 1}

    def recipe(draft):
        value = draft.get("a")
        assert value == 1
        draft["b"] = value + 1

    result, patches, reverse = produce(base, recipe)

    assert result["b"] == 2


def test_dict_get_missing_key_default():
    """Test get() with missing key and default."""
    base = {"a": 1}

    def recipe(draft):
        value = draft.get("missing", 99)
        assert value == 99
        draft["b"] = value

    result, patches, reverse = produce(base, recipe)

    assert result["b"] == 99


def test_dict_get_missing_key_no_default():
    """Test get() with missing key and no default."""
    base = {"a": 1}

    def recipe(draft):
        value = draft.get("missing")
        assert value is None

    result, patches, reverse = produce(base, recipe)

    assert result == {"a": 1}


def test_dict_pop_with_default():
    """Test pop() with default value."""
    base = {"a": 1}

    def recipe(draft):
        value = draft.pop("missing", 99)
        assert value == 99

    result, patches, reverse = produce(base, recipe)

    assert result == {"a": 1}
    assert len(patches) == 0  # No mutations


def test_dict_pop_missing_key_no_default():
    """Test pop() with missing key and no default raises KeyError."""
    base = {"a": 1}

    def recipe(draft):
        draft.pop("missing")

    with pytest.raises(KeyError):
        produce(base, recipe)


def test_dict_popitem():
    """Test popitem() method on dict proxy."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        key, value = draft.popitem()
        assert key in ("a", "b")
        assert value in (1, 2)

    result, patches, reverse = produce(base, recipe)

    assert len(result) == 1
    assert len(patches) == 1
    assert patches[0]["op"] == "remove"


def test_dict_popitem_empty():
    """Test popitem() on empty dict raises KeyError."""
    base = {}

    def recipe(draft):
        draft.popitem()

    with pytest.raises(KeyError):
        produce(base, recipe)


def test_dict_iter():
    """Test iterating over dict keys."""
    base = {"a": 1, "b": 2, "c": 3}

    def recipe(draft):
        keys = []
        for key in draft:
            keys.append(key)
        assert set(keys) == {"a", "b", "c"}

    result, patches, reverse = produce(base, recipe)

    assert result == base


# Additional ListProxy tests


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


# Additional SetProxy tests


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
