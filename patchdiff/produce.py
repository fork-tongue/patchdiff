"""Proxy-based patch generation for tracking mutations in real-time.

This module provides an alternative to diffing by using proxy objects that
monitor mutations as they are being made and emit patches immediately.
This approach is inspired by Immer's proxy-based implementation.

Proxies track their location through parent links instead of storing an
absolute path. A proxy's path is computed on demand by walking up to the
root, so paths stay correct when list indices shift, and proxies that have
been removed from the draft ("detached") stop recording patches: their data
is captured by the snapshot of whatever write re-inserts it later.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable
from copy import deepcopy
from typing import Any
from weakref import ref

from .pointer import Pointer
from .types import Operation

# Types that are immutable and can never contain a proxy, so they can be
# stored and snapshotted as-is.
_SCALAR_TYPES = frozenset({int, float, complex, bool, str, bytes, type(None)})

# Sentinel to distinguish "no default given" from falsy defaults like None or 0
_MISSING = object()


def _snapshot(value: Any) -> Any:
    """Deep copy a value for storage in a patch, replacing any proxies with
    plain copies of their underlying data.

    Hand-rolled for the common JSON-like types (faster than copy.deepcopy);
    unrecognized types fall back to deepcopy, which also unwraps third-party
    proxies (like observ's) through their __deepcopy__ hooks.
    """
    cls = value.__class__
    if cls in _SCALAR_TYPES:
        return value
    if cls is dict:
        return {key: _snapshot(item) for key, item in value.items()}
    if cls is list:
        return [_snapshot(item) for item in value]
    if cls is DictProxy or cls is ListProxy or cls is SetProxy:
        return _snapshot(value._data)
    if cls is set:
        return {_snapshot(item) for item in value}
    if cls is frozenset:
        return frozenset(_snapshot(item) for item in value)
    if cls is tuple:
        return tuple(_snapshot(item) for item in value)
    return deepcopy(value)


def _unwrap(value: Any) -> Any:
    """Return value with any nested proxies replaced by plain deep copies of
    their data, so that proxies never end up inside the draft.

    Returns the original object untouched when it contains no proxies (the
    common case). Replacing a nested proxy with a copy gives value
    semantics: later mutations through the original path are not shared,
    which keeps the recorded patches consistent.

    Set members must be hashable and proxies are not, so sets can never
    contain proxies and are returned as-is.
    """
    cls = value.__class__
    if cls in _SCALAR_TYPES:
        return value
    if cls is DictProxy or cls is ListProxy or cls is SetProxy:
        return _snapshot(value._data)
    if cls is dict:
        for item in value.values():
            if _unwrap(item) is not item:
                return {key: _unwrap(item) for key, item in value.items()}
        return value
    if cls is list:
        for item in value:
            if _unwrap(item) is not item:
                return [_unwrap(item) for item in value]
        return value
    if cls is tuple:
        for item in value:
            if _unwrap(item) is not item:
                return tuple(_unwrap(item) for item in value)
        return value
    return value


def _add_reader_methods(proxy_class, method_names):
    """Add simple pass-through reader methods to a proxy class.

    These methods don't modify the object and just pass through to _data.
    """

    def _make_reader(name):
        def reader(self, *args, **kwargs):
            method = getattr(self._data, name)
            return method(*args, **kwargs)

        reader.__name__ = name
        reader.__qualname__ = f"{proxy_class.__name__}.{name}"
        return reader

    for method_name in method_names:
        setattr(proxy_class, method_name, _make_reader(method_name))


class PatchRecorder:
    """Records patches as mutations happen on proxy objects.

    Reverse patches must run in the opposite order of the forward patches.
    They are appended here (O(1) instead of O(n) for inserting at the
    front) and reversed once in finalize().

    """

    def __init__(self):
        self.patches: list[Operation] = []
        self.reverse_patches: list[Operation] = []
        # Bumped on every structural change to the proxy tree (detach,
        # re-attach, list index shifts); proxies use it to invalidate
        # their memoized _location() results.
        self.epoch: int = 0

    def finalize(self, root: _Proxy) -> None:
        """Put the reverse patches in reverse application order and
        detach the root proxy.

        Call once, after all mutations have been recorded. Every attached
        proxy computes its path through the root, so detaching the root
        stops all recording: a proxy leaked out of the recipe can no
        longer append to the already-returned patch lists.
        """
        self.reverse_patches.reverse()
        root._detached = True
        self.epoch += 1

    def record_add(
        self, path: Pointer, value: Any, reverse_path: Pointer | None = None
    ) -> None:
        """Record an add operation.

        Args:
            path: The path for the add operation
            value: The value being added
            reverse_path: Optional path for the reverse (remove) operation.
                         If not provided, uses the same path. This is needed
                         for sets where add uses "/-" but remove needs "/value".
        """
        if value.__class__ not in _SCALAR_TYPES:
            value = _snapshot(value)
        self.patches.append({"op": "add", "path": path, "value": value})
        self.reverse_patches.append(
            {"op": "remove", "path": reverse_path if reverse_path else path}
        )

    def record_remove(
        self, path: Pointer, old_value: Any, reverse_path: Pointer | None = None
    ) -> None:
        """Record a remove operation.

        Args:
            path: The path where the item is being removed
            old_value: The value being removed
            reverse_path: Optional path for the reverse (add) operation.
                         If not provided, uses the same path. This is needed
                         for lists where remove uses "/index" but add needs "/-"
                         when removing from the end.
        """
        if old_value.__class__ not in _SCALAR_TYPES:
            old_value = _snapshot(old_value)
        self.patches.append({"op": "remove", "path": path})
        self.reverse_patches.append(
            {
                "op": "add",
                "path": reverse_path if reverse_path else path,
                "value": old_value,
            }
        )

    def record_replace(self, path: Pointer, old_value: Any, new_value: Any) -> None:
        """Record a replace operation, but only if the value actually changed."""
        if old_value == new_value:
            return  # Skip no-op replacements
        if new_value.__class__ not in _SCALAR_TYPES:
            new_value = _snapshot(new_value)
        if old_value.__class__ not in _SCALAR_TYPES:
            old_value = _snapshot(old_value)
        self.patches.append({"op": "replace", "path": path, "value": new_value})
        self.reverse_patches.append({"op": "replace", "path": path, "value": old_value})


class _Proxy:
    """Common base for proxies: location tracking through parent links.

    A proxy knows its parent proxy and its key/index within that parent.
    Its path is computed on demand by walking up to the root, so paths
    remain correct as the tree changes. The `_proxies` cache doubles as a
    registry of handed-out child proxies: structural changes update their
    keys (list shifts, sort, reverse) or mark them detached (removals and
    replacements). Detached proxies still mutate their data but no longer
    record patches.

    The parent link is a weak reference, so proxies never form reference
    cycles and are freed by reference counting (cyclic proxy garbage
    caused gc latency spikes). A dead parent reference means an ancestor
    was detached and dropped, so the proxy behaves as detached.
    """

    __slots__ = (
        "__weakref__",
        "_data",
        "_detached",
        "_key",
        "_loc_epoch",
        "_loc_tokens",
        "_parent",
        "_proxies",
        "_recorder",
    )
    __hash__ = None  # mutable containers are unhashable

    _data: Any
    _detached: bool
    _key: Any
    _loc_epoch: int
    _loc_tokens: tuple | None
    _parent: Any  # weakref.ref[_Proxy] | None
    _proxies: dict[Any, _Proxy] | None
    _recorder: PatchRecorder

    def __init__(
        self,
        data: Any,
        recorder: PatchRecorder,
        parent: _Proxy | None = None,
        key: Hashable = None,
    ):
        self._data = data
        self._recorder = recorder
        self._parent = ref(parent) if parent is not None else None
        self._key = key
        self._detached = False
        # Memoized _location() result, valid while _loc_epoch matches the
        # recorder's epoch (-1 = never computed)
        self._loc_epoch = -1
        self._loc_tokens = None
        # Child-proxy registry, allocated lazily on first wrap: most
        # proxies are leaves that never hand out children
        self._proxies = None

    def __deepcopy__(self, memo):
        # Deep copies of a proxy must yield plain data, never the proxy
        return deepcopy(self._data, memo)

    def _location(self) -> tuple | None:
        """Path tokens of this proxy in the draft, or None when this proxy
        or any of its ancestors has been detached from the draft (a dead
        parent reference counts as detached).

        The result is memoized per proxy and recursively reuses the
        parent's memoized location, so repeated writes into a stable tree
        pay O(1) per write instead of walking to the root every time.
        Every structural change (detach, re-attach, list index shifts)
        bumps the recorder's epoch, which invalidates all memoized
        locations at once.

        Returns a tuple so callers can build a child Pointer in a single
        allocation: Pointer((*tokens, key))."""
        recorder = self._recorder
        if self._loc_epoch == recorder.epoch:
            return self._loc_tokens
        tokens: tuple | None
        if self._detached:
            tokens = None
        else:
            parent_ref = self._parent
            if parent_ref is None:
                tokens = ()
            else:
                node = parent_ref()
                if node is None:
                    tokens = None
                else:
                    parent_tokens = node._location()
                    if parent_tokens is None:
                        tokens = None
                    else:
                        tokens = (*parent_tokens, self._key)
        self._loc_tokens = tokens
        self._loc_epoch = recorder.epoch
        return tokens

    def _wrap(self, key: Hashable, value: Any) -> Any:
        """Wrap nested structures in proxies using duck typing."""
        # Scalars never need wrapping and never have a cached child proxy
        # (cache entries only exist for container values), so skip both
        # the cache lookup and the hasattr chain for them
        if value.__class__ in _SCALAR_TYPES:
            return value
        # Check cache first - it's faster than hasattr() calls
        proxies = self._proxies
        if proxies is not None and key in proxies:
            return proxies[key]

        # Use duck typing to support observ reactive objects and other proxies
        if hasattr(value, "keys"):  # dict-like
            proxy = DictProxy(value, self._recorder, self, key)
        elif hasattr(value, "append"):  # list-like
            proxy = ListProxy(value, self._recorder, self, key)
        elif hasattr(value, "add") and hasattr(value, "discard"):  # set-like
            proxy = SetProxy(value, self._recorder, self, key)
        else:
            return value
        if proxies is None:
            proxies = self._proxies = {}
        proxies[key] = proxy
        return proxy

    def _detach(self, key: Hashable) -> None:
        """Detach the handed-out child proxy for key, if any.

        Only called when self._proxies is non-empty (callers guard).
        """
        proxies = self._proxies
        assert proxies is not None
        proxy = proxies.pop(key, None)
        if proxy is not None:
            proxy._detached = True
            self._recorder.epoch += 1

    def _detach_all(self) -> None:
        if not self._proxies:
            return
        for proxy in self._proxies.values():
            proxy._detached = True
        self._proxies.clear()
        self._recorder.epoch += 1

    def _in_parent_chain(self, proxy: _Proxy) -> bool:
        """True when proxy is self or an ancestor of self."""
        node = self
        while node is not None:
            if node is proxy:
                return True
            parent_ref = node._parent
            node = parent_ref() if parent_ref is not None else None
        return False

    def _adopt(self, key: Hashable, value: Any) -> Any:
        """Prepare value for storing at self._data[key], returning plain data.

        A detached proxy passed directly is re-attached at the new location
        (move semantics): the held reference stays live and later mutations
        through it record at the new path. A proxy that is still attached
        elsewhere is copied (a value can only live in one place), as are
        proxies nested inside plain containers.
        """
        cls = value.__class__
        if cls is DictProxy or cls is ListProxy or cls is SetProxy:
            if (
                value._detached
                # only re-attach plain data; duck-typed data (e.g. observ
                # proxies) is copied to plain data instead
                and value._data.__class__ in (dict, list, set)
                # guard against creating a cycle by adopting an ancestor
                and not self._in_parent_chain(value)
            ):
                value._detached = False
                value._parent = ref(self)
                value._key = key
                self._recorder.epoch += 1
                if self._proxies is None:
                    self._proxies = {}
                self._proxies[key] = value
                return value._data
            return _snapshot(value._data)
        return _unwrap(value)


class DictProxy(_Proxy):
    """Proxy for dict objects that tracks mutations and generates patches."""

    __slots__ = ()

    def __getitem__(self, key: Any) -> Any:
        value = self._data[key]
        if value.__class__ in _SCALAR_TYPES:
            return value
        return self._wrap(key, value)

    def __setitem__(self, key: Any, value: Any) -> None:
        # The current value for this key is being replaced, so a previously
        # handed-out proxy for it no longer lives in the draft
        if self._proxies:
            self._detach(key)
        if value.__class__ not in _SCALAR_TYPES:
            value = self._adopt(key, value)
        data = self._data
        tokens = self._location()
        if tokens is not None:
            path = Pointer((*tokens, key))
            # One lookup instead of a containment check plus a read
            old_value = data.get(key, _MISSING)
            if old_value is not _MISSING:
                self._recorder.record_replace(path, old_value, value)
            else:
                self._recorder.record_add(path, value)
        data[key] = value

    def __delitem__(self, key: Any) -> None:
        old_value = self._data[key]
        tokens = self._location()
        if tokens is not None:
            self._recorder.record_remove(Pointer((*tokens, key)), old_value)
        del self._data[key]
        if self._proxies:
            self._detach(key)

    def get(self, key: Any, default=None):
        if key in self._data:
            return self[key]
        return default

    def pop(self, key: Any, default=_MISSING):
        if key in self._data:
            old_value = self._data[key]
            tokens = self._location()
            if tokens is not None:
                self._recorder.record_remove(Pointer((*tokens, key)), old_value)
            result = self._data.pop(key)
            if self._proxies:
                self._detach(key)
            return result
        if default is _MISSING:
            raise KeyError(key)
        return default

    def setdefault(self, key: Any, default=None):
        if key not in self._data:
            self[key] = default
        # Return through __getitem__ so containers come back proxied and
        # further mutations on the returned value are tracked
        return self[key]

    def update(self, *args, **kwargs):
        # Collect all key-value pairs to update
        items = []
        if args:
            other = args[0]
            if hasattr(other, "items"):
                items.extend(other.items())
            else:
                items.extend(other)
        items.extend(kwargs.items())

        for key, value in items:
            self[key] = value

    def clear(self):
        # Generate patches for all keys and clear data
        tokens = self._location()
        if tokens is not None:
            for key, value in self._data.items():
                self._recorder.record_remove(Pointer((*tokens, key)), value)
        self._data.clear()
        self._detach_all()

    def popitem(self):
        key, value = self._data.popitem()
        tokens = self._location()
        if tokens is not None:
            self._recorder.record_remove(Pointer((*tokens, key)), value)
        if self._proxies:
            self._detach(key)
        return key, value

    def values(self):
        """Return proxied values so nested mutations are tracked."""
        scalar_types = _SCALAR_TYPES
        wrap = self._wrap
        for key, value in self._data.items():
            yield value if value.__class__ in scalar_types else wrap(key, value)

    def items(self):
        """Return (key, proxied_value) pairs so nested mutations are tracked."""
        scalar_types = _SCALAR_TYPES
        wrap = self._wrap
        for key, value in self._data.items():
            yield key, (value if value.__class__ in scalar_types else wrap(key, value))

    def __ior__(self, other):
        """Implement |= operator (merge update)."""
        self.update(other)
        return self


# Add simple reader methods to DictProxy
_add_reader_methods(
    DictProxy,
    [
        "__len__",
        "__contains__",
        "__repr__",
        "__iter__",
        # __reversed__ returns keys (not values), so pass-through is fine
        "__reversed__",
        "keys",
        # values() and items() are implemented as custom methods above
        # to return proxied nested objects
        "copy",
        "__str__",
        "__format__",
        "__eq__",
        "__ne__",
        "__or__",
        "__ror__",
    ],
)
# Skipped dict methods:
# - fromkeys: classmethod, not relevant for proxy instances
# - __class_getitem__: typing support (dict[str, int]), not relevant for instances
# - __lt__, __le__, __gt__, __ge__: dicts don't support ordering comparisons


class ListProxy(_Proxy):
    """Proxy for list objects that tracks mutations and generates patches."""

    __slots__ = ()

    def _shift_cache(self, start: int, delta: int) -> None:
        """Reindex handed-out child proxies at indices >= start by delta,
        after elements shifted in the underlying list."""
        if not self._proxies:
            return
        self._recorder.epoch += 1
        shifted = {}
        for index, proxy in self._proxies.items():
            if index >= start:
                index += delta
                proxy._key = index
            shifted[index] = proxy
        self._proxies = shifted

    def __getitem__(self, index: int | slice) -> Any:
        value = self._data[index]
        if isinstance(index, slice):
            # Wrap each element in the slice so nested mutations are tracked
            data = self._data
            wrap = self._wrap
            start, stop, step = index.indices(len(data))
            return [wrap(i, data[i]) for i in range(start, stop, step)]
        if value.__class__ in _SCALAR_TYPES:
            return value
        # Resolve negative indices to positive for consistent caching and paths
        if index < 0:
            index = len(self._data) + index
        return self._wrap(index, value)

    def __setitem__(self, index: int | slice, value: Any) -> None:
        if isinstance(index, slice):
            # Handle slice assignment with proper patch generation
            start, stop, step = index.indices(len(self._data))
            tokens = self._location()

            if step != 1:
                # Step slices must have same length
                old_values = self._data[index]
                new_values = list(value)
                if len(old_values) != len(new_values):
                    raise ValueError(
                        f"attempt to assign sequence of size {len(new_values)} "
                        f"to extended slice of size {len(old_values)}"
                    )
                # Replace each element in the stepped slice
                for idx, new_val in zip(range(start, stop, step), new_values):
                    if self._proxies:
                        self._detach(idx)
                    if new_val.__class__ not in _SCALAR_TYPES:
                        new_val = self._adopt(idx, new_val)
                    old_val = self._data[idx]
                    if tokens is not None:
                        self._recorder.record_replace(
                            Pointer((*tokens, idx)), old_val, new_val
                        )
                    self._data[idx] = new_val
            else:
                # Contiguous slice - can change length
                old_values = list(self._data[start:stop])
                old_len = len(old_values)
                new_values = list(value)
                new_len = len(new_values)

                # Replaced positions lose their proxies; the tail shifts
                if self._proxies:
                    for i in range(start, stop):
                        self._detach(i)
                    self._shift_cache(stop, new_len - old_len)
                new_values = [
                    item
                    if item.__class__ in _SCALAR_TYPES
                    else self._adopt(start + i, item)
                    for i, item in enumerate(new_values)
                ]

                # Perform the slice assignment
                self._data[start:stop] = new_values

                if tokens is not None:
                    # Replace common elements
                    for i in range(min(old_len, new_len)):
                        if old_values[i] != new_values[i]:
                            self._recorder.record_replace(
                                Pointer((*tokens, start + i)),
                                old_values[i],
                                new_values[i],
                            )

                    # Add new elements if new slice is longer
                    if new_len > old_len:
                        for i in range(old_len, new_len):
                            self._recorder.record_add(
                                Pointer((*tokens, start + i)), new_values[i]
                            )

                    # Remove extra elements if new slice is shorter
                    elif new_len < old_len:
                        # Remove from end to start to maintain correct indices
                        for i in range(old_len - 1, new_len - 1, -1):
                            self._recorder.record_remove(
                                Pointer((*tokens, start + i)), old_values[i]
                            )
            return

        # Resolve negative indices to positive for correct paths
        if index < 0:
            index = len(self._data) + index
        if self._proxies:
            self._detach(index)
        if value.__class__ not in _SCALAR_TYPES:
            value = self._adopt(index, value)
        old_value = self._data[index]
        tokens = self._location()
        if tokens is not None:
            self._recorder.record_replace(Pointer((*tokens, index)), old_value, value)
        self._data[index] = value

    def __delitem__(self, index: int | slice) -> None:
        if isinstance(index, slice):
            # Handle slice deletion with proper patch generation
            start, stop, step = index.indices(len(self._data))
            tokens = self._location()

            if step != 1:
                # For step slices, delete from end to start to maintain indices
                indices = list(range(start, stop, step))
                for idx in reversed(indices):
                    old_value = self._data[idx]
                    if tokens is not None:
                        self._recorder.record_remove(Pointer((*tokens, idx)), old_value)
                    del self._data[idx]
                    if self._proxies:
                        self._detach(idx)
                        self._shift_cache(idx + 1, -1)
            else:
                # Contiguous slice - delete from end to start
                old_values = list(self._data[start:stop])
                if tokens is not None:
                    for i in range(len(old_values) - 1, -1, -1):
                        self._recorder.record_remove(
                            Pointer((*tokens, start + i)), old_values[i]
                        )
                del self._data[start:stop]
                if self._proxies:
                    for i in range(start, stop):
                        self._detach(i)
                    self._shift_cache(stop, start - stop)
            return

        # Resolve negative indices to positive for correct paths
        if index < 0:
            index = len(self._data) + index
        old_value = self._data[index]
        tokens = self._location()
        if tokens is not None:
            self._recorder.record_remove(Pointer((*tokens, index)), old_value)
        del self._data[index]
        if self._proxies:
            self._detach(index)
            self._shift_cache(index + 1, -1)

    def append(self, value: Any) -> None:
        data = self._data
        if value.__class__ not in _SCALAR_TYPES:
            value = self._adopt(len(data), value)
        tokens = self._location()
        if tokens is not None:
            # Forward patch uses "-" (append to end), reverse patch uses
            # the actual index
            self._recorder.record_add(
                Pointer((*tokens, "-")), value, Pointer((*tokens, len(data)))
            )
        data.append(value)

    def insert(self, index: int, value: Any) -> None:
        # Normalize the index the same way list.insert does (clamped), so
        # the recorded path and the cache shift match the actual insertion
        n = len(self._data)
        if index < 0:
            index = max(0, n + index)
        else:
            index = min(index, n)
        if self._proxies:
            self._shift_cache(index, 1)
        if value.__class__ not in _SCALAR_TYPES:
            value = self._adopt(index, value)
        tokens = self._location()
        if tokens is not None:
            self._recorder.record_add(Pointer((*tokens, index)), value)
        self._data.insert(index, value)

    def pop(self, index: int = -1) -> Any:
        if index < 0:
            index = len(self._data) + index
        old_value = self._data[index]
        tokens = self._location()
        if tokens is not None:
            path = Pointer((*tokens, index))
            # If popping from the end, the reverse (add) operation should use
            # "-" to append rather than a specific index, since the index may
            # not exist when reversing
            is_last = index == len(self._data) - 1
            reverse_path = Pointer((*tokens, "-")) if is_last else None
            self._recorder.record_remove(path, old_value, reverse_path)
        result = self._data.pop(index)
        if self._proxies:
            self._detach(index)
            self._shift_cache(index + 1, -1)
        return result

    def remove(self, value: Any) -> None:
        index = self._data.index(value)
        del self[index]

    def clear(self) -> None:
        # Generate patches for all elements (from end to start for correct
        # indices). All reverse patches use "-" to append, since we're
        # restoring to an empty list
        tokens = self._location()
        if tokens is not None:
            reverse_path = Pointer((*tokens, "-"))
            for i in range(len(self._data) - 1, -1, -1):
                self._recorder.record_remove(
                    Pointer((*tokens, i)), self._data[i], reverse_path
                )
        self._data.clear()
        self._detach_all()

    def extend(self, values):
        # Generate patches and extend data
        start_index = len(self._data)
        values_list = [
            value
            if value.__class__ in _SCALAR_TYPES
            else self._adopt(start_index + i, value)
            for i, value in enumerate(values)
        ]
        tokens = self._location()
        if tokens is not None:
            forward_path = Pointer((*tokens, "-"))
            for i, value in enumerate(values_list):
                reverse_path = Pointer((*tokens, start_index + i))
                self._recorder.record_add(forward_path, value, reverse_path)
        self._data.extend(values_list)

    def reverse(self) -> None:
        """Reverse the list in place and generate appropriate patches."""
        n = len(self._data)
        # Reverse the underlying data
        self._data.reverse()
        # Reindex handed-out child proxies to their new positions
        if self._proxies:
            self._recorder.epoch += 1
            remapped = {}
            for index, proxy in self._proxies.items():
                new_index = n - 1 - index
                proxy._key = new_index
                remapped[new_index] = proxy
            self._proxies = remapped
        # Generate patches for each changed position
        # After reverse, element at position i came from position n-1-i
        tokens = self._location()
        if tokens is not None:
            for i in range(n):
                old_value = self._data[n - 1 - i]
                new_value = self._data[i]
                if old_value != new_value:
                    self._recorder.record_replace(
                        Pointer((*tokens, i)), old_value, new_value
                    )

    def sort(self, *args, **kwargs) -> None:
        """Sort the list in place and generate appropriate patches."""
        # Record the old state
        old_list = list(self._data)
        # Sort the underlying data
        self._data.sort(*args, **kwargs)
        # Reindex handed-out child proxies by following their element's
        # identity to its new position
        if self._proxies:
            self._recorder.epoch += 1
            positions = {}
            for i, item in enumerate(self._data):
                positions.setdefault(id(item), []).append(i)
            remapped = {}
            for _index, proxy in sorted(self._proxies.items()):
                new_index = positions[id(proxy._data)].pop(0)
                proxy._key = new_index
                remapped[new_index] = proxy
            self._proxies = remapped
        # Generate patches for each changed position
        tokens = self._location()
        if tokens is not None:
            for i in range(len(self._data)):
                if old_list[i] != self._data[i]:
                    self._recorder.record_replace(
                        Pointer((*tokens, i)), old_list[i], self._data[i]
                    )

    def __iter__(self):
        """Iterate over list elements, wrapping nested structures in proxies."""
        scalar_types = _SCALAR_TYPES
        wrap = self._wrap
        for i, value in enumerate(self._data):
            yield value if value.__class__ in scalar_types else wrap(i, value)

    def __reversed__(self):
        """Iterate in reverse, wrapping nested structures in proxies."""
        scalar_types = _SCALAR_TYPES
        wrap = self._wrap
        data = self._data
        for i in range(len(data) - 1, -1, -1):
            value = data[i]
            yield value if value.__class__ in scalar_types else wrap(i, value)

    def __iadd__(self, other):
        """Implement += operator (in-place extend)."""
        self.extend(other)
        return self

    def __imul__(self, n):
        """Implement *= operator (in-place repeat)."""
        if n <= 0:
            self.clear()
        elif n > 1:
            original = list(self._data)
            for _ in range(n - 1):
                self.extend(original)
        return self


# Add simple reader methods to ListProxy
_add_reader_methods(
    ListProxy,
    [
        "__len__",
        "__contains__",
        "__repr__",
        # __iter__ and __reversed__ are implemented as custom methods above
        # to return proxied nested objects
        "index",
        "count",
        "copy",
        "__str__",
        "__format__",
        "__eq__",
        "__ne__",
        "__lt__",
        "__le__",
        "__gt__",
        "__ge__",
        "__add__",
        "__mul__",
        "__rmul__",
    ],
)
# Skipped list methods:
# - __class_getitem__: typing support (list[int]), not relevant for instances


class SetProxy(_Proxy):
    """Proxy for set objects that tracks mutations and generates patches.

    Set members must be hashable, so they are never proxied and never
    contain proxies; the registry of child proxies stays unused.
    """

    __slots__ = ()

    def add(self, value: Any) -> None:
        if value not in self._data:
            tokens = self._location()
            if tokens is not None:
                path = Pointer((*tokens, "-"))
                reverse_path = Pointer((*tokens, value))
                self._recorder.record_add(path, value, reverse_path)
        self._data.add(value)

    def remove(self, value: Any) -> None:
        tokens = self._location()
        if tokens is not None:
            self._recorder.record_remove(Pointer((*tokens, value)), value)
        self._data.remove(value)

    def discard(self, value: Any) -> None:
        if value in self._data:
            tokens = self._location()
            if tokens is not None:
                self._recorder.record_remove(Pointer((*tokens, value)), value)
            self._data.discard(value)

    def pop(self) -> Any:
        value = self._data.pop()
        tokens = self._location()
        if tokens is not None:
            self._recorder.record_remove(Pointer((*tokens, value)), value)
        return value

    def clear(self) -> None:
        # Generate patches for all values and clear data
        tokens = self._location()
        if tokens is not None:
            for value in self._data:
                self._recorder.record_remove(Pointer((*tokens, value)), value)
        self._data.clear()

    def update(self, *others):
        # Generate patches and update data
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

    def difference_update(self, *others):
        """Remove all elements found in others."""
        for other in others:
            for value in other:
                if value in self._data:
                    self.remove(value)

    def intersection_update(self, *others):
        """Keep only elements found in all others."""
        # Compute the intersection first, then remove what's not in it
        keep = self._data.copy()
        for other in others:
            keep &= set(other)
        values_to_remove = [v for v in self._data if v not in keep]
        for value in values_to_remove:
            self.remove(value)

    def symmetric_difference_update(self, other):
        """Update with symmetric difference."""
        for value in other:
            if value in self._data:
                self.remove(value)
            else:
                self.add(value)


# Add simple reader methods to SetProxy
_add_reader_methods(
    SetProxy,
    [
        "__len__",
        "__contains__",
        "__repr__",
        "__iter__",
        "union",
        "intersection",
        "difference",
        "symmetric_difference",
        "isdisjoint",
        "issubset",
        "issuperset",
        "copy",
        "__str__",
        "__format__",
        "__eq__",
        "__ne__",
        "__le__",
        "__lt__",
        "__ge__",
        "__gt__",
        "__or__",
        "__ror__",
        "__and__",
        "__rand__",
        "__sub__",
        "__rsub__",
        "__xor__",
        "__rxor__",
    ],
)
# Skipped set methods:
# - __class_getitem__: typing support (set[int]), not relevant for instances


def produce(
    base: Any, recipe: Callable[[Any], None], in_place: bool = False
) -> tuple[Any, list[Operation], list[Operation]]:
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
        # Create a deep copy of the base object. _snapshot copies the
        # common JSON-like types directly (faster than copy.deepcopy);
        # unknown types (e.g. observ proxies) fall back to deepcopy.
        # Note: unlike deepcopy, _snapshot does not preserve shared
        # references within the base; aliased subtrees become independent
        # copies in the draft (which is what patches can express anyway).
        draft = _snapshot(base)

    # Create a patch recorder
    recorder = PatchRecorder()

    # Wrap the draft in a proxy using duck typing (similar to diff())
    # This allows compatibility with observ reactive objects and other proxies
    if hasattr(draft, "keys"):  # dict-like
        proxy = DictProxy(draft, recorder)
    elif hasattr(draft, "append"):  # list-like
        proxy = ListProxy(draft, recorder)
    elif hasattr(draft, "add"):  # set-like
        proxy = SetProxy(draft, recorder)
    else:
        raise TypeError(f"Unsupported type for produce: {type(draft)}")

    # Call the recipe function with the proxy
    recipe(proxy)

    # Put the reverse patches in reverse application order and release
    # all proxies (breaks their reference cycles)
    recorder.finalize(proxy)

    # Return the mutated draft and the patches
    return draft, recorder.patches, recorder.reverse_patches
