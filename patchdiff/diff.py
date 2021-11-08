from functools import reduce
from typing import Dict, List, Set, Tuple

from .pointer import Pointer
from .types import Diffable


def diff_lists(input: List, output: List, ptr: Pointer) -> Tuple[List, List]:
    memory = {(0, 0): {"ops": [], "rops": [], "cost": 0}}

    def dist(i, j):
        if (i, j) not in memory:
            if i > 0 and j > 0 and input[i - 1] == output[j - 1]:
                step = dist(i - 1, j - 1)
            else:
                paths = []
                if i > 0:
                    base = dist(i - 1, j)
                    op = {"op": "remove", "idx": i - 1}
                    rop = {"op": "add", "idx": i - 1, "value": input[i - 1]}
                    paths.append(
                        {
                            "ops": base["ops"] + [op],
                            "rops": base["rops"] + [rop],
                            "cost": base["cost"] + 1,
                        }
                    )
                if j > 0:
                    base = dist(i, j - 1)
                    op = {"op": "add", "idx": j - 1, "value": output[j - 1]}
                    rop = {"op": "remove", "idx": j - 1}
                    paths.append(
                        {
                            "ops": base["ops"] + [op],
                            "rops": base["rops"] + [rop],
                            "cost": base["cost"] + 1,
                        }
                    )
                if i > 0 and j > 0:
                    base = dist(i - 1, j - 1)
                    op = {
                        "op": "replace",
                        "idx": i - 1,
                        "original": input[i - 1],
                        "value": output[j - 1],
                    }
                    rop = {
                        "op": "replace",
                        "idx": i - 1,
                        "original": output[j - 1],
                        "value": input[i - 1],
                    }
                    paths.append(
                        {
                            "ops": base["ops"] + [op],
                            "rops": base["rops"] + [rop],
                            "cost": base["cost"] + 1,
                        }
                    )
                step = min(paths, key=lambda a: a["cost"])
            memory[(i, j)] = step
        return memory[(i, j)]

    def pad(state, op):
        ops, padding = state
        if op["op"] == "add":
            padded_idx = op["idx"] + 1 + padding
            idx_token = padded_idx if padded_idx < len(input) + padding else "-"
            full_op = {
                "op": "add",
                "path": ptr.append(idx_token),
                "value": op["value"],
            }
            return [ops + [full_op], padding + 1]
        elif op["op"] == "remove":
            full_op = {
                "op": "remove",
                "path": ptr.append(op["idx"] + padding),
            }
            return [ops + [full_op], padding - 1]
        else:
            replace_ptr = ptr.append(op["idx"] + padding)
            replace_ops, _ = diff(op["original"], op["value"], replace_ptr)
            return [ops + replace_ops, padding]

    solution = dist(len(input), len(output))
    padded_ops, _ = reduce(pad, solution["ops"], [[], 0])
    padded_rops, _ = reduce(pad, reversed(solution["rops"]), [[], 0])

    return padded_ops, padded_rops


def diff_dicts(input: Dict, output: Dict, ptr: Pointer) -> Tuple[List, List]:
    ops, rops = [], []
    input_keys = set(input.keys())
    output_keys = set(output.keys())
    for key in input_keys - output_keys:
        ops.append({"op": "remove", "path": ptr.append(key)})
        rops.insert(0, {"op": "add", "path": ptr.append(key), "value": output[key]})
    for key in output_keys - input_keys:
        ops.append(
            {
                "op": "add",
                "path": ptr.append(key),
                "value": output[key],
            }
        )
        rops.insert(0, {"op": "remove", "path": ptr.append(key)})
    for key in input_keys & output_keys:
        key_ops, key_rops = diff(input[key], output[key], ptr.append(key))
        ops.extend(key_ops)
        key_rops.extend(rops)
        rops = key_rops
    return ops, rops


def diff_sets(input: Set, output: Set, ptr: Pointer) -> Tuple[List, List]:
    ops, rops = [], []
    for value in input - output:
        ops.append({"op": "remove", "path": ptr.append(value)})
        rops.insert(0, {"op": "add", "path": ptr.append("-"), "value": value})
    for value in output - input:
        ops.append({"op": "add", "path": ptr.append("-"), "value": value})
        rops.insert(0, {"op": "remove", "path": ptr.append(value)})
    return ops, rops


def diff(input: Diffable, output: Diffable, ptr: Pointer = None) -> Tuple[List, List]:
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
