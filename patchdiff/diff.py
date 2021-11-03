from functools import reduce
from typing import Dict, List, Set

from .pointer import Pointer
from .types import Diffable


def diff_lists(input: List, output: List, ptr: Pointer) -> List:
    memory = {(0, 0): {"ops": [], "cost": 0}}

    def dist(i, j):
        if (i, j) not in memory:
            if i > 0 and j > 0 and input[i - 1] == output[j - 1]:
                step = dist(i - 1, j - 1)
            else:
                paths = []
                if i > 0:
                    base = dist(i - 1, j)
                    op = {"op": "remove", "idx": i - 1}
                    paths.append(
                        {
                            "ops": base["ops"] + [op],
                            "cost": base["cost"] + 1,
                        }
                    )
                if j > 0:
                    base = dist(i, j - 1)
                    op = {"op": "add", "idx": j - 1, "value": output[j - 1]}
                    paths.append(
                        {
                            "ops": base["ops"] + [op],
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
                    paths.append(
                        {
                            "ops": base["ops"] + [op],
                            "cost": base["cost"] + 1,
                        }
                    )
                step = min(paths, key=lambda a: a["cost"])
            memory[(i, j)] = step
        return memory[(i, j)]

    ops = dist(len(input), len(output))["ops"]

    def pad(state, op):
        ops, padding = state
        if op["op"] == "add":
            padded_idx = op["idx"] + 1 + padding
            idx_token = str(padded_idx) if padded_idx < len(input) + padding else "-"
            full_op = {
                "op": "add",
                "path": str(ptr.append(idx_token)),
                "value": op["value"],
            }
            return [ops + [full_op], padding + 1]
        elif op["op"] == "remove":
            full_op = {
                "op": "remove",
                "path": str(ptr.append(str(op["idx"] + padding))),
            }
            return [ops + [full_op], padding - 1]
        else:
            replace_ptr = ptr.append(str(op["idx"] + padding))
            replace_ops = diff(op["original"], op["value"], replace_ptr)
            return [ops + replace_ops, padding]

    padded_ops, _ = reduce(pad, ops, [[], 0])

    return padded_ops


def diff_dicts(input: Dict, output: Dict, ptr: Pointer) -> List:
    ops = []
    input_keys = set(input.keys())
    output_keys = set(output.keys())
    for key in input_keys - output_keys:
        ops.append({"op": "remove", "path": str(ptr.append(key)), "key": key})
    for key in output_keys - input_keys:
        ops.append(
            {
                "op": "add",
                "path": str(ptr.append(key)),
                "key": key,
                "value": output[key],
            }
        )
    for key in input_keys & output_keys:
        ops.extend(diff(input[key], output[key], ptr.append(key)))
    return ops


def diff_sets(input: Set, output: Set, ptr: Pointer) -> List:
    ops = []
    for value in input - output:
        ops.append({"op": "remove", "path": str(ptr.append(value)), "value": value})
    for value in output - input:
        ops.append({"op": "add", "path": str(ptr.append(value)), "value": value})
    return ops


def diff(input: Diffable, output: Diffable, ptr: Pointer = None) -> List:
    if input == output:
        return []
    if ptr is None:
        ptr = Pointer()
    if isinstance(input, list) and isinstance(output, list):
        return diff_lists(input, output, ptr)
    if isinstance(input, dict) and isinstance(output, dict):
        return diff_dicts(input, output, ptr)
    if isinstance(input, set) and isinstance(output, set):
        return diff_sets(input, output, ptr)
    return [{"op": "replace", "path": str(ptr), "value": output}]
