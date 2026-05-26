import pytest

from patchdiff import apply, diff
from patchdiff.pointer import Pointer


def test_apply():
    a = {
        "a": [5, 7, 9, {"a", "b", "c"}],
        "b": 6,
    }
    b = {
        "a": [5, 2, 9, {"b", "c"}],
        "b": 6,
        "c": 7,
    }

    ops, rops = diff(a, b)

    c = apply(a, ops)
    assert c == b

    d = apply(b, rops)
    assert a == d


def test_apply_list():
    a = [1, 5, 9, "sdfsdf", "fff"]
    b = ["sdf", 5, 9, "c"]

    ops, rops = diff(a, b)

    c = apply(a, ops)
    assert c == b

    d = apply(b, rops)
    assert a == d


def test_apply_empty():
    a = {
        "a": [5, 7, 9, {"a", "b", "c"}],
        "b": 6,
    }
    b = {
        "a": [5, 7, 9, {"a", "b", "c"}],
        "b": 6,
    }
    assert a == b

    ops, rops = diff(a, b)

    assert not ops
    assert not rops

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
    b = [1, 2, 3]

    ops, rops = diff(a, b)

    c = apply(a, ops)
    assert c == b

    d = apply(b, rops)
    assert a == d


def test_insertion_in_list_front():
    a = [1, 2]
    b = [3, 1, 2]
    ops, rops = diff(a, b)

    c = apply(a, ops)
    assert c == b

    d = apply(b, rops)
    assert a == d


def test_add_remove_list_extended_inverse():
    a = [1, 2, 3]
    b = []

    ops, rops = diff(a, b)

    c = apply(a, ops)
    assert c == b

    d = apply(b, rops)
    assert a == d


def test_add_remove_list_extended_inverse_leaving_start():
    a = [1, 2, 3, 4]
    b = [1]

    ops, rops = diff(a, b)

    c = apply(a, ops)
    assert c == b

    d = apply(b, rops)
    assert a == d


def test_add_remove_list_extended_inverse_leaving_end():
    a = [1, 2, 3, 4]
    b = [4]

    ops, rops = diff(a, b)

    c = apply(a, ops)
    assert c == b

    d = apply(b, rops)
    assert a == d


def test_apply_raises_on_missing_dict_key():
    ops = [{"op": "replace", "path": Pointer(["missing", "key"]), "value": 99}]
    with pytest.raises(KeyError):
        apply({"present": 1}, ops)


def test_apply_raises_on_out_of_range_list_index():
    ops = [{"op": "replace", "path": Pointer([10, "x"]), "value": 99}]
    with pytest.raises(IndexError):
        apply([1, 2, 3], ops)


def test_apply_raises_when_traversing_into_primitive():
    ops = [{"op": "replace", "path": Pointer(["a", "b"]), "value": 99}]
    with pytest.raises(TypeError):
        apply({"a": 5}, ops)
