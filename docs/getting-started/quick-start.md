# Quick Start

This page walks through the whole API: diff two objects, apply the patches, undo them, and serialize them to json.

## Diffing

[`diff`][patchdiff.diff.diff] compares two objects and returns two lists of operations: one that turns `input` into `output`, and one that turns `output` back into `input`.

```python
from patchdiff import diff

input = {"a": [5, 7, 9, {"a", "b", "c"}], "b": 6}
output = {"a": [5, 2, 9, {"b", "c"}], "b": 6, "c": 7}

ops, reverse_ops = diff(input, output)
```

Each operation is a plain dict in jsonpatch style, with an `"op"` (`"add"`, `"remove"` or `"replace"`), a `"path"` (a [`Pointer`][patchdiff.pointer.Pointer]), and a `"value"` for adds and replaces:

```python
from patchdiff import diff
from patchdiff.pointer import Pointer

ops, reverse_ops = diff({"count": 0}, {"count": 1})

assert ops == [{"op": "replace", "path": Pointer(["count"]), "value": 1}]
assert reverse_ops == [{"op": "replace", "path": Pointer(["count"]), "value": 0}]
```

## Applying patches

[`apply`][patchdiff.apply.apply] patches a deepcopy and leaves the original untouched, while [`iapply`][patchdiff.apply.iapply] patches the object in-place:

```python
from patchdiff import apply, diff, iapply

input = {"a": [5, 7, 9], "b": 6}
output = {"a": [5, 2, 9], "b": 6, "c": 7}

ops, reverse_ops = diff(input, output)

assert apply(input, ops) == output          # input is unchanged
assert apply(output, reverse_ops) == input  # ...and it round-trips

iapply(input, ops)  # in-place
assert input == output
```

Applying `reverse_ops` is your undo, re-applying `ops` is your redo.

## Serializing to json

Patches are jsonpatch compliant, so they can be serialized with [`to_json`][patchdiff.serialize.to_json]:

```python
from patchdiff import diff, to_json

ops, _ = diff({"a": [5, 7]}, {"a": [5, 2], "c": 7})

print(to_json(ops, indent=4))
```

```json
[
    {
        "op": "add",
        "path": "/c",
        "value": 7
    },
    {
        "op": "replace",
        "path": "/a/1",
        "value": 2
    }
]
```

## Recording patches while mutating

When your own code is making the changes, you don't need to diff at all. [`produce`][patchdiff.produce.produce] hands you a draft, records every mutation you make to it, and gives you the result plus both patch directions, without a full comparison pass:

```python
from patchdiff import produce

base = {"count": 0, "items": [1, 2, 3]}

def recipe(draft):
    draft["count"] = 5
    draft["items"].append(4)
    draft["new_field"] = "hello"

result, patches, reverse_patches = produce(base, recipe)

assert base == {"count": 0, "items": [1, 2, 3]}  # untouched
assert result == {"count": 5, "items": [1, 2, 3, 4], "new_field": "hello"}
```

The [guide](../guide/diffing.md) goes into the details of each of these. The complete public API is in the [API reference](../reference/api.md).
