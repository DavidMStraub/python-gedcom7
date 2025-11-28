"""GEDCOM 7 parser."""

import re

from . import cast, const, grammar
from .types import GedcomStructure


def loads(string: str) -> list[GedcomStructure]:
    """Load from a string."""
    context: dict[int, GedcomStructure] = {}
    records: list[GedcomStructure] = []
    ext: dict[str, str] = {}
    for match in re.finditer(grammar.line, string):
        data = match.groupdict()
        level = int(data["level"])
        linestr = data["linestr"] or ""
        # handle continuation lines
        if data["tag"] == const.CONT:
            context[level - 1].text += "\n" + linestr
            continue
        structure = GedcomStructure(
            tag=ext.get(data["tag"]) or data["tag"],
            pointer=data["pointer"],
            xref=data["xref"],
            text=linestr,
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
            parent.append_child(structure)
        else:
            records.append(structure)
    return records
