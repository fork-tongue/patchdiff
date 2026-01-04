"""Traps for proxy-based patch generation.

This module defines trap factories that intercept method calls on proxy objects
to generate patches. Inspired by observ's trap system.
"""

from typing import Any, Callable


def reader_trap(method_name: str) -> Callable:
    """Create a trap for non-mutating read operations.

    These methods don't modify the object and don't need patch recording.
    They just pass through to the underlying data.
    """
    def trap(self, *args, **kwargs):
        method = getattr(self._data, method_name)
        return method(*args, **kwargs)

    trap.__name__ = method_name
    trap.__qualname__ = f"Proxy.{method_name}"
    return trap


def wrapping_reader_trap(method_name: str) -> Callable:
    """Create a trap for read operations that need to wrap the result.

    Used for methods like __getitem__ where nested structures need to be wrapped.
    """
    def trap(self, key, *args, **kwargs):
        method = getattr(self._data, method_name)
        value = method(key, *args, **kwargs)
        # For dict/list proxies that have _wrap
        if hasattr(self, '_wrap'):
            return self._wrap(key, value)
        return value

    trap.__name__ = method_name
    trap.__qualname__ = f"Proxy.{method_name}"
    return trap


def writer_trap(method_name: str, patch_generator: Callable) -> Callable:
    """Create a trap for mutating write operations.

    Args:
        method_name: Name of the method to trap
        patch_generator: Function that generates patches for this operation
    """
    def trap(self, *args, **kwargs):
        # Call the patch generator before executing the method
        result = patch_generator(self, method_name, *args, **kwargs)
        return result

    trap.__name__ = method_name
    trap.__qualname__ = f"Proxy.{method_name}"
    return trap


# Method categories for DictProxy
DICT_READERS = [
    '__len__',
    '__contains__',
    '__repr__',
    'keys',
    'values',
    'items',
]

DICT_KEYREADERS = [
    'get',
]

DICT_ITERATORS = [
    '__iter__',
]

DICT_WRITERS = [
    # These are handled specially in DictProxy
]

DICT_KEYWRITERS = [
    # __setitem__ and __delitem__ are implemented directly
]


# Method categories for ListProxy
LIST_READERS = [
    '__len__',
    '__contains__',
    '__repr__',
    'index',
    'count',
]

LIST_ITERATORS = [
    '__iter__',
]

LIST_WRITERS = [
    # append, insert, etc. are implemented directly
]


# Method categories for SetProxy
SET_READERS = [
    '__len__',
    '__contains__',
    '__repr__',
    'union',
    'intersection',
    'difference',
    'symmetric_difference',
]

SET_ITERATORS = [
    '__iter__',
]

SET_WRITERS = [
    # add, remove, etc. are implemented directly
]


def construct_reader_methods(proxy_class, reader_methods):
    """Construct simple reader methods for a proxy class.

    Args:
        proxy_class: The proxy class to add methods to
        reader_methods: List of method names to create reader traps for
    """
    for method_name in reader_methods:
        setattr(proxy_class, method_name, reader_trap(method_name))
