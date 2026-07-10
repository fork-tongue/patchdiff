"""Run the json-patch-tests conformance corpus against patchdiff.

The JSON files in tests/rfc6902/ are vendored verbatim from
https://github.com/json-patch/json-patch-tests (retrieved 2026-07-10),
the community conformance suite for RFC 6902 implementations.

Patchdiff deliberately implements a subset-plus-extensions of RFC 6902
(see docs/guide/gotchas.md), so cases that exercise behavior outside
that subset are skipped with an explicit reason rather than silently
dropped:

* ``move``, ``copy`` and ``test`` operations are not implemented.
* Operations on the document root (path ``""``) are not supported;
  patches always address a location *inside* a container.
* Invalid-patch cases (the corpus' ``error`` records) are skipped
  wholesale: patchdiff does not validate patches, it applies trusted
  patches produced by ``diff()``/``produce()``, and what it raises for
  malformed input is not part of its contract.

Every remaining case must pass exactly: paths are parsed from their
JSON pointer string form with ``Pointer.from_str``, applied with
``apply``, and compared against the corpus' expected document.
"""

import json
from pathlib import Path

import pytest

from patchdiff import apply
from patchdiff.pointer import Pointer

CORPUS_DIR = Path(__file__).parent / "rfc6902"

SUPPORTED_OPS = {"add", "remove", "replace"}


def corpus_cases():
    for filename in ("tests.json", "spec_tests.json"):
        cases = json.loads((CORPUS_DIR / filename).read_text())
        for index, case in enumerate(cases):
            if "patch" not in case:
                continue  # comment-only records
            comment = case.get("comment", "")
            case_id = f"{filename.removesuffix('.json')}-{index:03d}-{comment[:60]}"
            yield pytest.param(case, id=case_id)


def skip_reason(case):
    if case.get("disabled"):
        return "disabled in the upstream corpus"
    if "error" in case:
        return f"patchdiff does not validate patches ({case['error']!r})"
    unsupported = {
        op.get("op") for op in case["patch"] if op.get("op") not in SUPPORTED_OPS
    }
    if unsupported:
        return f"unsupported operation(s): {sorted(unsupported)}"
    if any(op["path"] == "" for op in case["patch"]):
        return "operations on the document root are not supported"
    return None


def to_patchdiff_op(op):
    converted = {"op": op["op"], "path": Pointer.from_str(op["path"])}
    if "value" in op:
        converted["value"] = op["value"]
    return converted


@pytest.mark.parametrize("case", list(corpus_cases()))
def test_corpus_case(case):
    reason = skip_reason(case)
    if reason:
        pytest.skip(reason)
    ops = [to_patchdiff_op(op) for op in case["patch"]]
    result = apply(case["doc"], ops)
    if "expected" in case:
        assert result == case["expected"]
