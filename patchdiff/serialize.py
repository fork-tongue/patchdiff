import json
from typing import List


def to_str_paths(ops: List) -> List:
    return [{**op, "path": str(op["path"])} for op in ops]


def to_json(ops: List, **kwargs) -> str:
    str_ops = to_str_paths(ops)
    return json.dumps(str_ops, **kwargs)
