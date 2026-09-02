import ast
import decimal
from datetime import datetime, time
from enum import Enum
from typing import Any

# Handle bitarray optionally, as it is a third-party library
try:
    from bitarray import bitarray
except ImportError:
    class bitarray:  # type: ignore
        """Dummy class to prevent isinstance errors if bitarray is not installed."""
        pass


def str_to_bool(val: str | None, default: bool | None = None) -> bool:
    """
    Convert a string representation of truth to a boolean.
    Returns the default value if val is None.
    Raises ValueError if the value is not recognized, or if val is None and default is None.
    """
    if val is None:
        if default is not None:
            ret = default
            return ret
        raise ValueError("Cannot convert None to boolean without a default value.")

    val = val.strip().lower()

    if val in ('true', 't', 'yes', 'y', 'on', '1'):
        ret = True
        return ret
    if val in ('false', 'f', 'no', 'n', 'off', '0'):
        ret = False
        return ret

    raise ValueError(f"Cannot convert {val!r} to boolean.")


def _is_iterable(value: Any) -> bool:
    """Check if a value is iterable, safely excluding primitive strings and bytes."""
    if value is None or isinstance(value, (str, bytes)):
        return False

    try:
        iter(value)
        return True
    except TypeError:
        return False


def _is_mapping(value: Any) -> bool:
    """
    Check if a value behaves like a mapping (e.g., dictionary) safely.
    """
    if value is None or isinstance(value, (str, bytes)):
        return False

    items_attr = getattr(value, 'items', None)
    ret =  callable(items_attr)
    return ret


def _traverse_and_convert(obj: Any, is_raise_on_failure: bool, *enum_classes: type[Enum] | None) -> Any:
    """
    Traverses iterables and applies conversions in a single pass using an iterative DFS.

    Eliminates recursion to prevent RecursionError on deeply nested structures
    and strictly avoids the overhead of Python stack frame allocation per node.
    """

    # 1. DUMMY ROOT TRICK
    # A 1-element list acts as the root parent. This avoids edge cases
    # for the top-level object and unifies the assignment logic below.
    result_container: list[Any] = [None]

    # 2. STACK INITIALIZATION
    # Stack format: (parent_collection, key_or_index, current_object)
    # parent is typed as list | dict since we only attach to these types.
    stack: list[tuple[list | dict, Any, Any]] = [(result_container, 0, obj)]

    while stack:
        parent, key, current = stack.pop()

        if _is_mapping(current):
            # --- MAPPINGS (Dicts) ---
            new_dict = {}
            # Eagerly attach the empty dict to the parent
            parent[key] = new_dict
            reversed_items = None

            # FAST PATH: C-level pointer comparison for exact dicts (95% of cases).
            # Bypasses the try/except overhead.
            if type(current) is dict:
                # Python 3.8+ supports reversed() directly on dict views.
                reversed_items = reversed(current.items())
            else:
                # SAFE PATH: For subclasses and custom Mappings lacking __reversed__.
                try:
                    reversed_items = reversed(current.items())
                except TypeError:
                    reversed_items = reversed(list(current.items()))

            for k, v in reversed_items:
                stack.append((new_dict, k, v))

        elif _is_iterable(current):
            # --- ITERABLES (Lists, Tuples, Sets, Generators, etc.) ---
            # Avoid shallow copying if 'current' is already a sequence (list or tuple).
            # Cast to list only if it's a generator, set, or other unknown iterable.
            if isinstance(current, (list, tuple)):
                items = current
            else:
                items = list(current)

            items_len = 0 if not items else len(items)

            # Pre-allocate the list. This avoids dynamic array resizing overhead
            # (amortized O(1) becomes strict O(1) per assignment).
            new_list = [None] * items_len
            parent[key] = new_list

            # Push in reverse order so the left-most elements are popped first.
            # Using range backwards is extremely fast and avoids tuple allocations.
            for i in range(items_len - 1, -1, -1):
                stack.append((new_list, i, items[i]))
        else:
            # --- SCALARS (Leaf nodes) ---
            # Delegate to convert_scalar and attach the result directly to the parent
            parent[key] = convert_scalar(current, is_raise_on_failure, *enum_classes)

    # The dummy root's 0-th element now contains the fully reconstructed, converted tree
    return result_container[0]

def convert_scalar(value: Any, is_raise_on_failure: bool = True, *enum_classes: type[Enum] | None) -> Any:
    """
    Attempt to convert a scalar string value to a specific type:
    Python literal, None, boolean, datetime, or Enum.
    Also handles special formatting for time, decimal, bytes, and bitarray (moved up to prevent dead code).
    """
    if value is None:
        return value

    # 1. Handle special formatting types BEFORE the string check to avoid unreachable dead code
    if isinstance(value, time):
        ret = value.strftime("%H:%M:%S")
        return ret

    if isinstance(value, decimal.Decimal):
        ret = str(value)
        return ret

    if isinstance(value, bytes):
        ret = value.decode('utf8').replace("'", '"')
        return ret

    if isinstance(value, bitarray):
        ret = value.to01()  # type: ignore
        return ret

    # Guard: If value is not a string after evaluating special types, return it as is
    if not isinstance(value, str):
        return value

    eval_error = None

    # 2. Attempt to parse as a basic Python literal (e.g., int, float, list, dict)
    try:
        parsed = ast.literal_eval(value)

        # If the evaluated literal is a collection, recursively process its nested elements
        if _is_iterable(parsed):
            ret = _traverse_and_convert(parsed, is_raise_on_failure, *enum_classes)
            return ret

        # If it parsed into a basic type (like int, float, or cleanly quoted string), return it
        ret = parsed
        return ret
    except (SyntaxError, ValueError) as e:
        # Evaluation failed, meaning it's likely a custom scalar format (e.g., datetime, unquoted bool).
        # We capture 'e' to chain it later if all subsequent conversion attempts fail.
        eval_error = e

    clean_val = value.strip()
    lower_val = clean_val.casefold()

    # 3. Check for explicit 'none'
    if lower_val == 'none':
        return None

    # 4. Check for boolean string representations
    try:
        ret = str_to_bool(clean_val)
        return ret
    except ValueError:
        pass

    # 5. Check for datetime formats
    try:
        ret = datetime.fromisoformat(clean_val)
        return ret
    except ValueError:
        pass

    try:
        ret = datetime.strptime(clean_val, "%Y-%m-%d %H:%M:%S")
        return ret
    except ValueError:
        pass

    # 6. Check for Enum membership (Note: First matching Enum takes precedence)
    if enum_classes:
        for enum_class in enum_classes:
            if enum_class is not None:
                try:
                    ret = enum_class(clean_val)
                    return ret
                except ValueError:
                    pass

    # 7. Failure handling with exception chaining
    if is_raise_on_failure:
        raise ValueError(
            f"convert_scalar() was unable to resolve {value!r} of type {type(value).__name__}"
        ) from eval_error

    return value


def parse_str(element: Any, is_raise_on_failure: bool = False, *enum_classes: type[Enum] | None) -> Any:
    """
    Parse a string containing nested structures or scalar values.
    """

    if not isinstance(element, str):
        return element

    # _traverse_and_convert immediately delegates string types to convert_scalar,
    # which inherently attempts ast.literal_eval and processes all fallback conversions.
    ret = _traverse_and_convert(element, is_raise_on_failure, *enum_classes)
    return ret
