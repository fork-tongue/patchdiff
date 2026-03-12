"""
Benchmark suite for patchdiff performance testing using pytest-benchmark.

Run benchmarks:
    uv run pytest benchmarks/benchmark.py --benchmark-only

Save baseline:
    uv run pytest benchmarks/benchmark.py --benchmark-only --benchmark-autosave

Compare against baseline:
    uv run pytest benchmarks/benchmark.py --benchmark-only --benchmark-compare=0001

Fail if performance degrades >5%:
    uv run pytest benchmarks/benchmark.py --benchmark-only --benchmark-compare=0001 --benchmark-compare-fail=mean:5%
"""

import copy
import random

import pytest

from patchdiff import apply, diff, produce
from patchdiff.pointer import Pointer

# Optional observ integration for benchmarks
try:
    from observ import reactive, to_raw

    OBSERV_AVAILABLE = True
except ImportError:
    OBSERV_AVAILABLE = False

# Set seed for reproducibility
random.seed(42)


def generate_random_list(size: int, value_range: int = 1000) -> list[int]:
    """Generate a random list of integers."""
    return [random.randint(0, value_range) for _ in range(size)]


def generate_similar_lists(
    size: int, change_ratio: float = 0.1
) -> tuple[list[int], list[int]]:
    """
    Generate two similar lists with specified change ratio.

    Args:
        size: Size of the lists
        change_ratio: Ratio of elements that differ (0.0 to 1.0)
    """
    list_a = generate_random_list(size)
    list_b = list_a.copy()

    num_changes = int(size * change_ratio)

    # Make some replacements
    for _ in range(num_changes // 3):
        idx = random.randint(0, size - 1)
        list_b[idx] = random.randint(0, 1000)

    # Make some insertions
    for _ in range(num_changes // 3):
        idx = random.randint(0, len(list_b))
        list_b.insert(idx, random.randint(0, 1000))

    # Make some deletions
    for _ in range(num_changes // 3):
        if list_b:
            idx = random.randint(0, len(list_b) - 1)
            del list_b[idx]

    return list_a, list_b


def generate_nested_dict(depth: int, breadth: int) -> dict | int:
    """Generate a nested dictionary structure."""
    if depth == 0:
        return random.randint(0, 1000)

    result = {}
    for i in range(breadth):
        key = f"key_{i}"
        if random.random() > 0.3:
            result[key] = generate_nested_dict(depth - 1, breadth)
        else:
            result[key] = random.randint(0, 1000)
    return result


# ========================================
# List Diff Benchmarks
# ========================================


@pytest.mark.benchmark(group="list-diff")
def test_list_diff_small_10pct(benchmark):
    """Benchmark: 50 element list with 10% changes."""
    a, b = generate_similar_lists(50, 0.1)
    benchmark(diff, a, b)


@pytest.mark.benchmark(group="list-diff")
@pytest.mark.parametrize("change_ratio", [0.05, 0.1, 0.5])
def test_list_diff_medium(benchmark, change_ratio):
    """Benchmark: 1000 element list with varying change ratios."""
    a, b = generate_similar_lists(1000, change_ratio)
    benchmark(diff, a, b)


@pytest.mark.benchmark(group="list-diff-edge")
def test_list_diff_completely_different(benchmark):
    """Benchmark: Two completely different 1000 element lists."""
    a = generate_random_list(1000)
    b = generate_random_list(1000)
    benchmark(diff, a, b)


@pytest.mark.benchmark(group="list-diff-edge")
def test_list_diff_identical(benchmark):
    """Benchmark: Two identical 10000 element lists."""
    a = generate_random_list(10000)
    b = a.copy()
    benchmark(diff, a, b)


# ========================================
# Dict Diff Benchmarks
# ========================================


@pytest.mark.benchmark(group="dict-diff")
def test_dict_diff_flat_500_keys(benchmark):
    """Benchmark: Flat dict with 500 keys, 10% changed."""
    a = {f"key_{i}": i for i in range(500)}
    b = a.copy()
    # Change 10%
    for i in range(50):
        b[f"key_{i}"] = i + 500

    benchmark(diff, a, b)


@pytest.mark.benchmark(group="dict-diff")
def test_dict_diff_nested(benchmark):
    """Benchmark: Nested dict with depth=3, breadth=5."""
    a = generate_nested_dict(3, 5)
    b = generate_nested_dict(3, 5)
    benchmark(diff, a, b)


# ========================================
# Set Diff Benchmarks
# ========================================


@pytest.mark.benchmark(group="set-diff")
def test_set_diff_1000_elements(benchmark):
    """Benchmark: Sets with 1000 elements, 10% difference."""
    a = set(generate_random_list(1000, 2000))
    b = a.copy()
    # Remove 5%
    a_list = list(a)
    for i in range(50):
        a.remove(a_list[i])
    # Add 5%
    for i in range(50):
        b.add(2000 + i)

    benchmark(diff, a, b)


# ========================================
# Mixed Structure Benchmarks
# ========================================


@pytest.mark.benchmark(group="mixed")
def test_mixed_dict_with_list_values(benchmark):
    """Benchmark: Dict with 50 keys, each containing a 100-element list."""
    a = {f"key_{i}": generate_random_list(100) for i in range(50)}
    b = {f"key_{i}": generate_random_list(100) for i in range(50)}
    benchmark(diff, a, b)


# ========================================
# Apply Benchmarks
# ========================================


@pytest.mark.benchmark(group="apply")
def test_apply_list_1000_elements(benchmark):
    """Benchmark: Apply patch to 1000 element list with 10% changes."""
    a, b = generate_similar_lists(1000, 0.1)
    ops, _ = diff(a, b)

    benchmark(apply, a, ops)


# ========================================
# Pointer Evaluate Benchmarks
# ========================================


@pytest.mark.benchmark(group="pointer-evaluate")
def test_pointer_evaluate_deep_dict(benchmark):
    """Benchmark: Evaluate pointer on deeply nested structure."""
    depth = 100
    obj = 42
    for i in range(depth - 1, -1, -1):
        obj = {f"key_{i}": obj}
    ptr = Pointer([f"key_{i}" for i in range(depth)])

    benchmark(ptr.evaluate, obj)


@pytest.mark.benchmark(group="pointer-evaluate")
def test_pointer_evaluate_deep_list(benchmark):
    """Benchmark: Evaluate pointer on deep lists."""
    # Build nested lists 100 levels deep; innermost value is 42.
    depth = 100
    nested = 42
    for _ in range(depth):
        nested = [nested]
    obj = nested
    ptr = Pointer([0] * depth)

    benchmark(ptr.evaluate, obj)


# ========================================
# Pointer Append Benchmarks
# ========================================


@pytest.mark.benchmark(group="pointer-append")
def test_pointer_append(benchmark):
    """Benchmark: Append token to pointer."""
    ptr = Pointer.from_str("/a/b/c/d/e/f/g/h/i/j")

    benchmark(ptr.append, "k")


# ========================================
# Produce vs Diff Comparison Benchmarks
# ========================================


# --- Dict Benchmarks ---

DICT_SMALL_BASE = {f"key_{i}": i for i in range(100)}
DICT_LARGE_BASE = {f"key_{i}": i for i in range(1000)}


def dict_small_mutations_recipe(draft):
    """Recipe for small dict mutations."""
    draft["key_10"] = 999
    draft["new_key"] = "new_value"
    del draft["key_50"]


def dict_many_mutations_recipe(draft):
    """Recipe for many dict mutations."""
    # Modify 20% of keys
    for i in range(200):
        draft[f"key_{i}"] = i + 10000
    # Add 10% new keys
    for i in range(100):
        draft[f"new_key_{i}"] = i
    # Remove 10% of keys
    for i in range(100):
        del draft[f"key_{i + 200}"]


@pytest.mark.benchmark(group="produce-vs-diff-dict")
def test_diff_dict_small_mutations(benchmark):
    """Benchmark: diff() on dict with small mutations (baseline)."""

    def run():
        result = copy.deepcopy(DICT_SMALL_BASE)
        dict_small_mutations_recipe(result)
        return diff(DICT_SMALL_BASE, result)

    benchmark(run)


@pytest.mark.parametrize("in_place", [False, True], ids=["copy", "in_place"])
@pytest.mark.benchmark(group="produce-vs-diff-dict")
def test_produce_dict_small_mutations(benchmark, in_place):
    """Benchmark: produce() on dict with small mutations."""

    def run():
        data = copy.deepcopy(DICT_SMALL_BASE)
        return produce(data, dict_small_mutations_recipe, in_place=in_place)

    benchmark(run)


@pytest.mark.benchmark(group="produce-vs-diff-dict")
def test_diff_dict_many_mutations(benchmark):
    """Benchmark: diff() on dict with many mutations (baseline)."""

    def run():
        result = copy.deepcopy(DICT_LARGE_BASE)
        dict_many_mutations_recipe(result)
        return diff(DICT_LARGE_BASE, result)

    benchmark(run)


@pytest.mark.parametrize("in_place", [False, True], ids=["copy", "in_place"])
@pytest.mark.benchmark(group="produce-vs-diff-dict")
def test_produce_dict_many_mutations(benchmark, in_place):
    """Benchmark: produce() on dict with many mutations."""

    def run():
        data = copy.deepcopy(DICT_LARGE_BASE)
        return produce(data, dict_many_mutations_recipe, in_place=in_place)

    benchmark(run)


# --- List Benchmarks ---

LIST_BASE = list(range(100))


def list_small_mutations_recipe(draft):
    """Recipe for small list mutations."""
    draft.append(999)
    draft.insert(10, 888)
    draft[50] = 777
    del draft[20]


def list_many_appends_recipe(draft):
    """Recipe for many list appends."""
    for i in range(100):
        draft.append(i + 1000)


@pytest.mark.benchmark(group="produce-vs-diff-list")
def test_diff_list_small_mutations(benchmark):
    """Benchmark: diff() on list with small mutations (baseline)."""

    def run():
        result = copy.deepcopy(LIST_BASE)
        list_small_mutations_recipe(result)
        return diff(LIST_BASE, result)

    benchmark(run)


@pytest.mark.parametrize("in_place", [False, True], ids=["copy", "in_place"])
@pytest.mark.benchmark(group="produce-vs-diff-list")
def test_produce_list_small_mutations(benchmark, in_place):
    """Benchmark: produce() on list with small mutations."""

    def run():
        data = copy.deepcopy(LIST_BASE)
        return produce(data, list_small_mutations_recipe, in_place=in_place)

    benchmark(run)


@pytest.mark.benchmark(group="produce-vs-diff-list")
def test_diff_list_many_appends(benchmark):
    """Benchmark: diff() on list with many appends (baseline)."""

    def run():
        result = copy.deepcopy(LIST_BASE)
        list_many_appends_recipe(result)
        return diff(LIST_BASE, result)

    benchmark(run)


@pytest.mark.parametrize("in_place", [False, True], ids=["copy", "in_place"])
@pytest.mark.benchmark(group="produce-vs-diff-list")
def test_produce_list_many_appends(benchmark, in_place):
    """Benchmark: produce() on list with many appends."""

    def run():
        data = copy.deepcopy(LIST_BASE)
        return produce(data, list_many_appends_recipe, in_place=in_place)

    benchmark(run)


# --- Nested Structure Benchmarks ---

NESTED_BASE = {
    "users": [
        {"name": f"User{i}", "age": 20 + i, "tags": set(range(i, i + 5))}
        for i in range(50)
    ]
}


def nested_structure_recipe(draft):
    """Recipe for nested structure mutations."""
    draft["users"][10]["age"] = 99
    draft["users"][10]["tags"].add(999)
    draft["users"].append({"name": "NewUser", "age": 25, "tags": {1, 2, 3}})
    draft["admin"] = True


@pytest.mark.benchmark(group="produce-vs-diff-nested")
def test_diff_nested_structure(benchmark):
    """Benchmark: diff() on nested dict/list structure (baseline)."""

    def run():
        result = copy.deepcopy(NESTED_BASE)
        nested_structure_recipe(result)
        return diff(NESTED_BASE, result)

    benchmark(run)


@pytest.mark.parametrize("in_place", [False, True], ids=["copy", "in_place"])
@pytest.mark.benchmark(group="produce-vs-diff-nested")
def test_produce_nested_structure(benchmark, in_place):
    """Benchmark: produce() on nested dict/list structure."""

    def run():
        data = copy.deepcopy(NESTED_BASE)
        return produce(data, nested_structure_recipe, in_place=in_place)

    benchmark(run)


# --- Set Benchmarks ---

SET_BASE = set(range(500))


def set_mutations_recipe(draft):
    """Recipe for set mutations."""
    for i in range(50):
        draft.add(i + 1000)
    for i in range(50):
        draft.discard(i)


@pytest.mark.benchmark(group="produce-vs-diff-set")
def test_diff_set_mutations(benchmark):
    """Benchmark: diff() on set with mutations (baseline)."""

    def run():
        result = copy.deepcopy(SET_BASE)
        set_mutations_recipe(result)
        return diff(SET_BASE, result)

    benchmark(run)


@pytest.mark.parametrize("in_place", [False, True], ids=["copy", "in_place"])
@pytest.mark.benchmark(group="produce-vs-diff-set")
def test_produce_set_mutations(benchmark, in_place):
    """Benchmark: produce() on set with mutations."""

    def run():
        data = copy.deepcopy(SET_BASE)
        return produce(data, set_mutations_recipe, in_place=in_place)

    benchmark(run)


# --- Deep Nested Benchmarks ---

DEEP_NESTED_BASE = {
    "level1": {"level2": {"level3": {"level4": {"data": list(range(100))}}}}
}


def deep_nested_recipe(draft):
    """Recipe for deep nested mutation."""
    draft["level1"]["level2"]["level3"]["level4"]["data"].append(999)


@pytest.mark.benchmark(group="produce-vs-diff-deep")
def test_diff_deep_nested_mutation(benchmark):
    """Benchmark: diff() with deep nested mutation (baseline)."""

    def run():
        result = copy.deepcopy(DEEP_NESTED_BASE)
        deep_nested_recipe(result)
        return diff(DEEP_NESTED_BASE, result)

    benchmark(run)


@pytest.mark.parametrize("in_place", [False, True], ids=["copy", "in_place"])
@pytest.mark.benchmark(group="produce-vs-diff-deep")
def test_produce_deep_nested_mutation(benchmark, in_place):
    """Benchmark: produce() with deep nested mutation."""

    def run():
        data = copy.deepcopy(DEEP_NESTED_BASE)
        return produce(data, deep_nested_recipe, in_place=in_place)

    benchmark(run)


# --- Sparse Mutations Benchmarks ---

SPARSE_BASE = {f"key_{i}": list(range(100)) for i in range(100)}


def sparse_mutations_recipe(draft):
    """Recipe for sparse mutations on large object."""
    # Only mutate 3 keys out of 100
    draft["key_10"][0] = 999
    draft["key_50"][50] = 888
    draft["key_90"][90] = 777


@pytest.mark.benchmark(group="produce-vs-diff-sparse")
def test_diff_sparse_mutations_large_object(benchmark):
    """Benchmark: diff() with sparse mutations on large object (baseline)."""

    def run():
        result = copy.deepcopy(SPARSE_BASE)
        sparse_mutations_recipe(result)
        return diff(SPARSE_BASE, result)

    benchmark(run)


@pytest.mark.parametrize("in_place", [False, True], ids=["copy", "in_place"])
@pytest.mark.benchmark(group="produce-vs-diff-sparse")
def test_produce_sparse_mutations_large_object(benchmark, in_place):
    """Benchmark: produce() with sparse mutations on large object."""

    def run():
        data = copy.deepcopy(SPARSE_BASE)
        return produce(data, sparse_mutations_recipe, in_place=in_place)

    benchmark(run)


# ========================================
# Observ + produce(in_place=True) Benchmarks
# ========================================


@pytest.mark.skipif(not OBSERV_AVAILABLE, reason="observ not installed")
@pytest.mark.benchmark(group="observ-diff")
def test_diff_observ_dict_mutations(benchmark):
    """Benchmark: diff() on observ reactive dict (baseline)."""
    base_data = {f"key_{i}": i for i in range(100)}

    def run():
        state = reactive(base_data.copy())
        result = reactive(base_data.copy())
        result["key_10"] = 999
        result["new_key"] = "new_value"
        del result["key_50"]
        return diff(to_raw(state), to_raw(result))

    benchmark(run)


@pytest.mark.skipif(not OBSERV_AVAILABLE, reason="observ not installed")
@pytest.mark.benchmark(group="observ-produce")
def test_produce_observ_dict_mutations_copy(benchmark):
    """Benchmark: produce() on observ reactive dict (copy mode)."""
    base_data = {f"key_{i}": i for i in range(100)}

    def run():
        state = reactive(base_data.copy())

        def recipe(draft):
            draft["key_10"] = 999
            draft["new_key"] = "new_value"
            del draft["key_50"]

        return produce(state, recipe, in_place=False)

    benchmark(run)


@pytest.mark.skipif(not OBSERV_AVAILABLE, reason="observ not installed")
@pytest.mark.benchmark(group="observ-produce")
def test_produce_observ_dict_mutations_in_place(benchmark):
    """Benchmark: produce() on observ reactive dict (in_place=True)."""
    base_data = {f"key_{i}": i for i in range(100)}

    def run():
        state = reactive(base_data.copy())

        def recipe(draft):
            draft["key_10"] = 999
            draft["new_key"] = "new_value"
            del draft["key_50"]

        return produce(state, recipe, in_place=True)

    benchmark(run)


@pytest.mark.skipif(not OBSERV_AVAILABLE, reason="observ not installed")
@pytest.mark.benchmark(group="observ-nested")
def test_diff_observ_nested_structure(benchmark):
    """Benchmark: diff() on nested observ reactive structure (baseline)."""
    base_data = {
        "users": [{"name": f"User{i}", "age": 20 + i} for i in range(50)],
        "settings": {"theme": "light"},
    }

    def run():
        state = reactive(base_data.copy())
        result = reactive(base_data.copy())
        result["users"][10]["age"] = 99
        result["settings"]["theme"] = "dark"
        result["admin"] = True
        return diff(to_raw(state), to_raw(result))

    benchmark(run)


@pytest.mark.skipif(not OBSERV_AVAILABLE, reason="observ not installed")
@pytest.mark.benchmark(group="observ-nested")
def test_produce_observ_nested_in_place(benchmark):
    """Benchmark: produce(in_place=True) on nested observ reactive structure."""
    base_data = {
        "users": [{"name": f"User{i}", "age": 20 + i} for i in range(50)],
        "settings": {"theme": "light"},
    }

    def run():
        state = reactive(base_data.copy())

        def recipe(draft):
            draft["users"][10]["age"] = 99
            draft["settings"]["theme"] = "dark"
            draft["admin"] = True

        return produce(state, recipe, in_place=True)

    benchmark(run)


@pytest.mark.skipif(not OBSERV_AVAILABLE, reason="observ not installed")
@pytest.mark.benchmark(group="observ-list")
def test_produce_observ_list_many_appends_copy(benchmark):
    """Benchmark: produce() on observ reactive list (copy mode)."""

    def run():
        state = reactive(list(range(100)))

        def recipe(draft):
            for i in range(100):
                draft.append(i + 1000)

        return produce(state, recipe, in_place=False)

    benchmark(run)


@pytest.mark.skipif(not OBSERV_AVAILABLE, reason="observ not installed")
@pytest.mark.benchmark(group="observ-list")
def test_produce_observ_list_many_appends_in_place(benchmark):
    """Benchmark: produce(in_place=True) on observ reactive list."""

    def run():
        state = reactive(list(range(100)))

        def recipe(draft):
            for i in range(100):
                draft.append(i + 1000)

        return produce(state, recipe, in_place=True)

    benchmark(run)


@pytest.mark.skipif(not OBSERV_AVAILABLE, reason="observ not installed")
@pytest.mark.benchmark(group="observ-performance")
def test_produce_in_place_vs_copy_dict(benchmark):
    """Benchmark: Compare in_place=True vs in_place=False for dict."""
    base_data = {f"key_{i}": i for i in range(1000)}

    def run():
        state = reactive(base_data.copy())

        def recipe(draft):
            for i in range(100):
                draft[f"key_{i}"] = i + 10000

        return produce(state, recipe, in_place=True)

    benchmark(run)


@pytest.mark.skipif(not OBSERV_AVAILABLE, reason="observ not installed")
@pytest.mark.benchmark(group="observ-performance")
def test_produce_copy_mode_dict(benchmark):
    """Benchmark: produce() with in_place=False for comparison."""
    base_data = {f"key_{i}": i for i in range(1000)}

    def run():
        state = reactive(base_data.copy())

        def recipe(draft):
            for i in range(100):
                draft[f"key_{i}"] = i + 10000

        return produce(state, recipe, in_place=False)

    benchmark(run)
