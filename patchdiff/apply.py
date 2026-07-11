from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from .pointer import Pointer
from .types import Diffable, Operation

# Immutable types that can never contain (or be) shared mutable state, so
# patch values of these types can be written without a defensive copy.
_SCALAR_TYPES = frozenset({int, float, complex, bool, str, bytes, type(None)})


def iapply(obj: Diffable, patches: list[Operation]) -> Diffable:
    """Apply a list of patches to an object, in place.

    Patch values are deep-copied as they are written, so mutating the
    patched object afterwards never writes through into the patch list
    (and vice versa).

    Args:
        obj: The object to mutate.
        patches: Operations as returned by [`diff`][patchdiff.diff.diff]
            or [`produce`][patchdiff.produce.produce].

    Returns:
        The same object, mutated.
    """
    if not patches:
        return obj
    scalar_types = _SCALAR_TYPES
    copy_value = deepcopy
    for patch in patches:
        # The interpreter below is duck-typed on purpose (dict/list/set
        # look-alikes such as observ proxies must work), so the operation
        # is unpacked once into dynamically-typed locals.
        op_dict = cast("dict[str, Any]", patch)
        ptr: Pointer = op_dict["path"]
        op: str = op_dict["op"]
        target = ptr.evaluate(obj)
        parent: Any = target[0]
        key: Any = target[1]
        value: Any = None
        if op != "remove":
            value = op_dict["value"]
            if value.__class__ not in scalar_types:
                value = copy_value(value)
        # Dispatch on the parent's exact class first (the overwhelmingly
        # common case), falling back to duck typing for container
        # look-alikes such as observ proxies.
        parent_cls = parent.__class__
        if parent_cls is dict or (parent_cls is not list and hasattr(parent, "keys")):
            if op == "remove":
                del parent[key]
            else:  # add/replace
                parent[key] = value
        elif parent_cls is list or hasattr(parent, "append"):
            if key.__class__ is not int:
                try:
                    key = int(key)
                except ValueError:
                    pass

            if op == "replace":
                parent[key] = value
            elif op == "add":
                if key == "-":
                    parent.append(value)
                else:
                    parent.insert(key, value)
            else:  # remove
                del parent[key]
        else:  # set
            if op == "add":
                parent.add(value)
            else:  # remove
                parent.remove(key)
    return obj


def apply(obj: Diffable, patches: list[Operation]) -> Diffable:
    """Apply a list of patches to a deep copy of an object.

    Args:
        obj: The object to copy and patch; it is left unchanged.
        patches: Operations as returned by [`diff`][patchdiff.diff.diff]
            or [`produce`][patchdiff.produce.produce].

    Returns:
        The patched copy.
    """
    return iapply(deepcopy(obj), patches)
