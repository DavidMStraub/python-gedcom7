"""Tests for structure type resolution and payload casting."""

import logging

import pytest

import gedcom7
from gedcom7 import types

HEAD = "0 HEAD\n1 GEDC\n2 VERS 7.0\n"
TRLR = "0 TRLR\n"


def test_type_id_of_pseudostructures() -> None:
    """HEAD and TRLR are pseudo-structures, not records."""
    records = gedcom7.loads(HEAD + TRLR)
    assert records[0].type_id == "HEAD pseudostructure"
    assert records[-1].type_id == "TRLR pseudostructure"


def test_type_id_depends_on_superstructure() -> None:
    """The same tag denotes different structure types under different parents."""
    records = gedcom7.loads(
        HEAD + "0 @I1@ INDI\n1 ADOP\n2 FAMC @VOID@\n3 ADOP HUSB\n" + TRLR
    )
    adop = records[1].children[0]
    assert adop.type_id == "https://gedcom.io/terms/v7/ADOP"
    famc_adop = adop.children[0].children[0]
    assert famc_adop.type_id == "https://gedcom.io/terms/v7/FAMC-ADOP"


def test_type_id_of_extension_tag_is_its_uri() -> None:
    """A documented extension tag is identified by its URI."""
    records = gedcom7.loads(
        "0 HEAD\n1 SCHMA\n2 TAG _X http://example.com/x\n1 GEDC\n2 VERS 7.0\n"
        "0 @I1@ INDI\n1 _X hello\n" + TRLR
    )
    assert records[1].children[0].type_id == "http://example.com/x"


def test_value_casts_by_structure_type() -> None:
    """A payload is cast according to the structure type's payload type."""
    records = gedcom7.loads(
        HEAD + "0 @I1@ INDI\n1 BIRT\n2 DATE 1 JAN 2000\n2 PLAC Somewhere\n"
        "3 MAP\n4 LATI N18.150944\n4 LONG W168.150944\n"
        "1 NCHI 3\n" + TRLR
    )
    birt = records[1].children[0]
    assert birt.children[0].value == types.Date(day=1, month="JAN", year=2000)
    lati, long = birt.children[1].children[0].children
    assert lati.value == 18.150944
    assert long.value == -168.150944
    assert records[1].children[1].value == 3


def test_value_of_empty_payload_is_none() -> None:
    """Empty payloads and missing payloads are equivalent."""
    records = gedcom7.loads(HEAD + "0 @I1@ INDI\n1 BIRT\n" + TRLR)
    assert records[1].children[0].value is None


def test_value_of_payloadless_structure_type_is_none() -> None:
    """A structure type known to take no payload casts to None without warning."""
    records = gedcom7.loads(HEAD + "0 @I1@ INDI\n1 BIRT\n2 DATE 1 JAN 2000\n" + TRLR)
    assert records[1].value is None


def test_undocumented_extension_tag_has_no_type_id() -> None:
    """An undocumented extension tag is permitted but has no standard type."""
    records = gedcom7.loads(HEAD + "0 @I1@ INDI\n1 _UNDOCUMENTED payload\n" + TRLR)
    structure = records[1].children[0]
    assert structure.type_id is None
    # the payload's data type is the extension's to define, so it is not cast
    assert structure.value == "payload"


def test_extension_defined_substructure_has_no_type_id() -> None:
    """A standard tag under an extension structure is extension-defined."""
    records = gedcom7.loads(
        "0 HEAD\n1 SCHMA\n2 TAG _LOC http://example.com/loc\n1 GEDC\n2 VERS 7.0\n"
        "0 @P1@ _LOC\n1 NAME Byzantion\n2 DATE FROM 667 BCE TO 324\n" + TRLR
    )
    name = records[1].children[0]
    assert name.type_id is None
    assert name.value == "Byzantion"
    assert name.children[0].value == "FROM 667 BCE TO 324"


def test_unknown_structure_type_warns(caplog: pytest.LogCaptureFixture) -> None:
    """A documented extension URI with no known payload type is reported."""
    records = gedcom7.loads(
        "0 HEAD\n1 SCHMA\n2 TAG _X http://example.com/x\n1 GEDC\n2 VERS 7.0\n"
        "0 @I1@ INDI\n1 _X payload\n" + TRLR
    )
    structure = records[1].children[0]
    assert structure.type_id == "http://example.com/x"
    with caplog.at_level(logging.WARNING):
        assert structure.value is None
    assert "unknown structure type" in caplog.text


def test_parent_links() -> None:
    """Every substructure knows its superstructure; records have none."""
    records = gedcom7.loads(HEAD + "0 @I1@ INDI\n1 BIRT\n2 DATE 1 JAN 2000\n" + TRLR)
    indi = records[1]
    assert indi.parent is None
    assert indi.children[0].parent is indi
    assert indi.children[0].children[0].parent is indi.children[0]
