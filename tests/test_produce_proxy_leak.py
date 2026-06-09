"""Tests showing that proxies must never leak into the result or the patches.

When a recipe reads a nested container from the draft, it receives a proxy
(DictProxy/ListProxy/SetProxy). If that proxy is then written back into the
draft (assignment, append, update, ...), the proxy object itself currently
ends up in the result data and in the recorded patch values. These tests
pin down the expected behavior: results and patches must only ever contain
plain data.
"""

import json

import pytest

from patchdiff import apply, produce, to_json
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
    import copy

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


def test_reassign_nested_dict_to_other_key():
    """Reading a nested dict and storing it under another key must store
    plain data, not the proxy wrapper."""
    base = {"a": {"x": 1}}

    def recipe(draft):
        draft["b"] = draft["a"]

    result, patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert type(result["b"]) is dict
    assert type(patches[0]["value"]) is dict
    assert result == {"a": {"x": 1}, "b": {"x": 1}}


def test_reassign_nested_list_to_other_key():
    base = {"nums": [1, 2, 3]}

    def recipe(draft):
        draft["backup"] = draft["nums"]

    result, patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert type(result["backup"]) is list
    assert type(patches[0]["value"]) is list


def test_reassign_nested_set_to_other_key():
    base = {"tags": {"a", "b"}}

    def recipe(draft):
        draft["tags_copy"] = draft["tags"]

    result, patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert type(result["tags_copy"]) is set
    assert type(patches[0]["value"]) is set


def test_append_nested_dict_to_list():
    """Appending a nested proxy to a list must not leak the proxy."""
    base = {"a": {"x": 1}, "items": []}

    def recipe(draft):
        draft["items"].append(draft["a"])

    result, patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert type(result["items"][0]) is dict
    assert type(patches[0]["value"]) is dict


def test_insert_and_extend_with_proxies():
    base = {"a": {"x": 1}, "b": [1, 2], "items": [0]}

    def recipe(draft):
        draft["items"].insert(0, draft["a"])
        draft["items"].extend([draft["b"]])

    result, _patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert type(result["items"][0]) is dict
    assert type(result["items"][-1]) is list


def test_list_setitem_with_proxy():
    base = {"a": {"x": 1}, "items": [None]}

    def recipe(draft):
        draft["items"][0] = draft["a"]

    result, _patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert type(result["items"][0]) is dict


def test_list_slice_assignment_with_proxies():
    base = {"a": {"x": 1}, "items": [1, 2, 3]}

    def recipe(draft):
        draft["items"][1:2] = [draft["a"], draft["a"]]

    result, _patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert type(result["items"][1]) is dict
    assert type(result["items"][2]) is dict


def test_dict_update_with_proxy_values():
    base = {"a": {"x": 1}}

    def recipe(draft):
        draft.update({"b": draft["a"]})

    result, patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert type(result["b"]) is dict
    assert type(patches[0]["value"]) is dict


def test_dict_setdefault_with_proxy_default():
    base = {"a": {"x": 1}}

    def recipe(draft):
        draft.setdefault("b", draft["a"])

    result, _patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert type(result["b"]) is dict


def test_move_item_between_containers():
    """A common 'move' idiom: read from one container, push into another."""
    base = {"todo": [{"task": "write tests"}], "done": []}

    def recipe(draft):
        item = draft["todo"][0]
        draft["done"].append(item)
        del draft["todo"][0]

    result, _patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert result == {"todo": [], "done": [{"task": "write tests"}]}
    assert type(result["done"][0]) is dict


def test_iteration_yields_must_not_leak():
    """Values obtained via items()/values()/iteration are proxies; storing
    them back must not leak."""
    base = {"groups": {"a": {"n": 1}, "b": {"n": 2}}, "flat": []}

    def recipe(draft):
        for _key, value in draft["groups"].items():
            draft["flat"].append(value)

    result, _patches, _reverse = assert_clean_roundtrip(base, recipe)

    assert all(type(v) is dict for v in result["flat"])


def test_reverse_patch_value_is_plain_after_delete_of_leaked_value():
    """Deleting a key whose value was assigned from a proxy must record a
    plain value in the reverse (add) patch."""
    base = {"a": {"x": 1}}

    def recipe(draft):
        draft["b"] = draft["a"]
        del draft["b"]

    _result, _patches, reverse = assert_clean_roundtrip(base, recipe)

    for patch in reverse:
        if "value" in patch:
            assert_no_proxies(patch["value"], "reverse value")


def test_patches_are_json_serializable():
    """Patches containing leaked proxies cannot be serialized."""
    base = {"a": {"x": 1}}

    def recipe(draft):
        draft["b"] = draft["a"]

    _result, patches, reverse = produce(base, recipe)

    # Must not raise
    json.loads(to_json(patches))
    json.loads(to_json(reverse))


def test_alias_then_mutate_records_consistent_patches():
    """After draft["b"] = draft["a"], mutating either path must produce
    patches that, when applied to base, reproduce the result exactly —
    no double-recording through stale proxy paths."""
    base = {"a": {"x": 1}}

    def recipe(draft):
        draft["b"] = draft["a"]
        draft["b"]["x"] = 99

    result, patches, _reverse = assert_clean_roundtrip(base, recipe)

    # The mutation of "b" must be recorded exactly once
    paths = [str(p["path"]) for p in patches]
    assert paths.count("/b/x") <= 1
    assert "/a/x" not in paths or result["a"] == {"x": 99}


def test_assign_proxy_then_mutate_original_path():
    """Mutating via the original path after aliasing: patches must still
    reproduce the result when applied to the base."""
    base = {"a": {"x": 1}}

    def recipe(draft):
        draft["b"] = draft["a"]
        draft["a"]["x"] = 42

    assert_clean_roundtrip(base, recipe)


def test_result_values_usable_after_produce():
    """A leaked proxy in the result keeps recording into a dead recorder and
    breaks basic expectations like isinstance checks and json dumps."""
    base = {"a": {"x": 1}}

    def recipe(draft):
        draft["b"] = draft["a"]

    result, _patches, _reverse = produce(base, recipe)

    # The result must be plain data: serializable and isinstance-friendly
    json.dumps(result)
    assert isinstance(result["b"], dict)


# -- Scene-tree regrouping scenarios --
# Moving items around in a hierarchical tree is a core use case. These
# patterns detach an item from one place and reattach it elsewhere,
# possibly nested inside freshly created plain containers, possibly with
# mutations while detached.


def scene_tree():
    return {"children": [{"title": "a"}, {"title": "b"}, {"title": "c"}]}


def test_regroup_pop_then_append():
    """pop() returns raw data, so this works today — guard against regression."""

    def recipe(draft):
        item = draft["children"].pop(-1)
        new_group = {"title": "New group", "children": [item]}
        draft["children"].append(new_group)

    result, _patches, _reverse = assert_clean_roundtrip(scene_tree(), recipe)

    assert result["children"][-1] == {
        "title": "New group",
        "children": [{"title": "c"}],
    }


def test_regroup_find_then_move():
    """Find an item by iterating (yields proxies), remove it, and nest it
    inside a freshly built plain dict. The proxy hides inside plain
    containers, so unwrapping must be recursive."""

    def recipe(draft):
        for child in draft["children"]:
            if child["title"] == "c":
                draft["children"].remove(child)
                new_group = {"title": "New group", "children": [child]}
                draft["children"].append(new_group)
                break

    result, _patches, _reverse = assert_clean_roundtrip(scene_tree(), recipe)

    assert result["children"][-1]["children"] == [{"title": "c"}]
    assert type(result["children"][-1]["children"][0]) is dict


def test_regroup_getitem_then_pop_then_append():
    """Item read via __getitem__ (a proxy) before being popped, then
    reattached inside a new group."""

    def recipe(draft):
        item = draft["children"][-1]
        draft["children"].pop()
        draft["children"].append({"title": "G", "children": [item]})

    result, _patches, _reverse = assert_clean_roundtrip(scene_tree(), recipe)

    assert result["children"][-1]["children"] == [{"title": "c"}]


@pytest.mark.xfail(
    reason="requires Tier 2: detached proxies must stop recording", strict=True
)
def test_regroup_mutate_while_detached():
    """Mutating an item between detach and reattach. The mutation must not
    be recorded against the stale (removed) path; the reattach snapshot
    already carries the mutated state."""

    def recipe(draft):
        item = draft["children"][-1]
        draft["children"].pop()
        item["title"] = "moved"
        draft["children"].append({"title": "G", "children": [item]})

    result, _patches, _reverse = assert_clean_roundtrip(scene_tree(), recipe)

    assert result["children"][-1]["children"] == [{"title": "moved"}]


@pytest.mark.xfail(reason="requires Tier 2: parent-linked live paths", strict=True)
def test_stale_index_path_after_insert():
    """A held proxy must not record against its old index after the list
    shifted underneath it. Currently this silently corrupts patches:
    replaying them renames the wrong element."""

    def recipe(draft):
        p = draft["children"][2]
        draft["children"].insert(0, {"title": "new"})
        p["title"] = "renamed"

    result, _patches, _reverse = assert_clean_roundtrip(scene_tree(), recipe)

    assert [c["title"] for c in result["children"]] == ["new", "a", "b", "renamed"]


@pytest.mark.xfail(reason="requires Tier 2: parent-linked live paths", strict=True)
def test_stale_index_path_after_del():
    """Same as above but shifting the other way via a deletion."""

    def recipe(draft):
        p = draft["children"][2]
        del draft["children"][0]
        p["title"] = "renamed"

    result, _patches, _reverse = assert_clean_roundtrip(scene_tree(), recipe)

    assert [c["title"] for c in result["children"]] == ["b", "renamed"]


@pytest.mark.parametrize("in_place", [False, True])
def test_no_proxy_leak_with_in_place_modes(in_place):
    """The leak must not occur in either copy or in_place mode."""
    base = {"a": {"x": 1}}

    def recipe(draft):
        draft["b"] = draft["a"]

    result, patches, _reverse = produce(base, recipe, in_place=in_place)

    assert_no_proxies(result, "result")
    for patch in patches:
        if "value" in patch:
            assert_no_proxies(patch["value"], "patch value")
