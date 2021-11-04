from patchdiff.pointer import Pointer


def test_pointer_get():
    obj = [1, 5, {"foo": 1, "bar": [1, 2, 3]}, "sdfsdf", "fff"]
    assert Pointer(["1"]).evaluate(obj)[2] == 5
    assert Pointer(["2", "bar", "1"]).evaluate(obj)[2] == 2


def test_pointer_str():
    assert str(Pointer(["1"])) == "/1"
    assert str(Pointer(["foo", "bar", "-"])) == "/foo/bar/-"
