from patchdiff import diff


def test_list():
    a = [1, 5, 9, "sdfsdf", "fff"]
    b = ["sdf", 5, 9, "c"]
    ops = diff(a, b)

    assert ops == [
        {"op": "replace", "path": "/0", "value": "sdf"},
        {"op": "replace", "path": "/3", "value": "c"},
        {"op": "remove", "path": "/4"},
    ]


def test_list_end():
    a = [1, 2, 3]
    b = [1, 2, 3, 4]
    ops = diff(a, b)

    assert ops == [
        {"op": "add", "path": "/-", "value": 4},
    ]


def test_dicts():
    a = {
        "a": 5,
        "b": 6,
    }
    b = {"a": 3, "b": 6, "c": 7}
    ops = diff(a, b)

    assert ops == [
        {"op": "add", "path": "/c", "key": "c", "value": 7},
        {"op": "replace", "path": "/a", "value": 3},
    ]


def test_sets():
    a = {"a", "b"}
    b = {"a", "c"}
    ops = diff(a, b)

    assert ops == [
        {"op": "remove", "path": "/b", "value": "b"},
        {"op": "add", "path": "/c", "value": "c"},
    ]


def test_mixed():
    a = {
        "a": [5, 7, 9, {"a", "b", "c"}],
        "b": 6,
    }
    b = {"a": [5, 2, 9, {"b", "c"}], "b": 6, "c": 7}
    ops = diff(a, b)

    assert ops == [
        {"op": "add", "path": "/c", "key": "c", "value": 7},
        {"op": "replace", "path": "/a/1", "value": 2},
        {"op": "remove", "path": "/a/3/a", "value": "a"},
    ]
