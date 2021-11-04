from patchdiff import apply, diff
from patchdiff.pointer import Pointer


def test_mixed():
    a = {
        "a": [5, 7, 9, {"a", "b", "c"}],
        "b": 6,
    }
    b = {"a": [5, 2, 9, {"b", "c"}], "b": 6, "c": 7}
    ops = diff(a, b)

    assert ops == [
        {"op": "add", "path": Pointer(["c"]), "key": "c", "value": 7},
        {"op": "replace", "path": Pointer(["a", 1]), "value": 2},
        {"op": "remove", "path": Pointer(["a", 3, "a"]), "value": "a"},
    ]

    c = apply(a, ops)
    assert c == b
