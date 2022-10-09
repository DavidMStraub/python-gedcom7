"""Classes and data types."""

from typing import Optional, List


class GedcomStructure:
    """Gedcom structure class."""

    def __init__(
        self,
        tag: str,
        pointer: str,
        linestr: str,
        children: Optional[List["GedcomStructure"]] = None,
    ):
        """Initialize self."""
        self.tag = tag
        self.pointer = pointer
        self.linestr = linestr
        self.children = children or []
        self.parent: Optional["GedcomStructure"] = None

    def __repr__(self):
        if len(self.children) == 0:
            repr_children = "[]"
        else:
            repr_children = f"[{len(self.children)} <GedcomStructure>]"
        return (
            "GedcomStructure("
            f"tag={self.tag}, pointer={self.pointer}, linestr={self.linestr}, "
            f"children={repr_children}"
        )
