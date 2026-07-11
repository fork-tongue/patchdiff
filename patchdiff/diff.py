from __future__ import annotations

from typing import Any, cast

from .pointer import Pointer
from .types import Diffable, Operation


def _myers_script(a: list, b: list) -> list[tuple[str, int, int]]:
    """Compute a shortest edit script between a and b with Myers' greedy
    algorithm (An O(ND) Difference Algorithm and Its Variations, 1986).

    Returns forward-ordered entries ("del", i, j) / ("ins", i, j) where
    (i, j) are the pre-operation cursors: "del" removes a[i] while the
    output cursor is at j, "ins" inserts b[j] at input cursor i. Runs of
    equal elements produce no entries.

    Time is O((m+n)·D) and memory O(D²) for D actual differences, so
    nearly-equal lists are cheap regardless of their size. To keep the
    worst case (barely anything in common) from degenerating into a
    quadratic search for a shortest script nobody benefits from, the
    search gives up once D exceeds half the combined length — the lists
    then share less than a quarter of their elements, and the whole
    region is emitted as a single hunk (which the replace pairing turns
    into element-wise replaces, exactly what the old DP produced for
    such inputs). Small regions are always solved exactly.
    """
    m, n = len(a), len(b)
    if not m:
        return [("ins", 0, j) for j in range(n)]
    if not n:
        return [("del", i, 0) for i in range(m)]

    max_cost = (m + n) // 2
    if max_cost < 64:
        max_cost = m + n  # always exact below the cutoff floor

    # v[offset + k] = furthest x reached on diagonal k (k = x - y) with
    # the current number of edits d.
    offset = m + n
    v = [0] * (2 * offset + 2)
    trace = []
    d_final = -1
    for d in range(offset + 1):
        if d > max_cost:
            # Too expensive: emit the whole region as one hunk.
            return [("del", i, 0) for i in range(m)] + [("ins", m, j) for j in range(n)]
        # Snapshot the diagonals the backtrack for round d needs (the
        # state after round d-1); only [-d, d] is ever read.
        trace.append(v[offset - d : offset + d + 1])
        lo, hi = offset - d, offset + d
        for vi in range(lo, hi + 1, 2):  # vi = offset + k
            if vi == lo or (vi != hi and v[vi - 1] < v[vi + 1]):
                x = v[vi + 1]  # step down: insertion
            else:
                x = v[vi - 1] + 1  # step right: deletion
            y = x - vi + offset  # y = x - k
            while x < m and y < n and a[x] == b[y]:  # follow the snake
                x += 1
                y += 1
            v[vi] = x
            if x >= m and y >= n:
                d_final = d
                break
        if d_final >= 0:
            break

    # Backtrack from (m, n) to (0, 0), emitting one edit per round.
    script: list[tuple[str, int, int]] = []
    x, y = m, n
    for d in range(d_final, 0, -1):
        vprev = trace[d]  # covers k in [-d, d]; index with k + d
        k = x - y
        if k == -d or (k != d and vprev[k - 1 + d] < vprev[k + 1 + d]):
            prev_k = k + 1  # arrived by insertion
        else:
            prev_k = k - 1  # arrived by deletion
        prev_x = vprev[prev_k + d]
        prev_y = prev_x - prev_k
        if prev_k == k + 1:
            script.append(("ins", prev_x, prev_y))
        else:
            script.append(("del", prev_x, prev_y))
        x, y = prev_x, prev_y
    script.reverse()
    return script


def _pad_ops(
    intermediate: list[dict[str, Any]], list_len: int, ptr: Pointer
) -> list[Operation]:
    """Convert intermediate ops (absolute indices) into patch operations.

    Operations apply sequentially, so every applied add shifts later
    indices up by one and every remove shifts them down; `padding`
    tracks that running offset. Replaces recurse through diff() so
    paired containers turn into deep paths instead of wholesale element
    replacement.
    """
    padded: list[Operation] = []
    padding = 0
    for op in intermediate:
        kind = op["op"]
        if kind == "add":
            padded_idx = op["idx"] + 1 + padding
            idx_token = padded_idx if padded_idx < list_len + padding else "-"
            padded.append(
                {
                    "op": "add",
                    "path": ptr.append(idx_token),
                    "value": op["value"],
                }
            )
            padding += 1
        elif kind == "remove":
            padded.append(
                {
                    "op": "remove",
                    "path": ptr.append(op["idx"] + padding),
                }
            )
            padding -= 1
        else:  # replace
            replace_ptr = ptr.append(op["idx"] + padding)
            replace_ops, _ = diff(op["original"], op["value"], replace_ptr)
            padded.extend(replace_ops)
    return padded


def diff_lists(
    input: list, output: list, ptr: Pointer
) -> tuple[list[Operation], list[Operation]]:
    m_full, n_full = len(input), len(output)

    # Strip common prefix so the edit search only covers the changed region.
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

    # Group the edit script into hunks: maximal runs of edits with no
    # kept element in between. Within a hunk deletions come first (the
    # backtrack's tie-breaking guarantees it), so hunk boundaries are
    # exactly the places where an edit doesn't start at the previous
    # edit's end cursor.
    hunks: list[tuple[list[int], list[int], int, int]] = []
    dels: list[int] = []
    inss: list[int] = []
    hunk_i = hunk_j = 0
    post: tuple[int, int] | None = None
    for kind, i, j in _myers_script(sub_input, sub_output):
        if post is not None and (i, j) != post:
            hunks.append((dels, inss, hunk_i, hunk_j))
            dels, inss = [], []
            post = None
        if post is None:
            hunk_i, hunk_j = i, j
        if kind == "del":
            dels.append(i)
            post = (i + 1, j)
        else:
            inss.append(j)
            post = (i, j + 1)
    if dels or inss:
        hunks.append((dels, inss, hunk_i, hunk_j))

    # Emit intermediate operations per hunk: the k-th deletion pairs
    # with the k-th insertion as a replace (recursed into by _pad_ops),
    # the unpaired remainder becomes plain removes or adds. Indexes are
    # emitted in sub-list coordinates and shifted by `prefix` so they
    # refer to positions in the original input/output.
    ops: list[dict[str, Any]] = []
    rops: list[dict[str, Any]] = []
    for dels, inss, hunk_i, hunk_j in hunks:
        paired = min(len(dels), len(inss))
        for t in range(paired):
            di, sj = dels[t], inss[t]
            ops.append(
                {
                    "op": "replace",
                    "idx": di + prefix,
                    "original": sub_input[di],
                    "value": sub_output[sj],
                }
            )
            rops.append(
                {
                    "op": "replace",
                    "idx": sj + prefix,
                    "original": sub_output[sj],
                    "value": sub_input[di],
                }
            )
        if len(dels) > paired:
            # After the hunk the output cursor sits past its last
            # insertion (or where the hunk started, if it had none).
            add_idx = (inss[-1] if inss else hunk_j - 1) + prefix
            for di in dels[paired:]:
                ops.append({"op": "remove", "idx": di + prefix})
                rops.append({"op": "add", "idx": add_idx, "value": sub_input[di]})
        elif len(inss) > paired:
            add_idx = (dels[-1] if dels else hunk_i - 1) + prefix
            for sj in inss[paired:]:
                ops.append({"op": "add", "idx": add_idx, "value": sub_output[sj]})
                rops.append({"op": "remove", "idx": sj + prefix})

    return _pad_ops(ops, m_full, ptr), _pad_ops(rops, n_full, ptr)


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
