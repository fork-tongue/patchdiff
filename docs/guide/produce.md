# Proxy Based Patch Generation

Diffing compares two complete states after the fact. When your own code is the thing making the changes, [`produce`][patchdiff.produce.produce] can skip the comparison entirely: it hands your recipe a proxy-wrapped *draft*, records every mutation as it happens, and emits the patches directly. The idea (and the name) come from [Immer](https://immerjs.github.io/immer/produce).

```python
from patchdiff import produce

base = {"count": 0, "items": [1, 2, 3]}

def recipe(draft):
    draft["count"] = 5
    draft["items"].append(4)

result, patches, reverse_patches = produce(base, recipe)

assert base == {"count": 0, "items": [1, 2, 3]}  # base is unchanged
assert result == {"count": 5, "items": [1, 2, 3, 4]}
```

The recorded patches are exactly what [`diff`][patchdiff.diff.diff] would have produced: the same operation dicts, which can be applied with [`apply`][patchdiff.apply.apply]/[`iapply`][patchdiff.apply.iapply] and serialized with [`to_json`][patchdiff.serialize.to_json]:

```python
from patchdiff import apply, produce

base = {"count": 0}
result, patches, reverse_patches = produce(base, lambda d: d.update(count=5))

assert apply(base, patches) == result
assert apply(result, reverse_patches) == base
```

For small mutations to large states this is much faster than diffing, because the cost scales with the number of mutations instead of the size of the state. The `produce-vs-diff` groups in the benchmark suite quantify this.

## Immutable by default

By default the recipe operates on a copy: `base` stays untouched and `result` is a new object. The draft is only wrapped in proxies while the recipe runs; the returned `result` is plain data.

## In-place mutation

With `in_place=True` the draft *is* the base object. No copy is made, and mutations go straight through the proxy into it. Use this when the object's identity matters, most notably for [observ](observ.md) reactive state, where the writes must land on the reactive proxy so watchers fire:

```python
from patchdiff import produce

state = {"count": 0}

result, patches, reverse_patches = produce(
    state,
    lambda draft: draft.update(count=5),
    in_place=True,
)

assert result is state  # same object
assert state == {"count": 5}
```

You still get both patch directions, so in-place mutation with undo/redo doesn't cost a deepcopy at all.

## What the draft supports

The draft mirrors the wrapped container type. Dicts, lists and sets each get a dedicated proxy with the full mutating and reading API, including operators:

* dicts: item access/assignment/deletion, `get`, `pop`, `setdefault`, `update`, `clear`, `popitem`, `keys`/`values`/`items`, `|=`, iteration, ...
* lists: indexing and slicing (read and write), `append`, `insert`, `extend`, `pop`, `remove`, `clear`, `reverse`, `sort`, `+=`, `*=`, iteration, ...
* sets: `add`, `remove`, `discard`, `pop`, `clear`, `update`, the in-place operators (`|=`, `&=`, `-=`, `^=`) and their method forms, ...

Values you read from the draft are themselves wrapped, so nested mutations are tracked too, with correct deep paths, even when list indices shift under them:

```python
from patchdiff import produce, to_json

base = {"todos": [{"done": False}, {"done": False}]}

def recipe(draft):
    first = draft["todos"][0]
    draft["todos"].insert(0, {"done": True})  # shifts the original items
    first["done"] = True                       # still records the right path

result, patches, reverse_patches = produce(base, recipe)

assert result["todos"][1]["done"] is True
assert '"path": "/todos/1/done"' in to_json(patches)
```

## Snapshotting

Values recorded into patches are snapshotted (deepcopied, with proxies unwrapped) at the moment the mutation happens. Mutating an object after assigning it into the draft won't retroactively change earlier patches, and patches never share mutable state with the draft or the result.

!!! note "The draft is only valid inside the recipe"
    When `produce` returns, all proxies are released. Don't hold on to the draft (or values read from it) for use outside the recipe; take what you need from `result` instead.
