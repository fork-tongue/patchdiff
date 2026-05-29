"""Test that produce's patch values remain usable after deepcopy.

When produce(in_place=True) records patches on reactive state, it calls
deepcopy() on proxy values. Without observ's __deepcopy__ fix, the
deepcopy'd values are zombie proxies (unregistered in proxy_db) that
crash when inserted back into reactive state and accessed by watchers.

Fix: https://github.com/fork-tongue/observ/pull/165
"""

import pytest

try:
    from observ import reactive, watch

    OBSERV_AVAILABLE = True
except ImportError:
    OBSERV_AVAILABLE = False

from patchdiff import iapply, produce

pytestmark = pytest.mark.skipif(not OBSERV_AVAILABLE, reason="observ not installed")


def test_produce_in_place_undo_redo_with_deep_watcher():
    """Simulates undo/redo on reactive state with a deep watcher.

    1. Mutates reactive state in-place (grouping items) to generate patches
    2. Applies reverse patches (undo) to restore original state
    3. Applies forward patches (redo) to re-apply the mutation

    Without the fix, step 2 already crashes: iapply calls deepcopy on the
    patch values (which are reactive proxies stored during produce), creating
    zombie proxies that the deep watcher tries to traverse when they are
    inserted into the reactive state.
    """
    state = reactive(
        {
            "children": [
                {"obj_id": "a", "name": "Item A", "children": []},
                {"obj_id": "b", "name": "Item B", "children": []},
                {"obj_id": "c", "name": "Item C", "children": []},
            ]
        }
    )

    # Deep watcher that traverses all nested state (like collagraph's v-for does)
    observed = []
    _watcher = watch(
        lambda: state["children"],
        lambda val: observed.append(val),
        sync=True,
        deep=True,
    )

    def recipe(draft):
        # Group items a and b into a new group
        items = [draft["children"].pop(0), draft["children"].pop(0)]
        draft["children"].insert(
            0, {"obj_id": "group1", "name": "Group", "children": items}
        )

    # produce calls deepcopy on the values read from reactive state when
    # recording patches. The resulting patch values are reactive proxies.
    _result, patches, reverse_patches = produce(state, recipe, in_place=True)

    # After grouping: [group1, c] = 2 children
    assert len(state["children"]) == 2

    # Undo: iapply calls deepcopy on the reverse patch values (which are
    # reactive proxies). Without the fix, deepcopy creates zombie proxies
    # that get inserted into state. The deep watcher traverses them and
    # crashes with KeyError in proxy_db.attrs().
    iapply(state, reverse_patches)
    assert len(state["children"]) == 3

    # Redo: apply forward patches — iapply calls deepcopy on patch values
    # and inserts them into reactive state. The deep watcher traverses
    # these values, which also crashes without the fix.
    iapply(state, patches)
    assert len(state["children"]) == 2
