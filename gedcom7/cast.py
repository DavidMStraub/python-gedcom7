"""Cast strings values to the appropriate data type."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable

from . import const, grammar, types

logger = logging.getLogger(__name__)


def cast_value(text: str, type_id: str) -> types.DataType | None:
    if not text:
        return None
    payload = const.payloads.get(type_id)
    if not payload:
        logger.warning("Encountered unknown data type %s", type_id)
        return None
    cast_fuction = CAST_FUNCTIONS.get(payload)
    if not cast_fuction:
        return text
    return cast_fuction(text)


def _cast_bool(value: str) -> bool:
    """Cast a string to a boolean."""
    if value == "Y":
        return True
    if not value:
        return False
    else:
        raise ValueError(f"Cannot interpret {value} as boolean")


def _cast_integer(value: str) -> int:
    """Cast a string to an integer."""
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Cannot interpret {value} as integer")


def _cast_list_text(value: str) -> list[str]:
    """Cast a string to a list of strings."""
    return [el.strip() for el in value.split(",")]


def _match(text: str, regex: str, type_name: str) -> re.Match:
    """Match a string and raise if not compatible."""
    match = re.fullmatch(regex, text)
    if not match:
        raise ValueError(f"Cannot interpret {text} as type {type_name}")
    return match


def _cast_personal_name(value: str) -> types.PersonalName:
    """Cast a string to a PersonalName."""
    match = _match(value, grammar.personalname, "PersonalName")
    return types.PersonalName(
        fullname=value.replace("/", ""),
        surname=match.group("surname"),
    )


def _cast_time(value: str) -> types.Time:
    """Cast a string to a Time."""
    match = _match(value, grammar.time, "Time")
    return types.Time(
        tz=match.group("tz"),
        hour=int(match.group("hour")),
        minute=int(match.group("minute")),
        second=int(match.group("second")) if match.group("second") else None,
        fraction=int(match.group("fraction")) if match.group("fraction") else None,
    )


def _cast_age(value: str) -> types.Age:
    """Cast a string to an Age."""
    match = _match(value, grammar.age, "Age")
    res = {
        "agebound": match.group("agebound"),
        "years": match.group("years"),
        "months": match.group("months1") or match.group("months2"),
        "weeks": match.group("weeks1")
        or match.group("weeks2")
        or match.group("weeks3"),
        "days": match.group("days1")
        or match.group("days2")
        or match.group("days3")
        or match.group("days4"),
    }
    return types.Age(
        agebound=res["agebound"],
        years=int(res["years"].rstrip("y")) if res["years"] else None,
        months=int(res["months"].rstrip("m")) if res["months"] else None,
        weeks=int(res["weeks"].rstrip("w")) if res["weeks"] else None,
        days=int(res["days"].rstrip("d")) if res["days"] else None,
    )


def _cast_enum(value: str) -> str:
    """Cast a string to an Enum."""
    match = _match(value, grammar.enum, "Enum")
    return match.group(0)


def _cast_list_enum(value: str) -> list[str]:
    """Cast a string to a list of Enums."""
    match = _match(value, grammar.list_enum, "ListEnum")
    return [el.strip() for el in match.group(0).split(",")]


def _cast_mediatype(value: str) -> types.MediaType:
    """Cast a string to a MediaType."""
    match = _match(value, grammar.mediatype, "MediaType")
    return types.MediaType(media_type=match.group(0))


def _cast_date_exact(value: str) -> types.DateExact:
    """Cast a string to a DateExact."""
    match = _match(value, grammar.dateexact, "DateExact")
    return types.DateExact(
        day=int(match.group("day")),
        month=match.group("month"),
        year=int(match.group("year")),
    )


def _cast_date(value: str) -> types.Date:
    """Cast a string to a Date."""
    match = _match(value, grammar.date_capture, "Date")
    return types.Date(
        calendar=match.group("calendar"),
        day=int(match.group("day")) if match.group("day") else None,
        month=match.group("month"),
        year=int(match.group("year")),
        epoch=match.group("epoch"),
    )


def _cast_date_period(value: str) -> types.DatePeriod:
    """Cast a string to a DatePeriod."""
    match = _match(value, grammar.dateperiod, "DatePeriod")
    res = {}
    if match.group("todate1") or match.group("todate2"):
        to_date = match.group("todate1") or match.group("todate2")
        to_date_match = re.fullmatch(grammar.date_capture, to_date)
        if to_date_match:
            res["to"] = types.Date(
                calendar=to_date_match.group("calendar"),
                day=(
                    int(to_date_match.group("day"))
                    if to_date_match.group("day")
                    else None
                ),
                month=to_date_match.group("month"),
                year=int(to_date_match.group("year")),
                epoch=to_date_match.group("epoch"),
            )
    if match.group("fromdate"):
        from_date_match = re.fullmatch(grammar.date_capture, match.group("fromdate"))
        if from_date_match:
            res["from_"] = types.Date(
                calendar=from_date_match.group("calendar"),
                day=(
                    int(from_date_match.group("day"))
                    if from_date_match.group("day")
                    else None
                ),
                month=from_date_match.group("month"),
                year=int(from_date_match.group("year")),
                epoch=from_date_match.group("epoch"),
            )
    return types.DatePeriod(**res)


CAST_FUNCTIONS: dict[str, Callable[[str], types.DataType] | None] = {
    "Y|<NULL>": _cast_bool,
    "http://www.w3.org/2001/XMLSchema#Language": None,
    "http://www.w3.org/2001/XMLSchema#nonNegativeInteger": _cast_integer,
    "http://www.w3.org/2001/XMLSchema#string": None,
    "http://www.w3.org/ns/dcat#mediaType": _cast_mediatype,
    "https://gedcom.io/terms/v7/type-Age": _cast_age,
    "https://gedcom.io/terms/v7/type-Date": _cast_date,
    "https://gedcom.io/terms/v7/type-Date#exact": _cast_date_exact,
    "https://gedcom.io/terms/v7/type-Date#period": _cast_date_period,
    "https://gedcom.io/terms/v7/type-Enum": _cast_enum,
    "https://gedcom.io/terms/v7/type-List#Enum": _cast_list_enum,
    "https://gedcom.io/terms/v7/type-List#Text": _cast_list_text,
    "https://gedcom.io/terms/v7/type-Name": _cast_personal_name,
    "https://gedcom.io/terms/v7/type-Time": _cast_time,
}
