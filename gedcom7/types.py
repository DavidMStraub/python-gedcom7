"""Classes and data types."""

import re
from typing import Any, Dict, Optional, List, Union

from . import const
from . import grammar


class GedcomStructure:
    """Gedcom structure class."""

    def __init__(
        self,
        tag: str,
        pointer: str,
        text: str,
        xref: str,
        children: Optional[List["GedcomStructure"]] = None,
    ):
        """Initialize self."""
        self.tag = tag
        self.pointer = pointer
        self.text = text
        self.children = children or []
        self.xref = xref
        self.parent: Optional["GedcomStructure"] = None

    def __repr__(self):
        if len(self.children) == 0:
            repr_children = "[]"
        else:
            repr_children = f"[{len(self.children)} <GedcomStructure>]"
        return (
            "GedcomStructure("
            f"tag={self.tag}, pointer={self.pointer}, text={self.text}, "
            f"children={repr_children}"
        )

    def _get_type_id(self) -> str:
        """Get the structure type ID."""
        if "://" in self.tag:
            return self.tag
        if self.parent is None:
            if self.tag == const.HEAD:
                return "HEAD pseudostructure"
            if self.tag == const.TRLR:
                return "TRLR pseudostructure"
            return const.substructures[""][self.tag]
        return const.substructures[self.parent._get_type_id()][self.tag]

    def as_type(self, dtype: str):
        """Return as data type."""
        dtype_cls = globals()[dtype]
        return dtype_cls(self.text).parse()

    @property
    def data(self) -> Optional["DataType"]:
        """Return data in the correct type."""
        if not self.text:
            return None
        type_id = self._get_type_id()
        payload = const.payloads.get(type_id)
        dtype = dtypes.get(payload) or Text
        return dtype(self.text)


class DataType:
    """Gedcom data type."""

    REGEX = ""

    def __init__(self, text: str) -> None:
        """Initialize with a string."""
        self.text = text
        self.match = self._match()

    @property
    def name(self) -> str:
        """Name of the type."""
        return self.__class__.__name__

    def __repr__(self):
        return f'{self.name}("{self.text}")'

    def _match(self) -> re.Match:
        """Match a string and raise if not compatible."""
        match = re.fullmatch(self.REGEX, self.text)
        if not match:
            raise ValueError(f"Cannot interpret {self.text} as type {self.name}")
        return match

    def parse(self):
        """Parse the string."""
        return self.text


class Text(DataType):
    """Text type."""

    REGEX = grammar.text


class Integer(DataType):
    """Integer type."""

    REGEX = grammar.integer

    def parse(self):
        """Parse the string."""
        return int(self.text)


class Boolean(DataType):
    """Boolean type."""

    REGEX = grammar.boolean

    def parse(self):
        """Parse the string."""
        if self.text:
            return True
        return False


class PersonalName(DataType):
    """Personal name type."""

    REGEX = grammar.personalname

    def parse(self) -> Dict[str, Optional[str]]:
        """Parse the string."""
        fullname = self.text.replace("/", "")
        surname = self.match.group("surname")
        return {"fullname": fullname, "surname": surname}


class Time(DataType):
    """Time type."""

    REGEX = grammar.time

    def parse(self) -> Dict[str, Optional[Union[str, int]]]:
        """Parse the string."""
        match = self.match.groupdict()

        def f(k, v):
            if k == "tz":
                return v
            if v is None:
                return v
            return int(v)

        return {k: f(k, v) for k, v in match.items()}


class Age(DataType):
    """Age type."""

    REGEX = grammar.age

    def parse(self) -> Dict[str, Any]:
        """Parse the string."""
        match = self.match.groupdict()
        res = {
            "agebound": match["agebound"],
            "years": match["years"],
            "months": match["months1"] or match["months2"],
            "weeks": match["weeks1"] or match["weeks2"] or match["weeks3"],
            "days": match["days1"]
            or match["days2"]
            or match["days3"]
            or match["days4"],
        }

        def f(k, v):
            if k == "agebound":
                return v
            return int(v[:-1])

        return {k: f(k, v) for k, v in res.items() if v is not None}


class Enum(DataType):
    """Enum type."""

    REGEX = grammar.enum


class ListText(DataType):
    """List Text type."""

    REGEX = grammar.list_text

    def parse(self) -> List[str]:
        """Parse the string."""
        return [el.strip() for el in self.text.split(",")]


class ListEnum(ListText):
    """List Enum type."""

    REGEX = grammar.list_enum


class MediaType(DataType):
    """Media type type."""

    REGEX = grammar.mediatype


class DateExact(DataType):
    """Exact date type."""

    REGEX = grammar.dateexact

    def parse(self) -> Dict[str, Union[str, int]]:
        """Parse the string."""
        match = self.match.groupdict()
        return {
            "day": int(match["day"]),
            "month": match["month"],
            "year": int(match["year"]),
        }


class Date(DataType):
    """Date type."""

    REGEX = grammar.date_capture

    def parse(self) -> Dict[str, Union[str, int]]:
        """Parse the string."""
        match = self.match.groupdict()
        return {
            "calendar": match["calendar"],
            "day": int(match["day"]) if match["day"] else None,
            "month": match["month"],
            "year": int(match["year"]),
            "epoch": match["epoch"],
        }


class DatePeriod(DataType):
    """Date period type."""

    REGEX = grammar.dateperiod

    def parse(self) -> Dict[str, Any]:
        """Parse the string."""
        match = self.match.groupdict()
        res = {}
        if match["todate1"] or match["todate2"]:
            res["to"] = Date(match["todate1"] or match["todate2"]).parse()
        if match["fromdate"]:
            res["from"] = Date(match["fromdate"]).parse()
        return res


class DateApprox(DataType):
    """Date approx type."""

    REGEX = grammar.dateapprox

    def parse(self) -> Dict[str, Any]:
        """Parse the string."""
        match = self.match.groupdict()
        match["date"] = Date(match.pop("dateapprox")).parse()
        return match


class DateRange(DataType):
    """Date range type."""

    REGEX = grammar.daterange

    def parse(self) -> Dict[str, Any]:
        """Parse the string."""
        match = self.match.groupdict()
        return {k: Date(v).parse() for k, v in match.items() if v}


class DateValue(DataType):
    """Date value type."""

    REGEX = grammar.datevalue

    def parse(self) -> Dict[str, Any]:
        """Parse the string."""
        if not self.text:
            return {}
        try:
            res = Date(self.text).parse()
            return res
        except ValueError:
            pass
        try:
            res = DateRange(self.text).parse()
            return res
        except ValueError:
            pass
        try:
            res = DatePeriod(self.text).parse()
            return res
        except ValueError:
            pass
        return DateApprox(self.text).parse()


dtypes = {
    "Y|<NULL>": Boolean,
    "http://www.w3.org/2001/XMLSchema#Language": Text,
    "http://www.w3.org/2001/XMLSchema#nonNegativeInteger": Integer,
    "http://www.w3.org/2001/XMLSchema#string": Text,
    "http://www.w3.org/ns/dcat#mediaType": MediaType,
    "https://gedcom.io/terms/v7/type-Age": Age,
    "https://gedcom.io/terms/v7/type-Date": DateValue,
    "https://gedcom.io/terms/v7/type-Date#exact": DateExact,
    "https://gedcom.io/terms/v7/type-Date#period": DatePeriod,
    "https://gedcom.io/terms/v7/type-Enum": Enum,
    "https://gedcom.io/terms/v7/type-List#Enum": ListEnum,
    "https://gedcom.io/terms/v7/type-List#Text": ListText,
    "https://gedcom.io/terms/v7/type-Name": PersonalName,
    "https://gedcom.io/terms/v7/type-Time": Time,
}
