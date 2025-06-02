"""Utility functions for GEDCOM 7 processing."""

from __future__ import annotations

import datetime

from . import const, types


def get_first_child_with_tag(
    structure: types.GedcomStructure, tag: str
) -> types.GedcomStructure | None:
    """Get the first child of a GEDCOM structure with a specific tag.

    If no child with the specified tag is found, return None.
    """
    for child in structure.children:
        if child.tag == tag:
            return child
    return None


def date_exact_to_python_date(date: types.DateExact) -> datetime.date:
    """Convert a GEDCOM DateExact to a Python date."""
    try:
        month = const.GEDCOM_MONTHS[date.month.upper()]
    except KeyError:
        raise ValueError(f"Invalid month in date: {date.month}")
    return datetime.date(year=date.year, month=month, day=date.day)


def time_to_python_time(time: types.Time) -> datetime.time:
    """Convert a GEDCOM Time to a Python time."""
    second = 0
    microsecond = 0
    if time.second:
        second = time.second
    if time.fraction:
        fraction = float(f"0.{time.fraction}")
        microsecond = int(fraction * 1_000_000)
    return datetime.time(
        hour=time.hour,
        minute=time.minute,
        second=second,
        microsecond=microsecond,
        tzinfo=datetime.timezone.utc,
    )


def date_exact_and_time_to_python_datetime(
    date: types.DateExact, time: types.Time | None = None
) -> datetime.datetime:
    """Convert a GEDCOM date and optional time to a Python datetime."""
    date_obj = date_exact_to_python_date(date)
    if time:
        time_obj = time_to_python_time(time)
        return datetime.datetime.combine(date_obj, time_obj)
    return datetime.datetime.combine(
        date_obj, datetime.time.min, tzinfo=datetime.timezone.utc
    )
