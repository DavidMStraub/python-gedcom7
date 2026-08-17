"""Report what is wrong with a dataset, using the tables the package already has.

Covers the checks that need no data beyond ``const.payloads``,
``const.substructures`` and ``const.GEDCOM_MONTHS``. Cardinality and
enumeration vocabularies are not among them: nothing here knows that an
individual may have one SEX, or that its payload is drawn from a fixed list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from . import cast, const, grammar, types

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

_TAG = re.compile(grammar.tag)
_TAGDEF = re.compile(grammar.tagdef)

# February is taken at its longest so the check does not turn on which calendar's
# leap rule applies; a day past these is wrong under either.
_DAYS_IN_MONTH = {
    "JAN": 31, "FEB": 29, "MAR": 31, "APR": 30, "MAY": 31, "JUN": 30,
    "JUL": 31, "AUG": 31, "SEP": 30, "OCT": 31, "NOV": 30, "DEC": 31,
}  # fmt: skip

# The months above name the Gregorian and Julian year. Other calendars have their
# own, which these tables do not carry, so their dates are left alone.
_MONTH_CALENDARS = (None, "GREGORIAN", "JULIAN")


@dataclass
class Error:
    """One problem, and the path through the tree to where it was found."""

    category: str
    message: str
    path: str
    structure: types.GedcomStructure | None = field(
        default=None, repr=False, compare=False
    )


def validate(records: Iterable[types.GedcomStructure]) -> list[Error]:
    """Report every problem in a dataset, rather than raising at the first.

    ::

        for error in gedcom7.validate(records):
            print(error.category, error.path, error.message)

    An empty list means the dataset passes the checks this can make; it does not
    mean the dataset conforms, since cardinality and enumeration values are not
    checked. See :mod:`gedcom7.validate` for what that leaves out.
    """
    records = list(records)
    errors: list[Error] = []
    _check_dataset(records, errors)
    xrefs = {r.xref: r for r in records if r.xref}
    declared = _check_schema(records, errors)
    for record in records:
        _check_structure(record, xrefs, declared, errors)
    return errors


def _path(structure: types.GedcomStructure) -> str:
    """Name a structure by the tags leading down to it from its record."""
    parts = []
    node: types.GedcomStructure | None = structure
    while node is not None:
        parts.append(f"{node.xref} {node.tag}" if node.xref else node.tag)
        node = node.parent
    return " > ".join(reversed(parts))


def _report(
    errors: list[Error], category: str, message: str, structure: types.GedcomStructure
) -> None:
    errors.append(Error(category, message, _path(structure), structure))


def _check_dataset(records: list[types.GedcomStructure], errors: list[Error]) -> None:
    """Check the shape of the stream and the records at its top level."""
    if not records:
        errors.append(Error("document-shape", "a dataset has no records", ""))
        return
    for tag, where, found in (
        (const.HEAD, "begin", records[0]),
        (const.TRLR, "end", records[-1]),
    ):
        count = sum(1 for r in records if r.tag == tag)
        if count != 1:
            _report(
                errors,
                "document-shape",
                f"a dataset has one {tag} pseudo-structure, not {count}",
                found,
            )
        elif found.tag != tag:
            _report(
                errors,
                "document-shape",
                f"a dataset must {where} with {tag}, not {found.tag}",
                found,
            )

    seen: set[str] = set()
    for record in records:
        if record.tag in (const.HEAD, const.TRLR):
            continue
        if not record.xref:
            _report(
                errors, "document-shape", "a record needs a cross-reference", record
            )
        elif record.xref in seen:
            _report(errors, "duplicate-xref", f"{record.xref} is used twice", record)
        else:
            seen.add(record.xref)
        if (
            _TAG.fullmatch(record.tag)
            and not record.tag.startswith("_")
            and record.tag not in const.substructures[""]
        ):
            _report(
                errors,
                "document-shape",
                f"{record.tag} is not a record type",
                record,
            )


def _check_schema(
    records: list[types.GedcomStructure], errors: list[Error]
) -> set[str]:
    """Check that the header maps each tag to one URI and back, and list the URIs."""
    by_uri: dict[str, set[str]] = {}
    by_tag: dict[str, set[str]] = {}
    origin: dict[str, types.GedcomStructure] = {}
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
                if match is None:
                    _report(
                        errors,
                        "malformed-payload",
                        f"{definition.text!r} is not a tag definition",
                        definition,
                    )
                    continue
                tag, uri = match.group("exttag"), match.group("uri")
                by_uri.setdefault(uri, set()).add(tag)
                by_tag.setdefault(tag, set()).add(uri)
                origin.setdefault(uri, definition)
                origin.setdefault(tag, definition)

    for uri, tags in by_uri.items():
        if len(tags) > 1:
            _report(
                errors,
                "schema-conflict",
                f"{uri} is abbreviated by {' and '.join(sorted(tags))}, so "
                "which one is written is arbitrary",
                origin[uri],
            )
    for tag, uris in by_tag.items():
        if len(uris) > 1:
            _report(
                errors,
                "schema-conflict",
                f"{tag} stands for {' and '.join(sorted(uris))}, so it resolves "
                "to neither when read back",
                origin[tag],
            )
    return set(by_uri)


def _check_structure(
    structure: types.GedcomStructure,
    xrefs: dict[str, types.GedcomStructure],
    declared: set[str],
    errors: list[Error],
) -> None:
    """Check one structure and everything below it."""
    type_id = structure.type_id
    if _TAG.fullmatch(structure.tag) is None and structure.tag not in declared:
        _report(
            errors,
            "undeclared-extension",
            f"{structure.tag} has no HEAD.SCHMA.TAG declaration, so it cannot "
            "be written",
            structure,
        )
    _check_substructure(structure, errors)
    if type_id is not None:
        payload = const.payloads.get(type_id)
        if payload is not None:
            _check_payload_kind(structure, payload, errors)
            # Only one of these can say anything useful. Where the payload is of
            # the wrong kind entirely, chasing its pointer or casting its text
            # would report the same mistake a second time.
            if payload.startswith("@<"):
                _check_pointer(structure, payload, xrefs, errors)
            else:
                _check_payload_value(structure, type_id, errors)
    for child in structure.children:
        _check_structure(child, xrefs, declared, errors)


def _check_substructure(structure: types.GedcomStructure, errors: list[Error]) -> None:
    """Check that a standard tag is one its superstructure may contain."""
    parent = structure.parent
    if parent is None or parent.type_id is None:
        # a record, or a substructure of an extension, whose content the
        # extension defines rather than the specification
        return
    if structure.tag.startswith("_") or _TAG.fullmatch(structure.tag) is None:
        return
    if structure.tag not in const.substructures.get(parent.type_id, {}):
        _report(
            errors,
            "unknown-substructure",
            f"{parent.tag} has no {structure.tag} substructure",
            structure,
        )


def _check_payload_kind(
    structure: types.GedcomStructure, payload: str, errors: list[Error]
) -> None:
    """Check that the payload is of the kind the structure type carries."""
    if payload.startswith("@<"):
        if structure.text:
            _report(
                errors,
                "misplaced-payload",
                "this points at a record, so its text belongs in its pointer",
                structure,
            )
        elif not structure.pointer:
            _report(
                errors,
                "misplaced-payload",
                "this points at a record but has no pointer",
                structure,
            )
    elif payload == "":
        if structure.text or structure.pointer:
            _report(errors, "misplaced-payload", "this takes no payload", structure)
    elif structure.pointer:
        _report(
            errors,
            "misplaced-payload",
            "this carries a value, so its pointer belongs in its text",
            structure,
        )


def _check_pointer(
    structure: types.GedcomStructure,
    payload: str,
    xrefs: dict[str, types.GedcomStructure],
    errors: list[Error],
) -> None:
    """Check that a pointer reaches a record, and one of the right type."""
    if not structure.pointer or structure.pointer == const.VOIDPTR:
        return
    target = xrefs.get(structure.pointer)
    if target is None:
        _report(
            errors,
            "dangling-pointer",
            f"{structure.pointer} is not a record in this dataset",
            structure,
        )
    else:
        wanted = payload[2:-2]
        if target.type_id != wanted:
            _report(
                errors,
                "pointer-target-type",
                f"{structure.pointer} is a {target.tag} record, but this points "
                f"at {wanted.rsplit('/', 1)[-1]}",
                structure,
            )


def _dates(value: object) -> Iterator[types.Date | types.DateExact]:
    """Yield every date inside a value, however it is wrapped."""
    if isinstance(value, types.Date | types.DateExact):
        yield value
    elif isinstance(value, types.DateApprox):
        yield from _dates(value.date)
    elif isinstance(value, types.DateRange):
        for part in (value.start, value.end):
            yield from _dates(part)
    elif isinstance(value, types.DatePeriod):
        for part in (value.from_, value.to):
            yield from _dates(part)


def _check_payload_value(
    structure: types.GedcomStructure, type_id: str, errors: list[Error]
) -> None:
    """Check that the payload casts, and that any date in it could exist."""
    if not structure.text:
        return
    try:
        value = cast.cast_value(structure.text, type_id)
    except ValueError as exc:
        _report(errors, "malformed-payload", str(exc), structure)
        return
    for date in _dates(value):
        calendar = getattr(date, "calendar", None)
        if calendar not in _MONTH_CALENDARS or date.month is None:
            continue
        if date.month not in _DAYS_IN_MONTH:
            _report(errors, "invalid-date", f"{date.month} is not a month", structure)
        elif date.day is not None and not 1 <= date.day <= _DAYS_IN_MONTH[date.month]:
            _report(
                errors,
                "invalid-date",
                f"{date.month} has no day {date.day}",
                structure,
            )
