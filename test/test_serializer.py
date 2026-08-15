"""Tests for serializing structures back to a GEDCOM 7 data stream."""

import io
import pathlib

import pytest

import gedcom7
from gedcom7 import GedcomSerializeError, types

HEAD = "0 HEAD\n1 GEDC\n2 VERS 7.0\n"
TRLR = "0 TRLR\n"


def roundtrip(text: str) -> str:
    """Parse and re-serialize, without a byte order mark."""
    return gedcom7.dumps(gedcom7.loads(text), byte_order_mark=False)


# --------------------------------------------------------------------------
# Round-tripping
# --------------------------------------------------------------------------


def test_maximal_roundtrips_byte_for_byte() -> None:
    """The official maximal70.ged must survive a parse and re-serialize exactly."""
    filename = pathlib.Path(__file__).parent / "data" / "maximal70.ged"
    original = filename.read_text(encoding="utf-8")
    assert gedcom7.dumps(gedcom7.loads(original)) == original


def test_maximal_roundtrips_as_a_tree() -> None:
    """Re-parsing the serialized form yields an equal structure tree."""
    filename = pathlib.Path(__file__).parent / "data" / "maximal70.ged"
    records = gedcom7.loads(filename.read_text(encoding="utf-8"))
    assert gedcom7.loads(gedcom7.dumps(records)) == records


@pytest.mark.parametrize(
    "body",
    [
        "0 @I1@ INDI\n1 SEX M\n",
        "0 @I1@ INDI\n1 BIRT\n2 DATE 1 JAN 2000\n3 TIME 14:30\n",
        "0 @I1@ INDI\n1 ALIA @VOID@\n",
        "0 @I1@ INDI\n1 NOTE line one\n2 CONT line two\n2 CONT\n2 CONT line four\n",
        "0 @I1@ INDI\n1 NOTE @@leading at\n",
        "0 @I1@ INDI\n1 NOTE  leading space\n",
        "0 @I1@ INDI\n1 NOTE trailing space \n",
        "0 @N1@ SNOTE shared note\n1 LANG en\n",
    ],
)
def test_body_roundtrips(body: str) -> None:
    """Serializing is the exact inverse of parsing."""
    text = HEAD + body + TRLR
    assert roundtrip(text) == text


def test_extension_tag_roundtrips_through_the_schema() -> None:
    """A tag stored as a URI is abbreviated using the header schema."""
    text = (
        "0 HEAD\n1 SCHMA\n2 TAG _FOO http://example.com/foo\n1 GEDC\n2 VERS 7.0\n"
        "0 @I1@ INDI\n1 _FOO 23\n" + TRLR
    )
    records = gedcom7.loads(text)
    # the parser resolved the tag to its URI
    assert records[1].children[0].tag == "http://example.com/foo"
    assert roundtrip(text) == text


# --------------------------------------------------------------------------
# Encoding details
# --------------------------------------------------------------------------


def test_byte_order_mark_included_by_default() -> None:
    """The specification says a data stream should begin with U+FEFF."""
    out = gedcom7.dumps(gedcom7.loads(HEAD + TRLR))
    assert out.startswith("\ufeff")
    assert gedcom7.dumps(gedcom7.loads(HEAD + TRLR), byte_order_mark=False) == (
        HEAD + TRLR
    )


@pytest.mark.parametrize("eol", ["\n", "\r\n", "\r"])
def test_line_terminator(eol: str) -> None:
    """Any of the three permitted terminators may be written."""
    records = gedcom7.loads(HEAD + "0 @I1@ INDI\n1 SEX M\n" + TRLR)
    out = gedcom7.dumps(records, line_terminator=eol, byte_order_mark=False)
    assert out == (HEAD + "0 @I1@ INDI\n1 SEX M\n" + TRLR).replace("\n", eol)
    # and the result is still readable
    assert gedcom7.loads(out) == records


def test_invalid_line_terminator_rejected() -> None:
    """Only CR, LF and CR-LF are line terminators."""
    with pytest.raises(GedcomSerializeError, match="not a valid line terminator"):
        gedcom7.dumps(gedcom7.loads(HEAD + TRLR), line_terminator="\n\n")


def test_multiline_payload_is_split_into_cont() -> None:
    """A payload containing line terminators becomes CONT continuations."""
    records = gedcom7.loads(HEAD + "0 @I1@ INDI\n1 NOTE a\n" + TRLR)
    records[1].children[0].text = "a\nb\n\nc"
    out = gedcom7.dumps(records, byte_order_mark=False)
    assert "1 NOTE a\n2 CONT b\n2 CONT\n2 CONT c\n" in out
    assert gedcom7.loads(out)[1].children[0].text == "a\nb\n\nc"


def test_empty_payload_writes_no_line_value() -> None:
    """Empty and missing payloads are both written with no trailing space."""
    records = gedcom7.loads(HEAD + "0 @O1@ OBJE\n1 FILE\n2 FORM image/jpeg\n" + TRLR)
    out = gedcom7.dumps(records, byte_order_mark=False)
    assert "\n1 FILE\n" in out


def test_leading_at_is_escaped() -> None:
    """A leading "@" must be doubled; later ones must not."""
    records = gedcom7.loads(HEAD + "0 @I1@ INDI\n1 NOTE x\n" + TRLR)
    note = records[1].children[0]

    note.text = "@me and @I"
    assert "1 NOTE @@me and @I\n" in gedcom7.dumps(records, byte_order_mark=False)

    note.text = "@@@@"
    out = gedcom7.dumps(records, byte_order_mark=False)
    assert "1 NOTE @@@@@\n" in out
    assert gedcom7.loads(out)[1].children[0].text == "@@@@"

    note.text = "a@b"
    assert "1 NOTE a@b\n" in gedcom7.dumps(records, byte_order_mark=False)


def test_dump_writes_to_a_binary_file_object() -> None:
    """dump() mirrors dumps() but writes UTF-8 bytes to a stream."""
    text = HEAD + "0 @I1@ INDI\n1 SEX M\n" + TRLR
    records = gedcom7.loads(text)
    buffer = io.BytesIO()
    gedcom7.dump(records, buffer, byte_order_mark=False)
    assert buffer.getvalue() == text.encode("utf-8")


def test_load_reads_a_binary_file_object() -> None:
    """load() mirrors loads() but reads UTF-8 bytes from a stream."""
    text = HEAD + "0 @I1@ INDI\n1 SEX M\n" + TRLR
    buffer = io.BytesIO(text.encode("utf-8"))
    assert gedcom7.load(buffer) == gedcom7.loads(text)


def test_text_mode_is_rejected() -> None:
    """Text streams would re-encode and rewrite terminators, so they are refused."""
    records = gedcom7.loads(HEAD + TRLR)
    with pytest.raises(TypeError, match="binary mode"):
        gedcom7.dump(records, io.StringIO())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="binary mode"):
        gedcom7.load(io.StringIO(HEAD + TRLR))  # type: ignore[arg-type]


def test_dump_writes_nothing_to_a_text_stream() -> None:
    """The type error must arrive before any output is produced."""
    buffer = io.StringIO()
    with pytest.raises(TypeError):
        gedcom7.dump(gedcom7.loads(HEAD + TRLR), buffer)  # type: ignore[arg-type]
    assert buffer.getvalue() == ""


def test_invalid_utf8_rejected() -> None:
    """GEDCOM 7 data streams are always UTF-8."""
    with pytest.raises(gedcom7.GedcomParseError, match="not valid UTF-8"):
        gedcom7.load(io.BytesIO(b"0 HEAD\n1 NOTE \xff\xfe\n0 TRLR\n"))


@pytest.mark.parametrize("eol", ["\n", "\r\n", "\r"])
def test_file_roundtrip_preserves_terminators(eol: str, tmp_path: pathlib.Path) -> None:
    """Going through the filesystem must not rewrite the line terminators.

    Text mode would translate "\\n" to os.linesep on Windows, turning an
    explicit "\\r\\n" into "\\r\\r\\n" and producing a file this library rejects.
    """
    source = (HEAD + "0 @I1@ INDI\n1 SEX M\n" + TRLR).replace("\n", eol)
    path = tmp_path / "out.ged"

    with open(path, "wb") as f:
        gedcom7.dump(
            gedcom7.loads(source), f, line_terminator=eol, byte_order_mark=False
        )

    assert path.read_bytes() == source.encode("utf-8")
    with open(path, "rb") as f:
        assert gedcom7.load(f) == gedcom7.loads(source)


def test_official_file_roundtrips_through_the_filesystem(
    tmp_path: pathlib.Path,
) -> None:
    """load() and dump() reproduce a real file byte for byte."""
    source = pathlib.Path(__file__).parent / "data" / "maximal70.ged"
    path = tmp_path / "out.ged"
    with open(source, "rb") as f:
        records = gedcom7.load(f)
    with open(path, "wb") as f:
        gedcom7.dump(records, f)
    assert path.read_bytes() == source.read_bytes()


def test_levels_derive_from_the_tree() -> None:
    """Levels come from the structure tree, not from any stored value."""
    head = types.GedcomStructure(tag="HEAD", pointer=None, text="", xref=None)
    gedc = types.GedcomStructure(tag="GEDC", pointer=None, text="", xref=None)
    vers = types.GedcomStructure(tag="VERS", pointer=None, text="7.0", xref=None)
    head.append_child(gedc)
    gedc.append_child(vers)
    trlr = types.GedcomStructure(tag="TRLR", pointer=None, text="", xref=None)
    assert gedcom7.dumps([head, trlr], byte_order_mark=False) == HEAD + TRLR


# --------------------------------------------------------------------------
# Rejected input
# --------------------------------------------------------------------------


def test_unabbreviated_uri_tag_rejected() -> None:
    """A URI tag with no schema definition cannot be written as a tag."""
    records = gedcom7.loads(HEAD + "0 @I1@ INDI\n1 SEX M\n" + TRLR)
    records[1].children[0].tag = "http://example.com/unknown"
    with pytest.raises(GedcomSerializeError, match="HEAD.SCHMA.TAG"):
        gedcom7.dumps(records)


def test_invalid_tag_rejected() -> None:
    """Tags must match stdTag or extTag."""
    records = gedcom7.loads(HEAD + "0 @I1@ INDI\n1 SEX M\n" + TRLR)
    records[1].children[0].tag = "lower"
    with pytest.raises(GedcomSerializeError, match="not a valid tag"):
        gedcom7.dumps(records)


def test_xref_on_substructure_rejected() -> None:
    """Only records may carry a cross-reference identifier."""
    records = gedcom7.loads(HEAD + "0 @I1@ INDI\n1 SEX M\n" + TRLR)
    records[1].children[0].xref = "@X1@"
    with pytest.raises(GedcomSerializeError, match="only records may have"):
        gedcom7.dumps(records)


def test_voidptr_as_xref_rejected() -> None:
    """@VOID@ is not a cross-reference identifier."""
    records = gedcom7.loads(HEAD + "0 @I1@ INDI\n1 SEX M\n" + TRLR)
    records[1].xref = "@VOID@"
    with pytest.raises(GedcomSerializeError, match="not a valid cross-reference"):
        gedcom7.dumps(records)


def test_pointer_and_text_together_rejected() -> None:
    """A line value is a pointer or a line string, not both."""
    records = gedcom7.loads(HEAD + "0 @I1@ INDI\n1 ALIA @I1@\n" + TRLR)
    records[1].children[0].text = "oops"
    with pytest.raises(GedcomSerializeError, match="both a pointer and a text"):
        gedcom7.dumps(records)


def test_invalid_pointer_rejected() -> None:
    """Pointers must match the pointer production."""
    records = gedcom7.loads(HEAD + "0 @I1@ INDI\n1 ALIA @I1@\n" + TRLR)
    records[1].children[0].pointer = "@not a pointer@"
    with pytest.raises(GedcomSerializeError, match="not a valid pointer"):
        gedcom7.dumps(records)


def test_banned_character_in_payload_rejected() -> None:
    """Banned characters must not be written into a data stream."""
    records = gedcom7.loads(HEAD + "0 @I1@ INDI\n1 NOTE fine\n" + TRLR)
    records[1].children[0].text = "bad\x7fchar"
    with pytest.raises(GedcomSerializeError, match="banned character"):
        gedcom7.dumps(records)


# --------------------------------------------------------------------------
# Schema generation
# --------------------------------------------------------------------------

FOAF = "http://xmlns.com/foaf/0.1/skypeID"


def extension_record(*uris: str) -> types.GedcomStructure:
    """An individual carrying one substructure per extension URI."""
    individual = types.GedcomStructure(tag="INDI", xref="@I1@")
    for uri in uris:
        individual.append_child(types.GedcomStructure(tag=uri, text="payload"))
    return individual


def header(*children: types.GedcomStructure) -> types.GedcomStructure:
    head = types.GedcomStructure(tag="HEAD")
    gedc = types.GedcomStructure(tag="GEDC")
    gedc.append_child(types.GedcomStructure(tag="VERS", text="7.0"))
    head.append_child(gedc)
    for child in children:
        head.append_child(child)
    return head


def test_generate_schema_declares_an_undeclared_uri() -> None:
    """dumps refuses a URI tag it has no abbreviation for; this supplies one."""
    records = [header(), extension_record(FOAF), types.GedcomStructure(tag="TRLR")]
    with pytest.raises(GedcomSerializeError, match="not a valid tag"):
        gedcom7.dumps(records)

    gedcom7.generate_schema(records)
    assert gedcom7.dumps(records, byte_order_mark=False) == (
        "0 HEAD\n1 GEDC\n2 VERS 7.0\n1 SCHMA\n2 TAG _SKYPEID " + FOAF + "\n"
        "0 @I1@ INDI\n1 _SKYPEID payload\n0 TRLR\n"
    )


def test_generate_schema_round_trips_the_uri() -> None:
    """The abbreviation has to resolve back to the URI it stood for."""
    records = [header(), extension_record(FOAF), types.GedcomStructure(tag="TRLR")]
    gedcom7.generate_schema(records)
    reparsed = gedcom7.loads(gedcom7.dumps(records))
    assert reparsed[1].children[0].tag == FOAF


def test_generate_schema_keeps_declarations_already_made() -> None:
    """A tag chosen by hand is reused, not replaced."""
    schema = types.GedcomStructure(tag="SCHMA")
    schema.append_child(types.GedcomStructure(tag="TAG", text=f"_MINE {FOAF}"))
    records = [
        header(schema),
        extension_record(FOAF),
        types.GedcomStructure(tag="TRLR"),
    ]
    gedcom7.generate_schema(records)
    definitions = [c.text for c in records[0].children[1].children]
    assert definitions == [f"_MINE {FOAF}"]
    assert "1 _MINE payload" in gedcom7.dumps(records)


def test_generate_schema_is_idempotent() -> None:
    """Running it twice must not declare the same URI a second time."""
    records = [header(), extension_record(FOAF), types.GedcomStructure(tag="TRLR")]
    gedcom7.generate_schema(records)
    first = gedcom7.dumps(records)
    gedcom7.generate_schema(records)
    assert gedcom7.dumps(records) == first


def test_generate_schema_gives_each_uri_one_tag() -> None:
    """One URI on many structures is declared once."""
    records = [
        header(),
        extension_record(FOAF, FOAF, FOAF),
        types.GedcomStructure(tag="TRLR"),
    ]
    gedcom7.generate_schema(records)
    assert len(records[0].children[1].children) == 1


def test_generate_schema_avoids_colliding_with_another_uris_tag() -> None:
    """Two URIs whose last segments match must not be given the same tag."""
    other = "http://example.com/other/skypeID"
    records = [
        header(),
        extension_record(FOAF, other),
        types.GedcomStructure(tag="TRLR"),
    ]
    gedcom7.generate_schema(records)
    tags = [c.text.split()[0] for c in records[0].children[1].children]
    assert tags == ["_SKYPEID", "_SKYPEID2"]
    reparsed = gedcom7.loads(gedcom7.dumps(records))
    assert [c.tag for c in reparsed[1].children] == [FOAF, other]


def test_generate_schema_avoids_colliding_with_a_literal_tag() -> None:
    """A tag used literally must not be made to stand for a URI as well.

    Were _SKYPEID already in the document as an undocumented extension tag,
    declaring it here would make that structure resolve to the URI on the way
    back in, silently changing what it means.
    """
    individual = extension_record(FOAF)
    individual.append_child(types.GedcomStructure(tag="_SKYPEID", text="unrelated"))
    records = [header(), individual, types.GedcomStructure(tag="TRLR")]
    gedcom7.generate_schema(records)

    assert records[0].children[1].children[0].text == f"_SKYPEID2 {FOAF}"
    reparsed = gedcom7.loads(gedcom7.dumps(records))
    assert [c.tag for c in reparsed[1].children] == [FOAF, "_SKYPEID"]


def test_generate_schema_without_anything_to_declare() -> None:
    """A document using no extensions gets no empty schema."""
    records = [
        header(),
        types.GedcomStructure(tag="INDI", xref="@I1@"),
        types.GedcomStructure(tag="TRLR"),
    ]
    gedcom7.generate_schema(records)
    assert [c.tag for c in records[0].children] == ["GEDC"]


def test_generate_schema_falls_back_when_the_uri_yields_no_name() -> None:
    """A URI whose last segment gives nothing usable still gets a tag."""
    records = [
        header(),
        extension_record("http://example.com/"),
        types.GedcomStructure(tag="TRLR"),
    ]
    gedcom7.generate_schema(records)
    assert records[0].children[1].children[0].text == "_EXT http://example.com/"


def test_generate_schema_needs_a_header() -> None:
    records = [types.GedcomStructure(tag="TRLR")]
    with pytest.raises(GedcomSerializeError, match="HEAD"):
        gedcom7.generate_schema(records)


def test_generate_schema_rejects_a_tag_that_is_no_uri_either() -> None:
    """A tag that is neither writable nor abbreviatable cannot be rescued."""
    records = [
        header(),
        extension_record("not a tag and not a uri"),
        types.GedcomStructure(tag="TRLR"),
    ]
    with pytest.raises(GedcomSerializeError, match="neither a tag"):
        gedcom7.generate_schema(records)


def test_generate_schema_places_the_schema_after_gedc() -> None:
    """The slot is deterministic, so regenerating a file does not reshuffle it."""
    records = [header(), extension_record(FOAF), types.GedcomStructure(tag="TRLR")]
    gedcom7.generate_schema(records)
    assert [c.tag for c in records[0].children] == ["GEDC", "SCHMA"]


def test_generate_schema_reproduces_the_corpus_declarations() -> None:
    """Stripping maximal70.ged's schema and regenerating it declares the same tags.

    The hand-written declarations in the official file are the check on the tag
    naming: a generated tag has to be the one a person would have picked.
    """
    filename = pathlib.Path(__file__).parent / "data" / "maximal70.ged"
    original = gedcom7.loads(filename.read_text(encoding="utf-8"))
    declarations = [
        definition.text
        for schema in original[0].children
        if schema.tag == "SCHMA"
        for definition in schema.children
    ]

    stripped = gedcom7.loads(filename.read_text(encoding="utf-8"))
    stripped[0].children = [c for c in stripped[0].children if c.tag != "SCHMA"]
    gedcom7.generate_schema(stripped)

    regenerated = [
        definition.text
        for schema in stripped[0].children
        if schema.tag == "SCHMA"
        for definition in schema.children
    ]
    assert regenerated == declarations
    # the schema moves to its deterministic slot, so the bytes differ, but every
    # extension tag has to resolve to the URI it stood for before
    assert gedcom7.loads(gedcom7.dumps(stripped)) == stripped


def test_generate_schema_touches_only_the_header() -> None:
    """The one structure that changes is HEAD, which gains the declarations.

    The structures carrying the URIs keep them as their tags; dumps does the
    abbreviating as it writes. Nothing else in the tree is rewritten, and the
    records list is not itself changed.
    """
    records = [header(), extension_record(FOAF), types.GedcomStructure(tag="TRLR")]

    def snapshot() -> dict[int, tuple[object, ...]]:
        seen: dict[int, tuple[object, ...]] = {}

        def visit(s: types.GedcomStructure) -> None:
            seen[id(s)] = (
                s.tag,
                s.pointer,
                s.text,
                s.xref,
                tuple(id(c) for c in s.children),
            )
            for child in s.children:
                visit(child)

        for record in records:
            visit(record)
        return seen

    before = snapshot()
    contents = [id(r) for r in records]
    gedcom7.generate_schema(records)
    after = snapshot()

    changed = [before[k][0] for k in before if after[k] != before[k]]
    assert changed == ["HEAD"]
    assert [id(r) for r in records] == contents
    # the extension structure still holds its URI, unabbreviated
    assert records[1].children[0].tag == FOAF
