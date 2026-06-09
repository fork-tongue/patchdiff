"""Tests for live path tracking of proxies handed out by produce().

Proxies track their location through parent links, so a held reference
stays correct while the tree changes around it: list shifts reindex it,
removal detaches it (mutations are no longer recorded but still applied
to its data), and assigning a detached proxy back into the draft
re-attaches it at its new location (move semantics).
"""

import copy

from patchdiff import apply, produce
from patchdiff.produce import DictProxy, ListProxy, SetProxy

PROXY_TYPES = (DictProxy, ListProxy, SetProxy)


def assert_no_proxies(value, path="$"):
    """Recursively assert that value contains no proxy objects."""
    assert not isinstance(value, PROXY_TYPES), f"proxy leaked at {path}: {value!r}"
    if isinstance(value, dict):
        for key, item in value.items():
            assert_no_proxies(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple, set)):
        for i, item in enumerate(value):
            assert_no_proxies(item, f"{path}[{i}]")


def assert_clean_roundtrip(base, recipe):
    """Run produce() and assert results/patches are proxy-free and consistent."""
    base_copy = copy.deepcopy(base)

    result, patches, reverse = produce(base, recipe)

    assert_no_proxies(result, "result")
    for i, patch in enumerate(patches):
        if "value" in patch:
            assert_no_proxies(patch["value"], f"patches[{i}].value")
    for i, patch in enumerate(reverse):
        if "value" in patch:
            assert_no_proxies(patch["value"], f"reverse[{i}].value")

    applied = apply(base_copy, patches)
    assert applied == result, f"patches do not reproduce result: {patches}"

    reverted = apply(result, reverse)
    assert reverted == base_copy, f"reverse patches do not restore base: {reverse}"

    return result, patches, reverse


def scene_tree():
    return {"children": [{"title": "a"}, {"title": "b"}, {"title": "c"}]}


# -- Re-attachment (move semantics) --


def test_move_via_pop_and_setitem_keeps_reference_live():
    """Assigning a detached proxy directly re-attaches it: later mutations
    through the held reference are recorded at the new path."""

    def recipe(draft):
        item = draft["children"][-1]
        draft["children"].pop()
        draft["moved"] = item
        item["title"] = "moved"  # must record at /moved/title

    result, patches, _reverse = assert_clean_roundtrip(scene_tree(), recipe)

    assert result["moved"] == {"title": "moved"}
    assert "/moved/title" in [str(p["path"]) for p in patches]


def test_move_via_append_keeps_reference_live():
    """Appending a detached proxy directly re-attaches it at its new index."""

    def recipe(draft):
        item = draft["children"][0]
        del draft["children"][0]
        draft["children"].append(item)
        item["title"] = "first-to-last"  # must record at /children/2/title

    result, patches, _reverse = assert_clean_roundtrip(scene_tree(), recipe)

    assert result["children"][-1] == {"title": "first-to-last"}
    assert "/children/2/title" in [str(p["path"]) for p in patches]


def test_reattached_subtree_children_are_live_again():
    """Child proxies of a detached subtree become live again when the
    subtree is re-attached: their paths recompute through the new location."""
    base = {"group": {"items": [{"x": 1}]}, "out": []}

    def recipe(draft):
        group = draft["group"]
        items = group["items"]
        del draft["group"]  # detaches group and, transitively, items
        items.append({"x": 2})  # not recorded; carried by the re-attach
        draft["out"].append(group)  # re-attach at /out/0
        items[0]["x"] = 99  # must record at /out/0/items/0/x

    result, patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert result["out"][0]["items"] == [{"x": 99}, {"x": 2}]
    assert "/out/0/items/0/x" in [str(p["path"]) for p in patches]


def test_self_assignment_keeps_reference_live():
    """draft["a"] = draft["a"] is a no-op that must not orphan the proxy."""
    base = {"a": {"x": 1}}

    def recipe(draft):
        p = draft["a"]
        draft["a"] = p
        p["x"] = 5  # must still record at /a/x

    result, patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert result == {"a": {"x": 5}}
    assert [str(p["path"]) for p in patches] == ["/a/x"]


def test_attached_proxy_assignment_copies():
    """A proxy still attached elsewhere is copied, not aliased: mutations
    through the original afterwards only affect the original path."""
    base = {"a": {"x": 1}}

    def recipe(draft):
        draft["b"] = draft["a"]  # copy: "a" is still attached
        draft["a"]["x"] = 42

    result, _patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert result == {"a": {"x": 42}, "b": {"x": 1}}


def test_detached_proxy_cannot_become_its_own_descendant():
    """Adopting a detached ancestor into its own subtree must not create a
    parent-link cycle (it falls back to copying)."""
    base = {"a": {"b": {}}}

    def recipe(draft):
        a = draft["a"]
        del draft["a"]
        a["self"] = a  # would create a cycle; must copy instead

    result, _patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert result == {}


# -- Detached proxies stop recording --


def test_mutation_through_replaced_value_not_recorded():
    """Replacing a key detaches the old value's proxy; mutations through
    the held reference no longer affect the draft or the patches."""
    base = {"a": {"x": 1}}

    def recipe(draft):
        p = draft["a"]
        draft["a"] = {"x": 2}
        p["x"] = 99  # detached: not recorded, not in result

    result, patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert result == {"a": {"x": 2}}
    assert len(patches) == 1


def test_mutation_through_cleared_container_not_recorded():
    base = {"items": [{"x": 1}]}

    def recipe(draft):
        p = draft["items"][0]
        draft["items"].clear()
        p["x"] = 99  # detached: not recorded

    result, patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert result == {"items": []}
    assert all("99" not in str(p) for p in patches)


def test_mutation_through_child_of_detached_subtree_not_recorded():
    """Detachment is transitive: children of a removed subtree must not
    record either."""
    base = {"group": {"items": [{"x": 1}]}}

    def recipe(draft):
        items = draft["group"]["items"]
        del draft["group"]
        items.append({"x": 2})  # not recorded

    result, patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert result == {}
    assert len(patches) == 1  # only the remove


# -- Held proxies survive index shifts --


def test_proxy_live_after_multiple_inserts_and_dels():
    def recipe(draft):
        p = draft["children"][1]  # "b"
        draft["children"].insert(0, {"title": "x"})  # b -> 2
        draft["children"].insert(0, {"title": "y"})  # b -> 3
        del draft["children"][1]  # b -> 2
        p["title"] = "B"

    result, _patches, _reverse = assert_clean_roundtrip(scene_tree(), recipe)

    assert [c["title"] for c in result["children"]] == ["y", "a", "B", "c"]


def test_proxy_live_after_slice_assignment_shift():
    base = {"items": [{"t": "a"}, {"t": "b"}, {"t": "c"}, {"t": "d"}]}

    def recipe(draft):
        p = draft["items"][3]
        draft["items"][1:3] = [{"t": "x"}]  # shrink by one: p moves to 2
        p["t"] = "D"

    result, _patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert [i["t"] for i in result["items"]] == ["a", "x", "D"]


def test_proxy_live_after_slice_deletion():
    base = {"items": [{"t": "a"}, {"t": "b"}, {"t": "c"}, {"t": "d"}]}

    def recipe(draft):
        p = draft["items"][3]
        del draft["items"][0:2]  # p moves to 1
        p["t"] = "D"

    result, _patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert [i["t"] for i in result["items"]] == ["c", "D"]


def test_proxy_replaced_by_slice_assignment_is_detached():
    base = {"items": [{"t": "a"}, {"t": "b"}]}

    def recipe(draft):
        p = draft["items"][0]
        draft["items"][0:1] = [{"t": "x"}]
        p["t"] = "A"  # detached: not recorded

    result, _patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert [i["t"] for i in result["items"]] == ["x", "b"]


def test_proxy_live_after_reverse():
    def recipe(draft):
        p = draft["children"][0]  # "a"
        draft["children"].reverse()  # a moves to index 2
        p["title"] = "A"

    result, _patches, _reverse = assert_clean_roundtrip(scene_tree(), recipe)

    assert [c["title"] for c in result["children"]] == ["c", "b", "A"]


def test_proxy_live_after_sort():
    base = {"items": [{"k": 3}, {"k": 1}, {"k": 2}]}

    def recipe(draft):
        p = draft["items"][0]  # {"k": 3}, will move to index 2
        draft["items"].sort(key=lambda item: item["k"])
        p["k"] = 30

    result, _patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert [i["k"] for i in result["items"]] == [1, 2, 30]


def test_proxy_live_after_pop_of_earlier_index():
    def recipe(draft):
        p = draft["children"][2]
        draft["children"].pop(0)  # p moves to 1
        p["title"] = "C"

    result, _patches, _reverse = assert_clean_roundtrip(scene_tree(), recipe)

    assert [c["title"] for c in result["children"]] == ["b", "C"]


def test_proxy_live_after_remove_of_earlier_element():
    def recipe(draft):
        p = draft["children"][1]
        draft["children"].remove(draft["children"][0])  # p moves to 0
        p["title"] = "B"

    result, _patches, _reverse = assert_clean_roundtrip(scene_tree(), recipe)

    assert [c["title"] for c in result["children"]] == ["B", "c"]


# -- Full regroup scenario from the scene-tree use case --


def test_full_regroup_scenario():
    """Find items, remove them from their parents, group them under a new
    node, and keep editing them afterwards through the held references."""
    base = {
        "children": [
            {"title": "a", "children": []},
            {"title": "b", "children": []},
            {"title": "c", "children": []},
        ]
    }

    def recipe(draft):
        # Collect proxies first (iteration yields proxies)
        to_group = [c for c in draft["children"] if c["title"] in ("b", "c")]
        # Remove them from the root (reverse order keeps indices valid)
        for child in reversed(to_group):
            draft["children"].remove(child)
        # Build the new group; nested detached proxies are copied with
        # their current data
        new_group = {"title": "Group", "children": to_group}
        draft["children"].append(new_group)
        # Edit through the draft afterwards
        draft["children"][1]["children"][0]["title"] = "b!"

    result, _patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert [c["title"] for c in result["children"]] == ["a", "Group"]
    assert [c["title"] for c in result["children"][1]["children"]] == ["b!", "c"]
