# Patchdiff 🔍

Patchdiff computes **bidirectional, JSON-patch-compliant diffs** between composite Python data structures built out of dicts, lists, sets and tuples. Inspired by [rfc6902](https://github.com/chbrown/rfc6902), it has no dependencies and works on any Python >= 3.9.

One call gives you both directions:

```python
from patchdiff import apply, diff

input = {"a": [5, 7, 9, {"a", "b", "c"}], "b": 6}
output = {"a": [5, 2, 9, {"b", "c"}], "b": 6, "c": 7}

ops, reverse_ops = diff(input, output)

assert apply(input, ops) == output
assert apply(output, reverse_ops) == input
```

That makes patchdiff a natural fit for:

* **Undo/redo** — apply `reverse_ops` to go back, `ops` to go forward again.
* **Synchronization** — serialize patches with [`to_json`][patchdiff.serialize.to_json] and ship them over the wire instead of whole documents.
* **Change tracking** — record exactly what a piece of code did to your state.

Besides after-the-fact diffing, patchdiff can also record patches **while mutations happen**, through [`produce`][patchdiff.produce.produce] — a proxy-based recorder inspired by [Immer](https://immerjs.github.io/immer/produce):

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

## Where to go next

* Follow the [Quick Start](getting-started/quick-start.md) to learn the core API in a few minutes.
* Read the [Guide](guide/diffing.md) for an in-depth look at [diffing](guide/diffing.md), [applying patches](guide/applying.md), [pointers](guide/pointers.md), [proxy-based patch generation](guide/produce.md) and [serialization](guide/serialization.md).
* Using [observ](https://github.com/fork-tongue/observ)? See the [Observ Integration](guide/observ.md) page for reactive state with undo/redo.
* Browse the [API Reference](reference/api.md) for the complete public API.

## Related projects

* [observ](https://github.com/fork-tongue/observ): reactive state management for Python; patchdiff's `produce(..., in_place=True)` is built to work with its reactive proxies.
* [rfc6902](https://github.com/chbrown/rfc6902): the TypeScript library that inspired patchdiff's diffing approach.
