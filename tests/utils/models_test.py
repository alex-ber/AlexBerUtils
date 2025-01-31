import logging
import pytest


logger = logging.getLogger(__name__)

import pytest
from alexber.utils.models import Auto, create_auto, check_not_empty, parse_json, validate_same_length

def test_auto_initial_value():
    # Test that the initial value is set correctly
    auto = Auto(5)
    assert auto() == 5, "Initial value should be 5"

def test_auto_sequential_increment():
    # Test that the counter increments sequentially
    auto = Auto(10)
    assert auto() == 10, "First call should return 10"
    assert auto() == 11, "Second call should return 11"
    assert auto() == 12, "Third call should return 12"

def test_auto_default_start():
    # Test that the default start value is 0
    auto = Auto()
    assert auto() == 0, "Default start value should be 0"
    assert auto() == 1, "Next value should be 1"

def test_auto_multiple_instances():
    # Test that multiple instances maintain separate counters
    auto1 = Auto(0)
    auto2 = Auto(100)
    assert auto1() == 0, "First instance should start at 0"
    assert auto2() == 100, "Second instance should start at 100"
    assert auto1() == 1, "First instance should increment to 1"
    assert auto2() == 101, "Second instance should increment to 101"


def test_create_auto_default_start():
    # Test that create_auto returns an Auto instance starting at 0 by default
    auto = create_auto()
    assert isinstance(auto, Auto), "create_auto should return an instance of Auto"
    assert auto() == 0, "Default start value should be 0"
    assert auto() == 1, "Next value should be 1"

def test_create_auto_custom_start():
    # Test that create_auto returns an Auto instance starting at a custom value
    auto = create_auto(5)
    assert isinstance(auto, Auto), "create_auto should return an instance of Auto"
    assert auto() == 5, "Initial value should be 5"
    assert auto() == 6, "Next value should be 6"

def test_create_auto_independent_instances():
    # Test that create_auto creates independent instances
    auto1 = create_auto(0)
    auto2 = create_auto(100)
    assert auto1() == 0, "First instance should start at 0"
    assert auto2() == 100, "Second instance should start at 100"
    assert auto1() == 1, "First instance should increment to 1"
    assert auto2() == 101, "Second instance should increment to 101"

class MockField:
    def __init__(self, field_name):
        self.field_name = field_name

def test_check_not_empty_with_non_empty_value():
    # Test that a non-empty value is returned as is
    value = "non-empty"
    field = MockField("TestField")
    assert check_not_empty(value, field) == value, "The function should return the non-empty value"

def test_check_not_empty_with_empty_value():
    # Test that a ValueError is raised for an empty value
    value = ""
    field = MockField("TestField")
    with pytest.raises(ValueError) as excinfo:
        check_not_empty(value, field)
    assert str(excinfo.value) == "TestField must not be empty", "The function should raise a ValueError with the correct message"

def test_check_not_empty_with_none_value():
    # Test that a ValueError is raised for a None value
    value = None
    field = MockField("TestField")
    with pytest.raises(ValueError) as excinfo:
        check_not_empty(value, field)
    assert str(excinfo.value) == "TestField must not be empty", "The function should raise a ValueError with the correct message"

def test_parse_json_with_valid_json_string():
    # Test with a valid JSON string representing a list
    json_str = '["item1", "item2"]'
    field_name = "TestField"
    result = parse_json(json_str, field_name)
    assert result == ["item1", "item2"], "The function should return the parsed list"

def test_parse_json_with_invalid_json_string():
    # Test with an invalid JSON string
    json_str = '{"item1": "value1"}'
    field_name = "TestField"
    with pytest.raises(ValueError) as excinfo:
        parse_json(json_str, field_name)
    assert str(excinfo.value) == f"Parsed {field_name} is not a list.", "The function should raise a ValueError for non-list JSON"

def test_parse_json_with_none():
    # Test with None as input
    field_name = "TestField"
    with pytest.raises(ValueError) as excinfo:
        parse_json(None, field_name)
    assert str(excinfo.value) == f"Missing {field_name} field.", "The function should raise a ValueError for None input"

def test_parse_json_with_non_json_string():
    # Test with a non-JSON string
    json_str = "not a json"
    field_name = "TestField"
    with pytest.raises(ValueError) as excinfo:
        parse_json(json_str, field_name)
    assert str(excinfo.value) == f"Invalid JSON format for '{field_name}': {json_str}", "The function should raise a ValueError for invalid JSON format"

def test_parse_json_with_list():
    # Test with a list as input
    input_list = ["item1", "item2"]
    field_name = "TestField"
    result = parse_json(input_list, field_name)
    assert result == input_list, "The function should return the list as is when a list is provided"

def test_validate_same_length_with_equal_lengths():
    # Test with iterables of equal length
    iter1 = [1, 2, 3]
    iter2 = (4, 5, 6)
    field_names = ["iter1", "iter2"]
    try:
        validate_same_length(iter1, iter2, field_names=field_names)
    except ValueError:
        pytest.fail("validate_same_length raised ValueError unexpectedly!")

def test_validate_same_length_with_unequal_lengths():
    # Test with iterables of unequal length
    iter1 = [1, 2, 3]
    iter2 = (4, 5)
    field_names = ["iter1", "iter2"]
    with pytest.raises(ValueError) as excinfo:
        validate_same_length(iter1, iter2, field_names=field_names)
    assert str(excinfo.value) == f'The length of {field_names} must be the same', "The function should raise a ValueError for unequal lengths"

def test_validate_same_length_with_empty_args():
    # Test with no iterables passed
    field_names = []
    with pytest.raises(ValueError) as excinfo:
        validate_same_length(field_names=field_names)
    assert str(excinfo.value) == 'Please specify field_names', "The function should raise a ValueError if no iterables are passed"

def test_validate_same_length_with_empty_iterables():
    # Test with all empty iterables
    iter1 = []
    iter2 = ()
    field_names = ["iter1", "iter2"]
    try:
        validate_same_length(iter1, iter2, field_names=field_names)
    except ValueError:
        pytest.fail("validate_same_length raised ValueError unexpectedly!")

def test_validate_same_length_without_field_names():
    # Test without providing field_names
    iter1 = [1, 2, 3]
    iter2 = [4, 5, 6]
    with pytest.raises(ValueError) as excinfo:
        validate_same_length(iter1, iter2)
    assert str(excinfo.value) == 'Please specify field_names', "The function should raise a ValueError if field_names is not provided"


if __name__ == "__main__":
    pytest.main([__file__])
