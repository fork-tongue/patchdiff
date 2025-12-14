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

import random

import pytest

from patchdiff import apply, diff
from patchdiff.pointer import Pointer

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
# Pointer Benchmarks
# ========================================


@pytest.mark.benchmark(group="pointer")
def test_pointer_evaluate_deeply_nested(benchmark):
    """Benchmark: Evaluate pointer on deeply nested structure."""
    obj = {"key_0": {"key_1": {"key_2": {"key_3": {"key_4": 42}}}}}
    ptr = Pointer.from_str("/key_0/key_1/key_2/key_3/key_4")

    benchmark(ptr.evaluate, obj)


@pytest.mark.benchmark(group="pointer")
def test_pointer_evaluate_large_list(benchmark):
    """Benchmark: Evaluate pointer on large list."""
    obj = [i for i in range(10000)]
    ptr = Pointer([5000])

    benchmark(ptr.evaluate, obj)


@pytest.mark.benchmark(group="pointer")
def test_pointer_append(benchmark):
    """Benchmark: Append token to pointer."""
    ptr = Pointer.from_str("/a/b/c/d/e/f/g/h/i/j")

    benchmark(ptr.append, "k")
