from __future__ import annotations

from typing import Any, cast

from .pointer import Pointer
from .types import Diffable, Operation


def diff_lists(
    input: list, output: list, ptr: Pointer
) -> tuple[list[Operation], list[Operation]]:
    m_full, n_full = len(input), len(output)

    # Strip common prefix so the DP table only covers the changed region.
    prefix = 0
    prefix_limit = min(m_full, n_full)
    while prefix < prefix_limit and input[prefix] == output[prefix]:
        prefix += 1

    # Strip common suffix without crossing into the prefix region.
    suffix = 0
    while (
        suffix < (m_full - prefix)
        and suffix < (n_full - prefix)
        and input[m_full - 1 - suffix] == output[n_full - 1 - suffix]
    ):
        suffix += 1

    sub_input = input[prefix : m_full - suffix]
    sub_output = output[prefix : n_full - suffix]
    m, n = len(sub_input), len(sub_output)

    # Build DP table bottom-up (iterative approach)
    # dp[i][j] = cost of transforming sub_input[0:i] to sub_output[0:j]
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # Initialize base cases
    for i in range(1, m + 1):
        dp[i][0] = i  # Cost of deleting all elements
    for j in range(1, n + 1):
        dp[0][j] = j  # Cost of adding all elements

    # Fill DP table
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if sub_input[i - 1] == sub_output[j - 1]:
                # Elements match, no operation needed
                dp[i][j] = dp[i - 1][j - 1]
            else:
                # Take minimum of three operations
                dp[i][j] = min(
                    dp[i - 1][j] + 1,  # Remove from input
                    dp[i][j - 1] + 1,  # Add from output
                    dp[i - 1][j - 1] + 1,  # Replace
                )

    # Traceback to extract operations. Indexes are emitted in sub-list
    # coordinates and shifted by `prefix` below so they refer to positions
    # in the original input/output.
    ops: list[dict[str, Any]] = []
    rops: list[dict[str, Any]] = []
    i, j = m, n

    while i > 0 or j > 0:
        if i > 0 and j > 0 and sub_input[i - 1] == sub_output[j - 1]:
            # Elements match, no operation
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or dp[i][j] == dp[i - 1][j] + 1):
            # Remove from input
            ops.append({"op": "remove", "idx": i - 1 + prefix})
            rops.append({"op": "add", "idx": j - 1 + prefix, "value": sub_input[i - 1]})
            i -= 1
        elif j > 0 and (i == 0 or dp[i][j] == dp[i][j - 1] + 1):
            # Add from output
            ops.append({"op": "add", "idx": i - 1 + prefix, "value": sub_output[j - 1]})
            rops.append({"op": "remove", "idx": j - 1 + prefix})
            j -= 1
        else:
            # Replace
            ops.append(
                {
                    "op": "replace",
                    "idx": i - 1 + prefix,
                    "original": sub_input[i - 1],
                    "value": sub_output[j - 1],
                }
            )
            rops.append(
                {
                    "op": "replace",
                    "idx": j - 1 + prefix,
                    "original": sub_output[j - 1],
                    "value": sub_input[i - 1],
                }
            )
            i -= 1
            j -= 1

    # Apply padding to operations (using explicit loops instead of reduce)
    padded_ops: list[Operation] = []
    padding = 0
    # Iterate in reverse to get correct order (traceback extracts operations backwards)
    for op in reversed(ops):
        if op["op"] == "add":
            padded_idx = op["idx"] + 1 + padding
            idx_token = padded_idx if padded_idx < len(input) + padding else "-"
            padded_ops.append(
                {
                    "op": "add",
                    "path": ptr.append(idx_token),
                    "value": op["value"],
                }
            )
            padding += 1
        elif op["op"] == "remove":
            padded_ops.append(
                {
                    "op": "remove",
                    "path": ptr.append(op["idx"] + padding),
                }
            )
            padding -= 1
        else:  # replace
            replace_ptr = ptr.append(op["idx"] + padding)
            replace_ops, _ = diff(op["original"], op["value"], replace_ptr)
            padded_ops.extend(replace_ops)

    padded_rops: list[Operation] = []
    padding = 0
    # Iterate in reverse to get correct order (traceback extracts operations backwards)
    for op in reversed(rops):
        if op["op"] == "add":
            padded_idx = op["idx"] + 1 + padding
            idx_token = padded_idx if padded_idx < len(output) + padding else "-"
            padded_rops.append(
                {
                    "op": "add",
                    "path": ptr.append(idx_token),
                    "value": op["value"],
                }
            )
            padding += 1
        elif op["op"] == "remove":
            padded_rops.append(
                {
                    "op": "remove",
                    "path": ptr.append(op["idx"] + padding),
                }
            )
            padding -= 1
        else:  # replace
            replace_ptr = ptr.append(op["idx"] + padding)
            replace_ops, _ = diff(op["original"], op["value"], replace_ptr)
            padded_rops.extend(replace_ops)

    return padded_ops, padded_rops


def diff_dicts(
    input: dict, output: dict, ptr: Pointer
) -> tuple[list[Operation], list[Operation]]:
    ops: list[Operation] = []
    input_only_rops: list[Operation] = []
    output_only_rops: list[Operation] = []
    common_rops_chunks: list[list[Operation]] = []

    input_keys = set(input.keys()) if input else set()
    output_keys = set(output.keys()) if output else set()

    for key in input_keys - output_keys:
        key_ptr = ptr.append(key)
        ops.append({"op": "remove", "path": key_ptr})
        input_only_rops.append({"op": "add", "path": key_ptr, "value": input[key]})
    input_only_rops.reverse()

    for key in output_keys - input_keys:
        key_ptr = ptr.append(key)
        ops.append({"op": "add", "path": key_ptr, "value": output[key]})
        output_only_rops.append({"op": "remove", "path": key_ptr})
    output_only_rops.reverse()

    for key in input_keys & output_keys:
        key_ops, key_rops = diff(input[key], output[key], ptr.append(key))
        ops.extend(key_ops)
        if key_rops:
            common_rops_chunks.append(key_rops)

    # Match the historical insert(0,…) + key_rops.extend(rops) layering:
    # later common chunks went in front of earlier ones, and the input/output
    # singletons sat behind them in reverse iteration order.
    rops: list[Operation] = []
    for chunk in reversed(common_rops_chunks):
        rops.extend(chunk)
    rops.extend(output_only_rops)
    rops.extend(input_only_rops)
    return ops, rops


def diff_sets(
    input: set, output: set, ptr: Pointer
) -> tuple[list[Operation], list[Operation]]:
    ops: list[Operation] = []
    input_only_rops: list[Operation] = []
    output_only_rops: list[Operation] = []

    for value in input - output:
        ops.append({"op": "remove", "path": ptr.append(value)})
        input_only_rops.append({"op": "add", "path": ptr.append("-"), "value": value})
    input_only_rops.reverse()

    for value in output - input:
        ops.append({"op": "add", "path": ptr.append("-"), "value": value})
        output_only_rops.append({"op": "remove", "path": ptr.append(value)})
    output_only_rops.reverse()

    rops = output_only_rops + input_only_rops
    return ops, rops


def diff(
    input: Diffable, output: Diffable, ptr: Pointer | None = None
) -> tuple[list[Operation], list[Operation]]:
    """Compute the difference between two objects as JSON patch operations.

    Recursively compares `input` and `output` and returns operations in
    both directions. Dicts, lists and sets are compared structurally;
    any other value (scalars, but also tuples and frozensets) is treated
    as atomic and replaced wholesale when it differs.

    Args:
        input: The source object.
        output: The target object.
        ptr: Pointer prefix for the emitted operations; used internally
            during recursion. Leave as `None` to diff from the root.

    Returns:
        A tuple `(ops, reverse_ops)`: applying `ops` to `input` yields
        `output`, and applying `reverse_ops` to `output` yields `input`
        again. Each operation is a dict with an `"op"` key (`"add"`,
        `"remove"` or `"replace"`), a `"path"` key holding a
        [`Pointer`][patchdiff.pointer.Pointer], and a `"value"` key for
        add/replace operations.
    """
    if input == output:
        return [], []
    if ptr is None:
        ptr = Pointer()
    if hasattr(input, "append") and hasattr(output, "append"):  # list
        return diff_lists(cast("list", input), cast("list", output), ptr)
    if hasattr(input, "keys") and hasattr(output, "keys"):  # dict
        return diff_dicts(cast("dict", input), cast("dict", output), ptr)
    if hasattr(input, "add") and hasattr(output, "add"):  # set
        return diff_sets(cast("set", input), cast("set", output), ptr)
    return [{"op": "replace", "path": ptr, "value": output}], [
        {"op": "replace", "path": ptr, "value": input}
    ]
