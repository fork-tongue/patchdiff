from patchdiff import diff
from patchdiff.pointer import Pointer


def test_list():
    a = [1, 5, 9, "sdfsdf", "fff"]
    b = ["sdf", 5, 9, "c"]
    ops = diff(a, b)

    assert ops == [
        {"op": "replace", "path": Pointer([0]), "value": "sdf"},
        {"op": "replace", "path": Pointer([3]), "value": "c"},
        {"op": "remove", "path": Pointer([4])},
    ]


def test_list_end():
    a = [1, 2, 3]
    b = [1, 2, 3, 4]
    ops = diff(a, b)

    assert ops == [
        {"op": "add", "path": Pointer(["-"]), "value": 4},
    ]


def test_dicts():
    a = {
        "a": 5,
        "b": 6,
    }
    b = {"a": 3, "b": 6, "c": 7}
    ops = diff(a, b)

    assert ops == [
        {"op": "add", "path": Pointer(["c"]), "key": "c", "value": 7},
        {"op": "replace", "path": Pointer(["a"]), "value": 3},
    ]


def test_sets():
    a = {"a", "b"}
    b = {"a", "c"}
    ops = diff(a, b)

    assert ops == [
        {"op": "remove", "path": Pointer(["b"]), "value": "b"},
        {"op": "add", "path": Pointer(["c"]), "value": "c"},
    ]


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
