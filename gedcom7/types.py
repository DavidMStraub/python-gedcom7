"""Classes and data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Union

from . import cast, const


@dataclass
class GedcomStructure:
    """Gedcom structure class."""

    tag: str
    pointer: str
    text: str
    xref: str
    children: list["GedcomStructure"] = field(default_factory=list)
    parent: "GedcomStructure | None" = None

    @property
    def type_id(self) -> str:
        """Get the structure type ID."""
        if "://" in self.tag:
            return self.tag
        if self.parent is None:
            if self.tag == const.HEAD:
                return "HEAD pseudostructure"
            if self.tag == const.TRLR:
                return "TRLR pseudostructure"
            return const.substructures[""][self.tag]
        return const.substructures[self.parent.type_id][self.tag]

    def __post_init__(self):
        """Post-init steps: set parent on children."""
        for child in self.children:
            child.parent = self

    def append_child(self, child: "GedcomStructure") -> None:
        """Append a child to the structure and set the child's parent to self."""
        child.parent = self
        self.children.append(child)

    @property
    def value(self) -> "DataType | None":
        return cast.cast_value(text=self.text, type_id=self.type_id)


@dataclass
class PersonalName:
    """Personal name type."""

    fullname: str
    given: str | None = None
    surname: str | None = None
    suffix: str | None = None


@dataclass
class Time:
    """Time type."""

    hour: int
    minute: int
    second: int | None = None
    fraction: int | None = None
    tz: Literal["Z"] | None = None


@dataclass
class Age:
    """Age type."""

    agebound: str | None = None
    years: int | None = None
    months: int | None = None
    weeks: int | None = None
    days: int | None = None


@dataclass
class MediaType:
    """Media type type."""

    media_type: str


@dataclass
class DateExact:
    """Exact date type."""

    day: int
    month: str
    year: int


@dataclass
class Date:
    """Date type."""

    calendar: str | None = None
    day: int | None = None
    month: str | None = None
    year: int | None = None
    epoch: str | None = None


@dataclass
class DatePeriod:
    """Date period type."""

    from_: Date | None = None
    to: Date | None = None


@dataclass
class DateApprox:
    """Date approx type."""

    date: Date
    approx: str | None = None


@dataclass
class DateRange:
    """Date range type."""

    start: Date | None = None
    end: Date | None = None


DateValue = Union[
    Date,
    DatePeriod,
    DateApprox,
    DateRange,
]

DataType = Union[
    str,
    int,
    list[str],
    PersonalName,
    Time,
    Age,
    MediaType,
    DateExact,
    DateApprox,
    DateRange,
    DatePeriod,
    DateValue,
]
