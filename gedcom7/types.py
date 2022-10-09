"""Classes and data types."""

from typing import Optional, List


class GedcomStructure:
    """Gedcom structure class."""

    def __init__(
        self,
        tag: str,
        pointer: str,
        linestr: str,
        sub: Optional[List["GedcomStructure"]] = None,
    ):
        """Initialize self."""
        self.tag = tag
        self.pointer = pointer
        self.linestr = linestr
        self.sub = sub or []

    def __repr__(self):
        if len(self.sub) == 0:
            repr_sub = "[]"
        else:
            repr_sub = f"[{len(self.sub)} <GedcomStructure>]"
        return (
            "GedcomStructure("
            f"tag={self.tag}, pointer={self.pointer}, linestr={self.linestr}, "
            f"sub={repr_sub}"
        )
