"""Round-trip property tests for prefix/suffix-heavy list pairs.

These exercise lists that share long common prefixes and/or suffixes with
localized edits in the middle — the case that the prefix/suffix trimming
optimization targets in `diff_lists`. Each randomized case asserts the
bi-directional round-trip property: applying `ops` to `a` yields `b`, and
applying `rops` to `b` yields `a`.
"""

import random

from patchdiff import apply, diff


def _random_list(rng: random.Random, n: int) -> list:
    return [rng.randint(0, 100) for _ in range(n)]


def _mutate_middle(
    rng: random.Random,
    base: list,
    n_changes: int,
    kinds: tuple,
) -> list:
    """Apply `n_changes` localized edits in the middle of `base`."""
    out = list(base)
    mid = len(out) // 2
    for i in range(n_changes):
        idx = mid + i
        kind = rng.choice(kinds)
        if kind == "replace" and idx < len(out):
            out[idx] = -(rng.randint(1, 10_000))
        elif kind == "insert":
            out.insert(idx, -(rng.randint(1, 10_000)))
        elif kind == "delete" and idx < len(out):
            del out[idx]
    return out


def test_round_trip_prefix_suffix_heavy_lists():
    """Generates 20+ randomized prefix/suffix-heavy list pairs and asserts
    bi-directional round-trip apply correctness."""
    rng = random.Random(0xC0FFEE)
    cases = 0
    for seed in range(25):
        rng = random.Random(seed)
        n = rng.choice([50, 200, 500, 1000])
        base = _random_list(rng, n)
        n_changes = rng.choice([1, 2, 5, 10])
        kinds = rng.choice(
            [
                ("replace",),
                ("insert",),
                ("delete",),
                ("replace", "insert"),
                ("replace", "insert", "delete"),
            ]
        )
        mutated = _mutate_middle(rng, base, n_changes, kinds)

        ops, rops = diff(base, mutated)
        assert apply(base, ops) == mutated, (
            f"forward apply failed for seed={seed}, n={n}"
        )
        assert apply(mutated, rops) == base, (
            f"reverse apply failed for seed={seed}, n={n}"
        )
        cases += 1

    assert cases >= 20


def test_round_trip_pure_common_prefix():
    """Pair with only a common prefix (suffix differs)."""
    rng = random.Random(7)
    for seed in range(5):
        rng = random.Random(seed)
        prefix = _random_list(rng, 100)
        a = prefix + _random_list(rng, 10)
        b = prefix + _random_list(rng, 12)

        ops, rops = diff(a, b)
        assert apply(a, ops) == b
        assert apply(b, rops) == a


def test_round_trip_pure_common_suffix():
    """Pair with only a common suffix (prefix differs)."""
    for seed in range(5):
        rng = random.Random(seed)
        suffix = _random_list(rng, 100)
        a = _random_list(rng, 10) + suffix
        b = _random_list(rng, 12) + suffix

        ops, rops = diff(a, b)
        assert apply(a, ops) == b
        assert apply(b, rops) == a


def test_round_trip_identical_lists_no_ops():
    """Identical lists must produce no operations regardless of trim path."""
    rng = random.Random(42)
    a = _random_list(rng, 200)
    ops, rops = diff(a, list(a))
    assert ops == []
    assert rops == []


def test_round_trip_full_prefix_match_one_appended():
    """`b` extends `a` with extra trailing element."""
    a = list(range(50))
    b = [*a, 999]
    ops, rops = diff(a, b)
    assert apply(a, ops) == b
    assert apply(b, rops) == a


def test_round_trip_full_suffix_match_one_prepended():
    """`b` prepends a single element to `a`."""
    a = list(range(50))
    b = [-1, *a]
    ops, rops = diff(a, b)
    assert apply(a, ops) == b
    assert apply(b, rops) == a
