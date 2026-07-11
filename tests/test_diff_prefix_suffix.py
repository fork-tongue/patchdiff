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


# ---------------------------------------------------------------------------
# Nested-item lists
#
# The prefix/suffix trim uses the same `==` operator the DP uses, so for any
# value type the trim's "matched" decision agrees with the DP's diagonal-step
# decision. These cases lock that in for items whose equality is a deep
# structural compare (dicts, lists, sets, and mixed nested containers).
# ---------------------------------------------------------------------------


def _nested_dict(rng: random.Random, i: int) -> dict:
    """Build a dict whose equality is a non-trivial structural compare."""
    return {
        "id": i,
        "name": f"item_{i}",
        "tags": [f"t{i}_{k}" for k in range(rng.randint(2, 5))],
        "meta": {"a": i % 7, "b": i % 11, "nested": {"x": [i, i + 1, i + 2]}},
        "flags": {f"f{i % 5}", f"f{i % 3}"},
    }


def test_round_trip_lists_of_nested_dicts():
    """Round-trip property test for lists whose items are nested dicts."""
    for seed in range(10):
        rng = random.Random(seed)
        n = rng.choice([20, 50, 100])
        base = [_nested_dict(rng, i) for i in range(n)]

        # Mutate a small slice in the middle: replace, insert, delete one each.
        mutated = [
            {**d, "meta": dict(d["meta"])} for d in base
        ]  # shallow-deep copy enough to detach
        mid = n // 2
        # Replace: change a deeply-nested field
        mutated[mid]["meta"]["nested"] = {"x": [-1, -2, -3]}
        # Insert: brand-new dict between mid+1 and mid+2
        mutated.insert(mid + 1, _nested_dict(rng, 10_000 + seed))
        # Delete: drop the item after the inserted one
        del mutated[mid + 2]

        ops, rops = diff(base, mutated)
        assert apply(base, ops) == mutated, f"forward failed for seed={seed}"
        assert apply(mutated, rops) == base, f"reverse failed for seed={seed}"


def test_round_trip_lists_with_nested_lists_as_items():
    """Items are themselves lists — equality is recursive."""
    rng = random.Random(99)
    base = [[rng.randint(0, 9) for _ in range(rng.randint(3, 8))] for _ in range(60)]
    mutated = [list(row) for row in base]
    # Localized change deep inside one item.
    mutated[30][0] = 999
    # And replace one whole item.
    mutated[31] = [-1, -2, -3]

    ops, rops = diff(base, mutated)
    assert apply(base, ops) == mutated
    assert apply(mutated, rops) == base


def test_round_trip_lists_of_sets():
    """Items are sets — `==` is set-equality, not identity."""
    base = [{i, i + 1, i + 2} for i in range(40)]
    # Equal-by-value but distinct objects in the prefix/suffix region
    # ensures we exercise structural equality, not `is`.
    mutated = [{i, i + 1, i + 2} for i in range(40)]
    mutated[20] = {-1, -2, -3}  # one change in the middle

    ops, rops = diff(base, mutated)
    assert apply(base, ops) == mutated
    assert apply(mutated, rops) == base


def test_prefix_suffix_with_equal_but_distinct_nested_objects():
    """Items in the common prefix/suffix are *equal* but not the *same*
    object. The trim must rely on `==`, not `is`."""
    shared_prefix_a = [{"k": i, "v": [i, i + 1]} for i in range(20)]
    shared_prefix_b = [{"k": i, "v": [i, i + 1]} for i in range(20)]
    assert shared_prefix_a == shared_prefix_b
    assert all(x is not y for x, y in zip(shared_prefix_a, shared_prefix_b))

    middle_a = [{"k": "a_only", "v": [1]}]
    middle_b = [{"k": "b_only", "v": [2]}]

    shared_suffix_a = [{"k": i + 100, "v": [i]} for i in range(20)]
    shared_suffix_b = [{"k": i + 100, "v": [i]} for i in range(20)]

    a = shared_prefix_a + middle_a + shared_suffix_a
    b = shared_prefix_b + middle_b + shared_suffix_b

    ops, rops = diff(a, b)
    assert apply(a, ops) == b
    assert apply(b, rops) == a

    # The change should be confined to the middle position (index 20).
    # We don't assert the exact op shape, but every emitted op's path must
    # start with /20 (the middle index in the full list).
    for op in ops:
        path_tokens = op["path"].tokens
        assert path_tokens and path_tokens[0] == 20, (
            f"unexpected op outside the middle region: {op}"
        )


def test_mostly_different_large_lists_round_trip():
    """Large list pairs with almost nothing in common hit the Myers
    cutoff and are emitted as element-wise replaces, like the DP did."""
    a = list(range(0, 200))
    b = list(range(1000, 1200))  # fully disjoint
    ops, rops = diff(a, b)
    assert all(op["op"] == "replace" for op in ops)
    assert len(ops) == 200
    assert apply(a, ops) == b
    assert apply(b, rops) == a


def test_partially_common_large_lists_round_trip():
    """A large pair sharing ~15% of elements (below the cutoff's 25%
    threshold) still round-trips after the search gives up."""
    rng = random.Random(7)
    a = [rng.randint(0, 10_000) for _ in range(300)]
    b = [rng.randint(0, 10_000) for _ in range(300)]
    for i in range(0, 300, 7):  # sprinkle common elements
        b[i] = a[i]
    ops, rops = diff(a, b)
    assert apply(a, ops) == b
    assert apply(b, rops) == a
