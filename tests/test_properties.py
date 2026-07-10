"""Property-based tests of patchdiff's core promises.

Hypothesis generates arbitrary nested structures (dicts, lists, sets,
tuples, frozensets and scalars) and verifies the invariants the rest of
the test suite can only spot-check:

* ``diff`` + ``apply`` round-trips in both directions, for any pair of
  structures.
* ``apply`` never mutates its input; ``iapply`` mutates exactly its
  input and returns the same object.
* Serialization is lossless for JSON-shaped data: operations survive
  ``to_json`` → ``json.loads`` → ``Pointer.from_str`` and still apply
  correctly, in both directions.
* Pointer string rendering and token escaping round-trip.
"""

import json
from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st

from patchdiff import apply, diff, iapply, to_json
from patchdiff.pointer import Pointer, escape, unescape

# Scalars that are hashable, so they can double as set members.
hashable_scalars = (
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False)  # NaN != NaN breaks equality-based diffing
    | st.text()
)

# Tuples and frozensets are treated as atomic values by diff(); they stay
# in the value mix to pin that behavior.
atoms = (
    hashable_scalars
    | st.tuples(hashable_scalars, hashable_scalars)
    | st.frozensets(hashable_scalars, max_size=3)
)

values = st.recursive(
    atoms,
    lambda children: (
        st.lists(children, max_size=4)
        | st.dictionaries(st.text(), children, max_size=4)
        | st.sets(hashable_scalars, max_size=4)
    ),
    max_leaves=25,
)

# Top-level structures must be containers (patches address locations
# *inside* the document) and pairs must share their top-level kind:
# diffing e.g. a list against a dict yields a whole-document replace at
# the root, which apply/iapply cannot execute (pinned explicitly in
# test_mixed_kind_roots_are_a_known_limitation below).
diffable_pairs = (
    st.tuples(st.lists(values, max_size=6), st.lists(values, max_size=6))
    | st.tuples(
        st.dictionaries(st.text(), values, max_size=6),
        st.dictionaries(st.text(), values, max_size=6),
    )
    | st.tuples(
        st.sets(hashable_scalars, max_size=6),
        st.sets(hashable_scalars, max_size=6),
    )
)

diffables = (
    st.lists(values, max_size=6)
    | st.dictionaries(st.text(), values, max_size=6)
    | st.sets(hashable_scalars, max_size=6)
)

# The JSON-shaped subset, for which to_json is lossless.
json_values = st.recursive(
    hashable_scalars,
    lambda children: (
        st.lists(children, max_size=4)
        | st.dictionaries(st.text(), children, max_size=4)
    ),
    max_leaves=25,
)
json_diffable_pairs = st.tuples(
    st.lists(json_values, max_size=6), st.lists(json_values, max_size=6)
) | st.tuples(
    st.dictionaries(st.text(), json_values, max_size=6),
    st.dictionaries(st.text(), json_values, max_size=6),
)


@given(pair=diffable_pairs)
def test_diff_apply_round_trip(pair):
    a, b = pair
    ops, reverse_ops = diff(a, b)
    assert apply(a, ops) == b
    assert apply(b, reverse_ops) == a


@given(a=diffables)
def test_diff_of_equal_objects_is_empty(a):
    assert diff(a, deepcopy(a)) == ([], [])


@given(pair=diffable_pairs)
def test_apply_leaves_input_untouched(pair):
    a, b = pair
    ops, _ = diff(a, b)
    snapshot = deepcopy(a)
    apply(a, ops)
    assert a == snapshot


@given(pair=diffable_pairs)
def test_iapply_mutates_input_in_place(pair):
    a, b = pair
    ops, _ = diff(a, b)
    target = deepcopy(a)
    result = iapply(target, ops)
    assert result is target
    assert target == b


@given(pair=json_diffable_pairs)
def test_serialized_patches_round_trip(pair):
    a, b = pair
    ops, reverse_ops = diff(a, b)

    def reload(operations):
        parsed = json.loads(to_json(operations))
        return [{**op, "path": Pointer.from_str(op["path"])} for op in parsed]

    assert apply(a, reload(ops)) == b
    assert apply(b, reload(reverse_ops)) == a


def test_mixed_kind_roots_are_a_known_limitation():
    """Diffing documents of different top-level kinds yields a
    whole-document replace at the root, which apply cannot execute.

    Pinned so the limitation is explicit (and so a future fix has to
    update this test deliberately). See docs/guide/gotchas.md.
    """
    ops, reverse_ops = diff([], {})
    assert ops == [{"op": "replace", "path": Pointer(), "value": {}}]
    assert reverse_ops == [{"op": "replace", "path": Pointer(), "value": []}]
    with pytest.raises(AttributeError):
        apply([], ops)


# The empty pointer is excluded: patchdiff renders the root pointer as
# "/", which parses back as a pointer to the "" key (RFC 6901 renders
# the root as ""). Root pointers only occur in whole-document replaces,
# which cannot be applied anyway.
@given(tokens=st.lists(st.text(), min_size=1, max_size=5))
def test_pointer_string_round_trip(tokens):
    ptr = Pointer(tokens)
    assert Pointer.from_str(str(ptr)) == ptr


@given(token=st.text())
def test_escape_round_trip(token):
    assert unescape(escape(token)) == token
