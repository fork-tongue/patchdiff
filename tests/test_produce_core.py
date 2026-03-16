"""Core tests for produce() function - complex scenarios and edge cases."""

import pytest

from patchdiff import apply, produce
from patchdiff.produce import DictProxy, ListProxy, SetProxy


def assert_patches_work(base, recipe):
    """Helper to verify that patches and reverse patches work correctly.

    This applies the recipe, then verifies:
    1. Applying patches to base produces the result
    2. Applying reverse patches to result produces the base
    """
    import copy

    base_copy = copy.deepcopy(base)

    result, patches, reverse = produce(base, recipe)

    # Verify patches transform base to result
    applied = apply(base_copy, patches)
    assert applied == result, f"Patches failed: {patches}"

    # Verify reverse patches transform result back to base
    reverted = apply(result, reverse)
    assert reverted == base_copy, f"Reverse patches failed: {reverse}"

    return result, patches, reverse


def test_deeply_nested_mutation():
    """Test mutations on deeply nested structures."""
    base = {"a": {"b": {"c": [1, 2, 3]}}}

    def recipe(draft):
        draft["a"]["b"]["c"].append(4)
        draft["a"]["b"]["d"] = "new"

    result, patches, _reverse = produce(base, recipe)

    assert result == {"a": {"b": {"c": [1, 2, 3, 4], "d": "new"}}}
    assert len(patches) == 2


def test_mixed_operations():
    """Test mixed operations across different types."""
    base = {"users": [{"name": "Alice", "tags": {"python", "js"}}]}

    def recipe(draft):
        draft["users"][0]["name"] = "Bob"
        draft["users"][0]["tags"].add("rust")
        draft["users"].append({"name": "Charlie", "tags": set()})

    result, patches, _reverse = produce(base, recipe)

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

    result, _patches, _reverse = produce(base, recipe)

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

    result, patches, _reverse = produce(base, recipe)

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

    result, _patches, reverse = produce(base, recipe)

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

    result, _patches, _reverse = produce(base, recipe)

    assert result["user"]["name"] == "ALICE"


def test_no_patch_for_same_value_dict():
    """Test that setting a dict value to the same value produces no patch."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        draft["a"] = 1  # Same value

    result, patches, reverse = produce(base, recipe)

    assert result == {"a": 1, "b": 2}
    assert patches == [], f"Expected no patches, got {patches}"
    assert reverse == []


def test_no_patch_for_same_value_list():
    """Test that setting a list item to the same value produces no patch."""
    base = [1, 2, 3]

    def recipe(draft):
        draft[1] = 2  # Same value

    result, patches, reverse = produce(base, recipe)

    assert result == [1, 2, 3]
    assert patches == [], f"Expected no patches, got {patches}"
    assert reverse == []


def test_no_patch_for_same_nested_value():
    """Test that setting a nested value to the same value produces no patch."""
    base = {"user": {"name": "Alice", "age": 30}}

    def recipe(draft):
        draft["user"]["name"] = "Alice"  # Same value
        draft["user"]["age"] = 30  # Same value

    result, patches, reverse = produce(base, recipe)

    assert result == base
    assert patches == [], f"Expected no patches, got {patches}"
    assert reverse == []


def test_no_patch_for_update_with_same_values():
    """Test that dict.update() with same values produces no patches."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        draft.update({"a": 1, "b": 2})  # Same values

    result, patches, reverse = produce(base, recipe)

    assert result == base
    assert patches == [], f"Expected no patches, got {patches}"
    assert reverse == []


def test_no_patch_for_list_slice_same_values():
    """Test that slice assignment with same values produces no patches."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        draft[1:3] = [2, 3]  # Same values

    result, patches, reverse = produce(base, recipe)

    assert result == base
    assert patches == [], f"Expected no patches, got {patches}"
    assert reverse == []


def test_partial_patch_for_mixed_changes():
    """Test that only actual changes produce patches."""
    base = {"a": 1, "b": 2, "c": 3}

    def recipe(draft):
        draft["a"] = 1  # Same value - no patch
        draft["b"] = 20  # Different value - should patch
        draft["c"] = 3  # Same value - no patch

    result, patches, _reverse = produce(base, recipe)

    assert result == {"a": 1, "b": 20, "c": 3}
    assert len(patches) == 1
    assert patches[0]["op"] == "replace"
    assert patches[0]["path"].tokens == ("b",)
    assert patches[0]["value"] == 20


# =============================================================================
# Tests verifying patches and reverse patches actually work when applied
# =============================================================================


def test_dict_operations_patches_apply():
    """Test that dict operation patches can be applied correctly."""
    base = {"a": 1, "b": 2}

    def recipe(draft):
        draft["a"] = 10  # replace
        draft["c"] = 3  # add
        del draft["b"]  # remove

    assert_patches_work(base, recipe)


def test_dict_update_patches_apply():
    """Test that dict.update() patches can be applied correctly."""
    base = {"a": 1}

    def recipe(draft):
        draft.update({"b": 2, "c": 3})

    assert_patches_work(base, recipe)


def test_dict_pop_patches_apply():
    """Test that dict.pop() patches can be applied correctly."""
    base = {"a": 1, "b": 2, "c": 3}

    def recipe(draft):
        draft.pop("b")

    assert_patches_work(base, recipe)


def test_dict_clear_patches_apply():
    """Test that dict.clear() patches can be applied correctly."""
    base = {"a": 1, "b": 2, "c": 3}

    def recipe(draft):
        draft.clear()

    assert_patches_work(base, recipe)


def test_list_append_patches_apply():
    """Test that list.append() patches can be applied correctly."""
    base = [1, 2, 3]

    def recipe(draft):
        draft.append(4)
        draft.append(5)

    assert_patches_work(base, recipe)


def test_list_insert_patches_apply():
    """Test that list.insert() patches can be applied correctly."""
    base = [1, 2, 3]

    def recipe(draft):
        draft.insert(1, 10)

    assert_patches_work(base, recipe)


def test_list_pop_patches_apply():
    """Test that list.pop() patches can be applied correctly."""
    base = [1, 2, 3, 4]

    def recipe(draft):
        draft.pop()
        draft.pop(0)

    assert_patches_work(base, recipe)


def test_list_remove_patches_apply():
    """Test that list.remove() patches can be applied correctly."""
    base = [1, 2, 3, 2, 4]

    def recipe(draft):
        draft.remove(2)

    assert_patches_work(base, recipe)


def test_list_setitem_patches_apply():
    """Test that list setitem patches can be applied correctly."""
    base = [1, 2, 3]

    def recipe(draft):
        draft[0] = 10
        draft[-1] = 30

    assert_patches_work(base, recipe)


def test_list_delitem_patches_apply():
    """Test that list delitem patches can be applied correctly."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        del draft[2]

    assert_patches_work(base, recipe)


def test_list_extend_patches_apply():
    """Test that list.extend() patches can be applied correctly."""
    base = [1, 2]

    def recipe(draft):
        draft.extend([3, 4, 5])

    assert_patches_work(base, recipe)


def test_list_clear_patches_apply():
    """Test that list.clear() patches can be applied correctly."""
    base = [1, 2, 3]

    def recipe(draft):
        draft.clear()

    assert_patches_work(base, recipe)


def test_list_slice_setitem_patches_apply():
    """Test that list slice assignment patches can be applied correctly."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        draft[1:3] = [20, 30, 40]

    assert_patches_work(base, recipe)


def test_list_slice_delitem_patches_apply():
    """Test that list slice deletion patches can be applied correctly."""
    base = [1, 2, 3, 4, 5]

    def recipe(draft):
        del draft[1:4]

    assert_patches_work(base, recipe)


def test_list_reverse_patches_apply():
    """Test that list.reverse() patches can be applied correctly."""
    base = [1, 2, 3, 4]

    def recipe(draft):
        draft.reverse()

    assert_patches_work(base, recipe)


def test_list_sort_patches_apply():
    """Test that list.sort() patches can be applied correctly."""
    base = [3, 1, 4, 1, 5, 9, 2, 6]

    def recipe(draft):
        draft.sort()

    assert_patches_work(base, recipe)


def test_set_add_patches_apply():
    """Test that set.add() patches can be applied correctly."""
    base = {1, 2, 3}

    def recipe(draft):
        draft.add(4)
        draft.add(5)

    assert_patches_work(base, recipe)


def test_set_remove_patches_apply():
    """Test that set.remove() patches can be applied correctly."""
    base = {1, 2, 3, 4}

    def recipe(draft):
        draft.remove(2)

    assert_patches_work(base, recipe)


def test_set_discard_patches_apply():
    """Test that set.discard() patches can be applied correctly."""
    base = {1, 2, 3}

    def recipe(draft):
        draft.discard(2)
        draft.discard(10)  # Not present, should be no-op

    assert_patches_work(base, recipe)


def test_set_clear_patches_apply():
    """Test that set.clear() patches can be applied correctly."""
    base = {1, 2, 3}

    def recipe(draft):
        draft.clear()

    assert_patches_work(base, recipe)


def test_set_update_patches_apply():
    """Test that set.update() patches can be applied correctly."""
    base = {1, 2}

    def recipe(draft):
        draft.update({3, 4, 5})

    assert_patches_work(base, recipe)


def test_set_operators_patches_apply():
    """Test that set operator patches can be applied correctly."""
    base = {1, 2, 3, 4}

    def recipe(draft):
        draft |= {5, 6}  # union
        draft -= {1}  # difference
        draft &= {2, 3, 5, 6}  # intersection

    assert_patches_work(base, recipe)


def test_nested_operations_patches_apply():
    """Test that nested structure patches can be applied correctly."""
    base = {
        "users": [
            {"name": "Alice", "tags": {1, 2}},
            {"name": "Bob", "tags": {3, 4}},
        ],
        "count": 2,
    }

    def recipe(draft):
        draft["users"][0]["name"] = "Alicia"
        draft["users"][0]["tags"].add(5)
        draft["users"].append({"name": "Charlie", "tags": set()})
        draft["count"] = 3

    assert_patches_work(base, recipe)


def test_complex_list_operations_patches_apply():
    """Test complex list operations produce correct patches."""
    base = [{"id": 1}, {"id": 2}, {"id": 3}]

    def recipe(draft):
        draft[0]["id"] = 10
        draft.pop(1)
        draft.append({"id": 4})

    assert_patches_work(base, recipe)


def test_deeply_nested_mixed_types_many_operations():
    """Test deeply nested structure with all three proxy types and many operations."""
    base = {
        "organization": {
            "departments": [
                {
                    "name": "Engineering",
                    "teams": [
                        {"name": "Backend", "members": {"alice", "bob"}},
                        {"name": "Frontend", "members": {"charlie", "diana"}},
                    ],
                },
                {
                    "name": "Sales",
                    "teams": [{"name": "Enterprise", "members": {"eve", "frank"}}],
                },
            ],
            "metadata": {"founded": 2020, "tags": ["tech", "startup"]},
        }
    }

    def recipe(draft):
        # 1. Modify deeply nested value
        draft["organization"]["metadata"]["founded"] = 2021

        # 2. Add to deeply nested set
        draft["organization"]["departments"][0]["teams"][0]["members"].add("grace")

        # 3. Remove from deeply nested set
        draft["organization"]["departments"][0]["teams"][0]["members"].remove("bob")

        # 4. Modify nested dict
        draft["organization"]["departments"][0]["name"] = "Engineering & Product"

        # 5. Append to nested list
        draft["organization"]["metadata"]["tags"].append("AI")

        # 6. Insert into nested list
        draft["organization"]["metadata"]["tags"].insert(0, "innovative")

        # 7. Add new team to nested list
        draft["organization"]["departments"][0]["teams"].append(
            {"name": "DevOps", "members": {"henry"}}
        )

        # 8. Remove item from nested list
        draft["organization"]["departments"].pop(1)

        # 9. Update nested dict
        draft["organization"]["metadata"].update({"employees": 50, "remote": True})

        # 10. Clear and repopulate nested set
        draft["organization"]["departments"][0]["teams"][1]["members"].clear()
        draft["organization"]["departments"][0]["teams"][1]["members"].add("new_member")

    result, patches, reverse = produce(base, recipe)

    # Verify result
    assert result["organization"]["metadata"]["founded"] == 2021
    assert "grace" in result["organization"]["departments"][0]["teams"][0]["members"]
    assert "bob" not in result["organization"]["departments"][0]["teams"][0]["members"]
    assert result["organization"]["departments"][0]["name"] == "Engineering & Product"
    assert result["organization"]["metadata"]["tags"][0] == "innovative"
    assert "AI" in result["organization"]["metadata"]["tags"]
    assert len(result["organization"]["departments"][0]["teams"]) == 3
    assert len(result["organization"]["departments"]) == 1  # Sales removed
    assert result["organization"]["metadata"]["employees"] == 50

    # Verify patches were generated
    assert len(patches) > 10

    # Verify patches can be applied
    from patchdiff import apply

    patched = apply(base, patches)
    assert patched == result

    # Verify reverse patches work
    reversed_result = apply(result, reverse)
    assert reversed_result == base


def test_list_of_dicts_with_sets_comprehensive():
    """Test list of dicts containing sets with comprehensive operations."""
    base = [
        {"id": 1, "tags": {"python", "async"}, "scores": [85, 90, 92]},
        {"id": 2, "tags": {"javascript", "react"}, "scores": [78, 82]},
        {"id": 3, "tags": {"python", "django"}, "scores": [95, 88, 91]},
    ]

    def recipe(draft):
        # Operations on first item
        draft[0]["tags"].add("fastapi")
        draft[0]["tags"].discard("async")
        draft[0]["scores"].append(88)
        draft[0]["scores"][0] = 87

        # Operations on second item
        draft[1]["id"] = 20
        draft[1]["tags"] |= {"typescript", "redux"}
        draft[1]["scores"].extend([85, 90])

        # Operations on third item
        draft[2]["tags"].remove("django")
        draft[2]["scores"].reverse()
        draft[2]["scores"].pop()

        # List-level operations
        draft.append({"id": 4, "tags": {"go", "kubernetes"}, "scores": [92]})
        draft.insert(1, {"id": 5, "tags": set(), "scores": []})

        # Slice operations
        draft[3:5] = [{"id": 6, "tags": {"rust"}, "scores": [100]}]

    result, patches, _reverse = produce(base, recipe)

    # Verify complex nested modifications
    # Index 0: modified first item
    assert "fastapi" in result[0]["tags"]
    assert "async" not in result[0]["tags"]
    assert result[0]["scores"] == [87, 90, 92, 88]

    # Index 1: inserted item (inserted at position 1)
    assert result[1]["id"] == 5
    assert result[1]["tags"] == set()

    # Index 2: modified second item (shifted by insert)
    assert result[2]["id"] == 20
    assert "typescript" in result[2]["tags"]
    assert len(result[2]["scores"]) == 4

    # Index 3: slice replacement result
    assert result[3]["id"] == 6
    assert result[3]["tags"] == {"rust"}

    # Total length after all operations
    assert len(result) == 4

    assert len(patches) > 15


def test_dict_with_nested_lists_and_operations():
    """Test dict containing nested lists with slice operations and sorting."""
    base = {
        "matrix": [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
        "names": ["charlie", "alice", "bob"],
        "records": [{"x": 3}, {"x": 1}, {"x": 2}],
    }

    def recipe(draft):
        # Slice operations on nested lists
        draft["matrix"][0][1:2] = [20]
        draft["matrix"][1][:] = [40, 50, 60]
        draft["matrix"][2].append(10)

        # List operations
        draft["names"].sort()
        draft["names"].insert(0, "zara")

        # Complex operations on list of dicts
        draft["records"].sort(key=lambda r: r["x"])
        draft["records"][0]["x"] = 10
        draft["records"].append({"x": 4})

        # Replace entire nested list
        draft["matrix"].append([11, 12, 13])

    result, patches, _reverse = produce(base, recipe)

    assert result["matrix"][0] == [1, 20, 3]
    assert result["matrix"][1] == [40, 50, 60]
    assert result["matrix"][2] == [7, 8, 9, 10]
    assert result["names"] == ["zara", "alice", "bob", "charlie"]
    assert result["records"][0]["x"] == 10
    assert result["records"][-1]["x"] == 4
    assert len(result["matrix"]) == 4

    assert len(patches) > 10


def test_set_operations_in_nested_structures():
    """Test various set operations within nested structures."""
    base = {
        "groups": [
            {"name": "admins", "users": {"alice", "bob"}},
            {"name": "users", "users": {"charlie", "diana", "eve"}},
            {"name": "guests", "users": {"frank"}},
        ],
        "all_users": {"alice", "bob", "charlie", "diana", "eve", "frank"},
    }

    def recipe(draft):
        # Set operations on nested sets
        draft["groups"][0]["users"].add("grace")
        draft["groups"][0]["users"] |= {"henry", "iris"}  # update operator

        # Set arithmetic on nested sets
        draft["groups"][1]["users"] &= {"charlie", "eve"}  # intersection
        draft["groups"][2]["users"].clear()
        draft["groups"][2]["users"].update(["zara", "yolanda"])

        # Operations on top-level set
        draft["all_users"].add("grace")
        draft["all_users"] -= {"frank"}  # difference update via operator

        # List operations
        draft["groups"].pop(1)
        draft["groups"].append({"name": "moderators", "users": {"alice"}})

    result, patches, _reverse = produce(base, recipe)

    assert "grace" in result["groups"][0]["users"]
    assert len(result["groups"][0]["users"]) == 5  # alice, bob, grace, henry, iris
    assert result["groups"][1]["users"] == {"zara", "yolanda"}
    assert len(result["groups"]) == 3
    assert "grace" in result["all_users"]
    assert "frank" not in result["all_users"]

    assert len(patches) > 8


def test_mixed_operations_with_slice_and_bulk_updates():
    """Test mixed operations including slicing and bulk updates on nested structures."""
    base = {
        "data": {
            "values": [10, 20, 30, 40, 50],
            "metadata": {"count": 5, "sum": 150},
        },
        "backup": [[1, 2], [3, 4], [5, 6]],
    }

    def recipe(draft):
        # Slice operations on nested list
        draft["data"]["values"][1:4] = [200, 300]  # Shrink
        draft["data"]["values"].extend([60, 70])

        # Bulk update on nested dict
        draft["data"]["metadata"].update({"count": 5, "sum": 630, "avg": 126})

        # Operations on nested list of lists
        draft["backup"][0].extend([3, 4, 5])
        draft["backup"][1].clear()
        draft["backup"][1].extend([30, 40])
        draft["backup"].append([7, 8, 9])

        # Replace nested structure
        draft["data"]["extra"] = {"new": True}

    result, patches, _reverse = produce(base, recipe)

    assert result["data"]["values"] == [10, 200, 300, 50, 60, 70]
    assert result["data"]["metadata"]["avg"] == 126
    assert result["backup"][0] == [1, 2, 3, 4, 5]
    assert result["backup"][1] == [30, 40]
    assert len(result["backup"]) == 4
    assert result["data"]["extra"]["new"] is True

    assert len(patches) > 12


def test_cross_level_modifications():
    """Test modifications at multiple nesting levels simultaneously."""
    base = {
        "level1": {
            "level2": {"level3": {"level4": {"value": 1, "items": [1, 2, 3]}}},
            "sibling": [{"a": 1}, {"b": 2}],
        },
        "top": "unchanged",
    }

    def recipe(draft):
        # Modify at different levels
        draft["top"] = "changed"  # Level 0
        draft["level1"]["sibling"].append({"c": 3})  # Level 2
        draft["level1"]["level2"]["level3"]["level4"]["value"] = 100  # Level 4
        draft["level1"]["level2"]["level3"]["level4"]["items"].reverse()  # Level 4
        draft["level1"]["level2"]["level3"]["level4"]["items"].append(4)  # Level 4
        draft["level1"]["level2"]["new_key"] = "new_value"  # Level 2
        draft["level1"]["sibling"][0]["a"] = 10  # Level 3

    result, patches, _reverse = produce(base, recipe)

    assert result["top"] == "changed"
    assert len(result["level1"]["sibling"]) == 3
    assert result["level1"]["level2"]["level3"]["level4"]["value"] == 100
    assert result["level1"]["level2"]["level3"]["level4"]["items"] == [3, 2, 1, 4]
    assert result["level1"]["level2"]["new_key"] == "new_value"
    assert result["level1"]["sibling"][0]["a"] == 10

    assert len(patches) >= 7


# -- Proxy API completeness tests --
# These tests ensure that proxy classes cover all methods of their base types.
# If a new Python version adds a method to dict/list/set, the corresponding
# test will fail. To fix it, either:
# 1. Add the method name to SKIPPED below (if it doesn't need proxying), or
# 2. Implement it on the proxy class.

# Methods inherited from object that are not part of the container API
_OBJECT_INTERNALS = {
    "__class__",
    "__delattr__",
    "__dir__",
    "__doc__",
    "__getattribute__",
    "__getstate__",
    "__init__",
    "__init_subclass__",
    "__new__",
    "__reduce__",
    "__reduce_ex__",
    "__setattr__",
    "__sizeof__",
    "__subclasshook__",
}


def _unhandled_methods(proxy_cls, base_cls, skipped):
    """Return methods on base_cls that are missing from proxy_cls and not in skipped."""
    base_methods = set(dir(base_cls)) - _OBJECT_INTERNALS
    proxy_methods = set(dir(proxy_cls)) - _OBJECT_INTERNALS
    return (base_methods - proxy_methods) - set(skipped)


# Methods intentionally not implemented on the proxy classes.
# If a new Python version adds a method to dict/list/set, the test will
# fail. To fix, either implement the method or add it here.
_DICT_SKIPPED = {
    "fromkeys",  # classmethod, not relevant for proxy instances
    "__class_getitem__",  # typing support (dict[str, int])
}

_LIST_SKIPPED = {
    "__class_getitem__",  # typing support (list[int])
}

_SET_SKIPPED = {
    "__class_getitem__",  # typing support (set[int])
}


class TestProxyApiCompleteness:
    """Verify proxy classes implement all methods of their base types."""

    def test_dict_proxy_api_completeness(self):
        unhandled = _unhandled_methods(DictProxy, dict, _DICT_SKIPPED)
        assert not unhandled, (
            f"DictProxy is missing methods from dict: {sorted(unhandled)}. "
            f"Either implement them on DictProxy or add to _DICT_SKIPPED."
        )

    def test_list_proxy_api_completeness(self):
        unhandled = _unhandled_methods(ListProxy, list, _LIST_SKIPPED)
        assert not unhandled, (
            f"ListProxy is missing methods from list: {sorted(unhandled)}. "
            f"Either implement them on ListProxy or add to _LIST_SKIPPED."
        )

    def test_set_proxy_api_completeness(self):
        unhandled = _unhandled_methods(SetProxy, set, _SET_SKIPPED)
        assert not unhandled, (
            f"SetProxy is missing methods from set: {sorted(unhandled)}. "
            f"Either implement them on SetProxy or add to _SET_SKIPPED."
        )
