[![PyPI version](https://badge.fury.io/py/patchdiff.svg)](https://badge.fury.io/py/patchdiff)
[![CI status](https://github.com/fork-tongue/patchdiff/workflows/CI/badge.svg)](https://github.com/fork-tongue/patchdiff/actions)

# Patchdiff 🔍

**Bidirectional, JSON-patch-compliant diffs between Python data structures.**

📖 [Documentation](https://fork-tongue.github.io/patchdiff/) | [Quick Start](https://fork-tongue.github.io/patchdiff/getting-started/quick-start/) | [API Reference](https://fork-tongue.github.io/patchdiff/reference/api/)

Patchdiff diffs composite structures of dicts, lists, sets and tuples, and gives you **both directions** in one call: the patches to get from `input` to `output`, and the patches to get back. Patches are [RFC 6902](https://datatracker.ietf.org/doc/html/rfc6902) JSON-patch style, serializable to JSON, and can be applied in place or to a copy, which makes undo/redo, change synchronization and state auditing one-liners.

```python
from patchdiff import apply, diff, iapply, to_json

input = {"a": [5, 7, 9, {"a", "b", "c"}], "b": 6}
output = {"a": [5, 2, 9, {"b", "c"}], "b": 6, "c": 7}

ops, reverse_ops = diff(input, output)

assert apply(input, ops) == output          # patch a copy...
assert apply(output, reverse_ops) == input  # ...and it round-trips

iapply(input, ops)  # or patch in place
assert input == output

print(to_json(ops, indent=4))
```

## Proxy based patch generation

When your own code makes the changes, `produce()` (inspired by [Immer](https://immerjs.github.io/immer/produce)) skips the comparison entirely: it hands your recipe a draft, records every mutation, and returns the result plus both patch directions. Cost scales with the number of mutations instead of the size of the state:

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

With `in_place=True`, mutations (and patches applied with `iapply`) write straight through proxy-backed state, the natural companion to [observ](https://github.com/fork-tongue/observ) reactive objects, where mutating through the proxy is what triggers watchers. See [Observ Integration](https://fork-tongue.github.io/patchdiff/guide/observ/) for reactive state with undo/redo.

## Install

```sh
pip install patchdiff  # or: uv add patchdiff
```

No dependencies, Python >= 3.13.

## Learn more

The [documentation](https://fork-tongue.github.io/patchdiff/) covers [diffing semantics](https://fork-tongue.github.io/patchdiff/guide/diffing/), [applying patches](https://fork-tongue.github.io/patchdiff/guide/applying/), [JSON pointers](https://fork-tongue.github.io/patchdiff/guide/pointers/), [proxy-based patch generation](https://fork-tongue.github.io/patchdiff/guide/produce/), [serialization](https://fork-tongue.github.io/patchdiff/guide/serialization/) and the [gotchas](https://fork-tongue.github.io/patchdiff/guide/gotchas/), plus the [internals](https://fork-tongue.github.io/patchdiff/internals/architecture/) for the curious.
