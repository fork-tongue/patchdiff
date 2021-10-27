from patchdiff import diff


def test_all():
    a = [1, 5, 9, "sdfsdf"]
    b = ["sdf", "c"]
    assert diff(a, b)
