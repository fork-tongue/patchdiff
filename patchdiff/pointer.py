from __future__ import annotations

from collections.abc import Hashable, Iterable
from typing import Any, cast

from .types import Diffable


def unescape(token: str) -> str:
    """Decode a JSON pointer reference token (`~1` → `/`, `~0` → `~`)."""
    return token.replace("~1", "/").replace("~0", "~")


def escape(token: str) -> str:
    """Encode a reference token for a JSON pointer string (`~` → `~0`, `/` → `~1`)."""
    return token.replace("~", "~0").replace("/", "~1")


class Pointer:
    """A JSON pointer (RFC 6901): a path into a nested structure.

    A pointer is an immutable sequence of reference tokens;
    [`append`][patchdiff.pointer.Pointer.append] returns a new pointer
    rather than mutating. `str()` renders the escaped JSON pointer
    string form and [`from_str`][patchdiff.pointer.Pointer.from_str]
    parses one back. Unlike strict RFC 6901, tokens can be arbitrary
    hashable values (not just strings), so pointers can address set
    members and integer list indices directly.
    """

    __slots__ = ("tokens",)

    def __init__(self, tokens: Iterable[Hashable] | None = None) -> None:
        if tokens is None:
            tokens = []
        self.tokens = tuple(tokens)

    @staticmethod
    def from_str(path: str) -> Pointer:
        """Parse an escaped JSON pointer string (e.g. `"/a/0/b"`) into a Pointer.

        All tokens are parsed as strings; numeric list indices become
        string tokens, which `evaluate` and `iapply` convert back as
        needed.
        """
        tokens = [unescape(t) for t in path.split("/")[1:]]
        return Pointer(tokens)

    def __str__(self) -> str:
        return "/" + "/".join(escape(str(t)) for t in self.tokens)

    def __repr__(self) -> str:
        return f"Pointer({list(self.tokens)!r})"

    def __hash__(self) -> int:
        return hash(self.tokens)

    def __eq__(self, other: Any) -> bool:
        if other.__class__ != self.__class__:
            return False
        return self.tokens == other.tokens

    def evaluate(self, obj: Diffable) -> tuple[Diffable | None, Hashable, Any]:
        """Resolve the pointer against an object.

        Returns:
            A tuple `(parent, key, value)`: the container holding the
            addressed leaf, the leaf's key within that container, and
            the leaf's current value — `None` when the leaf does not
            exist yet (the target of an `"add"`, or a list append via
            the `"-"` token).
        """
        key: Hashable = ""
        parent: Any = None
        cursor: Any = obj
        if tokens := self.tokens:
            # Walk to the parent strictly: any failure here is a path that
            # doesn't exist in the target, and silently landing on a partial
            # parent would let iapply write to the wrong place.
            for key in tokens[:-1]:
                parent = cursor
                try:
                    cursor = parent[key]
                except TypeError:
                    # Pointers parsed from strings carry string tokens;
                    # sequences reject those, so retry list indices as
                    # integers (iapply does the same at the leaf).
                    if not hasattr(parent, "append"):
                        raise
                    cursor = parent[int(cast("str", key))]
            # The leaf may legitimately not exist (add ops on dicts, list
            # "-" append) so we tolerate lookup failures there — but only
            # when the parent is itself a container we can write into.
            parent = cursor
            key = tokens[-1]
            try:
                cursor = parent[key]
            except (KeyError, IndexError, TypeError):
                if not (
                    hasattr(parent, "keys")
                    or hasattr(parent, "append")
                    or hasattr(parent, "add")
                ):
                    raise
                cursor = None
        return parent, key, cursor

    def append(self, token: Hashable) -> Pointer:
        """Return a new Pointer with `token` appended; self is unchanged."""
        return Pointer((*self.tokens, token))
