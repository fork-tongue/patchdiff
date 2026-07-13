# Observ Integration

[observ](https://github.com/fork-tongue/observ) provides reactive state for Python: mutate a `reactive` proxy and watchers and computed values update automatically. Patchdiff turns those same mutations into patches, which is how you add **undo/redo or change synchronization on top of reactive state**.

Patchdiff has no hard dependency on observ; everything on this page also works on plain dicts and lists.

## Recording patches on reactive state

Use [`produce`][patchdiff.produce.produce] with `in_place=True`. The mutations are written *through* observ's reactive proxy, so watchers fire exactly as if you had mutated the state directly, and you get both patch directions for free:

```python
from observ import reactive, watch

from patchdiff import produce

state = reactive({"count": 0})

observed = []
watcher = watch(
    lambda: state["count"],
    lambda new: observed.append(new),
    sync=True,
)

result, patches, reverse_patches = produce(
    state,
    lambda draft: draft.update(count=5),
    in_place=True,
)

assert result is state          # same reactive object
assert state["count"] == 5      # state was mutated...
assert observed == [5]          # ...and the watcher fired
```

!!! note "Why `in_place=True`?"
    Without it, `produce` copies the state and mutates the copy, so the reactive object stays untouched and no watcher fires. In-place mode is also faster, since it skips the deep copy.

## Undo/redo for reactive state

Applying patches with [`iapply`][patchdiff.apply.iapply] writes through the reactive proxy as well, so undo and redo trigger watchers like any other mutation:

```python
from observ import reactive

from patchdiff import iapply, produce

state = reactive({"todos": ["write docs"]})

_, patches, reverse_patches = produce(
    state,
    lambda draft: draft["todos"].append("release 1.0"),
    in_place=True,
)

assert state["todos"] == ["write docs", "release 1.0"]

iapply(state, reverse_patches)  # undo
assert state["todos"] == ["write docs"]

iapply(state, patches)  # redo
assert state["todos"] == ["write docs", "release 1.0"]
```

## Diffing reactive state

[`diff`][patchdiff.diff.diff] duck-types its inputs, so observ proxies can be diffed directly, against plain data or other proxies:

```python
from observ import reactive

from patchdiff import diff, to_json

state = reactive({"count": 0})

ops, _ = diff(state, {"count": 1})

assert to_json(ops) == '[{"op": "replace", "path": "/count", "value": 1}]'
```

Patch values recorded from reactive state are snapshotted to **plain data** (observ proxies are unwrapped), so patches stay serializable and never keep reactive objects alive.

## Installing both

The observ integration is exercised in patchdiff's own test suite. To develop against both:

```sh
uv add patchdiff observ
```
