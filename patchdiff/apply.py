from copy import deepcopy
from typing import Dict, List

from .pointer import Pointer
from .types import Diffable


def apply(obj: Diffable, patches: List[Dict]) -> Diffable:
    for patch in patches:
        ptr = Pointer.from_str(patch["path"])
        op = patch["op"]
        parent, key, _ = ptr.evaluate(obj)
        value = None
        if op != "remove":
            value = deepcopy(patch["value"])
        if isinstance(parent, list):
            key = int(key)
            if op == "replace":
                parent[key] = value
            elif op == "add":
                if key == "-":
                    parent.append(value)
                else:
                    parent.insert(key, value)
            else:  # remove
                del parent[key]
        elif isinstance(parent, set):
            if op == "add":
                parent.add(value)
            else:  # remove
                parent.remove(key)
        else:  # dict
            if op == "remove":
                del parent[key]
            else:  # add/replace
                parent[key] = value
    return obj
