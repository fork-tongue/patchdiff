from __future__ import annotations

from typing import Dict, List, Set, Tuple

from .pointer import Pointer
from .types import Diffable


def diff_lists(input: List, output: List, ptr: Pointer) -> Tuple[List, List]:
    m, n = len(input), len(output)

    # Build DP table bottom-up (iterative approach)
    # dp[i][j] = cost of transforming input[0:i] to output[0:j]
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # Initialize base cases
    for i in range(1, m + 1):
        dp[i][0] = i  # Cost of deleting all elements
    for j in range(1, n + 1):
        dp[0][j] = j  # Cost of adding all elements

    # Fill DP table
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if input[i - 1] == output[j - 1]:
                # Elements match, no operation needed
                dp[i][j] = dp[i - 1][j - 1]
            else:
                # Take minimum of three operations
                dp[i][j] = min(
                    dp[i - 1][j] + 1,  # Remove from input
                    dp[i][j - 1] + 1,  # Add from output
                    dp[i - 1][j - 1] + 1,  # Replace
                )

    # Traceback to extract operations
    ops = []
    rops = []
    i, j = m, n

    while i > 0 or j > 0:
        if i > 0 and j > 0 and input[i - 1] == output[j - 1]:
            # Elements match, no operation
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or dp[i][j] == dp[i - 1][j] + 1):
            # Remove from input
            ops.append({"op": "remove", "idx": i - 1})
            rops.append({"op": "add", "idx": j - 1, "value": input[i - 1]})
            i -= 1
        elif j > 0 and (i == 0 or dp[i][j] == dp[i][j - 1] + 1):
            # Add from output
            ops.append({"op": "add", "idx": i - 1, "value": output[j - 1]})
            rops.append({"op": "remove", "idx": j - 1})
            j -= 1
        else:
            # Replace
            ops.append(
                {
                    "op": "replace",
                    "idx": i - 1,
                    "original": input[i - 1],
                    "value": output[j - 1],
                }
            )
            rops.append(
                {
                    "op": "replace",
                    "idx": j - 1,
                    "original": output[j - 1],
                    "value": input[i - 1],
                }
            )
            i -= 1
            j -= 1

    # Apply padding to operations (using explicit loops instead of reduce)
    padded_ops = []
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

    padded_rops = []
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


def diff_dicts(input: Dict, output: Dict, ptr: Pointer) -> Tuple[List, List]:
    ops, rops = [], []
    input_keys = set(input.keys()) if input else set()
    output_keys = set(output.keys()) if output else set()
    if (input_only := input_keys - output_keys):
        for key in input_only:
            key_ptr = ptr.append(key)
            ops.append({"op": "remove", "path": key_ptr})
            rops.insert(0, {"op": "add", "path": key_ptr, "value": input[key]})
    if (output_only := output_keys - input_keys):
        for key in output_only:
            key_ptr = ptr.append(key)
            ops.append(
                {
                    "op": "add",
                    "path": key_ptr,
                    "value": output[key],
                }
            )
            rops.insert(0, {"op": "remove", "path": key_ptr})
    if (common := input_keys & output_keys):
        for key in common:
            key_ops, key_rops = diff(input[key], output[key], ptr.append(key))
            ops.extend(key_ops)
            key_rops.extend(rops)
            rops = key_rops
    return ops, rops


def diff_sets(input: Set, output: Set, ptr: Pointer) -> Tuple[List, List]:
    ops, rops = [], []
    if (input_only := input - output):
        for value in input_only:
            ops.append({"op": "remove", "path": ptr.append(value)})
            rops.insert(0, {"op": "add", "path": ptr.append("-"), "value": value})
    if (output_only := output - input):
        for value in output_only:
            ops.append({"op": "add", "path": ptr.append("-"), "value": value})
            rops.insert(0, {"op": "remove", "path": ptr.append(value)})
    return ops, rops


def diff(
    input: Diffable, output: Diffable, ptr: Pointer | None = None
) -> Tuple[List, List]:
    if input == output:
        return [], []
    if ptr is None:
        ptr = Pointer()
    if hasattr(input, "append") and hasattr(output, "append"):  # list
        return diff_lists(input, output, ptr)
    if hasattr(input, "keys") and hasattr(output, "keys"):  # dict
        return diff_dicts(input, output, ptr)
    if hasattr(input, "add") and hasattr(output, "add"):  # set
        return diff_sets(input, output, ptr)
    return [{"op": "replace", "path": ptr, "value": output}], [
        {"op": "replace", "path": ptr, "value": input}
    ]
