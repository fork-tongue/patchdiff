"""Example demonstrating proxy-based patch generation using produce()."""

from patchdiff import produce, apply

# Example 1: Simple dict mutations
print("Example 1: Dict mutations")
base = {"count": 0, "name": "Alice"}


def recipe(draft):
    draft["count"] = 5
    draft["active"] = True
    draft["name"] = "Bob"


result, patches, reverse = produce(base, recipe)

print(f"Original: {base}")
print(f"Result: {result}")
print(f"Patches: {patches}")
print()

# Example 2: List mutations
print("Example 2: List mutations")
base = [1, 2, 3]


def recipe(draft):
    draft.append(4)
    draft.insert(0, 0)
    draft[2] = 999


result, patches, reverse = produce(base, recipe)

print(f"Original: {base}")
print(f"Result: {result}")
print(f"Patches: {patches}")
print()

# Example 3: Nested structures
print("Example 3: Nested structures")
base = {"user": {"name": "Alice", "age": 30, "tags": {"python", "javascript"}}}


def recipe(draft):
    draft["user"]["age"] = 31
    draft["user"]["tags"].add("rust")
    draft["user"]["city"] = "NYC"


result, patches, reverse = produce(base, recipe)

print(f"Original: {base}")
print(f"Result: {result}")
print(f"Patches: {patches}")
print()

# Example 4: Patches can be applied
print("Example 4: Applying patches")
base = {"x": 1}


def recipe(draft):
    draft["x"] = 10
    draft["y"] = 20


result, patches, reverse = produce(base, recipe)

# Apply the patches to the original base
applied = apply(base, patches)
print(f"Original: {base}")
print(f"After applying patches: {applied}")
print(f"Matches result: {applied == result}")
print()

# Example 5: Reverse patches
print("Example 5: Reverse patches")
base = {"a": 1, "b": 2}


def recipe(draft):
    draft["a"] = 100
    draft["c"] = 3
    del draft["b"]


result, patches, reverse = produce(base, recipe)

# Apply reverse patches to revert changes
reverted = apply(result, reverse)
print(f"Original: {base}")
print(f"Result: {result}")
print(f"After reverting: {reverted}")
print(f"Matches original: {reverted == base}")
