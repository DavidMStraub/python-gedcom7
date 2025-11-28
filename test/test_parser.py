GEDCOM_MIN = """0 HEAD
1 GEDC
2 VERS 7.0
0 TRLR
"""

GEDCOM_EXTTAG = """0 HEAD
1 GEDC
2 VERS 7.0.0
1 SCHMA
2 TAG _FOO http://example.com/placeholder
0 @I1@ INDI
1 ALIA @I2@
1 _FOO 23
0 TRLR
"""

import pathlib

import gedcom7


def test_minimal():
    records = gedcom7.loads(GEDCOM_MIN)
    assert len(records) == 2
    record = records[0]
    assert record.tag == "HEAD"
    assert len(record.children) == 1
    assert record.children[0].parent == record
    assert len(record.children[0].children) == 1
    assert record.children[0].children[0].text == "7.0"
    record = records[1]
    assert record.tag == "TRLR"
    assert len(record.children) == 0

def test_maximal():
    filename = pathlib.Path(__file__).parent / "data" / "maximal70.ged"
    with open(filename, encoding="utf-8") as f:
        gedcom7.loads(f.read())

def test_exttag():
    records = gedcom7.loads(GEDCOM_EXTTAG)
    assert len(records) == 3
    assert records[1].children[1].tag == "http://example.com/placeholder"


GEDCOM_BLANK_CONT = """0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NOTE This is a note
2 CONT
2 CONT with a blank line above
0 TRLR
"""


def test_blank_cont_line():
    """Test that blank CONT lines are handled correctly."""
    records = gedcom7.loads(GEDCOM_BLANK_CONT)
    assert len(records) == 3
    indi = records[1]
    note = indi.children[0]
    assert note.tag == "NOTE"
    assert note.text == "This is a note\n\nwith a blank line above"


GEDCOM_EMPTY_VALUE = """0 HEAD
1 GEDC
2 VERS 7.0
0 @O1@ OBJE
1 FILE
2 FORM image/jpeg
0 TRLR
"""


def test_empty_line_value():
    """Test that lines with no value (like empty FILE) are handled correctly."""
    records = gedcom7.loads(GEDCOM_EMPTY_VALUE)
    assert len(records) == 3
    obje = records[1]
    file_struct = obje.children[0]
    assert file_struct.tag == "FILE"
    assert file_struct.text == ""
    assert file_struct.children[0].tag == "FORM"