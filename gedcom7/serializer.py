"""GEDCOM 7 serializer."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from . import const, grammar
from .exceptions import GedcomSerializeError

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import BinaryIO

    from .types import GedcomStructure

_EOL = re.compile(r"\r\n|\r|\n")
_TAG = re.compile(grammar.tag)
_XREF = re.compile(grammar.xref)
_POINTER = re.compile(grammar.pointer)
_BANNED = re.compile(grammar.banned)
_TAGDEF = re.compile(grammar.tagdef)

_BOM = "﻿"


def _escape(linestr: str) -> str:
    """Escape a line string's leading "@" by doubling it.

    The inverse of the parser's unescaping: only a leading ``@`` is doubled, so
    ``@@@@`` is written as ``@@@@@``.
    """
    return "@" + linestr if linestr.startswith("@") else linestr


def _schema(records: Iterable[GedcomStructure]) -> dict[str, str]:
    """Map each URI declared by the header schema back to its extension tag."""
    uris: dict[str, str] = {}
    for record in records:
        if record.tag != const.HEAD:
            continue
        for schema in record.children:
            if schema.tag != const.SCHMA:
                continue
            for definition in schema.children:
                if definition.tag != const.TAG:
                    continue
                match = _TAGDEF.fullmatch(definition.text)
                # A schema should map only one tag to each URI; keep the first.
                if match is not None:
                    uris.setdefault(match.group("uri"), match.group("exttag"))
    return uris


def _lines(
    structure: GedcomStructure, level: int, uris: dict[str, str]
) -> Iterable[str]:
    """Yield the lines encoding a structure and everything below it."""
    tag = uris.get(structure.tag, structure.tag)
    if _TAG.fullmatch(tag) is None:
        hint = (
            " Add a matching HEAD.SCHMA.TAG definition to abbreviate it."
            if "://" in tag
            else ""
        )
        raise GedcomSerializeError(f"{tag!r} is not a valid tag.{hint}")

    parts = [str(level)]
    if structure.xref is not None and structure.xref != "":
        if level != 0:
            raise GedcomSerializeError(
                f"only records may have a cross-reference identifier, but {tag} "
                f"at level {level} has {structure.xref}"
            )
        if _XREF.fullmatch(structure.xref) is None or structure.xref == const.VOIDPTR:
            raise GedcomSerializeError(
                f"{structure.xref!r} is not a valid cross-reference identifier"
            )
        parts.append(structure.xref)
    parts.append(tag)

    if structure.pointer is not None and structure.pointer != "":
        if structure.text:
            raise GedcomSerializeError(
                f"{tag} has both a pointer and a text payload; a line value is "
                "one or the other"
            )
        if _POINTER.fullmatch(structure.pointer) is None:
            raise GedcomSerializeError(f"{structure.pointer!r} is not a valid pointer")
        parts.append(structure.pointer)
        yield " ".join(parts)
    else:
        # A payload containing line terminators is split across the structure's
        # own line and one CONT pseudo-structure per subsequent line.
        payload = _EOL.split(structure.text)
        if payload[0]:
            parts.append(_escape(payload[0]))
        yield " ".join(parts)
        for continuation in payload[1:]:
            yield (
                f"{level + 1} {const.CONT} {_escape(continuation)}"
                if continuation
                else f"{level + 1} {const.CONT}"
            )

    for child in structure.children:
        yield from _lines(child, level + 1, uris)


def dumps(
    records: Iterable[GedcomStructure],
    *,
    line_terminator: str = "\n",
    byte_order_mark: bool = True,
) -> str:
    """Serialize structures to a GEDCOM 7 data stream.

    Levels are derived from the structure tree, payloads containing line
    terminators are split into CONT pseudo-structures, and a leading "@" in a
    payload is escaped. Extension tags stored as URIs are abbreviated using the
    tag definitions in the header schema.

    The specification says a data stream should begin with U+FEFF, so a byte
    order mark is included by default; pass ``byte_order_mark=False`` to omit it.
    Write the result with ``encoding="utf-8"``, not ``"utf-8-sig"``.

    Raises :class:`~gedcom7.exceptions.GedcomSerializeError` if the structures
    cannot be encoded as conforming lines.
    """
    if line_terminator not in ("\n", "\r\n", "\r"):
        raise GedcomSerializeError(
            f"{line_terminator!r} is not a valid line terminator; "
            "use '\\n', '\\r\\n' or '\\r'"
        )

    records = list(records)
    uris = _schema(records)
    lines = [line for record in records for line in _lines(record, 0, uris)]

    string = "".join(line + line_terminator for line in lines)
    banned = _BANNED.search(string)
    if banned:
        raise GedcomSerializeError(
            f"banned character U+{ord(banned.group()):04X} in payload"
        )
    return (_BOM if byte_order_mark else "") + string


def dump(
    records: Iterable[GedcomStructure],
    fp: BinaryIO,
    *,
    line_terminator: str = "\n",
    byte_order_mark: bool = True,
) -> None:
    """Serialize structures to a binary file object.

    The file must be opened in binary mode, e.g. ``open(path, "wb")``. GEDCOM 7
    data streams are always UTF-8, and writing the bytes directly keeps text
    mode from re-encoding them or rewriting the line terminators.
    """
    data = dumps(
        records,
        line_terminator=line_terminator,
        byte_order_mark=byte_order_mark,
    ).encode("utf-8")
    try:
        fp.write(data)
    except TypeError:
        raise TypeError(
            'File must be opened in binary mode, e.g. use `open("my.ged", "wb")`'
        ) from None
