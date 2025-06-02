"""Test the utility functions."""

import datetime
from unittest.mock import patch

import pytest

from gedcom7 import types, util


def test_get_child_with_tag():
    """Test getting a child structure by tag."""
    # Create parent structure with children
    parent = types.GedcomStructure(tag="PARENT", pointer="", text="", xref="")
    child1 = types.GedcomStructure(tag="CHILD1", pointer="", text="Child 1", xref="")
    child2 = types.GedcomStructure(tag="CHILD2", pointer="", text="Child 2", xref="")
    child3 = types.GedcomStructure(
        tag="CHILD1", pointer="", text="Child 3", xref=""
    )  # Duplicate tag

    parent.children = [child1, child2, child3]

    # Test finding the first child with tag CHILD1
    result = util.get_first_child_with_tag(parent, "CHILD1")
    assert result == child1
    assert result.text == "Child 1"

    # Test finding child with tag CHILD2
    result = util.get_first_child_with_tag(parent, "CHILD2")
    assert result == child2
    assert result.text == "Child 2"


def test_no_matching_child():
    """Test when no child matches the given tag."""
    parent = types.GedcomStructure(tag="PARENT", pointer="", text="", xref="")
    child = types.GedcomStructure(tag="CHILD", pointer="", text="Child", xref="")

    parent.children = [child]

    # Test with a tag that doesn't exist
    result = util.get_first_child_with_tag(parent, "NONEXISTENT")
    assert result is None


def test_empty_children_list():
    """Test with an empty children list."""
    parent = types.GedcomStructure(tag="PARENT", pointer="", text="", xref="")
    parent.children = []

    result = util.get_first_child_with_tag(parent, "CHILD")
    assert result is None


def test_valid_date_conversion():
    """Test converting a valid GEDCOM DateExact to Python date."""
    # Test with all months
    months = [
        ("JAN", 1),
        ("FEB", 2),
        ("MAR", 3),
        ("APR", 4),
        ("MAY", 5),
        ("JUN", 6),
        ("JUL", 7),
        ("AUG", 8),
        ("SEP", 9),
        ("OCT", 10),
        ("NOV", 11),
        ("DEC", 12),
    ]

    for month_str, month_num in months:
        gedcom_date = types.DateExact(day=15, month=month_str, year=2023)
        python_date = util.date_exact_to_python_date(gedcom_date)

        assert isinstance(python_date, datetime.date)
        assert python_date.day == 15
        assert python_date.month == month_num
        assert python_date.year == 2023


def test_case_insensitive_month():
    """Test that month names are case-insensitive."""
    # Test with lowercase
    gedcom_date = types.DateExact(day=15, month="jan", year=2023)
    python_date = util.date_exact_to_python_date(gedcom_date)

    assert python_date.month == 1

    # Test with mixed case
    gedcom_date = types.DateExact(day=15, month="Jul", year=2023)
    python_date = util.date_exact_to_python_date(gedcom_date)

    assert python_date.month == 7


def test_invalid_month():
    """Test with an invalid month name."""
    gedcom_date = types.DateExact(day=15, month="INVALID", year=2023)

    with pytest.raises(ValueError, match="Invalid month in date: INVALID"):
        util.date_exact_to_python_date(gedcom_date)


def test_basic_time_conversion():
    """Test basic time conversion with hours and minutes only."""
    gedcom_time = types.Time(hour=14, minute=30)
    python_time = util.time_to_python_time(gedcom_time)

    assert isinstance(python_time, datetime.time)
    assert python_time.hour == 14
    assert python_time.minute == 30
    assert python_time.second == 0
    assert python_time.microsecond == 0
    assert python_time.tzinfo == datetime.timezone.utc


def test_time_with_seconds():
    """Test time conversion with seconds."""
    gedcom_time = types.Time(hour=14, minute=30, second=45)
    python_time = util.time_to_python_time(gedcom_time)

    assert python_time.second == 45


def test_time_with_fraction():
    """Test time conversion with fractional seconds."""
    gedcom_time = types.Time(hour=14, minute=30, second=45, fraction=123456)
    python_time = util.time_to_python_time(gedcom_time)

    assert python_time.second == 45
    assert python_time.microsecond == 123456

    # Test with different fraction lengths
    gedcom_time = types.Time(hour=14, minute=30, second=45, fraction=5)
    python_time = util.time_to_python_time(gedcom_time)

    assert python_time.second == 45
    assert python_time.microsecond == 500000


def test_time_without_fraction_or_seconds():
    """Test time conversion without fraction or seconds."""
    gedcom_time = types.Time(hour=14, minute=30, second=None, fraction=None)
    python_time = util.time_to_python_time(gedcom_time)

    assert python_time.second == 0
    assert python_time.microsecond == 0


def test_date_only():
    """Test conversion with date only (no time)."""
    gedcom_date = types.DateExact(day=15, month="JAN", year=2023)
    python_datetime = util.date_exact_and_time_to_python_datetime(gedcom_date)

    assert isinstance(python_datetime, datetime.datetime)
    assert python_datetime.day == 15
    assert python_datetime.month == 1
    assert python_datetime.year == 2023
    assert python_datetime.hour == 0
    assert python_datetime.minute == 0
    assert python_datetime.second == 0
    assert python_datetime.microsecond == 0
    assert python_datetime.tzinfo == datetime.timezone.utc


def test_date_and_time():
    """Test conversion with both date and time."""
    gedcom_date = types.DateExact(day=15, month="JAN", year=2023)
    gedcom_time = types.Time(hour=14, minute=30, second=45, fraction=123)

    python_datetime = util.date_exact_and_time_to_python_datetime(
        gedcom_date, gedcom_time
    )

    assert python_datetime.day == 15
    assert python_datetime.month == 1
    assert python_datetime.year == 2023
    assert python_datetime.hour == 14
    assert python_datetime.minute == 30
    assert python_datetime.second == 45
    assert python_datetime.microsecond == 123000
    assert python_datetime.tzinfo == datetime.timezone.utc


def test_integration_with_other_functions():
    """Test that the function integrates correctly with other utility functions."""
    with patch("gedcom7.util.date_exact_to_python_date") as mock_date_fn:
        with patch("gedcom7.util.time_to_python_time") as mock_time_fn:
            # Mock the return values
            mock_date_fn.return_value = datetime.date(2023, 1, 15)
            mock_time_fn.return_value = datetime.time(
                14, 30, 45, 123000, tzinfo=datetime.timezone.utc
            )

            gedcom_date = types.DateExact(day=15, month="JAN", year=2023)
            gedcom_time = types.Time(hour=14, minute=30, second=45, fraction=123)

            util.date_exact_and_time_to_python_datetime(gedcom_date, gedcom_time)

            # Verify the functions were called with correct arguments
            mock_date_fn.assert_called_once_with(gedcom_date)
            mock_time_fn.assert_called_once_with(gedcom_time)
