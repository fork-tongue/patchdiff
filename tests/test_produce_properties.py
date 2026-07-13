"""Property-based tests of ``produce``'s core promises.

``produce`` wraps a base structure in mutation-tracking proxies, runs a
recipe against the draft, and returns ``(result, patches, reverse)``. The
rest of the suite spot-checks individual proxy methods; these tests drive
Hypothesis-generated *recipes* -- random sequences of mutations against
randomly nested drafts -- and assert the invariants that must hold for
every recipe:

* **Transparency**: mutating through the proxies yields exactly the same
  final state as performing the same mutations on a plain copy. Proxies
  must not change what the recipe computes.
* **Forward fidelity**: the emitted ``patches``, applied to the original
  base, reproduce the result. This is ``produce``'s reason to exist.
* **Reverse round-trip**: the ``reverse`` patches, applied to the result,
  restore the original base.
* **Purity**: with ``in_place=False`` the base is left untouched.
* **``in_place=True`` parity**: mutating the base directly yields the same
  result and the same patches as the copying path.
* **Agreement with ``diff``**: ``produce``'s patches and ``diff(base,
  result)`` both carry the base to the same result.

The recipe is expressed as a deterministic interpreter over a
Hypothesis-drawn "program" (a list of integer choices). The exact same
program is replayed against the proxy draft and against a plain reference
copy; because equivalent operations keep both structures identical
step-for-step, the interpreter navigates to corresponding nodes and makes
identical choices on both sides, which is what lets ``result`` be compared
against ``reference`` directly.
"""

from copy import deepcopy

from hypothesis import given, settings
from hypothesis import strategies as st

from patchdiff import apply, diff, produce

# Hashable scalars, usable both as values and as set members. NaN is
# excluded because NaN != NaN would break the equality-based comparisons.
hashable_scalars = (
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False)
    | st.text(max_size=5)
)

# Tuples and frozensets are treated as atomic (immutable) values by the
# proxy layer -- they are never descended into or mutated in place.
atoms = (
    hashable_scalars
    | st.tuples(hashable_scalars, hashable_scalars)
    | st.frozensets(hashable_scalars, max_size=3)
)

# Values that can appear anywhere in a draft: scalars plus nested
# dict/list/set containers.
values = st.recursive(
    atoms,
    lambda children: (
        st.lists(children, max_size=3)
        | st.dictionaries(st.text(max_size=5), children, max_size=3)
        | st.sets(hashable_scalars, max_size=3)
    ),
    max_leaves=12,
)

# Top-level bases must be containers (produce wraps the root in a proxy).
bases = (
    st.lists(values, max_size=4)
    | st.dictionaries(st.text(max_size=5), values, max_size=4)
    | st.sets(hashable_scalars, max_size=4)
)

# A non-empty pool of values the recipe inserts, and a hashable-only pool
# for set members. Programs index into these, so they must not be empty.
value_pools = st.lists(values, min_size=1, max_size=6)
hashable_pools = st.lists(atoms, min_size=1, max_size=6)

# Each program step is (target selector, op selector, key selector, value
# selector); the interpreter reduces each selector modulo the live choices
# at that step, so any integers are valid.
_step = st.tuples(
    st.integers(min_value=0, max_value=1000),
    st.integers(min_value=0, max_value=1000),
    st.integers(min_value=0, max_value=1000),
    st.integers(min_value=0, max_value=1000),
)
programs = st.lists(_step, max_size=10)

# Fixed key alphabet the recipe writes into dicts; small so keys collide
# and exercise both "add" and "replace" paths.
_KEYS = ["a", "b", "c", "d", "e"]


def _is_dict(node):
    return hasattr(node, "keys")


def _is_list(node):
    return hasattr(node, "append")


def _is_set(node):
    return hasattr(node, "add") and hasattr(node, "discard")


def _is_container(node):
    return _is_dict(node) or _is_list(node) or _is_set(node)


def _mutable_nodes(node, acc):
    """Collect every mutable container reachable from ``node`` (itself
    included), in a deterministic pre-order walk.

    Reads go through ``node[key]`` / ``node[i]`` so that, for a proxy
    draft, descending yields the child proxies (which record their own
    mutations). Sets are collected as targets but not descended into --
    their members are atomic hashables, not addressable sub-containers.
    """
    acc.append(node)
    if _is_dict(node):
        for key in list(node.keys()):
            child = node[key]
            if _is_container(child):
                _mutable_nodes(child, acc)
    elif _is_list(node):
        for i in range(len(node)):
            child = node[i]
            if _is_container(child):
                _mutable_nodes(child, acc)
    return acc


def _edit_dict(node, op_sel, key_sel, value):
    keys = list(node.keys())
    op = op_sel % 5
    if op == 1 and keys:
        del node[keys[key_sel % len(keys)]]
    elif op == 2 and keys:
        node.pop(keys[key_sel % len(keys)])
    elif op == 3:
        node.setdefault(_KEYS[key_sel % len(_KEYS)], value)
    elif op == 4:
        node.update({_KEYS[key_sel % len(_KEYS)]: value})
    else:  # op == 0, or a remove op guarded out on an empty dict
        node[_KEYS[key_sel % len(_KEYS)]] = value


def _edit_list(node, op_sel, key_sel, value):
    n = len(node)
    op = op_sel % 6
    if op == 1:
        node.insert(key_sel % (n + 1), value)
    elif op == 2 and n:
        node[key_sel % n] = value
    elif op == 3 and n:
        del node[key_sel % n]
    elif op == 4 and n:
        node.pop(key_sel % n)
    elif op == 5:
        node.reverse()
    else:  # op == 0, or an index op guarded out on an empty list
        node.append(value)


def _edit_set(node, op_sel, value):
    # Only value-driven set ops: picking an existing member by position
    # would diverge between runs because sets are unordered.
    op = op_sel % 3
    if op == 1:
        node.discard(value)
    elif op == 2:
        node.update({value})
    else:  # op == 0
        node.add(value)


def _run(container, program, value_pool, hashable_pool):
    """Replay ``program`` against ``container`` (a proxy draft or a plain
    reference), mutating it in place."""
    for target_sel, op_sel, key_sel, val_sel in program:
        nodes = _mutable_nodes(container, [])
        node = nodes[target_sel % len(nodes)]
        if _is_set(node):
            value = deepcopy(hashable_pool[val_sel % len(hashable_pool)])
            _edit_set(node, op_sel, value)
        elif _is_dict(node):
            value = deepcopy(value_pool[val_sel % len(value_pool)])
            _edit_dict(node, op_sel, key_sel, value)
        else:  # list-like
            value = deepcopy(value_pool[val_sel % len(value_pool)])
            _edit_list(node, op_sel, key_sel, value)


def _make_recipe(program, value_pool, hashable_pool):
    def recipe(draft):
        _run(draft, program, value_pool, hashable_pool)

    return recipe


@settings(deadline=None)
@given(
    base=bases,
    program=programs,
    value_pool=value_pools,
    hashable_pool=hashable_pools,
)
def test_produce_patches_round_trip(base, program, value_pool, hashable_pool):
    original = deepcopy(base)

    # Reference: the same recipe run directly on a plain copy.
    reference = deepcopy(base)
    _run(reference, program, value_pool, hashable_pool)

    result, patches, reverse = produce(
        base, _make_recipe(program, value_pool, hashable_pool)
    )

    # Transparency: proxies compute the same final state as plain objects.
    assert result == reference
    # Purity: in_place=False must not touch the base.
    assert base == original
    # Forward fidelity: patches carry the original base to the result.
    assert apply(deepcopy(original), patches) == result
    # Reverse round-trip: reverse patches restore the base.
    assert apply(deepcopy(result), reverse) == original


@settings(deadline=None)
@given(
    base=bases,
    program=programs,
    value_pool=value_pools,
    hashable_pool=hashable_pools,
)
def test_produce_in_place_matches_copy(base, program, value_pool, hashable_pool):
    copy_result, copy_patches, copy_reverse = produce(
        deepcopy(base), _make_recipe(program, value_pool, hashable_pool)
    )

    target = deepcopy(base)
    inplace_result, inplace_patches, inplace_reverse = produce(
        target, _make_recipe(program, value_pool, hashable_pool), in_place=True
    )

    # in_place returns the very object it was handed, now mutated.
    assert inplace_result is target
    # Both paths agree on the result and on the patches they emit.
    assert inplace_result == copy_result
    assert inplace_patches == copy_patches
    assert inplace_reverse == copy_reverse


@settings(deadline=None)
@given(
    base=bases,
    program=programs,
    value_pool=value_pools,
    hashable_pool=hashable_pools,
)
def test_produce_agrees_with_diff(base, program, value_pool, hashable_pool):
    original = deepcopy(base)
    result, patches, _ = produce(base, _make_recipe(program, value_pool, hashable_pool))

    diff_ops, _ = diff(original, result)

    # produce's patches and diff's patches are different encodings of the
    # same change: both carry the base to the same result.
    assert apply(deepcopy(original), patches) == result
    assert apply(deepcopy(original), diff_ops) == result
