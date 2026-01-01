[![PyPI version](https://badge.fury.io/py/patchdiff.svg)](https://badge.fury.io/py/patchdiff)
[![CI status](https://github.com/fork-tongue/patchdiff/workflows/CI/badge.svg)](https://github.com/fork-tongue/patchdiff/actions)

# Patchdiff 🔍

Based on [rfc6902](https://github.com/chbrown/rfc6902) this library provides a simple API to generate bi-directional diffs between composite python datastructures composed out of lists, sets, tuples and dicts. The diffs are jsonpatch compliant, and can optionally be serialized to json format. Patchdiff can also be used to apply lists of patches to objects, both in-place or on a deepcopy of the input.

## Install

`pip install patchdiff`

## Quick-start

```python
from patchdiff import apply, diff, iapply, to_json

input = {"a": [5, 7, 9, {"a", "b", "c"}], "b": 6}
output = {"a": [5, 2, 9, {"b", "c"}], "b": 6, "c": 7}

ops, reverse_ops = diff(input, output)

assert apply(input, ops) == output
assert apply(output, reverse_ops) == input

iapply(input, ops)  # apply in-place
assert input == output

print(to_json(ops, indent=4))
# [
#     {
#         "op": "add",
#         "path": "/c",
#         "value": 7
#     },
#     {
#         "op": "replace",
#         "path": "/a/1",
#         "value": 2
#     },
#     {
#         "op": "remove",
#         "path": "/a/3/a"
#     }
# ]
```

## Proxy-based patch generation

For better performance and a more intuitive API, you can use `produce()` which generates patches by tracking mutations on a proxy object (inspired by [Immer](https://immerjs.github.io/immer/)):

```python
from patchdiff import produce

base = {"count": 0, "items": [1, 2, 3]}

def recipe(draft):
    """Mutate the draft object - changes are tracked automatically."""
    draft["count"] = 5
    draft["items"].append(4)
    draft["new_field"] = "hello"

result, patches, reverse_patches = produce(base, recipe)

# base is unchanged (immutable by default)
assert base == {"count": 0, "items": [1, 2, 3]}

# result contains the changes
assert result == {"count": 5, "items": [1, 2, 3, 4], "new_field": "hello"}

# patches describe what changed
print(patches)
# [
#     {"op": "replace", "path": "/count", "value": 5},
#     {"op": "add", "path": "/items/-", "value": 4},
#     {"op": "add", "path": "/new_field", "value": "hello"}
# ]
```

For reactive state management (e.g., with [observ](https://github.com/fork-tongue/observ)), use `in_place=True` to mutate the original object:

```python
from observ import reactive
from patchdiff import produce

state = reactive({"count": 0})

# Mutate in place and get patches for undo/redo
result, patches, reverse = produce(state, lambda draft: draft.update({"count": 5}), in_place=True)

assert result is state  # Same object
assert state["count"] == 5  # State was mutated, watchers triggered
```
