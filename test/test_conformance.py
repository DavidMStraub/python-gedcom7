"""Conformance tests against the FamilySearch GEDCOM 7 specification.

Each test cites the requirement it covers. Cases that the specification
prohibits must raise, not be silently skipped or reinterpreted.
"""

import pytest

import gedcom7
from gedcom7 import GedcomParseError

HEAD = "0 HEAD\n1 GEDC\n2 VERS 7.0\n"
TRLR = "0 TRLR\n"


def parse(
    body: str = "", *, head: str = HEAD, trlr: str = TRLR
) -> list[gedcom7.types.GedcomStructure]:
    """Parse a dataset built from a header, a body, and a trailer."""
    return gedcom7.loads(head + body + trlr)


# --------------------------------------------------------------------------
# Characters and line terminators
# --------------------------------------------------------------------------


@pytest.mark.parametrize("eol", ["\n", "\r\n", "\r"])
def test_line_terminators(eol: str) -> None:
    """EOL = %x0D [%x0A] / %x0A -- CR-LF, CR, or LF are all valid."""
    text = (HEAD + "0 @I1@ INDI\n1 SEX M\n" + TRLR).replace("\n", eol)
    records = gedcom7.loads(text)
    assert len(records) == 3
    assert records[1].children[0].text == "M"


def test_byte_order_mark_is_ignored() -> None:
    """The data stream should begin with U+FEFF, which carries no meaning."""
    records = gedcom7.loads("﻿" + HEAD + TRLR)
    assert records[0].tag == "HEAD"


def test_final_line_without_eol_is_kept() -> None:
    """A last line lacking its terminator must not be silently dropped."""
    records = gedcom7.loads(HEAD + "0 TRLR")
    assert records[-1].tag == "TRLR"


@pytest.mark.parametrize("char", ["\x00", "\x0b", "\x1f", "\x7f", "\x80", "\x9f"])
def test_banned_characters_rejected(char: str) -> None:
    """Banned characters must not appear anywhere within a data stream."""
    with pytest.raises(GedcomParseError, match="banned character"):
        parse(f"0 @I1@ INDI\n1 NOTE bad{char}char\n")


@pytest.mark.parametrize("char", ["\t", "é", "😀"])
def test_permitted_characters_accepted(char: str) -> None:
    """Tab and astral-plane characters are valid payload content."""
    records = parse(f"0 @I1@ INDI\n1 NOTE ok{char}here\n")
    assert records[1].children[0].text == f"ok{char}here"


# --------------------------------------------------------------------------
# Line grammar
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "1 NOTE @invalid",  # matches neither pointer nor lineStr
        "01 NAME John /Doe/",  # Level = "0" / nonzero *DIGIT, no leading zeros
        "  1 NAME John /Doe/",  # leading space prohibited since 7.0
        "1  NAME John /Doe/",  # a single delimiter only between components
        "1",  # no tag
        "NAME John /Doe/",  # no level
        "1 name john",  # tags are upper case
    ],
)
def test_malformed_lines_rejected(line: str) -> None:
    """A line not matching production Line must raise, not be skipped."""
    with pytest.raises(GedcomParseError, match="malformed line"):
        parse(f"0 @I1@ INDI\n{line}\n")


def test_blank_line_rejected() -> None:
    """Blank lines were removed from the format in 7.0."""
    with pytest.raises(GedcomParseError, match="malformed line"):
        parse("0 @I1@ INDI\n\n1 SEX M\n")


def test_error_reports_line_number() -> None:
    """Errors identify the offending line."""
    with pytest.raises(GedcomParseError) as excinfo:
        parse("0 @I1@ INDI\n1 NOTE @invalid\n")
    assert excinfo.value.line_number == 5
    assert excinfo.value.line == "1 NOTE @invalid"


def test_two_spaces_after_tag_is_payload() -> None:
    """If the tag is followed by 2 spaces, the second is part of the payload."""
    records = parse("0 @I1@ INDI\n1 NOTE  leading space kept\n")
    assert records[1].children[0].text == " leading space kept"


def test_trailing_space_preserved() -> None:
    """All characters in a payload must be preserved, including trailing spaces."""
    records = parse("0 @I1@ INDI\n1 NOTE trailing \n")
    assert records[1].children[0].text == "trailing "


# --------------------------------------------------------------------------
# Escaping of "@"
# --------------------------------------------------------------------------


def test_leading_at_is_unescaped() -> None:
    """A leading "@" in a line string is doubled and must be undoubled."""
    records = parse(
        "0 @I1@ INDI\n"
        "1 NOTE me@example.com is my email\n"
        "2 CONT @@me and @I are my social media handles\n"
    )
    assert records[1].children[0].text == (
        "me@example.com is my email\n@me and @I are my social media handles"
    )


def test_only_the_leading_at_is_escaped() -> None:
    """Later "@" stand for themselves: @@@@@ decodes to @@@@."""
    records = parse("0 @I1@ INDI\n1 NOTE @@@@@ has four @ characters\n")
    assert records[1].children[0].text == "@@@@ has four @ characters"


def test_interior_at_untouched() -> None:
    """An "@" that is not first is never doubled."""
    records = parse("0 @I1@ INDI\n1 NOTE a@@b\n")
    assert records[1].children[0].text == "a@@b"


# --------------------------------------------------------------------------
# Levels
# --------------------------------------------------------------------------


def test_level_may_not_skip() -> None:
    """A line is a substructure of the nearest preceding line one level up."""
    with pytest.raises(GedcomParseError, match="at most one level deeper"):
        parse("0 @I1@ INDI\n2 FOO bar\n")


def test_level_jump_does_not_reparent_across_records() -> None:
    """A level jump must not silently attach to the previous record."""
    with pytest.raises(GedcomParseError, match="at most one level deeper"):
        parse("0 @I1@ INDI\n1 BIRT\n2 DATE 1 JAN 2000\n0 @I2@ INDI\n2 FOO bar\n")


def test_dataset_must_start_at_level_zero() -> None:
    """The first line of a dataset encodes a record."""
    with pytest.raises(GedcomParseError, match="must begin with a level 0 line"):
        gedcom7.loads("1 SEX M\n")


def test_deep_nesting() -> None:
    """Levels beyond 9 are permitted; there is no depth limit."""
    body = "0 @I1@ INDI\n" + "".join(f"{i} _L{i}\n" for i in range(1, 13))
    records = gedcom7.loads(HEAD + body[:-1] + " x\n" + TRLR)
    node = records[1]
    for _ in range(12):
        node = node.children[0]
    assert node.text == "x"


# --------------------------------------------------------------------------
# Cross-reference identifiers and pointers
# --------------------------------------------------------------------------


def test_pointer_and_voidptr() -> None:
    """Pointers are encoded as the xref of the pointed-to structure."""
    records = parse("0 @I1@ INDI\n1 ALIA @I1@\n1 FAMC @VOID@\n")
    indi = records[1]
    assert indi.xref == "@I1@"
    assert indi.children[0].pointer == "@I1@"
    assert indi.children[1].pointer == "@VOID@"


def test_unresolved_pointer_rejected() -> None:
    """A pointer must match an xref of a structure within the document."""
    with pytest.raises(GedcomParseError, match="matches no cross-reference"):
        parse("0 @I1@ INDI\n1 ALIA @I9@\n")


def test_forward_pointer_allowed() -> None:
    """A pointer may precede the record it points to."""
    records = parse("0 @I1@ INDI\n1 ALIA @I2@\n0 @I2@ INDI\n1 SEX F\n")
    assert records[1].children[0].pointer == "@I2@"


def test_duplicate_xref_rejected() -> None:
    """Each cross-reference identifier must be unique within a document."""
    with pytest.raises(GedcomParseError, match="duplicate cross-reference"):
        parse("0 @I1@ INDI\n1 SEX M\n0 @I1@ INDI\n1 SEX F\n")


def test_substructure_may_not_have_xref() -> None:
    """A substructure or pseudo-structure must not have an xref."""
    with pytest.raises(GedcomParseError, match="only records may have"):
        parse("0 @I1@ INDI\n1 @X1@ NOTE hi\n")


def test_voidptr_may_not_be_an_xref() -> None:
    """Xref is "but not @VOID@"."""
    with pytest.raises(GedcomParseError, match="must not be used as a cross-ref"):
        parse("0 @VOID@ INDI\n1 SEX M\n")


# --------------------------------------------------------------------------
# CONT pseudo-structures
# --------------------------------------------------------------------------


def test_cont_multiline_payload() -> None:
    """Line terminators in a payload are encoded as CONT continuations."""
    records = parse(
        "0 @I1@ INDI\n"
        "1 NOTE This is a note field that\n"
        "2 CONT   spans four lines.\n"
        "2 CONT\n"
        "2 CONT (the third line was blank)\n"
    )
    assert records[1].children[0].text == (
        "This is a note field that\n  spans four lines.\n\n(the third line was blank)"
    )


def test_cont_is_not_a_substructure() -> None:
    """Line continuations are not part of the substructure collection."""
    records = parse("0 @I1@ INDI\n1 NOTE a\n2 CONT b\n")
    assert records[1].children[0].children == []


def test_orphan_cont_rejected() -> None:
    """A CONT must continue the line it immediately follows."""
    with pytest.raises(GedcomParseError, match="CONT must immediately follow"):
        gedcom7.loads("2 CONT orphan\n")


def test_cont_after_other_substructure_rejected() -> None:
    """CONT must come before any other substructure."""
    with pytest.raises(GedcomParseError, match="CONT must immediately follow"):
        parse("0 @I1@ INDI\n1 NOTE a\n2 LANG en\n2 CONT b\n")


def test_cont_at_wrong_level_rejected() -> None:
    """A CONT is one level deeper than the line it continues."""
    with pytest.raises(GedcomParseError, match="CONT must immediately follow"):
        parse("0 @I1@ INDI\n1 NOTE a\n1 CONT b\n")


def test_cont_on_pointer_payload_rejected() -> None:
    """A pointer payload has no continuation."""
    with pytest.raises(GedcomParseError, match="cannot continue a pointer"):
        parse("0 @I1@ INDI\n1 ALIA @I1@\n2 CONT b\n")


# --------------------------------------------------------------------------
# Header, trailer and schema
# --------------------------------------------------------------------------


def test_missing_header_rejected() -> None:
    """Every dataset must begin with a header pseudo-structure."""
    with pytest.raises(GedcomParseError, match="must begin with a HEAD"):
        gedcom7.loads("0 @I1@ INDI\n1 SEX M\n" + TRLR)


def test_missing_trailer_rejected() -> None:
    """Every dataset must end with a trailer pseudo-structure."""
    with pytest.raises(GedcomParseError, match="must end with a TRLR"):
        gedcom7.loads(HEAD + "0 @I1@ INDI\n1 SEX M\n")


def test_empty_dataset_rejected() -> None:
    """An empty data stream is not a dataset."""
    with pytest.raises(GedcomParseError, match="header and a trailer"):
        gedcom7.loads("")


def test_trailer_may_not_have_substructures() -> None:
    """The trailer cannot contain substructures."""
    with pytest.raises(GedcomParseError, match="no payload and no substructures"):
        gedcom7.loads(HEAD + "0 TRLR\n1 NOTE nope\n")


def test_documented_extension_tag_resolves_to_uri() -> None:
    """A documented extension tag is an abbreviation for its URI."""
    records = gedcom7.loads(
        "0 HEAD\n1 SCHMA\n2 TAG _SKYPEID http://xmlns.com/foaf/0.1/skypeID\n"
        "1 GEDC\n2 VERS 7.0\n0 @I0@ INDI\n1 _SKYPEID example.person\n" + TRLR
    )
    assert records[1].children[0].tag == "http://xmlns.com/foaf/0.1/skypeID"


def test_undocumented_extension_tag_kept() -> None:
    """An extension tag with no schema entry keeps its tag."""
    records = parse("0 @I1@ INDI\n1 _UNDOCUMENTED x\n")
    assert records[1].children[0].tag == "_UNDOCUMENTED"


def test_ambiguous_extension_tag_left_unresolved() -> None:
    """A tag the schema maps to several URIs cannot be disambiguated here."""
    records = gedcom7.loads(
        "0 HEAD\n1 SCHMA\n"
        "2 TAG _LOC https://example.com/LocationRecord\n"
        "2 TAG _LOC https://example.com/LocationPointer\n"
        "1 GEDC\n2 VERS 7.0\n0 @P1@ _LOC\n1 NAME x\n" + TRLR
    )
    assert records[1].tag == "_LOC"


def test_malformed_tag_definition_rejected() -> None:
    """A tag definition is an extension tag, a space, and a URI."""
    with pytest.raises(GedcomParseError, match="tag definition must be"):
        gedcom7.loads("0 HEAD\n1 SCHMA\n2 TAG _NOSPACE\n1 GEDC\n2 VERS 7.0\n" + TRLR)


def test_tag_outside_schema_is_not_a_definition() -> None:
    """TAG is only a tag definition as HEAD.SCHMA.TAG."""
    records = parse("0 @I1@ INDI\n1 _X\n2 TAG _Y http://example.com/y\n")
    assert records[1].children[0].children[0].tag == "TAG"
