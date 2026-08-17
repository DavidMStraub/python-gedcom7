"""Tests for reporting what is wrong with a dataset."""

import pathlib

import pytest

import gedcom7
from gedcom7 import GedcomValidationError, types

FOAF = "http://xmlns.com/foaf/0.1/skypeID"


def dataset(*records: types.GedcomStructure) -> list[types.GedcomStructure]:
    """A minimal conforming dataset wrapped around the given records."""
    head = types.GedcomStructure(tag="HEAD")
    gedc = types.GedcomStructure(tag="GEDC")
    head.append_child(gedc)
    gedc.append_child(types.GedcomStructure(tag="VERS", text="7.0"))
    return [head, *records, types.GedcomStructure(tag="TRLR")]


def individual(*children: types.GedcomStructure) -> types.GedcomStructure:
    record = types.GedcomStructure(tag="INDI", xref="@I1@")
    for child in children:
        record.append_child(child)
    return record


def categories(records: list[types.GedcomStructure]) -> list[str]:
    return sorted({error.category for error in gedcom7.validate(records)})


# --------------------------------------------------------------------------
# Nothing wrong
# --------------------------------------------------------------------------


def test_official_file_validates_clean() -> None:
    """The specification's own maximal file must report nothing."""
    filename = pathlib.Path(__file__).parent / "data" / "maximal70.ged"
    records = gedcom7.loads(filename.read_text(encoding="utf-8"))
    assert gedcom7.validate(records) == []


def test_minimal_dataset_validates_clean() -> None:
    assert gedcom7.validate(dataset(individual())) == []


# --------------------------------------------------------------------------
# Pointers
# --------------------------------------------------------------------------


def test_dangling_pointer() -> None:
    records = dataset(individual(types.GedcomStructure(tag="FAMS", pointer="@F9@")))
    assert categories(records) == ["dangling-pointer"]


def test_void_pointer_is_not_dangling() -> None:
    """@VOID@ deliberately points at nothing."""
    records = dataset(individual(types.GedcomStructure(tag="FAMS", pointer="@VOID@")))
    assert gedcom7.validate(records) == []


def test_pointer_at_the_wrong_record_type() -> None:
    """FAMS names a family, so pointing it at an individual is wrong."""
    other = types.GedcomStructure(tag="INDI", xref="@I2@")
    records = dataset(
        individual(types.GedcomStructure(tag="FAMS", pointer="@I2@")), other
    )
    assert categories(records) == ["pointer-target-type"]


def test_duplicate_xref() -> None:
    records = dataset(individual(), types.GedcomStructure(tag="INDI", xref="@I1@"))
    assert categories(records) == ["duplicate-xref"]


# --------------------------------------------------------------------------
# Document shape
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "records",
    [
        [types.GedcomStructure(tag="TRLR")],
        [types.GedcomStructure(tag="HEAD")],
        [
            types.GedcomStructure(tag="HEAD"),
            types.GedcomStructure(tag="HEAD"),
            types.GedcomStructure(tag="TRLR"),
        ],
        [
            types.GedcomStructure(tag="HEAD"),
            types.GedcomStructure(tag="INDI"),
            types.GedcomStructure(tag="TRLR"),
        ],
    ],
    ids=["no head", "no trlr", "two heads", "record without xref"],
)
def test_document_shape(records: list[types.GedcomStructure]) -> None:
    assert "document-shape" in categories(records)


def test_record_tag_that_is_not_a_record_type() -> None:
    """NAME is a substructure, not something that stands at level zero."""
    records = dataset(types.GedcomStructure(tag="NAME", xref="@X1@", text="John"))
    assert "document-shape" in categories(records)


def test_empty_dataset() -> None:
    assert categories([]) == ["document-shape"]


# --------------------------------------------------------------------------
# Payload kind
# --------------------------------------------------------------------------


def test_text_where_a_pointer_belongs() -> None:
    """The case format_value refuses for values, caught for hand-built trees."""
    records = dataset(individual(types.GedcomStructure(tag="FAMS", text="@F1@")))
    assert "misplaced-payload" in categories(records)


def test_pointer_where_text_belongs() -> None:
    records = dataset(individual(types.GedcomStructure(tag="SEX", pointer="@I2@")))
    assert categories(records) == ["misplaced-payload"]


def test_pointer_structure_with_no_pointer() -> None:
    records = dataset(individual(types.GedcomStructure(tag="FAMS")))
    assert categories(records) == ["misplaced-payload"]


def test_payload_on_a_structure_that_takes_none() -> None:
    records = dataset(individual(types.GedcomStructure(tag="BAPL", text="x")))
    assert categories(records) == ["misplaced-payload"]


# --------------------------------------------------------------------------
# Substructures
# --------------------------------------------------------------------------


def test_unknown_substructure() -> None:
    """A surname belongs under NAME, not under a birth."""
    birth = types.GedcomStructure(tag="BIRT")
    birth.append_child(types.GedcomStructure(tag="SURN", text="Doe"))
    assert categories(dataset(individual(birth))) == ["unknown-substructure"]


def test_extension_substructure_is_not_unknown() -> None:
    """An undocumented extension tag is permitted anywhere."""
    records = dataset(individual(types.GedcomStructure(tag="_MINE", text="x")))
    assert gedcom7.validate(records) == []


def test_substructure_of_an_extension_is_not_checked() -> None:
    """Below an extension the specification says nothing, so neither does this."""
    extension = types.GedcomStructure(tag="_MINE")
    extension.append_child(types.GedcomStructure(tag="SURN", text="Doe"))
    assert gedcom7.validate(dataset(individual(extension))) == []


# --------------------------------------------------------------------------
# Payload values
# --------------------------------------------------------------------------


def test_malformed_payload() -> None:
    birth = types.GedcomStructure(tag="BIRT")
    birth.append_child(types.GedcomStructure(tag="AGE", text="25x"))
    assert categories(dataset(individual(birth))) == ["malformed-payload"]


@pytest.mark.parametrize("text", ["32 JAN 2000", "0 JAN 2000", "30 FEB 2000"])
def test_day_outside_the_month(text: str) -> None:
    """The grammar allows any digits for a day, so the range is checked here."""
    birth = types.GedcomStructure(tag="BIRT")
    birth.append_child(types.GedcomStructure(tag="DATE", text=text))
    assert categories(dataset(individual(birth))) == ["invalid-date"]


def test_month_that_does_not_exist() -> None:
    birth = types.GedcomStructure(tag="BIRT")
    birth.append_child(types.GedcomStructure(tag="DATE", text="1 FOO 2000"))
    assert categories(dataset(individual(birth))) == ["invalid-date"]


def test_dates_inside_a_range_are_checked() -> None:
    birth = types.GedcomStructure(tag="BIRT")
    birth.append_child(
        types.GedcomStructure(tag="DATE", text="BET 1 JAN 2000 AND 32 JAN 2000")
    )
    assert categories(dataset(individual(birth))) == ["invalid-date"]


def test_other_calendars_keep_their_own_months() -> None:
    """TSH is a Hebrew month, and these tables only name the Gregorian ones."""
    birth = types.GedcomStructure(tag="BIRT")
    birth.append_child(types.GedcomStructure(tag="DATE", text="HEBREW 1 TSH 5760"))
    assert gedcom7.validate(dataset(individual(birth))) == []


def test_enumeration_values_are_not_checked() -> None:
    """A known gap: nothing here carries the vocabularies, so Q passes."""
    records = dataset(individual(types.GedcomStructure(tag="SEX", text="Q")))
    assert gedcom7.validate(records) == []


# --------------------------------------------------------------------------
# Schema
# --------------------------------------------------------------------------


def schema_dataset(*definitions: str) -> list[types.GedcomStructure]:
    records = dataset(individual(types.GedcomStructure(tag=FOAF, text="x")))
    schema = types.GedcomStructure(tag="SCHMA")
    for text in definitions:
        schema.append_child(types.GedcomStructure(tag="TAG", text=text))
    records[0].append_child(schema)
    return records


def test_two_tags_for_one_uri() -> None:
    """dumps would pick between them arbitrarily."""
    records = schema_dataset(f"_ONE {FOAF}", f"_TWO {FOAF}")
    assert categories(records) == ["schema-conflict"]


def test_two_uris_for_one_tag() -> None:
    """The parser refuses to resolve such a tag at all."""
    records = schema_dataset(f"_SAME {FOAF}", "_SAME http://example.com/other")
    assert "schema-conflict" in categories(records)


def test_undeclared_extension_tag() -> None:
    """dumps refuses this at write time; it is reported with everything else."""
    records = dataset(individual(types.GedcomStructure(tag=FOAF, text="x")))
    assert categories(records) == ["undeclared-extension"]


def test_declared_extension_tag_is_clean() -> None:
    assert gedcom7.validate(schema_dataset(f"_SKYPEID {FOAF}")) == []


# --------------------------------------------------------------------------
# The reported errors
# --------------------------------------------------------------------------


def test_error_says_where() -> None:
    """A list of problems is only useful if each names its structure."""
    birth = types.GedcomStructure(tag="BIRT")
    birth.append_child(types.GedcomStructure(tag="DATE", text="32 JAN 2000"))
    (error,) = gedcom7.validate(dataset(individual(birth)))
    assert error.path == "@I1@ INDI > BIRT > DATE"
    assert error.structure is birth.children[0]


def test_every_problem_is_reported_not_just_the_first() -> None:
    """The point of returning a list rather than raising."""
    birth = types.GedcomStructure(tag="BIRT")
    birth.append_child(types.GedcomStructure(tag="DATE", text="32 JAN 2000"))
    birth.append_child(types.GedcomStructure(tag="SURN", text="Doe"))
    records = dataset(
        individual(birth, types.GedcomStructure(tag="FAMS", pointer="@F9@"))
    )
    assert categories(records) == [
        "dangling-pointer",
        "invalid-date",
        "unknown-substructure",
    ]


# --------------------------------------------------------------------------
# dumps(validate=True)
# --------------------------------------------------------------------------


def test_dumps_does_not_validate_by_default() -> None:
    """Validation costs a full walk, so it stays opt-in."""
    records = dataset(individual(types.GedcomStructure(tag="FAMS", pointer="@F9@")))
    assert "1 FAMS @F9@" in gedcom7.dumps(records)


def test_dumps_validate_raises_with_every_error() -> None:
    birth = types.GedcomStructure(tag="BIRT")
    birth.append_child(types.GedcomStructure(tag="DATE", text="32 JAN 2000"))
    records = dataset(
        individual(birth, types.GedcomStructure(tag="FAMS", pointer="@F9@"))
    )
    with pytest.raises(GedcomValidationError) as caught:
        gedcom7.dumps(records, validate=True)
    assert sorted(e.category for e in caught.value.errors) == [
        "dangling-pointer",
        "invalid-date",
    ]


def test_dumps_validate_writes_a_clean_dataset() -> None:
    records = dataset(individual())
    assert gedcom7.dumps(records, validate=True, byte_order_mark=False).startswith(
        "0 HEAD"
    )
