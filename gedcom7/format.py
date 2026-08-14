"""Format data type values back to payload strings.

This is the inverse of :mod:`gedcom7.cast`. Every formatter checks its result
against the same grammar production the corresponding cast function matches, so
a value that cannot be written as a conforming payload raises rather than
producing a data stream that will not parse.

The inverse normalizes: casting discards detail that carries no meaning, such as
the spacing around list separators or a leading zero on a day number, so
``format_value(cast_value(text, type_id), type_id)`` may differ from ``text``
while denoting the same thing. :class:`~gedcom7.types.PersonalName` is the one
type whose casting is lossy in a way that formatting cannot always undo; see
:func:`_format_personal_name`.
"""

from __future__ import annotations

import decimal
import re
from collections.abc import Callable
from typing import Any, TypeVar

from . import const, grammar, types
from .exceptions import GedcomSerializeError

_T = TypeVar("_T")


def format_value(value: types.DataType | None, type_id: str) -> str | None:
    """Format a value as the payload string for its structure type.

    ``None`` and the empty string mean different things, and a caller deciding
    what to write has to tell them apart. ``None`` means there is no structure to
    write: it comes back for a value of ``None``, and for a false ``Y|<NULL>``,
    which the specification expresses by leaving the structure out rather than by
    writing it empty. The empty string means the structure is written with no
    payload, as for an empty :class:`~gedcom7.types.DatePeriod`, which is a legal
    date period and not the absence of one.

    Raises :class:`~gedcom7.exceptions.GedcomSerializeError` if the value cannot
    be written as a payload conforming to its structure type, including when the
    structure type points at a record: a pointer belongs in the structure's
    pointer, and writing it as text would escape its leading "@" and turn the
    link into a line of text. A structure with no standard type has no data type
    to format, so its text is written as it stands rather than passed here.
    """
    if value is None:
        return None
    payload = const.payloads.get(type_id)
    if payload is None:
        raise GedcomSerializeError(f"Unknown structure type {type_id}")
    if not payload:
        raise GedcomSerializeError(f"{type_id} takes no payload")
    if payload.startswith("@<") and payload.endswith(">@"):
        raise GedcomSerializeError(
            f"{type_id} points at a record rather than carrying a value; "
            "set the structure's pointer instead of its text"
        )
    format_function = FORMAT_FUNCTIONS.get(payload)
    if not format_function:
        return _format_string(value)
    return format_function(value)


def _expect(value: object, expected: type[_T], type_name: str) -> _T:
    """Return the value if it is the type the structure type calls for."""
    if not isinstance(value, expected):
        raise GedcomSerializeError(
            f"{type_name} takes {expected.__name__}, "
            f"not {type(value).__name__}: {value!r}"
        )
    return value


def _check(text: str, regex: str, type_name: str) -> str:
    """Return the text if it conforms to the grammar, and raise if it does not."""
    if re.fullmatch(regex, text) is None:
        raise GedcomSerializeError(f"{text!r} is not a valid {type_name} payload")
    return text


def _format_string(value: object) -> str:
    """Format a payload whose data type leaves it an uninterpreted string."""
    return _expect(value, str, "This structure type")


def _format_bool(value: object) -> str | None:
    """Format a boolean, false being written as no structure at all."""
    return "Y" if _expect(value, bool, "Boolean") else None


def _format_integer(value: object) -> str:
    """Format a non-negative integer."""
    if isinstance(value, bool):
        raise GedcomSerializeError(f"Integer takes int, not bool: {value!r}")
    number = _expect(value, int, "Integer")
    if number < 0:
        raise GedcomSerializeError(f"{number} is not a non-negative integer")
    return str(number)


def _format_list_text(value: object) -> str:
    """Format a list of strings as a comma separated payload.

    The grammar allows space on either side of the separator, so space around an
    item carries no meaning and is stripped, as casting strips it. A comma is a
    different matter: a list has no escaping mechanism, so an item containing one
    cannot be written at all, because reading it back would give two items.
    """
    items = [_expect(item, str, "List:Text") for item in _expect(value, list, "List")]
    for item in items:
        if "," in item:
            raise GedcomSerializeError(
                f"{item!r} cannot be written as a list item: it contains a comma"
            )
    return _check(
        ", ".join(item.strip() for item in items), grammar.list_text, "List:Text"
    )


def _format_enum(value: object) -> str:
    """Format an enumeration value."""
    return _check(_expect(value, str, "Enum"), grammar.enum, "Enum")


def _format_list_enum(value: object) -> str:
    """Format a list of enumeration values.

    Unlike a list of text, the items are not stripped. An enumeration value may
    not contain a space at all, so one that arrives with a space is not a value
    needing tidying but a value from outside the vocabulary, and it is refused
    here exactly as :func:`_format_enum` refuses it on its own.
    """
    items = [_expect(item, str, "List:Enum") for item in _expect(value, list, "List")]
    return _check(", ".join(items), grammar.list_enum, "List:Enum")


def _format_mediatype(value: object) -> str:
    """Format a media type."""
    media_type = _expect(value, types.MediaType, "MediaType")
    return _check(media_type.media_type, grammar.mediatype, "MediaType")


def _format_tag_definition(value: object) -> str:
    """Format a tag definition."""
    definition = _expect(value, types.TagDefinition, "TagDef")
    return _check(f"{definition.tag} {definition.uri}", grammar.tagdef, "TagDef")


def _format_personal_name(value: object) -> str:
    """Format a personal name, the parts taking precedence over the full name.

    ``fullname`` is the payload with its slashes removed, so it cannot say where
    they belong and the parts are the only faithful source. A name whose parts
    are all absent never carried slashes, and is written as it stands. Where both
    disagree the parts win, which is the one place this module cannot reproduce
    its input: a surname that also occurs in the given name is unrecoverable.
    """
    name = _expect(value, types.PersonalName, "PersonalName")
    if name.given is None and name.surname is None and name.suffix is None:
        return _check(name.fullname, grammar.personalname, "PersonalName")
    text = (
        (f"{name.given} " if name.given else "")
        + f"/{name.surname or ''}/"
        + (f" {name.suffix}" if name.suffix else "")
    )
    return _check(text, grammar.personalname, "PersonalName")


def _format_time(value: object) -> str:
    """Format a time, the hour and minute padded to the conventional two digits."""
    time = _expect(value, types.Time, "Time")
    text = f"{time.hour:02d}:{time.minute:02d}"
    if time.second is None and time.fraction is not None:
        raise GedcomSerializeError("a Time with a fraction must have seconds")
    if time.second is not None:
        text += f":{time.second:02d}"
        if time.fraction is not None:
            text += f".{time.fraction}"
    if time.tz is not None:
        text += time.tz
    return _check(text, grammar.time, "Time")


def _format_age(value: object) -> str:
    """Format an age, in the years, months, weeks, days order the grammar fixes."""
    age = _expect(value, types.Age, "Age")
    units = ((age.years, "y"), (age.months, "m"), (age.weeks, "w"), (age.days, "d"))
    parts = [f"{number}{unit}" for number, unit in units if number is not None]
    if not parts:
        # unlike an empty DatePeriod, an age with no duration has no valid payload
        raise GedcomSerializeError(
            "an Age must have at least one of years, months, weeks or days"
        )
    if age.agebound is not None:
        parts.insert(0, age.agebound)
    return _check(" ".join(parts), grammar.age, "Age")


def _format_degrees(degrees: float) -> str:
    """Format a coordinate's magnitude in the fixed notation the grammar requires.

    ``str`` renders small magnitudes in exponent notation, which no coordinate
    payload may contain, so the number is rendered through :class:`~decimal.Decimal`
    instead.

    A trailing zero after the decimal point comes from the float rather than from
    the coordinate, and casting has already discarded which of "N90" and "N90.0"
    was written, so the shorter spelling is chosen for both. Dropping it also
    keeps a whole number of degrees from depending on whether the caller happened
    to hold it as an int or a float.
    """
    text = format(decimal.Decimal(repr(abs(degrees))), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _expect_degrees(value: object, type_name: str, limit: int) -> float:
    """Return the value if it is a number within the coordinate's range."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise GedcomSerializeError(
            f"{type_name} takes a number, not {type(value).__name__}: {value!r}"
        )
    if not -limit <= value <= limit:
        raise GedcomSerializeError(
            f"{value} is not a {type_name.lower()} between -{limit} and {limit}"
        )
    return value


def _format_latitude(value: object) -> str:
    """Format a latitude in signed decimal degrees, north positive."""
    degrees = _expect_degrees(value, "Latitude", 90)
    direction = "S" if degrees < 0 else "N"
    return _check(direction + _format_degrees(degrees), grammar.latitude, "Latitude")


def _format_longitude(value: object) -> str:
    """Format a longitude in signed decimal degrees, east positive."""
    degrees = _expect_degrees(value, "Longitude", 180)
    direction = "W" if degrees < 0 else "E"
    return _check(direction + _format_degrees(degrees), grammar.longitude, "Longitude")


def _date_text(date: types.Date) -> str:
    """Build the text of a date, for use on its own or inside a compound date."""
    date = _expect(date, types.Date, "Date")
    if date.year is None:
        raise GedcomSerializeError("a Date must have a year")
    if date.day is not None and date.month is None:
        raise GedcomSerializeError("a Date with a day must have a month")
    parts = []
    if date.calendar is not None:
        parts.append(date.calendar)
    if date.day is not None:
        parts.append(str(date.day))
    if date.month is not None:
        parts.append(date.month)
    parts.append(str(date.year))
    if date.epoch is not None:
        parts.append(date.epoch)
    return " ".join(parts)


def _format_date(value: object) -> str:
    """Format a date."""
    return _check(_date_text(_expect(value, types.Date, "Date")), grammar.date, "Date")


def _format_date_exact(value: object) -> str:
    """Format an exact date, whose day, month and year are all required."""
    date = _expect(value, types.DateExact, "DateExact")
    return _check(
        f"{date.day} {date.month} {date.year}", grammar.dateexact, "DateExact"
    )


def _format_date_approx(value: object) -> str:
    """Format an approximate date."""
    approx = _expect(value, types.DateApprox, "DateApprox")
    if approx.approx is None:
        raise GedcomSerializeError(
            "a DateApprox must have a qualifier of ABT, CAL or EST"
        )
    return _check(
        f"{approx.approx} {_date_text(approx.date)}", grammar.dateapprox, "DateApprox"
    )


def _format_date_range(value: object) -> str:
    """Format a date range as one of its BET/AND, AFT or BEF forms."""
    date_range = _expect(value, types.DateRange, "DateRange")
    if date_range.start is not None and date_range.end is not None:
        text = f"BET {_date_text(date_range.start)} AND {_date_text(date_range.end)}"
    elif date_range.start is not None:
        text = f"AFT {_date_text(date_range.start)}"
    elif date_range.end is not None:
        text = f"BEF {_date_text(date_range.end)}"
    else:
        raise GedcomSerializeError("a DateRange must have a start or an end")
    return _check(text, grammar.daterange, "DateRange")


def _format_date_period(value: object) -> str:
    """Format a date period, an empty period being a legal empty payload."""
    period = _expect(value, types.DatePeriod, "DatePeriod")
    if period.from_ is not None and period.to is not None:
        text = f"FROM {_date_text(period.from_)} TO {_date_text(period.to)}"
    elif period.from_ is not None:
        text = f"FROM {_date_text(period.from_)}"
    elif period.to is not None:
        text = f"TO {_date_text(period.to)}"
    else:
        text = ""
    return _check(text, grammar.dateperiod, "DatePeriod")


def _format_date_value(value: object) -> str:
    """Format whichever of the date value forms the value carries."""
    if isinstance(value, types.DateApprox):
        return _format_date_approx(value)
    if isinstance(value, types.DateRange):
        return _format_date_range(value)
    if isinstance(value, types.DatePeriod):
        return _format_date_period(value)
    return _format_date(value)


# Mirrors cast.CAST_FUNCTIONS: a None entry marks a payload that is carried as an
# uninterpreted string in both directions.
FORMAT_FUNCTIONS: dict[str, Callable[[Any], str | None] | None] = {
    "Y|<NULL>": _format_bool,
    "http://www.w3.org/2001/XMLSchema#Language": None,
    "http://www.w3.org/2001/XMLSchema#anyURI": None,
    "http://www.w3.org/2001/XMLSchema#nonNegativeInteger": _format_integer,
    "http://www.w3.org/2001/XMLSchema#string": None,
    "http://www.w3.org/ns/dcat#mediaType": _format_mediatype,
    "https://gedcom.io/terms/v7/type-Age": _format_age,
    "https://gedcom.io/terms/v7/type-Date": _format_date_value,
    "https://gedcom.io/terms/v7/type-Date#exact": _format_date_exact,
    "https://gedcom.io/terms/v7/type-Date#period": _format_date_period,
    "https://gedcom.io/terms/v7/type-Enum": _format_enum,
    "https://gedcom.io/terms/v7/type-FilePath": None,
    "https://gedcom.io/terms/v7/type-Latitude": _format_latitude,
    "https://gedcom.io/terms/v7/type-List#Enum": _format_list_enum,
    "https://gedcom.io/terms/v7/type-List#Text": _format_list_text,
    "https://gedcom.io/terms/v7/type-Longitude": _format_longitude,
    "https://gedcom.io/terms/v7/type-Name": _format_personal_name,
    "https://gedcom.io/terms/v7/type-TagDef": _format_tag_definition,
    "https://gedcom.io/terms/v7/type-Time": _format_time,
}
