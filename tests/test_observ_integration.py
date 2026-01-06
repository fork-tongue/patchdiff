"""Test integration with observ reactive objects."""

import pytest

try:
    from observ import reactive, watch

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


def test_watcher_triggered_on_in_place_dict_mutation():
    """Test that observ watchers are triggered when using produce(in_place=True) on dicts."""
    state = reactive({"count": 0, "name": "Alice"})
    changes = []

    def callback(new_val, old_val):
        changes.append(("count", new_val, old_val))

    # Create a synchronous watcher on the count field
    watcher = watch(lambda: state["count"], callback, sync=True)

    def recipe(draft):
        draft["count"] = 5
        draft["name"] = "Bob"

    result, patches, _reverse = produce(state, recipe, in_place=True)

    # Watcher should have been triggered
    assert len(changes) == 1
    assert changes[0] == ("count", 5, 0)

    # State should be mutated
    assert state["count"] == 5
    assert state["name"] == "Bob"


def test_watcher_triggered_on_in_place_list_mutation():
    """Test that observ watchers are triggered when using produce(in_place=True) on lists."""
    state = reactive([1, 2, 3])
    changes = []

    def callback(new_val, old_val):
        changes.append(("first", new_val, old_val))

    # Create a synchronous watcher on the first element
    watcher = watch(lambda: state[0], callback, sync=True)

    def recipe(draft):
        draft[0] = 10
        draft.append(4)

    result, patches, _reverse = produce(state, recipe, in_place=True)

    # Watcher should have been triggered
    assert len(changes) == 1
    assert changes[0] == ("first", 10, 1)

    # State should be mutated
    assert state == [10, 2, 3, 4]


def test_watcher_triggered_on_nested_mutation():
    """Test that observ watchers are triggered for nested mutations with produce(in_place=True)."""
    state = reactive({"user": {"name": "Alice", "age": 30}})
    changes = []

    def callback(new_val, old_val):
        changes.append(("age", new_val, old_val))

    # Create a synchronous watcher on nested field
    watcher = watch(lambda: state["user"]["age"], callback, sync=True)

    def recipe(draft):
        draft["user"]["age"] = 31

    result, patches, _reverse = produce(state, recipe, in_place=True)

    # Watcher should have been triggered
    assert len(changes) == 1
    assert changes[0] == ("age", 31, 30)

    # State should be mutated
    assert state["user"]["age"] == 31


def test_watcher_not_triggered_without_in_place():
    """Test that observ watchers are NOT triggered when using produce() without in_place."""
    state = reactive({"count": 0})
    changes = []

    def callback(new_val, old_val):
        changes.append(("count", new_val, old_val))

    # Create a synchronous watcher
    watcher = watch(lambda: state["count"], callback, sync=True)

    def recipe(draft):
        draft["count"] = 5

    # Without in_place=True, the original state should not be mutated
    result, patches, _reverse = produce(state, recipe)

    # Watcher should NOT have been triggered (original not mutated)
    assert len(changes) == 0

    # Original state should be unchanged
    assert state["count"] == 0
    # But result should have the new value
    assert result["count"] == 5


def test_multiple_watchers_triggered():
    """Test that multiple watchers are all triggered on in_place mutations."""
    state = reactive({"a": 1, "b": 2})
    changes_a = []
    changes_b = []

    def callback_a(new_val, old_val):
        changes_a.append((new_val, old_val))

    def callback_b(new_val, old_val):
        changes_b.append((new_val, old_val))

    # Create synchronous watchers on both fields
    watcher_a = watch(lambda: state["a"], callback_a, sync=True)
    watcher_b = watch(lambda: state["b"], callback_b, sync=True)

    def recipe(draft):
        draft["a"] = 10
        draft["b"] = 20

    result, patches, _reverse = produce(state, recipe, in_place=True)

    # Both watchers should have been triggered
    assert len(changes_a) == 1
    assert changes_a[0] == (10, 1)
    assert len(changes_b) == 1
    assert changes_b[0] == (20, 2)


def test_watcher_triggered_on_list_append():
    """Test that observ watchers are triggered when appending to a list with in_place."""
    state = reactive({"items": [1, 2, 3]})
    changes = []

    def callback(new_val, old_val):
        changes.append(("length", new_val, old_val))

    # Watch the length of the list
    watcher = watch(lambda: len(state["items"]), callback, sync=True)

    def recipe(draft):
        draft["items"].append(4)
        draft["items"].append(5)

    result, patches, _reverse = produce(state, recipe, in_place=True)

    # Watcher should have been triggered (possibly multiple times for each append)
    assert len(changes) >= 1
    # Final length should be 5
    assert len(state["items"]) == 5
    assert state["items"] == [1, 2, 3, 4, 5]


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
