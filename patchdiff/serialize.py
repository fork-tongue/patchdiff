import json
from typing import List


def to_str_paths(ops: List) -> List:
    """Return a copy of the operations with each path rendered as a string.

    The [`Pointer`][patchdiff.pointer.Pointer] objects in the `"path"`
    fields are replaced by their escaped JSON pointer (RFC 6901) string
    form; the operations themselves are not mutated.
    """
    return [{**op, "path": str(op["path"])} for op in ops]


def to_json(ops: List, **kwargs) -> str:
    """Serialize a list of operations to a JSON patch (RFC 6902) string.

    Pointer paths are rendered as JSON pointer strings; any keyword
    arguments (like `indent`) are forwarded to `json.dumps`.
    """
    str_ops = to_str_paths(ops)
    return json.dumps(str_ops, **kwargs)
