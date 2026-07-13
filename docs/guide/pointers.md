# JSON Pointers

Every operation's `"path"` is a [`Pointer`][patchdiff.pointer.Pointer], patchdiff's implementation of a JSON pointer ([RFC 6901](https://datatracker.ietf.org/doc/html/rfc6901)): a sequence of *reference tokens* that address a location inside a nested structure.

```python
from patchdiff import diff

ops, _ = diff({"a": {"b": [1]}}, {"a": {"b": [2]}})

ptr = ops[0]["path"]
assert ptr.tokens == ("a", "b", 0)
assert str(ptr) == "/a/b/0"
```

## Immutable, hashable, comparable

Pointers are immutable ([`append`][patchdiff.pointer.Pointer.append] returns a *new* pointer) and they support equality and hashing, so they can be used as dict keys or set members:

```python
from patchdiff.pointer import Pointer

root = Pointer()
child = root.append("a").append(0)

assert root.tokens == ()
assert child == Pointer(["a", 0])
assert str(child) == "/a/0"
```

## String form and escaping

`str(pointer)` renders the RFC 6901 string form, escaping `~` as `~0` and `/` as `~1` inside tokens. [`Pointer.from_str`][patchdiff.pointer.Pointer.from_str] parses one back:

```python
from patchdiff.pointer import Pointer

ptr = Pointer(["a/b", "c~d"])
assert str(ptr) == "/a~1b/c~0d"
assert Pointer.from_str("/a~1b/c~0d").tokens == ("a/b", "c~d")
```

Note that parsing is string-typed: `from_str` cannot know whether `"0"` was a list index or a dict key, so all parsed tokens are strings. That's fine for applying patches, since [`iapply`][patchdiff.apply.iapply] converts numeric-looking keys back to list indices as needed.

## Resolving a pointer

[`evaluate`][patchdiff.pointer.Pointer.evaluate] resolves a pointer against an object and returns `(parent, key, value)`: the container holding the addressed leaf, the leaf's key in it, and its current value:

```python
from patchdiff.pointer import Pointer

obj = {"a": {"b": [10, 20]}}
parent, key, value = Pointer(["a", "b", 1]).evaluate(obj)

assert parent is obj["a"]["b"]
assert key == 1
assert value == 20
```

The walk to the parent is strict, so a missing intermediate raises. Only the *leaf* may be missing (with a container parent), because that's a legitimate target for an `"add"`. Its value then resolves to `None`.

## Divergence from RFC 6901

Strict JSON pointers only contain string tokens. Patchdiff pointers can hold **arbitrary hashable values**: integer list indices stay integers, and set members are addressed by the member value itself (see [diffing sets](diffing.md#sets)). Rendering to a string (or [`to_json`][patchdiff.serialize.to_json]) stringifies each token, which is lossy for non-string tokens. See [gotchas](gotchas.md).
