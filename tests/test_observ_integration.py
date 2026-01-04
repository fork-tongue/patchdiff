"""Test integration with observ reactive objects."""

import pytest

try:
    from observ import reactive

    OBSERV_AVAILABLE = True
except ImportError:
    OBSERV_AVAILABLE = False

from patchdiff import apply, produce

pytestmark = pytest.mark.skipif(not OBSERV_AVAILABLE, reason="observ not installed")


def test_produce_with_reactive_dict():
    """Test that produce() works with observ reactive dicts."""
    # Create a reactive object
    state = reactive({"count": 0, "name": "Alice"})

    def recipe(draft):
        draft["count"] = 5
        draft["name"] = "Bob"

    # This should work with reactive objects
    result, patches, _reverse = produce(state, recipe)

    assert result["count"] == 5
    assert result["name"] == "Bob"
    assert len(patches) == 2


def test_produce_with_reactive_list():
    """Test that produce() works with observ reactive lists."""
    state = reactive([1, 2, 3])

    def recipe(draft):
        draft.append(4)
        draft[0] = 10

    result, patches, _reverse = produce(state, recipe)

    assert result == [10, 2, 3, 4]
    assert len(patches) == 2


def test_produce_with_nested_reactive():
    """Test that produce() works with nested reactive structures."""
    state = reactive({"user": {"name": "Alice", "age": 30}})

    def recipe(draft):
        draft["user"]["age"] = 31
        draft["user"]["city"] = "NYC"

    result, patches, _reverse = produce(state, recipe)

    assert result["user"]["age"] == 31
    assert result["user"]["city"] == "NYC"
    assert len(patches) == 2


def test_patches_apply_to_reactive_result():
    """Test that patches generated from reactive objects can be applied."""
    state = reactive({"a": 1, "b": 2})

    def recipe(draft):
        draft["a"] = 10
        draft["c"] = 3

    result, patches, _reverse = produce(state, recipe)

    # Apply patches to the original (non-reactive) data
    original_data = {"a": 1, "b": 2}
    applied = apply(original_data, patches)

    assert applied == result


def test_produce_does_not_affect_original_reactive():
    """Test that produce() doesn't mutate the original reactive object."""
    original_state = {"count": 0}
    state = reactive(original_state)

    def recipe(draft):
        draft["count"] = 10

    result, _patches, _reverse = produce(state, recipe)

    # The result should be different
    assert result["count"] == 10
    # But the original should be unchanged
    assert state["count"] == 0
    assert original_state["count"] == 0


def test_produce_in_place_mutates_original():
    """Test that produce(in_place=True) mutates the original object."""
    state = {"count": 0, "items": [1, 2, 3]}

    def recipe(draft):
        draft["count"] = 10
        draft["items"].append(4)

    result, patches, _reverse = produce(state, recipe, in_place=True)

    # Result should be the same object
    assert result is state
    # Original should be mutated
    assert state["count"] == 10
    assert state["items"] == [1, 2, 3, 4]
    # Patches should still be generated
    assert len(patches) == 2


def test_produce_in_place_with_reactive_mutates_state():
    """Test that produce(in_place=True) mutates reactive objects directly."""
    state = reactive({"count": 0, "name": "Alice"})

    def recipe(draft):
        draft["count"] = 5
        draft["name"] = "Bob"

    result, patches, _reverse = produce(state, recipe, in_place=True)

    # Result should be the same object
    assert result is state
    # State should be mutated
    assert state["count"] == 5
    assert state["name"] == "Bob"
    # Patches should be generated
    assert len(patches) == 2
    assert patches[0]["op"] == "replace"
    assert patches[0]["value"] == 5


def test_produce_in_place_with_nested_reactive():
    """Test that produce(in_place=True) works with nested reactive structures."""
    state = reactive({"user": {"name": "Alice", "age": 30}, "count": 0})

    def recipe(draft):
        draft["user"]["age"] = 31
        draft["count"] = 1

    result, patches, _reverse = produce(state, recipe, in_place=True)

    # State should be mutated
    assert state["user"]["age"] == 31
    assert state["count"] == 1
    # Result is the same object
    assert result is state
    # Patches should be generated
    assert len(patches) == 2


def test_produce_in_place_with_reactive_list():
    """Test that produce(in_place=True) works with reactive lists."""
    state = reactive([1, 2, 3])

    def recipe(draft):
        draft.append(4)
        draft[0] = 10

    result, patches, _reverse = produce(state, recipe, in_place=True)

    # State should be mutated
    assert state == [10, 2, 3, 4]
    # Result is the same object
    assert result is state
    # Patches should be generated
    assert len(patches) == 2
