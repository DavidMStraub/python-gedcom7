"""Classes and data types."""

import re
from typing import Any, Dict, Optional, List, Union

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

    def as_type(self, dtype: str):
        """Return as data type."""
        dtype_cls = globals()[dtype]
        return dtype_cls(self.text).parse()


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


class Integer(DataType):
    """Integer type."""

    REGEX = grammar.integer

    def parse(self):
        """Parse the string."""
        return int(self.text)


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
