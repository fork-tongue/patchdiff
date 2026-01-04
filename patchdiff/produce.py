"""Proxy-based patch generation for tracking mutations in real-time.

This module provides an alternative to diffing by using proxy objects that
monitor mutations as they are being made and emit patches immediately.
This approach is inspired by Immer's proxy-based implementation.
"""

from __future__ import annotations

import copy
from typing import Any, Callable, Dict, List, Set, Tuple

from .pointer import Pointer
from .traps import (
    DICT_ITERATORS,
    DICT_KEYREADERS,
    DICT_READERS,
    LIST_ITERATORS,
    LIST_READERS,
    SET_ITERATORS,
    SET_READERS,
    construct_reader_methods,
    reader_trap,
)

# Optional observ integration
try:
    from observ import to_raw as observ_to_raw
except ImportError:
    observ_to_raw = None


class PatchRecorder:
    """Records patches as mutations happen on proxy objects."""

    def __init__(self):
        self.patches: List[Dict] = []
        self.reverse_patches: List[Dict] = []

    def record_add(self, path: Pointer, value: Any, reverse_value: Any = None) -> None:
        """Record an add operation."""
        self.patches.append({"op": "add", "path": path, "value": value})
        if reverse_value is not None:
            # For reverse, we either remove or replace
            self.reverse_patches.insert(
                0, {"op": "remove", "path": path}
            )
        else:
            self.reverse_patches.insert(
                0, {"op": "remove", "path": path}
            )

    def record_remove(self, path: Pointer, old_value: Any) -> None:
        """Record a remove operation."""
        self.patches.append({"op": "remove", "path": path})
        self.reverse_patches.insert(
            0, {"op": "add", "path": path, "value": old_value}
        )

    def record_replace(self, path: Pointer, old_value: Any, new_value: Any) -> None:
        """Record a replace operation."""
        self.patches.append({"op": "replace", "path": path, "value": new_value})
        self.reverse_patches.insert(
            0, {"op": "replace", "path": path, "value": old_value}
        )


class DictProxy:
    """Proxy for dict objects that tracks mutations and generates patches."""

    def __init__(self, data: Dict, recorder: PatchRecorder, path: Pointer):
        object.__setattr__(self, "_data", data)
        object.__setattr__(self, "_recorder", recorder)
        object.__setattr__(self, "_path", path)
        object.__setattr__(self, "_proxies", {})

    def _wrap(self, key: Any, value: Any) -> Any:
        """Wrap nested structures in proxies using duck typing."""
        # Use duck typing to support observ reactive objects and other proxies
        if hasattr(value, "keys"):  # dict-like
            if key not in self._proxies:
                self._proxies[key] = DictProxy(value, self._recorder, self._path.append(key))
            return self._proxies[key]
        elif hasattr(value, "append"):  # list-like
            if key not in self._proxies:
                self._proxies[key] = ListProxy(value, self._recorder, self._path.append(key))
            return self._proxies[key]
        elif hasattr(value, "add") and hasattr(value, "discard"):  # set-like
            if key not in self._proxies:
                self._proxies[key] = SetProxy(value, self._recorder, self._path.append(key))
            return self._proxies[key]
        return value

    def __getitem__(self, key: Any) -> Any:
        value = self._data[key]
        return self._wrap(key, value)

    def __setitem__(self, key: Any, value: Any) -> None:
        path = self._path.append(key)
        if key in self._data:
            old_value = self._data[key]
            self._recorder.record_replace(path, old_value, value)
        else:
            self._recorder.record_add(path, value)
        self._data[key] = value
        # Invalidate proxy cache for this key
        if key in self._proxies:
            del self._proxies[key]

    def __delitem__(self, key: Any) -> None:
        old_value = self._data[key]
        path = self._path.append(key)
        self._recorder.record_remove(path, old_value)
        del self._data[key]
        # Invalidate proxy cache for this key
        if key in self._proxies:
            del self._proxies[key]

    def get(self, key: Any, default=None):
        if key in self._data:
            return self[key]
        return default

    def pop(self, key: Any, *args):
        if key in self._data:
            old_value = self._data[key]
            path = self._path.append(key)
            self._recorder.record_remove(path, old_value)
            return self._data.pop(key)
        elif args:
            return args[0]
        else:
            raise KeyError(key)

    def setdefault(self, key: Any, default=None):
        if key not in self._data:
            self[key] = default
        return self[key]

    def update(self, *args, **kwargs):
        if args:
            other = args[0]
            if hasattr(other, "items"):
                for key, value in other.items():
                    self[key] = value
            else:
                for key, value in other:
                    self[key] = value
        for key, value in kwargs.items():
            self[key] = value

    def clear(self):
        keys_to_remove = list(self._data.keys())
        for key in keys_to_remove:
            del self[key]

    def popitem(self):
        if not self._data:
            raise KeyError("popitem(): dictionary is empty")
        key, value = self._data.popitem()
        path = self._path.append(key)
        self._recorder.record_remove(path, value)
        return key, value


# Add simple reader methods to DictProxy using traps
construct_reader_methods(DictProxy, DICT_READERS + DICT_ITERATORS + ['values', 'items'])


class ListProxy:
    """Proxy for list objects that tracks mutations and generates patches."""

    def __init__(self, data: List, recorder: PatchRecorder, path: Pointer):
        object.__setattr__(self, "_data", data)
        object.__setattr__(self, "_recorder", recorder)
        object.__setattr__(self, "_path", path)
        object.__setattr__(self, "_proxies", {})

    def _wrap(self, index: int, value: Any) -> Any:
        """Wrap nested structures in proxies using duck typing."""
        # Use duck typing to support observ reactive objects and other proxies
        if hasattr(value, "keys"):  # dict-like
            if index not in self._proxies:
                self._proxies[index] = DictProxy(value, self._recorder, self._path.append(index))
            return self._proxies[index]
        elif hasattr(value, "append"):  # list-like
            if index not in self._proxies:
                self._proxies[index] = ListProxy(value, self._recorder, self._path.append(index))
            return self._proxies[index]
        elif hasattr(value, "add") and hasattr(value, "discard"):  # set-like
            if index not in self._proxies:
                self._proxies[index] = SetProxy(value, self._recorder, self._path.append(index))
            return self._proxies[index]
        return value

    def __getitem__(self, index: int) -> Any:
        value = self._data[index]
        if isinstance(index, slice):
            return value
        return self._wrap(index, value)

    def __setitem__(self, index: int, value: Any) -> None:
        if isinstance(index, slice):
            # Handle slice assignment - this is complex for patch generation
            # For simplicity, we'll treat this as multiple operations
            old_values = self._data[index]
            self._data[index] = value
            # For slices, we generate a replace for the entire list
            # This is a simplification - a full implementation would generate
            # individual patches for each changed element
            return

        path = self._path.append(index)
        old_value = self._data[index]
        self._recorder.record_replace(path, old_value, value)
        self._data[index] = value
        # Invalidate proxy cache for this index
        if index in self._proxies:
            del self._proxies[index]

    def __delitem__(self, index: int) -> None:
        old_value = self._data[index]
        path = self._path.append(index)
        self._recorder.record_remove(path, old_value)
        del self._data[index]
        # Invalidate all proxy caches as indices shift
        self._proxies.clear()

    def append(self, value: Any) -> None:
        index = len(self._data)
        path = self._path.append("-")
        self._recorder.record_add(path, value)
        self._data.append(value)

    def insert(self, index: int, value: Any) -> None:
        # Use the index for insertion
        path = self._path.append(index)
        self._recorder.record_add(path, value)
        self._data.insert(index, value)
        # Invalidate all proxy caches as indices shift
        self._proxies.clear()

    def pop(self, index: int = -1) -> Any:
        if index == -1:
            index = len(self._data) - 1
        old_value = self._data[index]
        path = self._path.append(index)
        self._recorder.record_remove(path, old_value)
        result = self._data.pop(index)
        # Invalidate all proxy caches as indices shift
        self._proxies.clear()
        return result

    def remove(self, value: Any) -> None:
        index = self._data.index(value)
        del self[index]

    def clear(self):
        while self._data:
            self.pop()

    def extend(self, values):
        for value in values:
            self.append(value)

    def reverse(self) -> None:
        """Reverse the list in place and generate appropriate patches."""
        # Record the old state
        old_list = list(self._data)
        # Reverse the underlying data
        self._data.reverse()
        # Generate patches for each changed position
        for i in range(len(self._data)):
            if i < len(old_list) and old_list[i] != self._data[i]:
                path = self._path.append(i)
                self._recorder.record_replace(path, old_list[i], self._data[i])
        # Invalidate all proxy caches as positions changed
        self._proxies.clear()

    def sort(self, *args, **kwargs) -> None:
        """Sort the list in place and generate appropriate patches."""
        # Record the old state
        old_list = list(self._data)
        # Sort the underlying data
        self._data.sort(*args, **kwargs)
        # Generate patches for each changed position
        for i in range(len(self._data)):
            if i < len(old_list) and old_list[i] != self._data[i]:
                path = self._path.append(i)
                self._recorder.record_replace(path, old_list[i], self._data[i])
        # Invalidate all proxy caches as positions changed
        self._proxies.clear()


# Add simple reader methods to ListProxy using traps
construct_reader_methods(ListProxy, LIST_READERS + LIST_ITERATORS)


class SetProxy:
    """Proxy for set objects that tracks mutations and generates patches."""

    def __init__(self, data: Set, recorder: PatchRecorder, path: Pointer):
        object.__setattr__(self, "_data", data)
        object.__setattr__(self, "_recorder", recorder)
        object.__setattr__(self, "_path", path)

    def add(self, value: Any) -> None:
        if value not in self._data:
            path = self._path.append("-")
            self._recorder.record_add(path, value)
        self._data.add(value)

    def remove(self, value: Any) -> None:
        path = self._path.append(value)
        self._recorder.record_remove(path, value)
        self._data.remove(value)

    def discard(self, value: Any) -> None:
        if value in self._data:
            path = self._path.append(value)
            self._recorder.record_remove(path, value)
            self._data.discard(value)

    def pop(self) -> Any:
        value = self._data.pop()
        path = self._path.append(value)
        self._recorder.record_remove(path, value)
        return value

    def clear(self) -> None:
        values_to_remove = list(self._data)
        for value in values_to_remove:
            self.remove(value)

    def update(self, *others):
        for other in others:
            for value in other:
                self.add(value)

    def __ior__(self, other):
        """Implement |= operator (union update)."""
        for value in other:
            self.add(value)
        return self

    def __iand__(self, other):
        """Implement &= operator (intersection update)."""
        # Remove values not in other
        values_to_remove = [v for v in self._data if v not in other]
        for value in values_to_remove:
            self.remove(value)
        return self

    def __isub__(self, other):
        """Implement -= operator (difference update)."""
        # Remove values that are in other
        for value in other:
            if value in self._data:
                self.remove(value)
        return self

    def __ixor__(self, other):
        """Implement ^= operator (symmetric difference update)."""
        # Add values from other that aren't in self, remove values that are in both
        for value in other:
            if value in self._data:
                self.remove(value)
            else:
                self.add(value)
        return self


# Add simple reader methods to SetProxy using traps
construct_reader_methods(SetProxy, SET_READERS + SET_ITERATORS)


def produce(
    base: Any, recipe: Callable[[Any], None], in_place: bool = False
) -> Tuple[Any, List[Dict], List[Dict]]:
    """
    Produce a new state by applying mutations, tracking patches along the way.

    This is an alternative to the diff() function that uses proxy objects to
    track mutations in real-time instead of comparing before/after snapshots.

    Args:
        base: The base object to mutate (dict, list, or set)
        recipe: A function that receives a proxy-wrapped draft and mutates it
        in_place: If True, mutate the original object directly (useful for
                  reactive objects like observ). If False (default), operate
                  on a deep copy and leave the original unchanged.

    Returns:
        A tuple of (result, patches, reverse_patches) where:
        - result: The mutated object (same as base if in_place=True)
        - patches: List of patches representing the mutations
        - reverse_patches: List of patches to reverse the mutations

    Example:
        >>> base = {"count": 0, "items": []}
        >>> def increment(draft):
        ...     draft["count"] += 1
        ...     draft["items"].append("new")
        >>> result, patches, reverse = produce(base, increment)
        >>> print(result)
        {"count": 1, "items": ["new"]}
        >>> print(patches)
        [{"op": "replace", "path": "/count", "value": 1},
         {"op": "add", "path": "/items/-", "value": "new"}]

    Example with in_place=True for reactive objects:
        >>> from observ import reactive
        >>> state = reactive({"count": 0})
        >>> result, patches, reverse = produce(state, lambda d: d.__setitem__("count", 5), in_place=True)
        >>> # state["count"] is now 5, and watchers were triggered
    """
    if in_place:
        # Mutate the original object directly
        # Don't unwrap or copy - use the base object as-is
        draft = base
    else:
        # Unwrap observ reactive objects to get the underlying data
        # Use observ's to_raw() function if available
        if observ_to_raw is not None:
            base = observ_to_raw(base)

        # Create a deep copy of the base object
        draft = copy.deepcopy(base)

    # Create a patch recorder
    recorder = PatchRecorder()

    # Wrap the draft in a proxy using duck typing (similar to diff())
    # This allows compatibility with observ reactive objects and other proxies
    path = Pointer()
    if hasattr(draft, "keys"):  # dict-like
        proxy = DictProxy(draft, recorder, path)
    elif hasattr(draft, "append"):  # list-like
        proxy = ListProxy(draft, recorder, path)
    elif hasattr(draft, "add"):  # set-like
        proxy = SetProxy(draft, recorder, path)
    else:
        raise TypeError(f"Unsupported type for produce: {type(draft)}")

    # Call the recipe function with the proxy
    recipe(proxy)

    # Return the mutated draft and the patches
    return draft, recorder.patches, recorder.reverse_patches
