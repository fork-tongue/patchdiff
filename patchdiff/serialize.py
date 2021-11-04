import json
from typing import List


def to_str_paths(ops: List) -> List:
    str_ops = ops.copy()
    for op in str_ops:
        op["path"] = str(op["path"])
    return str_ops


def to_json(ops: List, **kwargs) -> str:
    str_ops = to_str_paths(ops)
    return json.dumps(str_ops, **kwargs)
