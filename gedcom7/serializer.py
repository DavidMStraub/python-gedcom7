"""GEDCOM 7 serializer."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from . import const, grammar
from .exceptions import GedcomSerializeError
from .types import GedcomStructure

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import BinaryIO

_EOL = re.compile(r"\r\n|\r|\n")
_TAG = re.compile(grammar.tag)
_XREF = re.compile(grammar.xref)
_POINTER = re.compile(grammar.pointer)
_BANNED = re.compile(grammar.banned)
_TAGDEF = re.compile(grammar.tagdef)
_EXTTAG = re.compile(grammar.exttag)

_BOM = "\ufeff"


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


def _extension_tag(uri: str, taken: set[str]) -> str:
    """Invent an extension tag for a URI, avoiding every tag already spoken for.

    The last path segment or fragment of the URI usually reads as a name, so it
    is the basis for the tag; a URI that yields nothing usable falls back to a
    plain counter. A tag already in use is stepped past rather than reused, since
    a tag standing for two things resolves to neither on the way back in.
    """
    segment = re.split(r"[/#]", uri)[-1]
    base = "_" + re.sub(r"[^A-Z0-9_]", "", segment.upper())
    if _EXTTAG.fullmatch(base) is None:
        base = "_EXT"
    candidate, suffix = base, 1
    while candidate in taken:
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


def generate_schema(records: list[GedcomStructure]) -> None:
    """Add to HEAD the schema declarations dumps needs to write extension tags.

    Takes a whole dataset, HEAD included, and modifies it in place::

        records = gedcom7.loads(text)
        gedcom7.generate_schema(records)   # records[0] gains HEAD.SCHMA.TAG
        gedcom7.dumps(records)

    A tag held as a URI cannot be written until the header abbreviates it. Only
    HEAD changes; the URIs stay on their own structures for :func:`dumps` to
    substitute as it writes. Declarations already there are kept, so a second
    call does nothing.

    Raises :class:`~gedcom7.exceptions.GedcomSerializeError` if there is no HEAD,
    or if a tag is neither writable nor a URI that can be abbreviated.
    """
    head = next((record for record in records if record.tag == const.HEAD), None)
    if head is None:
        raise GedcomSerializeError(
            "a schema is declared in the HEAD pseudo-structure, and these "
            "records do not have one"
        )

    declared = _schema(records)
    # Every literal tag in the document is spoken for as well: were a generated
    # tag to collide with one, that structure would resolve to the extension's
    # URI when the stream was read back.
    taken = set(declared.values())
    undeclared: dict[str, None] = {}

    def visit(structure: GedcomStructure) -> None:
        if _TAG.fullmatch(structure.tag) is None:
            if structure.tag not in declared:
                undeclared.setdefault(structure.tag, None)
        else:
            taken.add(structure.tag)
        for child in structure.children:
            visit(child)

    for record in records:
        visit(record)

    if not undeclared:
        return

    schema = next((c for c in head.children if c.tag == const.SCHMA), None)
    if schema is None:
        schema = GedcomStructure(tag=const.SCHMA)
        schema.parent = head
        gedc = next(
            (i for i, c in enumerate(head.children) if c.tag == const.GEDC), None
        )
        head.children.insert(0 if gedc is None else gedc + 1, schema)

    # One tag per URI and one URI per tag: dumps picks arbitrarily between two
    # tags for a URI, and the parser refuses to resolve a tag that maps to two.
    for uri in undeclared:
        tag = _extension_tag(uri, taken)
        taken.add(tag)
        definition = f"{tag} {uri}"
        if _TAGDEF.fullmatch(definition) is None:
            raise GedcomSerializeError(
                f"{uri!r} cannot be declared in a schema: it is neither a tag "
                "this serializer can write nor a URI it can abbreviate"
            )
        schema.append_child(GedcomStructure(tag=const.TAG, text=definition))


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
    Use :func:`dump` to write to a file, so that the encoding and the line
    terminators are not altered on the way out.

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
