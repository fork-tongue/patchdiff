"""Example demonstrating in_place=True for mutating reactive objects directly."""

try:
    from observ import reactive
except ImportError:
    print("This example requires the 'observ' library.")
    print("Install it with: pip install observ")
    exit(1)

from patchdiff import produce

print("=" * 60)
print("Example 1: Default behavior (in_place=False)")
print("=" * 60)

# Default behavior: operate on a copy
state = reactive({"count": 0, "items": [1, 2, 3]})
print(f"\nOriginal state before: {dict(state)}")


def recipe(draft):
    draft["count"] = 10
    draft["items"].append(4)


result, patches, reverse = produce(state, recipe)

print(f"Original state after:  {dict(state)}")
print(f"Result:                {result}")
print(f"Original unchanged:    {state['count'] == 0}")

print("\n" + "=" * 60)
print("Example 2: In-place mutation (in_place=True)")
print("=" * 60)

# In-place: mutate the original reactive object
state = reactive({"count": 0, "items": [1, 2, 3]})
print(f"\nOriginal state before: {dict(state)}")

result, patches, reverse = produce(state, recipe, in_place=True)

print(f"Original state after:  {dict(state)}")
print(f"Result:                {result}")
print(f"Result is same object: {result is state}")
print(f"Original was mutated:  {state['count'] == 10}")

print("\n" + "=" * 60)
print("Example 3: Tracking multiple mutations")
print("=" * 60)

# Use case: track a sequence of mutations
state = reactive({"count": 0, "history": []})

print(f"\nInitial state: {dict(state)}")

all_patches = []

# First mutation
def increment(draft):
    draft["count"] += 1
    draft["history"].append(f"Incremented to {draft['count']}")


result, patches, reverse = produce(state, increment, in_place=True)
all_patches.extend(patches)
print(f"After mutation 1: {dict(state)}")

# Second mutation
def increment_again(draft):
    draft["count"] += 1
    draft["history"].append(f"Incremented to {draft['count']}")


result, patches, reverse = produce(state, increment_again, in_place=True)
all_patches.extend(patches)
print(f"After mutation 2: {dict(state)}")

print(f"\nTotal patches generated: {len(all_patches)}")
print("Patches:")
for i, patch in enumerate(all_patches, 1):
    print(f"  {i}. {patch}")

print("\n" + "=" * 60)
print("Example 4: Complex state updates")
print("=" * 60)

# Complex nested state
state = reactive({
    "user": {"name": "Alice", "preferences": {"theme": "light"}},
    "data": [1, 2, 3],
})

print(f"\nBefore: {dict(state)}")


def complex_update(draft):
    draft["user"]["name"] = "Bob"
    draft["user"]["preferences"]["theme"] = "dark"
    draft["data"].append(4)
    draft["timestamp"] = "2024-01-01"


result, patches, reverse = produce(state, complex_update, in_place=True)

print(f"After:  {dict(state)}")
print(f"\nGenerated {len(patches)} patches:")
for i, patch in enumerate(patches, 1):
    print(f"  {i}. op={patch['op']}, path={patch['path']}, value={patch.get('value', 'N/A')}")

print("\n" + "=" * 60)
print("Summary")
print("=" * 60)
print("""
The in_place=True option enables:

1. ✓ Direct mutation of reactive objects (watchers will trigger)
2. ✓ Patch generation while mutating
3. ✓ Undo/redo functionality for reactive state
4. ✓ Store implementations with history tracking
5. ✓ Zero-copy operations (no deepcopy overhead)

Perfect for:
- State management libraries with observ
- Undo/redo systems
- Time-travel debugging
- Optimistic updates with rollback
""")
