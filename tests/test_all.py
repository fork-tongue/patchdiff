from patchdiff import diff


def test_list():
    a = [1, 5, 9, "sdfsdf", "fff"]
    b = ["sdf", 5, 9, "c"]
    ops = diff(a, b)

    assert len(ops) == 3
    assert (ops[0]["op"], ops[0]["idx"]) == ("replace", 0)
    assert (ops[1]["op"], ops[1]["idx"]) == ("replace", 3)
    assert (ops[2]["op"], ops[2]["idx"]) == ("remove", 4)


def test_dicts():
    a = {
        "a": 5,
        "b": 6,
    }
    b = {
        "a": 3,
        "b": 6,
        "c": 7
    }
    ops = diff(a, b)

    assert len(ops) == 2
    assert (ops[0]["op"], ops[0]["key"]) == ("add", "c")
    assert (ops[1]["op"], ops[1]["value"]) == ("replace", 3)
