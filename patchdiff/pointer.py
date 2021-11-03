import re
from typing import List

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
    def __init__(self, tokens: List[str] = None) -> None:
        if tokens is None:
            tokens = [""]
        self.tokens = tokens

    @staticmethod
    def from_str(path: str) -> "Pointer":
        tokens = [unescape(t) for t in path.split("/")]
        return Pointer(tokens)

    def __str__(self) -> str:
        return "/".join(escape(t) for t in self.tokens)

    def evaluate(self, obj: Diffable):
        key = ""
        parent = None
        value = obj
        for key in self.tokens[1:]:
            parent = value
            if isinstance(parent, set):
                value = key
                continue
            if isinstance(parent, list):
                key = int(key)
            try:
                value = parent[key]
            except KeyError:
                break
        return parent, key, value

    def get(self, obj: Diffable):
        _, _, value = self.evaluate(obj)
        return value

    def set(self, obj: Diffable, value):
        cursor = obj
        for key in self.tokens[1:-1]:
            cursor = cursor[key]
        cursor[self.tokens[-1]] = value

    def iappend(self, token):
        """append, in-place"""
        self.tokens.append(token)

    def append(self, token):
        """append, creating new Pointer"""
        return Pointer(self.tokens + [token])
