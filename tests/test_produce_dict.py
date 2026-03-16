"""Tests for DictProxy operations in produce()."""

import pytest

from patchdiff import produce
from patchdiff.pointer import Pointer


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

    result, patches, _reverse = produce(base, recipe)

    assert result == {"a": 10, "c": 3}
    assert len(patches) == 3


def test_dict_nested():
    """Test operations on nested dicts."""
    base = {"user": {"name": "Alice", "age": 30}}

    def recipe(draft):
        draft["user"]["age"] = 31
        draft["user"]["city"] = "NYC"

    result, patches, _reverse = produce(base, recipe)

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

    result, patches, _reverse = produce(base, recipe)

    assert result == {"a": 1}
    assert len(patches) == 1
    assert patches[0]["op"] == "remove"


def test_dict_pop_invalidates_proxy_cache():
    """Test that pop() invalidates the proxy cache for nested structures."""
    base = {"nested": {"a": 1}, "other": 2}

    def recipe(draft):
        # Access nested to populate the proxy cache
        _ = draft["nested"]["a"]
        # Pop the key that has a cached proxy
        draft.pop("nested")

    result, patches, _reverse = produce(base, recipe)

    assert result == {"other": 2}
    assert len(patches) == 1
    assert patches[0]["op"] == "remove"


def test_dict_update():
    """Test dict.update() operation."""
    base = {"a": 1}

    def recipe(draft):
        draft.update({"b": 2, "c": 3})

    result, patches, _reverse = produce(base, recipe)

    assert result == {"a": 1, "b": 2, "c": 3}
    assert len(patches) == 2


def test_dict_setdefault():
    """Test dict.setdefault() operation."""
    base = {"a": 1}

    def recipe(draft):
        draft.setdefault("b", 2)
        draft.setdefault("a", 10)  # Should not change

    result, patches, _reverse = produce(base, recipe)

    assert result == {"a": 1, "b": 2}
    assert len(patches) == 1  # Only "b" was added


def test_dict_clear():
    """Test dict.clear() operation."""
    base = {"a": 1, "b": 2, "c": 3}

    def recipe(draft):
        draft.clear()

    result, patches, _reverse = produce(base, recipe)

    assert result == {}
    assert len(patches) == 3  # All keys removed


def test_dict_contains():
    """Test __contains__ (in operator) on dict proxy."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        assert "a" in draft
        assert "c" not in draft
        draft["c"] = 3

    result, _patches, _reverse = produce(base, recipe)

    assert result == {"a": 1, "b": 2, "c": 3}


def test_dict_len():
    """Test __len__ on dict proxy."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        assert len(draft) == 2
        draft["c"] = 3
        assert len(draft) == 3

    result, _patches, _reverse = produce(base, recipe)

    assert len(result) == 3


def test_dict_keys():
    """Test keys() method on dict proxy."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        keys = list(draft.keys())
        assert "a" in keys
        assert "b" in keys
        draft["c"] = 3

    result, _patches, _reverse = produce(base, recipe)

    assert "c" in result.keys()


def test_dict_items():
    """Test items() method on dict proxy."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        items = list(draft.items())
        assert ("a", 1) in items
        draft["c"] = 3

    result, _patches, _reverse = produce(base, recipe)

    assert ("c", 3) in result.items()


def test_dict_get_existing_key():
    """Test get() with existing key."""
    base = {"a": 1}

    def recipe(draft):
        value = draft.get("a")
        assert value == 1
        draft["b"] = value + 1

    result, _patches, _reverse = produce(base, recipe)

    assert result["b"] == 2


def test_dict_get_missing_key_default():
    """Test get() with missing key and default."""
    base = {"a": 1}

    def recipe(draft):
        value = draft.get("missing", 99)
        assert value == 99
        draft["b"] = value

    result, _patches, _reverse = produce(base, recipe)

    assert result["b"] == 99


def test_dict_get_missing_key_no_default():
    """Test get() with missing key and no default."""
    base = {"a": 1}

    def recipe(draft):
        value = draft.get("missing")
        assert value is None

    result, _patches, _reverse = produce(base, recipe)

    assert result == {"a": 1}


def test_dict_pop_with_default():
    """Test pop() with default value."""
    base = {"a": 1}

    def recipe(draft):
        value = draft.pop("missing", 99)
        assert value == 99

    result, patches, _reverse = produce(base, recipe)

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

    result, patches, _reverse = produce(base, recipe)

    assert len(result) == 1
    assert len(patches) == 1
    assert patches[0]["op"] == "remove"


def test_dict_popitem_invalidates_proxy_cache():
    """Test that popitem() invalidates the proxy cache for nested structures."""
    base = {"a": {"x": 1}}

    def recipe(draft):
        # Access nested to populate the proxy cache
        _ = draft["a"]["x"]
        # popitem removes the only key which has a cached proxy
        draft.popitem()

    result, patches, _reverse = produce(base, recipe)

    assert result == {}
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

    result, _patches, _reverse = produce(base, recipe)

    assert result == base


def test_dict_values():
    """Test iterating over dict values."""
    base = {"a": 1, "b": 2, "c": 3}

    def recipe(draft):
        total = sum(draft.values())
        draft["total"] = total

    result, _patches, _reverse = produce(base, recipe)

    assert result["total"] == 6


def test_dict_reversed():
    """Test __reversed__ on dict proxy."""
    base = {"a": 1, "b": 2, "c": 3}

    def recipe(draft):
        keys = list(reversed(draft))
        # Verify reversed returns keys in reverse insertion order
        assert keys == ["c", "b", "a"]

    result, patches, _reverse = produce(base, recipe)

    # No mutations, so no patches
    assert patches == []
    assert result == base


def test_dict_copy():
    """Test copy() method on dict proxy."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        copied = draft.copy()
        # Verify copy returns a real dict with same contents
        assert copied == {"a": 1, "b": 2}
        assert isinstance(copied, dict)
        # Verify it's a different object (not a proxy)
        copied["new"] = 3
        # This mutation is on the copy, not the draft

    result, patches, _reverse = produce(base, recipe)

    # No mutations to draft, so no patches
    assert patches == []
    assert result == base


def test_dict_setitem_invalidates_proxy_cache():
    """Test that __setitem__ invalidates the proxy cache for nested structures.

    When a nested structure is accessed and then replaced, the old proxy
    should be invalidated so subsequent access returns a new proxy.
    """
    base = {"nested": {"a": 1}}

    def recipe(draft):
        # Access nested to create a proxy cache entry
        _ = draft["nested"]["a"]
        # Replace the nested structure entirely
        draft["nested"] = {"b": 2}
        # Access again - should get new structure, not cached proxy
        assert dict(draft["nested"]) == {"b": 2}

    result, _patches, _reverse = produce(base, recipe)

    assert result == {"nested": {"b": 2}}


def test_dict_delitem_invalidates_proxy_cache():
    """Test that __delitem__ invalidates the proxy cache."""
    base = {"nested": {"a": 1}, "other": 2}

    def recipe(draft):
        # Access nested to create a proxy cache entry
        _ = draft["nested"]["a"]
        # Delete the nested key
        del draft["nested"]
        # Verify it's gone
        assert "nested" not in draft

    result, _patches, _reverse = produce(base, recipe)

    assert result == {"other": 2}


def test_dict_update_replaces_existing_keys():
    """Test that update() correctly replaces existing keys and invalidates cache."""
    base = {"a": {"x": 1}, "b": 2}

    def recipe(draft):
        # Access nested to create proxy cache
        _ = draft["a"]["x"]
        # Update with new values for existing keys
        draft.update({"a": {"y": 2}, "b": 3, "c": 4})
        # Verify the updates
        assert dict(draft["a"]) == {"y": 2}
        assert draft["b"] == 3
        assert draft["c"] == 4

    result, patches, _reverse = produce(base, recipe)

    assert result == {"a": {"y": 2}, "b": 3, "c": 4}
    # Should have: replace a, replace b, add c
    assert len(patches) == 3


def test_dict_update_with_iterable_of_pairs():
    """Test that update() works with an iterable of key-value pairs."""
    base = {"a": 1}

    def recipe(draft):
        # Update with a list of tuples instead of a dict
        draft.update([("b", 2), ("c", 3)])

    result, patches, _reverse = produce(base, recipe)

    assert result == {"a": 1, "b": 2, "c": 3}
    assert len(patches) == 2


def test_dict_update_with_kwargs():
    """Test that update() works with keyword arguments."""
    base = {"a": 1}

    def recipe(draft):
        draft.update(b=2, c=3)

    result, patches, _reverse = produce(base, recipe)

    assert result == {"a": 1, "b": 2, "c": 3}
    assert len(patches) == 2


def test_dict_update_with_dict_and_kwargs():
    """Test that update() works with both dict and keyword arguments."""
    base = {"a": 1}

    def recipe(draft):
        draft.update({"b": 2}, c=3, d=4)

    result, patches, _reverse = produce(base, recipe)

    assert result == {"a": 1, "b": 2, "c": 3, "d": 4}
    assert len(patches) == 3


def test_dict_update_empty():
    """Test that update() with empty dict/no args is a no-op."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        draft.update({})
        draft.update()

    result, patches, _reverse = produce(base, recipe)

    assert result == {"a": 1, "b": 2}
    assert len(patches) == 0


def test_dict_setdefault_none_implicit():
    """Test setdefault() with implicit None default."""
    base = {"a": 1}

    def recipe(draft):
        value = draft.setdefault("b")
        assert value is None

    result, patches, _reverse = produce(base, recipe)

    assert result == {"a": 1, "b": None}
    assert len(patches) == 1
    assert patches[0]["value"] is None


def test_dict_setdefault_none_explicit():
    """Test setdefault() with explicit None default."""
    base = {"a": 1}

    def recipe(draft):
        value = draft.setdefault("b", None)
        assert value is None

    result, patches, _reverse = produce(base, recipe)

    assert result == {"a": 1, "b": None}
    assert len(patches) == 1
    assert patches[0]["value"] is None


def test_dict_setdefault_return_value():
    """Test that setdefault() returns the correct value."""
    base = {"a": 1}

    def recipe(draft):
        # Return existing value
        val1 = draft.setdefault("a", 999)
        assert val1 == 1

        # Return new default value
        val2 = draft.setdefault("b", 2)
        assert val2 == 2

    result, _patches, _reverse = produce(base, recipe)

    assert result == {"a": 1, "b": 2}


def test_dict_clear_empty():
    """Test clear() on an already empty dict."""
    base = {}

    def recipe(draft):
        draft.clear()

    result, patches, _reverse = produce(base, recipe)

    assert result == {}
    assert len(patches) == 0


def test_dict_popitem_lifo_order():
    """Test that popitem() removes items in LIFO (last inserted) order."""
    base = {}

    def recipe(draft):
        # Add items in order
        draft["a"] = 1
        draft["b"] = 2
        draft["c"] = 3

        # popitem should remove last inserted (LIFO)
        key, value = draft.popitem()
        assert key == "c"
        assert value == 3

        key, value = draft.popitem()
        assert key == "b"
        assert value == 2

    result, _patches, _reverse = produce(base, recipe)

    assert result == {"a": 1}


def test_dict_get_none_implicit():
    """Test get() returns None implicitly when key missing."""
    base = {"a": 1}

    def recipe(draft):
        value = draft.get("b")
        assert value is None

    result, _patches, _reverse = produce(base, recipe)

    assert result == {"a": 1}


def test_dict_values_returns_proxied_nested():
    """Test that values() returns proxied nested objects."""
    base = {"a": {"x": 1}, "b": {"x": 2}}

    def recipe(draft):
        for v in draft.values():
            v["x"] = 99

    result, patches, _reverse = produce(base, recipe)

    assert result == {"a": {"x": 99}, "b": {"x": 99}}
    assert len(patches) == 2


def test_dict_items_returns_proxied_nested():
    """Test that items() returns proxied nested objects."""
    base = {"a": {"x": 1}, "b": {"x": 2}}

    def recipe(draft):
        for k, v in draft.items():
            v["x"] = 99

    result, patches, _reverse = produce(base, recipe)

    assert result == {"a": {"x": 99}, "b": {"x": 99}}
    assert len(patches) == 2


def test_dict_ior_operator():
    """Test |= operator (merge update) on dict proxy."""
    base = {"a": 1}

    def recipe(draft):
        draft |= {"b": 2, "c": 3}

    result, patches, _reverse = produce(base, recipe)

    assert result == {"a": 1, "b": 2, "c": 3}
    assert len(patches) == 2


def test_dict_or_operator():
    """Test | operator (merge) on dict proxy returns new dict."""
    base = {"a": 1}

    def recipe(draft):
        merged = draft | {"b": 2}
        assert isinstance(merged, dict)
        assert merged == {"a": 1, "b": 2}

    _result, patches, _reverse = produce(base, recipe)

    assert patches == []  # No mutations to draft


def test_dict_eq():
    """Test __eq__ on dict proxy."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        assert draft == {"a": 1, "b": 2}
        assert not (draft == {"a": 1})

    produce(base, recipe)


def test_dict_ne():
    """Test __ne__ on dict proxy."""
    base = {"a": 1}

    def recipe(draft):
        assert draft != {"b": 2}
        assert not (draft != {"a": 1})

    produce(base, recipe)


def test_dict_bool():
    """Test __bool__ on dict proxy."""
    base_empty = {}
    base_full = {"a": 1}

    def recipe_empty(draft):
        assert not draft

    def recipe_full(draft):
        assert draft

    produce(base_empty, recipe_empty)
    produce(base_full, recipe_full)


def test_dict_get_none_explicit():
    """Test get() with explicit None default."""
    base = {"a": 1}

    def recipe(draft):
        value = draft.get("b", None)
        assert value is None

    result, _patches, _reverse = produce(base, recipe)

    assert result == {"a": 1}
