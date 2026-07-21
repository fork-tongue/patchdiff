from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, TypedDict

if TYPE_CHECKING:
    from .pointer import Pointer

# The structures patchdiff diffs and patches. Consumers may also pass
# duck-typed container look-alikes (e.g. observ reactive proxies).
type Diffable = dict | list | set


class AddOperation(TypedDict):
    """An `add` JSON patch operation."""

    op: Literal["add"]
    path: Pointer
    value: Any


class RemoveOperation(TypedDict):
    """A `remove` JSON patch operation."""

    op: Literal["remove"]
    path: Pointer


class ReplaceOperation(TypedDict):
    """A `replace` JSON patch operation."""

    op: Literal["replace"]
    path: Pointer
    value: Any


type Operation = AddOperation | RemoveOperation | ReplaceOperation
