import re
from typing import Any, Hashable, List, Tuple

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
    def __init__(self, tokens: List[Hashable] = None) -> None:
        if tokens is None:
            tokens = []
        self.tokens = tokens

    @staticmethod
    def from_str(path: str) -> "Pointer":
        tokens = [unescape(t) for t in path.split("/")]
        return Pointer(tokens)

    def __str__(self) -> str:
        return "/" + "/".join(escape(str(t)) for t in self.tokens)

    def __repr__(self) -> str:
        return f"Pointer({repr(self.tokens)})"

    def __hash__(self) -> int:
        return hash(self.tokens)

    def __eq__(self, other: "Pointer") -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.tokens == other.tokens

    def evaluate(self, obj: Diffable) -> Tuple[Diffable, Hashable, Any]:
        key = ""
        parent = None
        cursor = obj
        for key in self.tokens:
            parent = cursor
            if hasattr(parent, "add"):  # set
                break
            if hasattr(parent, "append"):  # list
                if key == "-":
                    break
            try:
                cursor = parent[key]
            except KeyError:
                break
        return parent, key, cursor

    def append(self, token: Hashable) -> "Pointer":
        """append, creating new Pointer"""
        return Pointer(self.tokens + [token])
