[![PyPI version](https://badge.fury.io/py/patchdiff.svg)](https://badge.fury.io/py/patchdiff)
[![CI status](https://github.com/fork-tongue/patchdiff/workflows/CI/badge.svg)](https://github.com/fork-tongue/patchdiff/actions)

# Patchdiff 🔍

Based on [rfc6902](https://github.com/chbrown/rfc6902) this library provides a simple API to generate **bi-directional** diffs between composite Python data structures composed out of lists, sets, tuples and dicts. The diffs are JSON-patch compliant, and can optionally be serialized to JSON format. Patchdiff can also be used to apply lists of patches to objects, both **in place** or on a **deep copy** of the input.

Documentation: https://fork-tongue.github.io/patchdiff/

## Install

`pip install patchdiff`

No dependencies, requires Python 3.9 or newer.

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

Since every diff comes with its reverse, undo/redo and state synchronization are easy to build on top.

## Proxy based patch generation

As an alternative to diffing two objects, patchdiff can also record patches while mutations are being made, using a proxy mechanism. This is how [Immer](https://immerjs.github.io/immer/produce) works. It's much more efficient than diffing, since the cost scales with the number of mutations instead of the size of the data:

```python
from patchdiff import produce

base = {"count": 0, "items": [1, 2, 3]}

def recipe(draft):
    draft["count"] = 5
    draft["items"].append(4)

result, patches, reverse_patches = produce(base, recipe)

assert base == {"count": 0, "items": [1, 2, 3]}  # base is untouched
assert result == {"count": 5, "items": [1, 2, 3, 4]}
```

With `in_place=True` mutations are applied directly to the input object through the proxy. This is what you want when combining patchdiff with [observ](https://github.com/fork-tongue/observ), since observ watchers only trigger when you mutate through the reactive proxy. See [observ integration](https://fork-tongue.github.io/patchdiff/guide/observ/) for an example with undo/redo.
