from collections.abc import Iterable
import importlib
from typing import Optional, Any
import pytest
from logitest.config import ASSERTION_MAPPING


def assert_equal(result: Any, expected: Any, visited: Optional[dict] = None) -> Optional[bool]:
    """Check if any two objects are equal

    Args:
        result (Any): any python object coming as the result
        expected (Any): any python object that is expected to come
        visited (Optional[dict], optional): dictionary with ID of the object as the key, and the object itself as the value. Defaults to None.

    Returns:
        Optional[bool]: Returns True, if the given two objects are equal while testing
    """
    if visited is None:
        visited = {}

    # Ensure both result and expected are of the same type
    assert type(result) == type(
        expected), f"Types do not match: {type(result)} != {type(expected)}"

    # Check if the data type is in the ASSERTION_MAPPING dictionary
    result_type = type(result).__name__
    if result_type in ASSERTION_MAPPING:
        module_name, test_func_name = ASSERTION_MAPPING[result_type]

        # Dynamically import the module using importlib
        module = importlib.import_module(module_name)

        # Dynamically get the test function and call it
        test_func = getattr(module, test_func_name)
        # Use the testing function from the library
        test_func(result, expected)
        return True

    # Primitive type comparison (int, str, bool, etc.)
    if isinstance(result, (int, float, bool, str, bytes, complex, type(None))):
        assert result == expected, f"Values do not match: {result} != {expected}"
        return True

    # Handle iterables (list, tuple, set, frozenset, etc.)
    elif isinstance(result, Iterable) and not isinstance(result, (dict, str)):
        assert len(result) == len(
            expected), f"Length mismatch: {len(result)} != {len(expected)}"

        for r, e in zip(result, expected):
            assert_equal(r, e, visited)
        return True

    # Handle dictionaries
    elif isinstance(result, dict):
        assert set(result.keys()) == set(
            expected.keys()), f"Keys do not match: {result.keys()} != {expected.keys()}"

        for key in result:
            # Ensure the values for this key are comparable before proceeding
            if not is_comparable(result[key], expected[key]):
                raise ValueError(
                    f"Values for key {key} are not comparable: {result[key]} != {expected[key]}")
            assert_equal(result[key], expected[key], visited)
        return True

    # Handle sets and frozensets
    elif isinstance(result, (set, frozenset)):
        assert len(result) == len(
            expected), f"Set/Frozenset length mismatch: {len(result)} != {len(expected)}"

        for r, e in zip(result, expected):
            assert_equal(r, e, visited)
        return True

    # Handle custom objects (including NamedTuples)
    elif hasattr(result, '_fields'):  # NamedTuple
        assert isinstance(expected, type(
            result)), f"Types do not match: {type(result)} != {type(expected)}"

        for field in result._fields:
            assert_equal(getattr(result, field),
                         getattr(expected, field), visited)
        return True

    elif hasattr(result, "__dict__"):  # For custom objects with __dict__
        assert isinstance(expected, type(
            result)), f"Types do not match: {type(result)} != {type(expected)}"

        # Check for circular references to prevent infinite recursion
        if id(result) in visited and visited[id(result)] == visited.get(id(expected)):
            return True

        visited[id(result)] = expected

        # Compare attributes (including properties) by inspecting the object
        for attr in dir(result):
            if not attr.startswith('__'):
                assert_equal(getattr(result, attr),
                             getattr(expected, attr), visited)
        return True

    # Handle cases for objects with __eq__
    elif hasattr(result, "__eq__"):
        assert result == expected, f"Objects do not match: {result} != {expected}"
        return True

    # If none of the above, raise an error
    else:
        raise ValueError(f"Unsupported type for comparison: {type(result)}")


def is_comparable(val1: Any, val2: Any) -> bool:
    """A helper function to check if two values are comparable.
    It handles special cases where direct comparison might not be possible.

    Args:
        val1 (Any): any python object
        val2 (Any): any python object

    Returns:
        bool: True, if both the objects are equal else False
    """
    try:
        # Check if the types are comparable directly
        val1 == val2
        return True
    except TypeError:
        # If comparison raises an error, return False
        return False
