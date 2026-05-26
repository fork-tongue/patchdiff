import pytest

from patchdiff.pointer import Pointer


def test_pointer_get():
    obj = [1, 5, {"foo": 1, "bar": [1, 2, 3]}, "sdfsdf", "fff"]
    assert Pointer([1]).evaluate(obj)[2] == 5
    assert Pointer([2, "bar", 1]).evaluate(obj)[2] == 2


def test_pointer_str():
    assert str(Pointer([1])) == "/1"
    assert str(Pointer(["foo", "bar", "-"])) == "/foo/bar/-"


def test_pointer_repr():
    assert repr(Pointer([1])) == "Pointer([1])"
    assert repr(Pointer(["foo", "bar", "-"])) == "Pointer(['foo', 'bar', '-'])"


def test_pointer_from_str():
    assert Pointer.from_str("/1") == Pointer(["1"])
    assert Pointer.from_str("/foo/bar/-") == Pointer(["foo", "bar", "-"])


def test_pointer_hash():
    assert hash(Pointer([1])) == hash((1,))
    assert hash(Pointer(["foo", "bar", "-"])) == hash(("foo", "bar", "-"))


def test_pointer_set():
    # hash supports comparison operators for use as keys and set elements
    # so we exercise that as well
    unique_pointers = [Pointer([1]), Pointer(["2", "3"])]
    duplicated_pointers = unique_pointers + unique_pointers
    assert len(set(duplicated_pointers)) == len(unique_pointers)


def test_pointer_eq():
    assert Pointer([1]) != [1]
    assert Pointer([1]) != Pointer(["1"])
    assert Pointer([1]) != Pointer([0])
    assert Pointer([1]) == Pointer([1])


def test_pointer_append():
    assert Pointer([1]).append("foo") == Pointer([1, "foo"])


def test_pointer_evaluate_raises_on_missing_dict_key():
    with pytest.raises(KeyError):
        Pointer(["missing", "key"]).evaluate({"present": 1})


def test_pointer_evaluate_raises_on_out_of_range_list_index():
    with pytest.raises(IndexError):
        Pointer([10, "x"]).evaluate([1, 2, 3])


def test_pointer_evaluate_raises_when_traversing_into_primitive():
    with pytest.raises(TypeError):
        Pointer(["a", "b"]).evaluate({"a": 5})
