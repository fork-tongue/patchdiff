from patchdiff import diff
from patchdiff.pointer import Pointer


def test_list():
    a = [1, 5, 9, "sdfsdf", "fff"]
    b = ["sdf", 5, 9, "c"]
    ops, rops = diff(a, b)

    assert ops == [
        {"op": "replace", "path": Pointer([0]), "value": "sdf"},
        {"op": "replace", "path": Pointer([3]), "value": "c"},
        {"op": "remove", "path": Pointer([4])},
    ]
    assert rops == [
        {"op": "add", "path": Pointer(["-"]), "value": "fff"},
        {"op": "replace", "path": Pointer([4]), "value": "sdfsdf"},
        {"op": "replace", "path": Pointer([1]), "value": 1},
    ]


def test_list_end():
    a = [1, 2, 3]
    b = [1, 2, 3, 4]
    ops, rops = diff(a, b)

    assert ops == [
        {"op": "add", "path": Pointer(["-"]), "value": 4},
    ]
    assert rops == [{"op": "remove", "path": Pointer([3])}]


def test_dicts():
    a = {
        "a": 5,
        "b": 6,
    }
    b = {"a": 3, "b": 6, "c": 7}
    ops, rops = diff(a, b)

    assert ops == [
        {"op": "add", "path": Pointer(["c"]), "value": 7},
        {"op": "replace", "path": Pointer(["a"]), "value": 3},
    ]
    assert rops == [
        {"op": "replace", "path": Pointer(["a"]), "value": 5},
        {"op": "remove", "path": Pointer(["c"])},
    ]


def test_sets():
    a = {"a", "b"}
    b = {"a", "c"}
    ops, rops = diff(a, b)

    assert ops == [
        {"op": "remove", "path": Pointer(["b"])},
        {"op": "add", "path": Pointer(["-"]), "value": "c"},
    ]
    assert rops == [
        {"op": "remove", "path": Pointer(["c"])},
        {"op": "add", "path": Pointer(["-"]), "value": "b"},
    ]


def test_mixed():
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
