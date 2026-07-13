# Applying Patches

Patchdiff can apply a list of operations to an object in two ways:

* [`apply`][patchdiff.apply.apply] first makes a deepcopy, patches that, and returns it. The input is left untouched.
* [`iapply`][patchdiff.apply.iapply] patches the object in-place and returns the same object. This is faster (no copy) and is what you want for objects that must keep their identity, such as observ reactive proxies.

```python
from patchdiff import apply, diff, iapply

input = {"a": [5, 7, 9], "b": 6}
output = {"a": [5, 2, 9], "b": 6, "c": 7}

ops, reverse_ops = diff(input, output)

patched = apply(input, ops)
assert patched == output
assert input == {"a": [5, 7, 9], "b": 6}  # unchanged

result = iapply(input, ops)
assert result is input  # same object, mutated
assert input == output
```

## Order matters

Operations are applied sequentially, and paths refer to the state of the object at that point in the sequence, just like in RFC 6902. List indices in particular shift as adds and removes are applied. Both lists that [`diff`][patchdiff.diff.diff] returns are already ordered accordingly, so apply them as-is. Don't reorder or cherry-pick individual operations.

## Undo and redo

Since every diff comes with its reverse, undo/redo is just a pair of stacks of patch lists:

```python
from patchdiff import diff, iapply

state = {"count": 0}
undo_stack = []
redo_stack = []

def update(new_state):
    ops, reverse_ops = diff(state, new_state)
    iapply(state, ops)
    undo_stack.append((ops, reverse_ops))
    redo_stack.clear()

def undo():
    ops, reverse_ops = undo_stack.pop()
    iapply(state, reverse_ops)
    redo_stack.append((ops, reverse_ops))

def redo():
    ops, reverse_ops = redo_stack.pop()
    iapply(state, ops)
    undo_stack.append((ops, reverse_ops))

update({"count": 1})
update({"count": 2})
undo()
assert state == {"count": 1}
redo()
assert state == {"count": 2}
```

## Patch values are copied on write

When a patch is applied, its `"value"` is deepcopied before being written into the target. The patched object and the patch list never share mutable state, so you can keep patches around (on an undo stack for example) and freely mutate the object afterwards:

```python
from patchdiff import diff, iapply

ops, _ = diff({}, {"items": [1, 2]})

state = iapply({}, ops)
state["items"].append(3)

assert ops[0]["value"] == [1, 2]  # the patch is not affected
```
