"""GEDCOM 7 parser."""

from __future__ import annotations

import re

from . import const, grammar
from .exceptions import GedcomParseError
from .types import GedcomStructure

# EOL = %x0D [%x0A] / %x0A -- CR-LF, CR, or LF
_EOL = re.compile(r"\r\n|\r|\n")
_LINE = re.compile(grammar.line)
_BANNED = re.compile(grammar.banned)
_TAGDEF = re.compile(grammar.tagdef)

# U+FEFF, the byte-order mark, may open a data stream and carries no meaning
_BOM = "﻿"


def _unescape(linestr: str) -> str:
    """Undo the escaping of a line string's leading "@".

    ``lineStr = (nonAt / atsign atsign) *nonEOL``, so only a leading ``@`` is
    doubled; any later ``@`` stands for itself. ``@@@@@`` therefore decodes to
    ``@@@@``, not to ``@@``.
    """
    return linestr[1:] if linestr.startswith("@@") else linestr


def loads(string: str) -> list[GedcomStructure]:
    """Load a GEDCOM 7 dataset from a string.

    Raises :class:`~gedcom7.exceptions.GedcomParseError` if the data stream does
    not conform to the specification. Non-conforming lines are never skipped.
    """
    string = string.removeprefix(_BOM)

    banned = _BANNED.search(string)
    if banned:
        raise GedcomParseError(
            f"banned character U+{ord(banned.group()):04X} in data stream",
            line_number=string.count("\n", 0, banned.start()) + 1,
        )

    lines = _EOL.split(string)
    # A terminating EOL leaves a final empty element that is not itself a line.
    # A data stream whose last line lacks its EOL is tolerated: the line is
    # complete and unambiguous, and dropping it would silently lose data.
    if lines and lines[-1] == "":
        lines.pop()

    records: list[GedcomStructure] = []
    # stack[i] is the structure encoded by the nearest preceding line of level i
    stack: list[GedcomStructure] = []
    # extension tag -> URIs declared for it by the header schema
    schema: dict[str, list[str]] = {}
    xrefs: set[str] = set()
    pointers: list[tuple[str, int]] = []
    # the structure a CONT on the very next line would continue
    continuable: GedcomStructure | None = None

    for number, text in enumerate(lines, start=1):
        match = _LINE.fullmatch(text + "\n")
        if match is None:
            raise GedcomParseError(
                f"malformed line: {text!r}", line_number=number, line=text
            )

        level = int(match.group("level"))
        tag = match.group("tag")
        xref = match.group("xref")
        pointer = match.group("pointer")
        linestr = match.group("linestr")
        payload = _unescape(linestr) if linestr is not None else ""

        if tag == const.CONT:
            if (
                continuable is None
                or level != len(stack)
                or stack[-1] is not continuable
            ):
                raise GedcomParseError(
                    "CONT must immediately follow the line it continues, at one "
                    "greater level, and before any other substructure",
                    line_number=number,
                    line=text,
                )
            if continuable.pointer:
                raise GedcomParseError(
                    "CONT cannot continue a pointer payload",
                    line_number=number,
                    line=text,
                )
            continuable.text += "\n" + payload
            continue

        if level > len(stack):
            if not stack:
                raise GedcomParseError(
                    f"a dataset must begin with a level 0 line, found level {level}",
                    line_number=number,
                    line=text,
                )
            raise GedcomParseError(
                f"level {level} follows level {len(stack) - 1}; a line may be at "
                "most one level deeper than the line it follows",
                line_number=number,
                line=text,
            )
        del stack[level:]

        if xref is not None:
            if level != 0:
                raise GedcomParseError(
                    "only records may have a cross-reference identifier",
                    line_number=number,
                    line=text,
                )
            if xref == const.VOIDPTR:
                raise GedcomParseError(
                    f"{const.VOIDPTR} must not be used as a cross-reference identifier",
                    line_number=number,
                    line=text,
                )
            if xref in xrefs:
                raise GedcomParseError(
                    f"duplicate cross-reference identifier {xref}",
                    line_number=number,
                    line=text,
                )
            xrefs.add(xref)

        # A documented extension tag stands for its URI. A tag the schema maps to
        # several URIs cannot be disambiguated without the extension's own
        # documentation, so it is left as the tag.
        uris = schema.get(tag)
        structure = GedcomStructure(
            tag=uris[0] if uris is not None and len(uris) == 1 else tag,
            pointer=pointer,
            xref=xref,
            text=payload,
        )

        if (
            tag == const.TAG
            and level == 2
            and stack[0].tag == const.HEAD
            and stack[1].tag == const.SCHMA
        ):
            tagdef = _TAGDEF.fullmatch(structure.text)
            if tagdef is None:
                raise GedcomParseError(
                    "a tag definition must be an extension tag, a space, and a "
                    f"URI, found {structure.text!r}",
                    line_number=number,
                    line=text,
                )
            schema.setdefault(tagdef.group("exttag"), []).append(tagdef.group("uri"))

        if level == 0:
            records.append(structure)
        else:
            stack[level - 1].append_child(structure)
        stack.append(structure)
        continuable = structure

        if pointer is not None and pointer != const.VOIDPTR:
            pointers.append((pointer, number))

    # Pointers may be forward references, so they are resolved once the whole
    # data stream has been read.
    for pointer, number in pointers:
        if pointer not in xrefs:
            raise GedcomParseError(
                f"pointer {pointer} matches no cross-reference identifier in the "
                "data stream",
                line_number=number,
            )

    if not records:
        raise GedcomParseError("a dataset must contain a header and a trailer")
    if records[0].tag != const.HEAD:
        raise GedcomParseError(
            f"a dataset must begin with a {const.HEAD} pseudo-structure, found "
            f"{records[0].tag}"
        )
    trailer = records[-1]
    if trailer.tag != const.TRLR:
        raise GedcomParseError(
            f"a dataset must end with a {const.TRLR} pseudo-structure, found "
            f"{trailer.tag}"
        )
    if trailer.text or trailer.children:
        raise GedcomParseError(
            f"{const.TRLR} must have no payload and no substructures"
        )

    return records
