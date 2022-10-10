"""GEDCOM 7 parser."""


import re
from typing import Dict, List

from . import const, grammar
from .types import GedcomStructure


def loads(string: str) -> List[GedcomStructure]:
    """Load from a string."""
    context: Dict[int, GedcomStructure] = {}
    records: List[GedcomStructure] = []
    ext: Dict[str, str] = {}
    for match in re.finditer(grammar.line, string):
        data = match.groupdict()
        level = int(data["level"])
        # handle continuation lines
        if data["tag"] == const.CONT:
            context[level - 1].text += "\n" + data["linestr"]
            continue
        structure = GedcomStructure(
            tag=ext.get(data["tag"]) or data["tag"],
            pointer=data["pointer"],
            xref=data["xref"],
            text=data["linestr"],
        )
        # handle extension tags
        if (
            structure.tag == const.TAG
            and context[0].tag == const.HEAD
            and context[1].tag == const.SCHMA
        ):
            tag_name, tag_uri = structure.text.split(" ")
            ext[tag_name] = tag_uri
        context[level] = structure
        # append structure to output
        if level > 0:
            parent = context[level - 1]
            structure.parent = parent
            parent.children.append(structure)
        else:
            records.append(structure)
    return records
