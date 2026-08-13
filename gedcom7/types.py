"""Classes and data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from . import cast, const


@dataclass
class GedcomStructure:
    """Gedcom structure class."""

    tag: str
    # absent for a line without a pointer payload / without a cross-reference id
    pointer: str | None
    text: str
    xref: str | None
    children: list[GedcomStructure] = field(default_factory=list)
    # Excluded from comparison and repr: it points back up the tree, so including
    # it would make __eq__ recurse endlessly and __repr__ print every ancestor.
    # A structure's superstructure is implied by its position in the tree.
    parent: GedcomStructure | None = field(default=None, compare=False, repr=False)

    @property
    def type_id(self) -> str | None:
        """Get the structure type ID, or None if no standard type applies.

        A structure has no standard type when it uses an undocumented extension
        tag, or when it is an extension-defined substructure -- both of which the
        specification permits, and whose meaning is defined by the extension
        rather than by this document.
        """
        if "://" in self.tag:
            return self.tag
        if self.parent is None:
            if self.tag == const.HEAD:
                return "HEAD pseudostructure"
            if self.tag == const.TRLR:
                return "TRLR pseudostructure"
            return const.substructures[""].get(self.tag)
        parent_type_id = self.parent.type_id
        if parent_type_id is None:
            return None
        return const.substructures.get(parent_type_id, {}).get(self.tag)

    def __post_init__(self) -> None:
        """Post-init steps: set parent on children."""
        for child in self.children:
            child.parent = self

    def append_child(self, child: GedcomStructure) -> None:
        """Append a child to the structure and set the child's parent to self."""
        child.parent = self
        self.children.append(child)

    @property
    def value(self) -> DataType | None:
        """Get the payload cast to its appropriate data type."""
        type_id = self.type_id
        if type_id is None:
            # No standard structure type applies, so the payload's data type is
            # defined by the extension. It is returned uninterpreted.
            return self.text or None
        return cast.cast_value(text=self.text, type_id=type_id)


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
    # The digits after the decimal point, kept verbatim. Leading zeros are part
    # of the value: ".05" and ".5" are different instants. Trailing zeros are
    # not, but they belong to the payload, so keeping the digits as written
    # preserves those too.
    fraction: str | None = None
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
class TagDefinition:
    """Tag definition type: an extension tag and the URI it abbreviates."""

    tag: str
    uri: str


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


DateValue = Date | DatePeriod | DateApprox | DateRange

DataType = (
    str
    | int
    | float
    | list[str]
    | TagDefinition
    | PersonalName
    | Time
    | Age
    | MediaType
    | DateExact
    | DateApprox
    | DateRange
    | DatePeriod
    | DateValue
)
