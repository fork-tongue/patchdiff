"""Example demonstrating produce() integration with observ reactive objects."""

try:
    from observ import reactive, watch
except ImportError:
    print("This example requires the 'observ' library.")
    print("Install it with: pip install observ")
    exit(1)

from patchdiff import apply, produce

print("=" * 60)
print("Example 1: Using produce() with observ reactive objects")
print("=" * 60)

# Create a reactive state
state = reactive({"count": 0, "user": {"name": "Alice"}})

# Watch for changes (optional - just to demonstrate observ still works)
changes = []


def on_change(old, new):
    changes.append((old, new))


watcher = watch(lambda: state["count"], on_change)


# Use produce to generate patches from mutations
def increment_recipe(draft):
    draft["count"] += 1
    draft["user"]["name"] = "Bob"


result, patches, reverse = produce(state, increment_recipe)

print(f"\nOriginal state: {state}")
print(f"Result: {result}")
print("\nPatches generated:")
for patch in patches:
    print(f"  {patch}")

print("\n" + "=" * 60)
print("Example 2: Applying patches to non-reactive objects")
print("=" * 60)

# The patches can be applied to regular non-reactive objects
plain_state = {"count": 0, "user": {"name": "Alice"}}
applied = apply(plain_state, patches)

print(f"\nPlain state before: {plain_state}")
print(f"After applying patches: {applied}")
print(f"Matches result: {applied == result}")

print("\n" + "=" * 60)
print("Example 3: Reverse patches work too")
print("=" * 60)

reverted = apply(result, reverse)
print(f"\nResult: {result}")
print(f"After applying reverse patches: {reverted}")
print(f"Matches original: {reverted == dict(state)}")

print("\n" + "=" * 60)
print("Example 4: Complex nested mutations")
print("=" * 60)

# More complex state with nested structures
app_state = reactive(
    {
        "users": [
            {"id": 1, "name": "Alice", "active": True},
            {"id": 2, "name": "Bob", "active": False},
        ],
        "settings": {"theme": "light", "notifications": True},
    }
)


def complex_recipe(draft):
    # Modify existing user
    draft["users"][0]["active"] = False
    # Add new user
    draft["users"].append({"id": 3, "name": "Charlie", "active": True})
    # Update settings
    draft["settings"]["theme"] = "dark"
    draft["settings"]["language"] = "en"


result, patches, reverse = produce(app_state, complex_recipe)

print("\nOriginal app state:")
print(f"  Users: {app_state['users']}")
print(f"  Settings: {app_state['settings']}")

print("\nResult after mutations:")
print(f"  Users: {result['users']}")
print(f"  Settings: {result['settings']}")

print(f"\nGenerated {len(patches)} patches:")
for i, patch in enumerate(patches, 1):
    print(f"  {i}. {patch}")

print("\n" + "=" * 60)
print("Summary")
print("=" * 60)
print("""
The produce() function seamlessly integrates with observ reactive objects:

1. ✓ Accepts observ reactive objects as input
2. ✓ Unwraps them to access underlying data
3. ✓ Generates accurate patches from mutations
4. ✓ Doesn't affect the original reactive object
5. ✓ Patches can be applied to both reactive and non-reactive objects
6. ✓ Reverse patches work correctly

This allows you to:
- Track changes in reactive state with patch generation
- Apply state changes to non-reactive objects
- Implement undo/redo functionality
- Sync state across systems using patches
""")
