from patchdiff import apply, diff, to_json


def test_to_json_does_not_mutate_ops():
    a = {"x": [1, 2, 3]}
    b = {"x": [1, 9, 3]}
    ops, _ = diff(a, b)

    to_json(ops)

    assert apply(a, ops) == b


def test_to_json():
    a = {
        "a": [5, 7, 9, {"a", "b", "c"}],
        "b": 6,
    }
    b = {"a": [5, 2, 9, {"b", "c"}], "b": 6, "c": 7}

    ops, _ = diff(a, b)

    assert (
        to_json(ops, indent=4)
        == """[
    {
        "op": "add",
        "path": "/c",
        "value": 7
    },
    {
        "op": "replace",
        "path": "/a/1",
        "value": 2
    },
    {
        "op": "remove",
        "path": "/a/3/a"
    }
]"""
    )
