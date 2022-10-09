"""Classes and data types."""

from typing import Optional, List


class GedcomStructure:
    """Gedcom structure class."""

    def __init__(
        self,
        tag: str,
        pointer: str,
        text: str,
        children: Optional[List["GedcomStructure"]] = None,
    ):
        """Initialize self."""
        self.tag = tag
        self.pointer = pointer
        self.text = text
        self.children = children or []
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
