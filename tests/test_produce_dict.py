"""Tests for DictProxy operations in produce()."""

import pytest

from patchdiff import apply, produce
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


def test_dict_values():
    """Test iterating over dict values."""
    base = {"a": 1, "b": 2, "c": 3}

    def recipe(draft):
        total = sum(draft.values())
        draft["total"] = total

    result, patches, reverse = produce(base, recipe)

    assert result["total"] == 6
