# Diffing

[`diff`][patchdiff.diff.diff] recursively compares two objects and emits jsonpatch style operations in both directions:

```python
from patchdiff import apply, diff

ops, reverse_ops = diff({"a": 1}, {"a": 2, "b": 3})

assert apply({"a": 1}, ops) == {"a": 2, "b": 3}
assert apply({"a": 2, "b": 3}, reverse_ops) == {"a": 1}
```

The comparison starts with a plain equality check: if `input == output`, both lists are empty. Otherwise the strategy depends on the types involved.

## What gets compared structurally

Containers are compared recursively when both sides are container-like. The check is duck-typed, so third-party proxies such as observ's reactive objects work too:

| both sides have | treated as | operations emitted |
|---|---|---|
| `.append` | list | minimal edit script: adds, removes, replaces per index |
| `.keys` | dict | add/remove per key, recursion into common keys |
| `.add` | set | add/remove per element |

Anything else (scalars, but also tuples and frozensets, or two containers of different kinds) is treated as an atomic value and replaced wholesale:

```python
from patchdiff import diff
from patchdiff.pointer import Pointer

ops, _ = diff({"t": (1, 2)}, {"t": (1, 3)})

assert ops == [{"op": "replace", "path": Pointer(["t"]), "value": (1, 3)}]
```

## Lists

List diffing computes a minimal edit script (fewest adds/removes/replaces) between the two lists. Common prefixes and suffixes are stripped first, so localized changes in large lists stay cheap. When a replace pairs up two containers, patchdiff recurses into them instead of replacing the whole element:

```python
from patchdiff import diff, to_json

ops, _ = diff(
    [1, {"name": "a"}, 3],
    [1, {"name": "b"}, 3],
)

assert to_json(ops) == '[{"op": "replace", "path": "/1/name", "value": "b"}]'
```

Insertions at the end use the `-` token from RFC 6901, which means "append":

```python
from patchdiff import diff, to_json

ops, _ = diff([1, 2], [1, 2, 3])

assert to_json(ops) == '[{"op": "add", "path": "/-", "value": 3}]'
```

## Dicts

Keys only in the input become removes, keys only in the output become adds, and common keys are diffed recursively, so nested changes produce deep paths rather than replacing whole subtrees:

```python
from patchdiff import diff, to_json

ops, _ = diff(
    {"user": {"name": "kim", "age": 40}},
    {"user": {"name": "kim", "age": 41}},
)

assert to_json(ops) == '[{"op": "replace", "path": "/user/age", "value": 41}]'
```

## Sets

Sets have no indices or keys, so patchdiff extends jsonpatch slightly: an element is added with the `-` token (like a list append) and removed by addressing the element itself as the final path token:

```python
from patchdiff import diff
from patchdiff.pointer import Pointer

ops, _ = diff({1, 2}, {2, 3})

assert ops == [
    {"op": "remove", "path": Pointer([1])},
    {"op": "add", "path": Pointer(["-"]), "value": 3},
]
```

See [gotchas](gotchas.md) for the places where this deliberately diverges from strict RFC 6902.

## Reverse operations

The second list that `diff` returns is not just the first with `add`/`remove` swapped. The operations are also ordered for reverse application, so that indices resolve correctly as each patch is applied. Always apply `reverse_ops` as-is, in order:

```python
from patchdiff import apply, diff

input = [1, 2, 3, 4, 5]
output = [1, 4, 5, 6]

ops, reverse_ops = diff(input, output)

assert apply(input, ops) == output
assert apply(output, reverse_ops) == input
```
