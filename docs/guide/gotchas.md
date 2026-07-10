# Gotchas and Best Practices

## Where patchdiff diverges from strict RFC 6902

Patchdiff's patches are JSON-patch *compliant* for JSON-shaped data (dicts with string keys, lists, scalars), but the library deliberately supports more of Python than JSON has:

* **Sets** are diffed and patched natively: elements are added with the `-` token and removed by addressing the element value itself as the final path token. Strict RFC 6902 has no set concept at all.
* **Tuples and frozensets** are treated as atomic values — they are never diffed into, only replaced wholesale.
* **Pointer tokens can be non-strings** (integer list indices, set members). They stringify losslessly for lists, but set-member tokens can't be parsed back from a string — see [Serialization](serialization.md#non-json-values).
* **Only `add`, `remove` and `replace` are emitted.** `move`, `copy` and `test` from RFC 6902 are neither generated nor understood by [`apply`][patchdiff.apply.apply]/[`iapply`][patchdiff.apply.iapply].

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
