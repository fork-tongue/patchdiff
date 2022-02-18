from patchdiff import apply, diff
from patchdiff.pointer import Pointer


def test_apply():
    a = {
        "a": [5, 7, 9, {"a", "b", "c"}],
        "b": 6,
    }
    b = {"a": [5, 2, 9, {"b", "c"}], "b": 6, "c": 7}
    ops, rops = diff(a, b)

    assert ops == [
        {"op": "add", "path": Pointer(["c"]), "value": 7},
        {"op": "replace", "path": Pointer(["a", 1]), "value": 2},
        {"op": "remove", "path": Pointer(["a", 3, "a"])},
    ]

    assert rops == [
        {"op": "add", "path": Pointer(["a", 3, "-"]), "value": "a"},
        {"op": "replace", "path": Pointer(["a", 1]), "value": 7},
        {"op": "remove", "path": Pointer(["c"])},
    ]

    c = apply(a, ops)
    assert c == b

    d = apply(b, rops)
    assert a == d


def test_add_remove_list():
    a = []
    b = [1]

    ops, rops = diff(a, b)

    c = apply(a, ops)
    assert c == b

    d = apply(b, rops)
    assert a == d


def test_add_remove_list_extended():
    a = []
    b = ["a", "b", "c"]

    ops, rops = diff(a, b)

    c = apply(a, ops)
    assert c == b

    d = apply(b, rops)
    assert a == d
