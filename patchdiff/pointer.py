from __future__ import annotations

from typing import Any, Hashable, Iterable

from .types import Diffable


def unescape(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


class Pointer:
    __slots__ = ("tokens",)

    def __init__(self, tokens: Iterable[Hashable] | None = None) -> None:
        if tokens is None:
            tokens = []
        self.tokens = tuple(tokens)

    @staticmethod
    def from_str(path: str) -> "Pointer":
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

    def evaluate(self, obj: Diffable) -> tuple[Diffable, Hashable, Any]:
        key = ""
        parent = None
        cursor = obj
        if tokens := self.tokens:
            # Walk to the parent strictly: any failure here is a path that
            # doesn't exist in the target, and silently landing on a partial
            # parent would let iapply write to the wrong place.
            for key in tokens[:-1]:
                parent = cursor
                cursor = parent[key]
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

    def append(self, token: Hashable) -> "Pointer":
        """append, creating new Pointer"""
        return Pointer((*self.tokens, token))
