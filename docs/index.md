# Patchdiff 🔍

Based on [rfc6902](https://github.com/chbrown/rfc6902) this library provides a simple API to generate **bi-directional** diffs between composite Python data structures composed out of lists, sets, tuples and dicts. The diffs are JSON-patch compliant, and can optionally be serialized to JSON format. Patchdiff has no dependencies and works on Python 3.13 and up.

A single call to [`diff`][patchdiff.diff.diff] gives you the patches in **both directions**:

```python
from patchdiff import apply, diff

input = {"a": [5, 7, 9, {"a", "b", "c"}], "b": 6}
output = {"a": [5, 2, 9, {"b", "c"}], "b": 6, "c": 7}

ops, reverse_ops = diff(input, output)

assert apply(input, ops) == output
assert apply(output, reverse_ops) == input
```

Having both directions makes it easy to build undo/redo, to synchronize state between processes (send patches over the wire instead of whole documents), or to keep a log of exactly what changed.

As an alternative to diffing, patchdiff can also record patches while mutations are being made, using a proxy mechanism like [Immer](https://immerjs.github.io/immer/produce). See [`produce`][patchdiff.produce.produce]:

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

## Where to start

* The [quick start](getting-started/quick-start.md) walks through the core API.
* The guide covers [diffing](guide/diffing.md), [applying patches](guide/applying.md), [pointers](guide/pointers.md), [produce](guide/produce.md), [serialization](guide/serialization.md) and [gotchas](guide/gotchas.md) in more detail.
* If you use [observ](https://github.com/fork-tongue/observ), have a look at [observ integration](guide/observ.md).
* The complete public API is documented in the [API reference](reference/api.md).
* The [internals](internals/architecture.md) page describes how everything works under the hood.

## Related projects

* [observ](https://github.com/fork-tongue/observ): reactive state management for Python. Patchdiff's `produce(..., in_place=True)` is designed to work with its reactive proxies.
* [rfc6902](https://github.com/chbrown/rfc6902): the TypeScript library that patchdiff's diffing approach is based on.
