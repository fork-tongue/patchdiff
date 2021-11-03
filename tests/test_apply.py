from patchdiff import apply, diff


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

    c = apply(a, ops)
    assert c == b
