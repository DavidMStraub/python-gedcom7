"""Classes and data types."""

import re
from typing import Optional, List

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

    def _match_type(self, regex, name: str):
        """Check if content matches type."""
        match = re.fullmatch(regex, self.text)
        if not match:
            raise ValueError(f"Cannot interpret {self.text} as type {name}")
        return match

    def as_list_enum(self) -> List[str]:
        """Return as list enum data type."""
        self._match_type(grammar.list_enum, "list enum")
        return [el.strip() for el in self.text.split(",")]

    def as_enum(self) -> List[str]:
        """Return as list enum data type."""
        self._match_type(grammar.enum, "enum")
        return self.text

    def as_personal_name(self) -> List[str]:
        """Return as personal name data type."""
        match = self._match_type(grammar.personalname, "personal name")
        full_name = self.text.replace("/", "")
        surname = match.group("surname")
        return full_name, surname

    def as_integer(self) -> List[str]:
        """Return as integer data type."""
        self._match_type(grammar.integer, "integer")
        return int(self.text)
