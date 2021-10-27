from typing import Dict, List


__version__ = "0.1.0"


def diff_lists(input: List, output: List):
    memory = {(0, 0): {"ops": [], "cost": 0}}

    def dist(i, j):
        if (i, j) not in memory:
            if i > 0 and j > 0 and not diff(input[i - 1], output[j - 1]):
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

    return dist(len(input), len(output))["ops"]


def diff_dicts(input: Dict, output: Dict):
    ops = []
    input_keys = set(input.keys())
    output_keys = set(output.keys())
    for key in input_keys - output_keys:
        ops.append({"op": "remove", "key": key})
    for key in output_keys - input_keys:
        ops.append({"op": "add", "key": key, "value": output[key]})
    for key in input_keys & output_keys:
        ops.extend(diff(input[key], output[key]))
    return ops


def diff(input, output):
    # TODO: track paths
    # TODO: properly check equality
    if input == output:
        return []
    if isinstance(input, list) and isinstance(output, list):
        return diff_lists(input, output)
    if isinstance(input, dict) and isinstance(output, dict):
        return diff_dicts(input, output)
    # TODO: sets, tuples
    return [{"op": "replace", "value": output}]
