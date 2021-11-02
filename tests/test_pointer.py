from patchdiff.pointer import Pointer


def test_pointer_get():
    obj = [1, 5, {"foo": 1, "bar": [1, 2, 3]}, "sdfsdf", "fff"]
    assert Pointer(["", "1"]).get(obj) == 5
    assert Pointer(["", "2", "bar", "1"]).get(obj) == 2


def test_pointer_str():
    assert str(Pointer(["", "1"])) == "/1"
    assert str(Pointer(["", "foo", "bar", "-"])) == "/foo/bar/-"


def test_pointer_iappend():
    ptr = Pointer()
    ptr.iappend("3")
    ptr.iappend("foo")
    assert str(ptr) == "/3/foo"
