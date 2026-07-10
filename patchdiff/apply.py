from copy import deepcopy
from typing import Dict, List

from .types import Diffable


def iapply(obj: Diffable, patches: List[Dict]) -> Diffable:
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
    for patch in patches:
        ptr = patch["path"]
        op = patch["op"]
        parent, key, _ = ptr.evaluate(obj)
        value = None
        if op != "remove":
            value = deepcopy(patch["value"])
        if hasattr(parent, "keys"):  # dict
            if op == "remove":
                del parent[key]
            else:  # add/replace
                parent[key] = value
        elif hasattr(parent, "append"):  # list
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


def apply(obj: Diffable, patches: List[Dict]) -> Diffable:
    """Apply a list of patches to a deep copy of an object.

    Args:
        obj: The object to copy and patch; it is left unchanged.
        patches: Operations as returned by [`diff`][patchdiff.diff.diff]
            or [`produce`][patchdiff.produce.produce].

    Returns:
        The patched copy.
    """
    return iapply(deepcopy(obj), patches)
