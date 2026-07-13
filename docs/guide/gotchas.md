# Gotchas and Best Practices

## Where patchdiff diverges from strict RFC 6902

Patchdiff's patches are JSON-patch *compliant* for JSON-shaped data (dicts with string keys, lists, scalars), but the library deliberately supports more of Python than JSON has:

* **Sets** are diffed and patched natively: elements are added with the `-` token and removed by addressing the element value itself as the final path token. Strict RFC 6902 has no set concept at all.
* **Tuples and frozensets** are treated as atomic values — they are never diffed into, only replaced wholesale.
* **Pointer tokens can be non-strings** (integer list indices, set members). They stringify losslessly for lists, but set-member tokens can't be parsed back from a string — see [Serialization](serialization.md#non-json-values).
* **Only `add`, `remove` and `replace` are emitted.** `move`, `copy` and `test` from RFC 6902 are neither generated nor understood by [`apply`][patchdiff.apply.apply]/[`iapply`][patchdiff.apply.iapply].
* **Operations on the document root are not supported.** Patches address locations *inside* a container. Diffing two documents of different top-level kinds (say a list against a dict) yields a whole-document `replace` at the root, which `apply`/`iapply` cannot execute — keep the top-level type of your state stable.

If you feed patches to a strict third-party JSON patch implementation, stick to JSON-shaped data and everything lines up.

## Apply patches in order, as a unit

Paths refer to the state of the object *at that point in the patch sequence* — list indices shift as adds and removes apply. Both lists returned by [`diff`][patchdiff.diff.diff] and [`produce`][patchdiff.produce.produce] are ordered for exactly this; reordering or cherry-picking operations from the middle of a list will corrupt paths.

Also, reverse operations undo the *whole* forward list, not individual forward ops one-for-one.

## Diffing compares by equality

`diff` starts with `input == output`. Anything Python considers equal produces no patch — including e.g. `1 == True` and `0.0 == 0`. If you need to normalize such values, do it before diffing.

## Patches never share state with your objects

Patch values are snapshotted when recorded (by `produce`) and deep-copied when applied (by `apply`/`iapply`). You can keep patch lists on an undo stack indefinitely and freely mutate your state — they won't drift. The flip side: don't rely on object identity surviving a round-trip through patches; equality survives, identity doesn't.

## `produce` drafts don't outlive the recipe

The draft proxy (and everything you read from it) is only wired up while the recipe runs. When [`produce`][patchdiff.produce.produce] returns, proxies are released; use the returned `result` instead of stashing draft references. Values you *detach* from the draft during the recipe (e.g. `popped = draft["items"].pop()`) stop recording — reinserting `popped` later records its plain data, which is usually what you want.

## Choose `diff` or `produce` deliberately

* Use **`diff`** when you receive two complete states (e.g. from a form, a file, an API response). Cost scales with the size of the structures.
* Use **`produce`** when your code performs the mutations. Cost scales with the number of mutations, which is usually far smaller than the state.

The `produce-vs-diff` benchmark groups in the repository quantify the difference for typical shapes.

## Use `in_place=True` for proxy-backed state

For observ reactive objects (or anything where identity and write-through behavior matter), pass `in_place=True` to `produce` and use `iapply` rather than `apply` — both write through the original object instead of replacing it. See [Observ Integration](observ.md).

## Keep the draft a tree, not a graph

`produce` assumes the structure it's wrapping is a tree: every dict, list, or set reachable from the draft has exactly one path down from the root. Shared references (the same object reachable from two locations) and cycles aren't detected or specially handled, and they cause two distinct problems depending on where the sharing comes from.

**Aliasing already in your base object is silently dropped by the default (copy) mode.** Immutable mode copies the structure key by key rather than as one graph-aware deep copy, so two keys that pointed at the same object going in point at two independent copies coming out — even if the recipe makes no changes at all:

```python
from patchdiff import produce

shared = {"x": 1}
base = {"a": shared, "b": shared}
assert base["a"] is base["b"]  # aliased in your own data

result, patches, reverse_patches = produce(base, lambda draft: None)  # no-op recipe

assert result == {"a": {"x": 1}, "b": {"x": 1}}
assert result["a"] is not result["b"]  # identity silently lost
```

If your data model relies on that shared reference (a config object reused across several slots, a node referenced from two places), the default mode quietly forks it. Use `in_place=True` if identity must survive — it mutates `base` directly, so pre-existing aliasing is preserved.

**Aliasing does survive `in_place=True`, but the recorded patches still won't capture the full mutation.** Each proxy only records what it directly observes, so if two drafted locations share an object, a write made through one location is invisible to the other's patch trail:

```python
from patchdiff import produce, to_json

shared = {"x": 1}
base = {"a": shared, "b": shared}

def recipe(draft):
    draft["a"]["x"] = 2   # mutates the shared dict via the "a" proxy
    draft["b"]["y"] = 3   # mutates the *same* shared dict via a separate "b" proxy

result, patches, reverse_patches = produce(base, recipe, in_place=True)

assert result["a"] is result["b"] == {"x": 2, "y": 3}   # identity preserved, both keys see both changes
assert to_json(patches) == (
    '[{"op": "replace", "path": "/a/x", "value": 2}, '
    '{"op": "add", "path": "/b/y", "value": 3}]'
)  # the patch list never mentions /b/x
```

`result` is correct in your process because it's the same object either way. But replay those `patches` against a fresh, non-aliased copy of `base` — which is what any JSON-based consumer gets, since JSON has no notion of shared references — and `/b/x` never gets set: the replayed state ends up as `{"a": {"x": 2}, "b": {"y": 3}}`, silently missing `/b/x`.

The same reasoning applies to reference cycles (an object nested inside itself, directly or via another container): the draft's proxies track a parent chain and don't detect or break cycles, so building one during a recipe leads to unbounded recursion rather than a clean error.

It's on you to keep the object graph you hand to `produce` acyclic and reference-free — i.e. a proper tree, not a graph. If the same data needs to live in two places, assign independent copies (`copy.deepcopy`, or your own constructor call) rather than the same object twice.
