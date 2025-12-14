from __future__ import annotations

import re
from typing import Any, Hashable, Iterable, Tuple

from .types import Diffable

tilde0_re = re.compile("~0")
tilde1_re = re.compile("~1")
tilde_re = re.compile("~")
slash_re = re.compile("/")


def unescape(token: str) -> str:
    return tilde0_re.sub("~", tilde1_re.sub("/", token))


def escape(token: str) -> str:
    return slash_re.sub("~1", tilde_re.sub("~0", token))


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

    def __eq__(self, other: "Pointer") -> bool:
        if other.__class__ != self.__class__:
            return False
        return self.tokens == other.tokens

    def evaluate(self, obj: Diffable) -> Tuple[Diffable, Hashable, Any]:
        key = ""
        parent = None
        cursor = obj
        if not (tokens := self.tokens):
            return parent, key, cursor
        for key in tokens:
            parent = cursor
            try:
                cursor = parent[key]
            except (KeyError, TypeError):
                # KeyError for dicts, TypeError for sets and lists
                break
        return parent, key, cursor

    def append(self, token: Hashable) -> "Pointer":
        """append, creating new Pointer"""
        return Pointer((*self.tokens, token))
