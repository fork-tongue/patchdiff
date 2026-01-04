"""Traps for proxy-based patch generation.

This module defines a simple trap system for proxy methods to avoid code duplication.
Inspired by observ's trap system.
"""

from typing import Callable, List


def reader_trap(method_name: str) -> Callable:
    """Create a trap for non-mutating read operations.

    These methods don't modify the object and just pass through to the underlying data.
    """
    def trap(self, *args, **kwargs):
        method = getattr(self._data, method_name)
        return method(*args, **kwargs)

    trap.__name__ = method_name
    trap.__qualname__ = f"Proxy.{method_name}"
    return trap


def add_reader_methods(proxy_class, method_names: List[str]):
    """Add simple reader methods to a proxy class.

    Args:
        proxy_class: The proxy class to add methods to
        method_names: List of method names to create reader traps for
    """
    for method_name in method_names:
        setattr(proxy_class, method_name, reader_trap(method_name))

