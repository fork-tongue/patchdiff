"""
Tests that check that patchdiff apply and diff work
on proxied objects.
"""
from collections import UserDict, UserList
from collections.abc import Set

from patchdiff import apply, diff


class SetProxy(Set):
    """
    Custom proxy class that works like UserDict and UserList by
    storing the original data under the 'data' attribute.
    """

    def __init__(self, *args, **kwargs):
        self.data = set(*args, **kwargs)

    def __contains__(self, *args, **kwargs):
        return self.data.__contains__(*args, **kwargs)

    def __iter__(self, *args, **kwargs):
        return self.data.__iter__(*args, **kwargs)

    def __len__(self, *args, **kwargs):
        return self.data.__len__(*args, **kwargs)

    def __getattribute__(self, attr):
        # Redirect __class__ to super() to make sure
        # isinstance(obj, set) will fail
        if attr in {"data", "_from_iterable", "__class__"}:
            return super().__getattribute__(attr)
        return self.data.__getattribute__(attr)


def test_proxy_dict():
    data = {"foo": "bar"}
    obj = UserDict(data)
    assert not isinstance(obj, dict)

    old = obj.copy()
    obj["foo"] = "baz"

    assert old["foo"] == "bar"
    assert obj["foo"] == "baz"

    ops, reverse_ops = diff(old, obj)

    assert apply(old, ops) == obj
    assert apply(obj, reverse_ops) == old


def test_proxy_list():
    data = [1, 2]
    obj = UserList(data)
    assert not isinstance(obj, list)

    old = obj.copy()
    obj[1] = 3

    assert old[1] == 2
    assert obj[1] == 3

    ops, reverse_ops = diff(old, obj)

    assert apply(old, ops) == obj
    assert apply(obj, reverse_ops) == old


def test_proxy_set():
    data = {"a", "b"}
    obj = SetProxy(data)
    assert not isinstance(obj, set)

    old = obj.copy()
    obj.add("c")

    assert "c" not in old
    assert "c" in obj

    ops, reverse_ops = diff(old, obj)

    assert apply(old, ops) == obj
    assert apply(obj, reverse_ops) == old
