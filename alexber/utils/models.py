import json
import logging
from typing import Any, Type, List, Iterable, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class Auto:
    """
    A callable counter class that generates sequential integers starting from a
	configurable initial value.

    This class is designed to be used with Python's `Enum` to automatically assign
    sequential integer values to enum members. Each call to an instance of `Auto`
    increments the counter and returns the next integer in the sequence.

    Attributes:
        current (int): The current value of the counter. This is updated on each call.

    """

    def __init__(self, start: int = 0):
        """
        Initializes the Auto counter with a starting value.

        Args:
            start (int): The initial value to start counting from. Defaults to 0.
                        The counter will return this value on the first call.
        """
        self.current = start - 1  # Initialize to one less than the start value

    def __call__(self) -> int:
        """
        Increments the counter and returns the next integer in the sequence.

        Returns:
            int: The next value in the sequence.

        """

        self.current += 1
        return self.current  # return ++self.current


def create_auto(start: int = 0) -> Auto:
    """
    Factory function to create a new Auto instance.

    Args:
        start (int): The initial value to start counting from. Defaults to 0.

    Returns:
        Auto: A new instance of the Auto class.
    """
    return Auto(start)

def enum_field_validator(field, enum_class: Type[Enum]):
    """
    Returns a validator function to convert a field to a list of enums.

    This validator ensures that each item in the input list is converted to the
	appropriate enum instance.

    Args:
        field: The field being validated.
        enum_class (Type[Enum]): The enum class to which the values will be converted.

    Returns:
        A validator function that converts a list of values to enums.


    """

    def _validator(v: Any) -> List[Enum]:
        if isinstance(v, list):
            # Convert each item in the list to the appropriate enum
            return [convert_value_to_enum(item, enum_class) for item in v]
        else:
            raise ValueError(
                f"Invalid '{field.field_name}' format: {v}. "
                f"It should be a list of {enum_class.__name__} values."
            )

    return _validator


def convert_value_to_enum(value: Any, enum_class: Type[Enum]) -> Enum:
    """
    Converts a value (int, str, or Enum) to the appropriate enum instance.

    This function supports conversion from:
    - An existing enum instance (returns it directly).
    - An integer (maps to the corresponding enum value).
    - A string (matches enum names or string representations of enum values).

    Args:
        value (Any): The value to convert. Can be an integer, string, or enum instance.
        enum_class (Type[Enum]): The enum class to convert the value to.

    Returns:
        Enum: The enum instance corresponding to the provided value.

    Raises:
        ValueError: If the value cannot be converted to the enum.

    """
    if isinstance(value, enum_class):
        # If the value is already an instance of the enum, return it directly
        return value

    if isinstance(value, int):
        try:
            # If the value is an integer, attempt to convert it to the corresponding enum
            return enum_class(value)
        except ValueError:
            raise ValueError(f"Invalid value {value} for enum {enum_class.__name__}")

    if isinstance(value, str):
        # If the value is a string, try converting it to an integer and then use _value2member_map_

        # try to match the string against the enum values
        # for member in enum_class:
        #    if str(member.value) == value:
        #        return member

        try:
            # Attempt to find the enum instance by using the integer version of the string
            return enum_class._value2member_map_[int(value)]
        except (ValueError, KeyError):
            # If the string is not a valid integer, try to match it against enum names
            for member in enum_class:
                if str(member.name) == value:
                    return member

    raise ValueError(f"Cannot convert {value} to enum {enum_class.__name__}")


def parse_json(json_d: Any, field_name: str) -> List[Any]:
    """
    Parses a JSON string or list into a Python list.

    This function is designed to handle cases where a field can be provided as either
    a JSON string or a list. If the input is a JSON string, it is parsed into a list.
    If the input is already a list, it is returned directly.

    Args:
        json_d (Any): The input to parse. Can be a JSON string or a list.
        field_name (str): The name of the field being parsed (used for error messages).

    Returns:
        List[Any]: The parsed list.

    Raises:
        ValueError: If the input is invalid (e.g., not a JSON string or list).

    Examples:
        >>> parse_json('[1, 2, 3]', 'examples')
        [1, 2, 3]

        >>> parse_json([1, 2, 3], 'examples')
        [1, 2, 3]
    """
    if json_d is None:
        raise ValueError(f"Missing {field_name} field.")

    if isinstance(json_d, str):
        try:
            d = json.loads(json_d)
            if not isinstance(d, list):
                raise ValueError(f"Parsed {field_name} is not a list.")
            return d
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON format for '{field_name}': {json_d}")

    if isinstance(json_d, list):
        return json_d

    raise ValueError(
        f"'{field_name}' must be a list or a JSON string representing a list, got {type(json_d).__name__}"
    )


def validate_same_length(*args: Iterable, field_names: Optional[str] = None) -> None:
    """
    Validates that all provided iterables have the same length.

    Args:
        *args (Iterable): The iterables to validate.
        field_names (Optional[str]): The names of the fields being validated (used for error messages).

    Raises:
        ValueError: If the iterables have different lengths.

    """
    if not field_names:
        raise ValueError('Please specify field_names')

    # Special case: return if all arguments are empty
    if all(not arg for arg in args):
        return

    # Get the length of the first iterable to compare with others
    try:
        first_length = len(args[0])
    except IndexError:
        # If no iterables are provided, return
        return

    # Check if all other iterables have the same length as the first one
    b = not all(len(arg) == first_length for arg in args)
    if b:
        raise ValueError(f'The length of {field_names} must be the same')


def check_not_empty(v, field):
    """
    Checks if a given value is not empty and raises a ValueError if it is.

    This function is typically used to validate that a required field in a data structure
    is not empty. If the value is empty, a ValueError is raised with a message indicating
    the field name.

    Args:
        v: The value to check for emptiness.
        field: An object that contains a `field_name` attribute, which is used in the error message.

    Returns:
        The original value `v` if it is not empty.

    Raises:
        ValueError: If the value `v` is empty.
    """
    if not v:
        raise ValueError(f"{field.field_name} must not be empty")
    return v



