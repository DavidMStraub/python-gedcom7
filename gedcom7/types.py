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

    def as_list_enum(self) -> List[str]:
        """Return as list enum data type."""
        match = re.fullmatch(grammar.list_enum, self.text)
        if not match:
            raise ValueError(f"Cannot interpret {self.text} as type list enum")
        return [el.strip() for el in self.text.split(",")]
