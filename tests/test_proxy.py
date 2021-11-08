"""
Tests that check that patchdiff apply and diff work
on proxied objects.
"""
from collections import UserDict, UserList

from patchdiff import apply, diff


def test_proxy_dict():
    data = {"foo": "bar"}
    obj = UserDict(data)

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

    old = obj.copy()
    obj[1] = 3

    assert old[1] == 2
    assert obj[1] == 3

    ops, reverse_ops = diff(old, obj)

    assert apply(old, ops) == obj
    assert apply(obj, reverse_ops) == old
